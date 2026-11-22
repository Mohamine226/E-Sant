import { api, deconnecter, echapper, formaterDate, formaterDateHeure } from "./api.js";
import { monterLayout, toast } from "./layout.js";

const moi = monterLayout({ actif: "fiches", titre: "Historique des fiches" });
const zone = document.getElementById("zone");
const fType = document.getElementById("f-type");
const fStatut = document.getElementById("f-statut");
const fCsps = document.getElementById("f-csps");
const fDu = document.getElementById("f-du");
const fAu = document.getElementById("f-au");
let listeCsps = [];
let fiches = [];

const nomCsps = (id) => (listeCsps.find((c) => c.id === id) || {}).nom || `CSPS ${id}`;

async function charger() {
  zone.innerHTML = `<p class="chargement">Chargement…</p>`;
  const p = new URLSearchParams({ limite: "200" });
  if (fType.value) p.set("type_fiche", fType.value);
  if (fStatut.value) p.set("statut", fStatut.value);
  if (fCsps.value && moi.role !== "agent") p.set("csps_id", fCsps.value);
  if (fDu.value) p.set("du", fDu.value);
  if (fAu.value) p.set("au", fAu.value);
  try {
    fiches = await api(`/api/fiches?${p}`);
    afficher();
  } catch (e) {
    zone.innerHTML = `<p class="erreur">${echapper(e.message)}</p>`;
  }
}

const MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
  "septembre", "octobre", "novembre", "décembre"];

// Semaine -> lundi de la semaine ; mensuelle -> "AAAA-MM". Sert à ranger les fiches par période.
function cle(f) {
  if (f.type_fiche === "mensuel") return "M" + f.date_debut.slice(0, 7);
  const [a, m, j] = f.date_debut.split("-").map(Number);
  const d = new Date(Date.UTC(a, m - 1, j));
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return "S" + d.toISOString().slice(0, 10);
}

function titrePeriode(k) {
  if (k[0] === "M") {
    const [a, m] = k.slice(1).split("-");
    return `Mois de ${MOIS[Number(m) - 1]} ${a}`;
  }
  const lundi = k.slice(1);
  const d = new Date(lundi + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + 6);
  return `Semaine du ${formaterDate(lundi)} au ${formaterDate(d.toISOString().slice(0, 10))}`;
}

function afficher() {
  if (!fiches.length) {
    zone.innerHTML = `<p class="vide">Aucune fiche pour le moment.</p>`;
    return;
  }
  const staff = moi.role !== "agent";
  const totalCsps = listeCsps.filter((c) => c.actif).length;

  const groupes = new Map();
  for (const f of fiches) {
    const k = cle(f);
    if (!groupes.has(k)) groupes.set(k, []);
    groupes.get(k).push(f);
  }
  // semaines et mois de la plus récente à la plus ancienne
  const ordre = [...groupes.keys()].sort((x, y) => {
    const dx = x[0] === "M" ? x.slice(1) + "-01" : x.slice(1);
    const dy = y[0] === "M" ? y.slice(1) + "-01" : y.slice(1);
    return dy.localeCompare(dx) || x.localeCompare(y);
  });

  zone.innerHTML = ordre.map((k) => {
    const liste = groupes.get(k).sort((a, b) => nomCsps(a.csps_id).localeCompare(nomCsps(b.csps_id)));
    const transmises = liste.filter((f) => f.statut === "transmis").length;
    const resume = staff && totalCsps
      ? `${transmises} / ${totalCsps} CSPS ont transmis`
      : `${transmises} transmise(s) sur ${liste.length}`;
    const lignes = liste.map((f) => {
      const brouillon = f.statut === "brouillon";
      const boutons = [
        `<a class="btn-leger" href="/pages/saisie.html?id=${f.id}">${brouillon && !staff ? "Modifier" : "Voir"}</a>`,
        brouillon && !staff ? `<button class="btn-leger danger" data-action="supprimer" data-id="${f.id}">Supprimer</button>` : "",
        !brouillon && staff ? `<button class="btn-leger" data-action="rouvrir" data-id="${f.id}">Rouvrir</button>` : "",
      ].join("");
      return `<tr>
        ${staff ? `<td>${echapper(nomCsps(f.csps_id))}</td>` : ""}
        <td>${formaterDate(f.date_debut)} → ${formaterDate(f.date_fin)}</td>
        <td><span class="badge-statut ${brouillon ? "inactif" : "actif"}">${brouillon ? "Brouillon" : "Transmis"}</span></td>
        <td>${f.transmis_le ? formaterDateHeure(f.transmis_le) : "—"}</td>
        <td><div class="actions">${boutons}</div></td></tr>`;
    }).join("");
    return `<section class="periode">
      <h3>${echapper(titrePeriode(k))} <small>${echapper(resume)}</small></h3>
      <div class="table-wrap"><table>
        <thead><tr>${staff ? "<th>CSPS</th>" : ""}<th>Période saisie</th><th>Statut</th><th>Transmis le</th><th>Actions</th></tr></thead>
        <tbody>${lignes}</tbody></table></div></section>`;
  }).join("");
}

