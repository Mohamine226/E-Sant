from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import lire_token

schema_bearer = HTTPBearer(auto_error=False)


def utilisateur_courant(
    identifiants: Optional[HTTPAuthorizationCredentials] = Depends(schema_bearer),
    db: Session = Depends(get_db),
) -> models.Utilisateur:
    erreur = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Session invalide ou expirée",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if identifiants is None:
        raise erreur
    donnees = lire_token(identifiants.credentials)
    if not donnees:
        raise erreur
    utilisateur = db.get(models.Utilisateur, int(donnees["sub"]))
    if utilisateur is None or not utilisateur.actif:
        raise erreur
    return utilisateur


def exiger_roles(*roles: str):
    """Usage : Depends(exiger_roles("admin", "district"))"""

    def verifier(utilisateur: models.Utilisateur = Depends(utilisateur_courant)):
        if utilisateur.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé")
        return utilisateur

    return verifier