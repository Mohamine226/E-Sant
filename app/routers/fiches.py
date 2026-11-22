import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..dependencies import exiger_roles, utilisateur_courant

router = APIRouter(prefix="/api/fiches", tags=["Fiches"])
district_ou_admin = exiger_roles("district", "admin")
# Seuls les agents CSPS remplissent les fiches ; district et admin consultent.
agent_seulement = exiger_roles("agent")


# ---------- Fonctions utiles ----------
def _maintenant() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fiche_ou_404(db: Session, fiche_id: int, utilisateur: models.Utilisateur) -> models.Fiche:
    """Charge la fiche avec ses lignes. Un agent ne voit que les fiches de son CSPS."""
    fiche = db.scalar(
        select(models.Fiche)
        .options(selectinload(models.Fiche.lignes).selectinload(models.LigneFiche.produit))
        .where(models.Fiche.id == fiche_id)
    )
    if fiche is None or (utilisateur.role == "agent" and fiche.csps_id != utilisateur.csps_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fiche introuvable")
    return fiche


def _exiger_brouillon(fiche: models.Fiche):
    if fiche.statut != "brouillon":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette fiche est déjà transmise et ne peut plus être modifiée",
        )


def _csps_de_la_fiche(
    db: Session, donnees: schemas.FicheCreate, utilisateur: models.Utilisateur
) -> int:
    if utilisateur.role == "agent":
        if utilisateur.csps_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ton compte n'est rattaché à aucun CSPS")
        csps_id = utilisateur.csps_id
    else:
        if donnees.csps_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Indique le CSPS concerné (csps_id)")
        csps_id = donnees.csps_id
    csps = db.get(models.Csps, csps_id)
    if csps is None or not csps.actif:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSPS introuvable ou inactif")
    return csps.id


def _bornes_periode(type_fiche: str, jour: date) -> tuple:
    """Semaine (lundi -> dimanche) ou mois qui contient `jour`."""
    if type_fiche == "mensuel":
        return jour.replace(day=1), jour.replace(day=calendar.monthrange(jour.year, jour.month)[1])
    lundi = jour - timedelta(days=jour.weekday())
    return lundi, lundi + timedelta(days=6)


def _verifier_doublon(
    db: Session, csps_id: int, type_fiche: str, date_debut: date, sauf_id: Optional[int] = None
):
    """Une seule fiche par CSPS et par semaine (ou par mois)."""
    debut, fin = _bornes_periode(type_fiche, date_debut)
    existante = db.scalar(
        select(models.Fiche).where(
            models.Fiche.csps_id == csps_id,
            models.Fiche.type_fiche == type_fiche,
            models.Fiche.date_debut >= debut,
            models.Fiche.date_debut <= fin,
            models.Fiche.id != (sauf_id or 0),
        )
    )
    if existante is not None:
        quand = "ce mois" if type_fiche == "mensuel" else "cette semaine"
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Une fiche existe déjà pour ce CSPS pour {quand} "
            f"(du {existante.date_debut:%d/%m/%Y} au {existante.date_fin:%d/%m/%Y})",
        )


def _verifier_produits(db: Session, lignes: list, autorises: Optional[set] = None):
    """Chaque produit doit exister et être actif (sauf ceux déjà présents dans la fiche)."""
    ids = {ligne.produit_id for ligne in lignes}
    actifs = set(
        db.scalars(
            select(models.Produit.id).where(
                models.Produit.id.in_(ids), models.Produit.actif.is_(True)
            )
        )
    )
    inconnus = ids - actifs - (autorises or set())
    if inconnus:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Produit(s) introuvable(s) ou inactif(s) : {sorted(inconnus)}",
        )


def _appliquer_lignes(fiche: models.Fiche, lignes_recues: list):
    """Met à jour les lignes existantes, ajoute les nouvelles, retire celles qui ne sont plus envoyées."""
    existantes = {ligne.produit_id: ligne for ligne in fiche.lignes}
    recues = set()
    for recue in lignes_recues:
        recues.add(recue.produit_id)
        ligne = existantes.get(recue.produit_id)
        if ligne is None:
            fiche.lignes.append(
                models.LigneFiche(
                    produit_id=recue.produit_id,
                    dmeg_fs=recue.dmeg_fs,
                    asbc_plus_5km=recue.asbc_plus_5km,
                    nb_asbc_acr=recue.nb_asbc_acr,
                )
            )
        else:
            ligne.dmeg_fs = recue.dmeg_fs
            ligne.asbc_plus_5km = recue.asbc_plus_5km
            ligne.nb_asbc_acr = recue.nb_asbc_acr
    for produit_id, ligne in existantes.items():
        if produit_id not in recues:
            fiche.lignes.remove(ligne)


def _enregistrer(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Cette fiche existe déjà (enregistrement en double)"
        )


