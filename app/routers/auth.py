from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import utilisateur_courant
from ..security import creer_token, verifier_mot_de_passe

router = APIRouter(prefix="/api/auth", tags=["Authentification"])


@router.post("/login", response_model=schemas.Token)
def login(donnees: schemas.LoginIn, db: Session = Depends(get_db)):
    utilisateur = db.scalar(
        select(models.Utilisateur).where(
            models.Utilisateur.identifiant == donnees.identifiant
        )
    )
    if (
        utilisateur is None
        or not utilisateur.actif
        or not verifier_mot_de_passe(donnees.motdepasse, utilisateur.mot_de_passe_hash)
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect"
        )
    return {
        "access_token": creer_token(utilisateur.id, utilisateur.role),
        "token_type": "bearer",
        "utilisateur": utilisateur,
    }


@router.get("/me", response_model=schemas.UtilisateurOut)
def moi(utilisateur: models.Utilisateur = Depends(utilisateur_courant)):
    return utilisateur