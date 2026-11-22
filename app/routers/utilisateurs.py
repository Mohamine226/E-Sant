from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import exiger_roles
from ..security import hasher_mot_de_passe

router = APIRouter(prefix="/api/utilisateurs", tags=["Utilisateurs"])
admin_seulement = exiger_roles("admin")


def _verifier_csps(db: Session, csps_id: int):
    csps = db.get(models.Csps, csps_id)
    if csps is None or not csps.actif:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSPS introuvable ou inactif")


@router.get("", response_model=list[schemas.UtilisateurOut])
def lister(
    role: Optional[str] = None,
    csps_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    requete = select(models.Utilisateur).order_by(models.Utilisateur.nom_complet)
    if role:
        requete = requete.where(models.Utilisateur.role == role)
    if csps_id:
        requete = requete.where(models.Utilisateur.csps_id == csps_id)
    return db.scalars(requete).all()


@router.post("", response_model=schemas.UtilisateurOut, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: schemas.UtilisateurCreate,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    identifiant = donnees.identifiant.strip()
    deja = db.scalar(
        select(models.Utilisateur.id).where(models.Utilisateur.identifiant == identifiant)
    )
    if deja is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet identifiant existe déjà")
    if donnees.csps_id is not None:
        _verifier_csps(db, donnees.csps_id)

    utilisateur = models.Utilisateur(
        identifiant=identifiant,
        nom_complet=donnees.nom_complet.strip(),
        mot_de_passe_hash=hasher_mot_de_passe(donnees.motdepasse),
        role=donnees.role,
        csps_id=donnees.csps_id,
    )
    db.add(utilisateur)
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.patch("/{utilisateur_id}", response_model=schemas.UtilisateurOut)
def modifier(
    utilisateur_id: int,
    donnees: schemas.UtilisateurUpdate,
    db: Session = Depends(get_db),
    admin: models.Utilisateur = Depends(admin_seulement),
):
    utilisateur = db.get(models.Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")

    changements = donnees.model_dump(exclude_unset=True)

    if utilisateur.id == admin.id and (
        changements.get("actif") is False
        or ("role" in changements and changements["role"] != "admin")
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Tu ne peux pas désactiver ton propre compte ni retirer ton rôle admin",
        )

    motdepasse = changements.pop("motdepasse", None)
    if motdepasse is not None:
        utilisateur.mot_de_passe_hash = hasher_mot_de_passe(motdepasse)

    for champ, valeur in changements.items():
        # csps_id peut être remis à vide (None) ; les autres champs ne le peuvent pas
        if valeur is not None or champ == "csps_id":
            setattr(utilisateur, champ, valeur)

    if utilisateur.role == "agent":
        if utilisateur.csps_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Un agent doit être rattaché à un CSPS"
            )
        _verifier_csps(db, utilisateur.csps_id)

    db.commit()
    db.refresh(utilisateur)
    return utilisateur