# ---------- Routes ----------
@router.post("", response_model=schemas.FicheOut, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: schemas.FicheCreate,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(agent_seulement),
):
    # Même fiche renvoyée deux fois par le téléphone (synchro hors ligne) : on la rend telle quelle
    if donnees.client_uuid:
        deja = db.scalar(
            select(models.Fiche.id).where(models.Fiche.client_uuid == donnees.client_uuid)
        )
        if deja is not None:
            return _fiche_ou_404(db, deja, utilisateur)

    csps_id = _csps_de_la_fiche(db, donnees, utilisateur)
    _verifier_doublon(db, csps_id, donnees.type_fiche, donnees.date_debut)
    _verifier_produits(db, donnees.lignes)

    fiche = models.Fiche(
        csps_id=csps_id,
        type_fiche=donnees.type_fiche,
        date_debut=donnees.date_debut,
        date_fin=donnees.date_fin,
        observations=donnees.observations,
        statut="brouillon",
        cree_par_id=utilisateur.id,
        client_uuid=donnees.client_uuid,
    )
    _appliquer_lignes(fiche, donnees.lignes)
    db.add(fiche)
    _enregistrer(db)
    return _fiche_ou_404(db, fiche.id, utilisateur)


@router.get("", response_model=list[schemas.FicheResume])
def lister(
    type_fiche: Optional[schemas.TypeFiche] = None,
    statut: Optional[schemas.Statut] = None,
    csps_id: Optional[int] = None,
    du: Optional[date] = Query(default=None, description="Date de début à partir du"),
    au: Optional[date] = Query(default=None, description="Date de début jusqu'au"),
    limite: int = Query(default=50, ge=1, le=200),
    decalage: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(utilisateur_courant),
):
    requete = select(models.Fiche).order_by(
        models.Fiche.date_debut.desc(), models.Fiche.id.desc()
    )
    if utilisateur.role == "agent":
        requete = requete.where(models.Fiche.csps_id == utilisateur.csps_id)
    elif csps_id is not None:
        requete = requete.where(models.Fiche.csps_id == csps_id)
    if type_fiche:
        requete = requete.where(models.Fiche.type_fiche == type_fiche)
    if statut:
        requete = requete.where(models.Fiche.statut == statut)
    if du:
        requete = requete.where(models.Fiche.date_debut >= du)
    if au:
        requete = requete.where(models.Fiche.date_debut <= au)
    return db.scalars(requete.limit(limite).offset(decalage)).all()


@router.get("/{fiche_id}", response_model=schemas.FicheOut)
def lire(
    fiche_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(utilisateur_courant),
):
    return _fiche_ou_404(db, fiche_id, utilisateur)


@router.put("/{fiche_id}", response_model=schemas.FicheOut)
def modifier(
    fiche_id: int,
    donnees: schemas.FicheCreate,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(agent_seulement),
):
    fiche = _fiche_ou_404(db, fiche_id, utilisateur)
    _exiger_brouillon(fiche)
    _verifier_doublon(db, fiche.csps_id, donnees.type_fiche, donnees.date_debut, sauf_id=fiche.id)
    _verifier_produits(db, donnees.lignes, autorises={ligne.produit_id for ligne in fiche.lignes})

    fiche.type_fiche = donnees.type_fiche
    fiche.date_debut = donnees.date_debut
    fiche.date_fin = donnees.date_fin
    fiche.observations = donnees.observations
    _appliquer_lignes(fiche, donnees.lignes)
    _enregistrer(db)
    return _fiche_ou_404(db, fiche_id, utilisateur)


@router.post("/{fiche_id}/transmettre", response_model=schemas.FicheOut)
def transmettre(
    fiche_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(agent_seulement),
):
    fiche = _fiche_ou_404(db, fiche_id, utilisateur)
    _exiger_brouillon(fiche)
    fiche.statut = "transmis"
    fiche.transmis_le = _maintenant()
    _enregistrer(db)
    return _fiche_ou_404(db, fiche_id, utilisateur)


@router.post("/{fiche_id}/rouvrir", response_model=schemas.FicheOut)
def rouvrir(
    fiche_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(district_ou_admin),
):
    """Le district ou l'admin repasse une fiche transmise en brouillon (correction d'une erreur)."""
    fiche = _fiche_ou_404(db, fiche_id, utilisateur)
    if fiche.statut != "transmis":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette fiche n'est pas transmise")
    fiche.statut = "brouillon"
    fiche.transmis_le = None
    _enregistrer(db)
    return _fiche_ou_404(db, fiche_id, utilisateur)


@router.delete("/{fiche_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    fiche_id: int,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(agent_seulement),
):
    fiche = _fiche_ou_404(db, fiche_id, utilisateur)
    _exiger_brouillon(fiche)
    db.delete(fiche)
    db.commit()
