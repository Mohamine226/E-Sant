from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pwdlib import PasswordHash

from .config import settings

_hasher = PasswordHash.recommended()


def hasher_mot_de_passe(motdepasse: str) -> str:
    return _hasher.hash(motdepasse)


def verifier_mot_de_passe(motdepasse: str, hash_enregistre: str) -> bool:
    return _hasher.verify(motdepasse, hash_enregistre)


def creer_token(utilisateur_id: int, role: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    charge = {"sub": str(utilisateur_id), "role": role, "exp": expiration}
    return jwt.encode(charge, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def lire_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None