from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import exiger_roles, utilisateur_courant

router = APIRouter(prefix="/api/produits", tags=["Produits"])
admin_seulement = exiger_roles("admin")


def _produit_ou_404(db: Session, produit_id: int) -> models.Produit:
    produit = db.get(models.Produit, produit_id)
    if produit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit introuvable")
    return produit


def _verifier_code_libre(db: Session, code: str, sauf_id: Optional[int] = None):
    existant = db.scalar(select(models.Produit).where(models.Produit.code == code))
    if existant is not None and existant.id != sauf_id:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Le code {code} existe déjà")


@router.get("", response_model=list[schemas.ProduitOut])
def lister(
    inclure_inactifs: bool = False,
    db: Session = Depends(get_db),
    utilisateur: models.Utilisateur = Depends(utilisateur_courant),
):
    requete = select(models.Produit).order_by(models.Produit.ordre, models.Produit.id)
    if not (inclure_inactifs and utilisateur.role == "admin"):
        requete = requete.where(models.Produit.actif.is_(True))
    return db.scalars(requete).all()


@router.post("", response_model=schemas.ProduitOut, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: schemas.ProduitCreate,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    code = donnees.code.strip().upper()
    _verifier_code_libre(db, code)
    produit = models.Produit(
        code=code, designation=donnees.designation.strip(), ordre=donnees.ordre
    )
    db.add(produit)
    db.commit()
    db.refresh(produit)
    return produit


@router.patch("/{produit_id}", response_model=schemas.ProduitOut)
def modifier(
    produit_id: int,
    donnees: schemas.ProduitUpdate,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    produit = _produit_ou_404(db, produit_id)
    changements = donnees.model_dump(exclude_unset=True)
    if changements.get("code"):
        changements["code"] = changements["code"].strip().upper()
        _verifier_code_libre(db, changements["code"], sauf_id=produit.id)
    for champ, valeur in changements.items():
        if valeur is not None:
            setattr(produit, champ, valeur)
    db.commit()
    db.refresh(produit)
    return produit


@router.delete("/{produit_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    produit_id: int,
    db: Session = Depends(get_db),
    _: models.Utilisateur = Depends(admin_seulement),
):
    produit = _produit_ou_404(db, produit_id)
    utilise = db.scalar(
        select(models.LigneFiche.id).where(models.LigneFiche.produit_id == produit.id).limit(1)
    )
    if utilise is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ce produit est utilisé dans des fiches : désactive-le au lieu de le supprimer",
        )
    db.delete(produit)
    db.commit()