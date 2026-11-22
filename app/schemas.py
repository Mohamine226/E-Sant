from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Role = Literal["agent", "district", "admin"]
TypeFiche = Literal["hebdo", "mensuel"]
Statut = Literal["brouillon", "transmis"]


class SchemaBase(BaseModel):
    # Permet de convertir directement les objets SQLAlchemy en réponses JSON
    model_config = ConfigDict(from_attributes=True)


# ---------- CSPS ----------
class CspsCreate(SchemaBase):
    nom: str = Field(min_length=2, max_length=100)
    asbc_prevus: Optional[int] = Field(default=None, ge=0)


class CspsOut(CspsCreate):
    id: int
    actif: bool


# ---------- Produits ----------
class ProduitOut(SchemaBase):
    id: int
    code: str
    designation: str
    ordre: int
    actif: bool

class ProduitCreate(SchemaBase):
    code: str = Field(min_length=2, max_length=10)
    designation: str = Field(min_length=2, max_length=200)
    ordre: int = Field(default=0, ge=0)


class ProduitUpdate(SchemaBase):
    code: Optional[str] = Field(default=None, min_length=2, max_length=10)
    designation: Optional[str] = Field(default=None, min_length=2, max_length=200)
    ordre: Optional[int] = Field(default=None, ge=0)
    actif: Optional[bool] = None


class CspsUpdate(SchemaBase):
    nom: Optional[str] = Field(default=None, min_length=2, max_length=100)
    asbc_prevus: Optional[int] = Field(default=None, ge=0)
    actif: Optional[bool] = None


class UtilisateurUpdate(SchemaBase):
    nom_complet: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role: Optional[Role] = None
    csps_id: Optional[int] = None
    actif: Optional[bool] = None
    motdepasse: Optional[str] = Field(default=None, min_length=8, max_length=128)


# ---------- Utilisateurs ----------
class UtilisateurCreate(SchemaBase):
    identifiant: str = Field(min_length=3, max_length=50)
    nom_complet: str = Field(min_length=2, max_length=120)
    motdepasse: str = Field(min_length=8, max_length=72)  # 72 = limite de bcrypt
    role: Role = "agent"
    csps_id: Optional[int] = None

    @model_validator(mode="after")
    def agent_rattache_a_un_csps(self):
        if self.role == "agent" and self.csps_id is None:
            raise ValueError("Un agent doit être rattaché à un CSPS")
        return self


class UtilisateurOut(SchemaBase):
    id: int
    identifiant: str
    nom_complet: str
    role: Role
    csps_id: Optional[int]
    actif: bool


# ---------- Authentification ----------
class LoginIn(SchemaBase):
    identifiant: str
    motdepasse: str          # mêmes noms que ceux envoyés par login.js


class Token(SchemaBase):
    access_token: str
    token_type: str = "bearer"
    utilisateur: UtilisateurOut


# ---------- Fiches ----------
class LigneFicheIn(SchemaBase):
    produit_id: int
    dmeg_fs: int = Field(default=0, ge=0)
    asbc_plus_5km: int = Field(default=0, ge=0)
    nb_asbc_acr: int = Field(default=0, ge=0)


class LigneFicheOut(LigneFicheIn):
    id: int
    produit: ProduitOut


class FicheCreate(SchemaBase):
    type_fiche: TypeFiche
    date_debut: date
    date_fin: date
    observations: Optional[str] = Field(default=None, max_length=2000)
    client_uuid: Optional[str] = Field(default=None, min_length=36, max_length=36)
    csps_id: Optional[int] = None    # ignoré pour un agent (son CSPS est utilisé)
    lignes: list[LigneFicheIn] = Field(min_length=1)

    @model_validator(mode="after")
    def verifier(self):
        if self.date_fin < self.date_debut:
            raise ValueError("La date de fin doit être après la date de début")
        ids = [ligne.produit_id for ligne in self.lignes]
        if len(ids) != len(set(ids)):
            raise ValueError("Un produit apparaît plusieurs fois dans la fiche")
        return self


class FicheResume(SchemaBase):
    id: int
    csps_id: int
    type_fiche: TypeFiche
    date_debut: date
    date_fin: date
    statut: Statut
    transmis_le: Optional[datetime]


class FicheOut(FicheResume):
    observations: Optional[str]
    client_uuid: Optional[str]
    cree_le: datetime
    lignes: list[LigneFicheOut]