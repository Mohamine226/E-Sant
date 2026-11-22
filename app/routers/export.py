import calendar
import io
from datetime import date, timedelta
from typing import Literal, Optional

import xlsxwriter
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..dependencies import exiger_roles

router = APIRouter(prefix="/api/export", tags=["Export"])

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
CHAMPS = [("dmeg_fs", "DMEG / FS"), ("asbc_plus_5km", "ASBC PLUS 5 km"), ("nb_asbc_acr", "Nb ASBC ACR")]


def _periode(f: models.Fiche):
    """Clé de regroupement (même règle que l'historique) : lundi de la semaine, ou mois."""
    if f.type_fiche == "mensuel":
        return (f.date_debut.year, f.date_debut.month)
    return f.date_debut - timedelta(days=f.date_debut.weekday())


def _titre(f_type: str, cle) -> str:
    if f_type == "mensuel":
        return f"Mois de {MOIS[cle[1] - 1]} {cle[0]}"
    fin = cle + timedelta(days=6)
    return f"Semaine du {cle:%d/%m/%Y} au {fin:%d/%m/%Y}"


def _nom_feuille(f_type: str, cle, deja: set) -> str:
    if f_type == "mensuel":
        base = f"{MOIS[cle[1] - 1].capitalize()} {cle[0]}"
    else:
        base = f"{cle:%d-%m} au {cle + timedelta(days=6):%d-%m-%Y}"
    nom, n = base, 2
    while nom in deja:
        nom, n = f"{base} ({n})", n + 1
    deja.add(nom)
    return nom