zone.addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-action]");
  if (!b) return;
  const id = Number(b.dataset.id);
  try {
    if (b.dataset.action === "supprimer") {
      if (!confirm("Supprimer ce brouillon ? Cette action est définitive.")) return;
      await api(`/api/fiches/${id}`, { methode: "DELETE" });
      toast("Brouillon supprimé");
    } else {
      if (!confirm("Rouvrir cette fiche ? L'agent pourra la modifier à nouveau.")) return;
      await api(`/api/fiches/${id}/rouvrir`, { methode: "POST" });
      toast("Fiche rouverte");
    }
    await charger();
  } catch (e) {
    toast(e.message, "erreur");
  }
});

[fType, fStatut, fCsps, fDu, fAu].forEach((s) => s.addEventListener("change", charger));

const eType = document.getElementById("export-type");
const eJour = document.getElementById("export-jour");

function majAideExport() {
  const mensuel = eType.value === "mensuel";
  document.getElementById("lib-export-jour").textContent = mensuel ? "Un jour du mois" : "Un jour de la semaine";
  document.getElementById("aide-export").textContent = eJour.value
    ? `Période exportée : ${titrePeriode(cle({ type_fiche: eType.value, date_debut: eJour.value })).replace(/^./, (c) => c.toLowerCase())}`
    : "Choisis une date : le fichier couvre toute la semaine ou tout le mois qui la contient.";
}
[eType, eJour].forEach((x) => x.addEventListener("change", majAideExport));

async function exporter() {
  if (!eJour.value) return toast("Choisis une date pour la semaine ou le mois à exporter", "erreur");
  const p = new URLSearchParams({ type_fiche: eType.value, jour: eJour.value });
  if (document.getElementById("export-brouillons").checked) p.set("statut", "tous");
  const bouton = document.getElementById("btn-export");
  bouton.disabled = true;
  try {
    const rep = await fetch(`/api/export/fiches?${p}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });
    if (rep.status === 401) return deconnecter();
    if (!rep.ok) {
      const d = await rep.json().catch(() => null);
      throw new Error((d && typeof d.detail === "string" && d.detail) || `Erreur ${rep.status}`);
    }
    const nom = /filename="([^"]+)"/.exec(rep.headers.get("Content-Disposition") || "")?.[1] || "fiches.xlsx";
    const url = URL.createObjectURL(await rep.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: nom });
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("Export téléchargé");
  } catch (e) {
    toast(e.message, "erreur");
  } finally {
    bouton.disabled = false;
  }
}

(async () => {
  if (moi.role !== "agent") {
    document.getElementById("bloc-f-dates").hidden = false;
    document.getElementById("barre-export").hidden = false;
    document.getElementById("btn-export").addEventListener("click", exporter);
    eJour.value = new Date().toISOString().slice(0, 10);
    majAideExport();
  }
  if (moi.role === "agent") {
    document.querySelector(".lien-bouton").hidden = false;
  } else {
    try {
      listeCsps = await api("/api/csps?inclure_inactifs=true");
      listeCsps.forEach((c) => fCsps.insertAdjacentHTML("beforeend", `<option value="${c.id}">${echapper(c.nom)}</option>`));
      document.getElementById("bloc-f-csps").hidden = false;
    } catch { /* filtre CSPS indisponible */ }
  }
  charger();
})();
