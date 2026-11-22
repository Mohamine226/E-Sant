from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Valeurs autorisées (contrôlées plus tard dans les schémas)
ROLES = ("agent", "district", "admin")
TYPES_FICHE = ("hebdo", "mensuel")
STATUTS = ("brouillon", "transmis")


class Csps(Base):
    __tablename__ = "csps"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    asbc_prevus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    utilisateurs: Mapped[list["Utilisateur"]] = relationship(back_populates="csps")
    fiches: Mapped[list["Fiche"]] = relationship(back_populates="csps")


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifiant: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nom_complet: Mapped[str] = mapped_column(String(120))
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="agent")
    csps_id: Mapped[Optional[int]] = mapped_column(ForeignKey("csps.id"), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    csps: Mapped[Optional["Csps"]] = relationship(back_populates="utilisateurs")


class Produit(Base):
    __tablename__ = "produits"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)       # PF001, PL003...
    designation: Mapped[str] = mapped_column(String(200))
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Fiche(Base):
    __tablename__ = "fiches"
    __table_args__ = (
        UniqueConstraint("csps_id", "type_fiche", "date_debut", name="uq_fiche_csps_type_debut"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    csps_id: Mapped[int] = mapped_column(ForeignKey("csps.id"))
    type_fiche: Mapped[str] = mapped_column(String(10))               # hebdo | mensuel
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date] = mapped_column(Date)
    observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    statut: Mapped[str] = mapped_column(String(12), default="brouillon")
    cree_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    transmis_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Identifiant généré sur le téléphone : évite les doublons lors de la synchro hors ligne
    client_uuid: Mapped[Optional[str]] = mapped_column(String(36), unique=True, nullable=True)

    csps: Mapped["Csps"] = relationship(back_populates="fiches")
    lignes: Mapped[list["LigneFiche"]] = relationship(
        back_populates="fiche", cascade="all, delete-orphan"
    )


class LigneFiche(Base):
    __tablename__ = "lignes_fiche"
    __table_args__ = (
        UniqueConstraint("fiche_id", "produit_id", name="uq_ligne_fiche_produit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fiche_id: Mapped[int] = mapped_column(ForeignKey("fiches.id", ondelete="CASCADE"))
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id"))
    dmeg_fs: Mapped[int] = mapped_column(Integer, default=0)
    asbc_plus_5km: Mapped[int] = mapped_column(Integer, default=0)
    nb_asbc_acr: Mapped[int] = mapped_column(Integer, default=0)

    fiche: Mapped["Fiche"] = relationship(back_populates="lignes")
    produit: Mapped["Produit"] = relationship()