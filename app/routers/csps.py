from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import exiger_roles, utilisateur_courant

router = APIRouter(prefix="/api/csps", tags=["CSPS"])
admin_seulement = exiger_roles("admin")


def _csps_ou_404(db: Session, csps_id: int) -> models.Csps:
    csps = db.get(models.Csps, csps_id)
    if csps is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CSPS introuvable")
    return csps


def _verifier_nom_libre(db: Session, nom: str, sauf_id: Optional[int] = None):
    existant = db.scalar(select(models.Csps).where(models.Csps.nom == nom))
    if existant is not None and existant.id != sauf_id:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Le CSPS {nom} existe déjà")


@router.get("", response_model=list[schemas.CspsOut])
def lister(
    inclure_inactifs: bool = False,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(utilisateur_courant),
):
    requete = select(models.Csps).order_by(models.Csps.nom)
    if not (inclure_inactifs and utilisateur.role == "admin"):
        requete = requete.where(models.Csps.actif.is_(True))
    return db.scalars(requete).all()


@router.post("", response_model=schemas.CspsOut, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: schemas.CspsCreate,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    nom = donnees.nom.strip().upper()
    _verifier_nom_libre(db, nom)
    csps = models.Csps(nom=nom, asbc_prevus=donnees.asbc_prevus)
    db.add(csps)
    db.commit()
    db.refresh(csps)
    return csps


@router.patch("/{csps_id}", response_model=schemas.CspsOut)
def modifier(
    csps_id: int,
    donnees: schemas.CspsUpdate,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    csps = _csps_ou_404(db, csps_id)
    changements = donnees.model_dump(exclude_unset=True)
    if changements.get("nom"):
        changements["nom"] = changements["nom"].strip().upper()
        _verifier_nom_libre(db, changements["nom"], sauf_id=csps.id)
    for champ, valeur in changements.items():
        # asbc_prevus peut être remis à vide (None) ; les autres champs ne le peuvent pas
        if valeur is not None or champ == "asbc_prevus":
            setattr(csps, champ, valeur)
    db.commit()
    db.refresh(csps)
    return csps


@router.delete("/{csps_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    csps_id: int,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    csps = _csps_ou_404(db, csps_id)
    a_des_fiches = db.scalar(
        select(models.Fiche.id).where(models.Fiche.csps_id == csps.id).limit(1)
    )
    a_des_agents = db.scalar(
        select(models.Utilisateur.id).where(models.Utilisateur.csps_id == csps.id).limit(1)
    )
    if a_des_fiches is not None or a_des_agents is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ce CSPS a des fiches ou des agents : désactive-le au lieu de le supprimer",
        )
    db.delete(csps)
    db.commit()