@router.get("/fiches")
def exporter_fiches(
    type_fiche: schemas.TypeFiche = Query(description="hebdo ou mensuel"),
    jour: date = Query(description="Un jour quelconque de la semaine ou du mois à exporter"),
    statut: Literal["transmis", "tous"] = "transmis",
    db: Session = Depends(get_db),
    _=Depends(exiger_roles("district", "admin")),
):
    """Fichier Excel d'UNE semaine (lundi -> dimanche) ou d'UN mois : produits en lignes, CSPS en colonnes."""
    if type_fiche == "mensuel":
        debut = jour.replace(day=1)
        fin = jour.replace(day=calendar.monthrange(jour.year, jour.month)[1])
    else:
        debut = jour - timedelta(days=jour.weekday())
        fin = debut + timedelta(days=6)
    requete = (
        select(models.Fiche)
        .options(selectinload(models.Fiche.lignes))
        .where(models.Fiche.type_fiche == type_fiche)
    )
    if statut == "transmis":
        requete = requete.where(models.Fiche.statut == "transmis")
    requete = requete.where(models.Fiche.date_debut >= debut, models.Fiche.date_debut <= fin)
    fiches = db.scalars(requete).all()
    if not fiches:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aucune fiche {'transmise ' if statut == 'transmis' else ''}pour la période du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}")

    csps_tous = db.scalars(select(models.Csps).order_by(models.Csps.nom)).all()
    csps_nom = {c.id: c.nom for c in csps_tous}
    produits_tous = db.scalars(
        select(models.Produit).order_by(models.Produit.ordre, models.Produit.id)
    ).all()
    utilises = {l.produit_id for f in fiches for l in f.lignes}
    produits = [p for p in produits_tous if p.actif or p.id in utilises]

    groupes: dict = {}
    for f in fiches:
        groupes.setdefault(_periode(f), []).append(f)

    flux = io.BytesIO()
    classeur = xlsxwriter.Workbook(flux, {"in_memory": True})
    fmt = lambda **k: classeur.add_format({"font_name": "Calibri", "font_size": 11, **k})
    f_titre = fmt(bold=True, font_size=14, font_color="#0b3a6e")
    f_entete = fmt(bold=True, align="center", valign="vcenter", text_wrap=True,
                   bg_color="#6a5ce8", font_color="#FFFFFF", border=1)
    f_sous = fmt(bold=True, align="center", valign="vcenter", text_wrap=True, bg_color="#ecebff", border=1)
    f_texte = fmt(border=1)
    f_nombre = fmt(border=1, align="center")
    f_absent = fmt(border=1, font_color="#98a2b3", italic=True)
    f_obs = fmt(border=1, text_wrap=True, valign="top")
    f_centre_texte = fmt(border=1, align="center", font_size=9)
    f_total_l = fmt(bold=True, border=1, bg_color="#dde3ee")
    f_total_n = fmt(bold=True, border=1, align="center", bg_color="#dde3ee")

    noms_utilises: set = set()
    for cle in sorted(groupes, reverse=True):
        liste = groupes[cle]
        par_csps = {}
        for f in liste:
            # en cas de plusieurs fiches du même CSPS dans la période : la plus récente
            if f.csps_id not in par_csps or f.date_debut > par_csps[f.csps_id].date_debut:
                par_csps[f.csps_id] = f
        ids = [c.id for c in csps_tous if c.actif or c.id in par_csps]

        ws = classeur.add_worksheet(_nom_feuille(type_fiche, cle, noms_utilises))
        ws.write(0, 0, f"E-Santé — Fiche de stock {'mensuelle' if type_fiche == 'mensuel' else 'hebdomadaire'}", f_titre)
        ws.write(1, 0, _titre(type_fiche, cle))

        # Produits en lignes (vertical), CSPS en colonnes (horizontal, 3 colonnes chacun)
        ligne_ent, ligne_sous, premiere = 3, 4, 5
        derniere = premiere + len(produits) - 1
        ws.merge_range(ligne_ent, 0, ligne_sous, 0, "Produit", f_entete)
        colonnes_csps = {}
        col = 1
        for cid in ids:
            ws.merge_range(ligne_ent, col, ligne_ent, col + 2, csps_nom[cid], f_entete)
            for i, (_, libelle) in enumerate(CHAMPS):
                ws.write(ligne_sous, col + i, libelle, f_sous)
            colonnes_csps[cid] = col
            col += 3
        col_total = col
        ws.merge_range(ligne_ent, col_total, ligne_ent, col_total + 2, "TOTAL", f_entete)
        for i, (_, libelle) in enumerate(CHAMPS):
            ws.write(ligne_sous, col_total + i, libelle, f_sous)

        valeurs = {
            cid: {l.produit_id: l for l in par_csps[cid].lignes} for cid in ids if cid in par_csps
        }
        for n, p in enumerate(produits):
            r = premiere + n
            ws.write(r, 0, p.designation, f_texte)
            for cid, c0 in colonnes_csps.items():
                for i, (champ, _) in enumerate(CHAMPS):
                    if cid in valeurs:
                        ligne = valeurs[cid].get(p.id)
                        ws.write_number(r, c0 + i, getattr(ligne, champ) if ligne else 0, f_nombre)
                    else:
                        ws.write_blank(r, c0 + i, None, f_nombre)
            for i, (champ, _) in enumerate(CHAMPS):
                cellules = ",".join(
                    f"{xlsxwriter.utility.xl_rowcol_to_cell(r, c0 + i)}" for c0 in colonnes_csps.values()
                )
                somme = sum(
                    getattr(valeurs[cid].get(p.id), champ, 0) if valeurs[cid].get(p.id) else 0
                    for cid in valeurs
                )
                ws.write_formula(r, col_total + i, f"=SUM({cellules})", f_total_n, somme)

        # Lignes d'information sous le tableau : statut, période saisie, observations
        r_info = derniere + 2
        infos = [("Statut", 18), ("Période saisie", 18), ("Observations", 60)]
        for k, (titre, haut) in enumerate(infos):
            r = r_info + k
            ws.write(r, 0, titre, f_total_l)
            ws.set_row(r, haut)
            for cid, c0 in colonnes_csps.items():
                f = par_csps.get(cid)
                if k == 0:
                    texte = ("Transmis" if f.statut == "transmis" else "Brouillon") if f else "Non transmis"
                    style = f_texte if f else f_absent
                elif k == 1:
                    texte = f"{f.date_debut:%d/%m/%Y} → {f.date_fin:%d/%m/%Y}" if f else ""
                    style = f_centre_texte
                else:
                    texte = (f.observations or "") if f else ""
                    style = f_obs
                ws.merge_range(r, c0, r, c0 + 2, texte, style)
            transmis = sum(1 for cid in ids if cid in par_csps and par_csps[cid].statut == "transmis")
            ws.merge_range(r, col_total, r, col_total + 2,
                           f"{transmis} / {len(ids)} CSPS" if k == 0 else "", f_total_l)

        ws.set_column(0, 0, 34)
        ws.set_column(1, col_total + 2, 12)
        ws.set_row(ligne_ent, 34)
        ws.set_row(ligne_sous, 30)
        ws.freeze_panes(premiere, 1)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)

    classeur.close()
    flux.seek(0)
    genre = "mensuel" if type_fiche == "mensuel" else "semaine"
    nom = f"E-Sante_stock_{genre}_du_{debut:%d-%m-%Y}_au_{fin:%d-%m-%Y}.xlsx"
    return StreamingResponse(
        flux,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
