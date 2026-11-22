from sqlalchemy import select

from . import models
from .config import settings
from .database import Base, SessionLocal, engine
from .security import hasher_mot_de_passe

PRODUITS = [
    ("PF001", "Condom Féminin"),
    ("PF002", "Condom masculin"),
    ("PF003", "SAYANA PRESS"),
    ("PF004", "Microgynon/Zinnia F"),
    ("PF005", "Microlut"),
    ("MMR01", "Amoxicilline 250 mg cp dispersible"),
    ("MMR02", "Kit SRO/Zinc, kit"),
    ("PL001", "Artésunate + Pyronaridine (20mg + 60mg) sachets"),
    ("PL002", "Artésunate + Pyronaridine (60mg + 180mg) blisters de 3x3 comprimés"),
    ("PL003", "Test de diagnostic rapide (TDR) du paludisme"),
    ("PL004", "Sulfadoxine + Pyriméthamine (500+25) mg comprimé blister de 3"),
    ("PL005", "Artesunate 100 mg suppositoire"),
]

CSPS = [
    "BEUN", "BIEHA", "BON", "BOURA", "BOZO", "BREDIE", "DANFI DAGARA", "DABIOU",
    "DIO", "GORI", "KAYERO", "KELIE", "KELINDOU", "KOALGA", "KONZIO", "KOUMBOGORO",
    "LIVARA", "LONGA", "LORO", "LOGO", "NAPARO", "NEBIEL", "NIABOURI", "PINA",
    "PISSAI", "POIN", "POUPOUROU", "PRATA", "SAADON", "SANGA", "SECTEUR1",
    "SECTEUR3", "SECTEUR5", "SILLY", "SISSILI", "TABOU", "TIESSOUROU", "TO",
    "TONON", "YA", "YELBOUGA", "YORO", "ZAMOUNA", "ZINOU",
]


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        codes = set(db.scalars(select(models.Produit.code)))
        for ordre, (code, designation) in enumerate(PRODUITS, start=1):
            if code not in codes:
                db.add(models.Produit(code=code, designation=designation, ordre=ordre))

        noms = set(db.scalars(select(models.Csps.nom)))
        for nom in CSPS:
            if nom not in noms:
                db.add(models.Csps(nom=nom))
        db.commit()

        admin = db.scalar(
            select(models.Utilisateur).where(models.Utilisateur.role == "admin")
        )
        if admin is None:
            identifiant = settings.ADMIN_IDENTIFIANT.strip()
            motdepasse = settings.ADMIN_MOTDEPASSE
            if len(identifiant) < 3 or len(motdepasse) < 8:
                raise SystemExit(
                    "Renseigne ADMIN_IDENTIFIANT et ADMIN_MOTDEPASSE "
                    "(8 caractères minimum) dans le .env"
                )
            db.add(
                models.Utilisateur(
                    identifiant=identifiant,
                    nom_complet=settings.ADMIN_NOM.strip(),
                    mot_de_passe_hash=hasher_mot_de_passe(motdepasse),
                    role="admin",
                )
            )
            db.commit()
            print(f"Compte admin créé : {identifiant}")
        print("Données de départ prêtes.")


if __name__ == "__main__":
    main()