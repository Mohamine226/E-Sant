import { api, echapper, formaterDate } from "./api.js";
import { monterLayout, toast } from "./layout.js";

const moi = monterLayout({ actif: "saisie", titre: "Fiche de stock" })
if (moi.role !== "agent" && !new URLSearchParams(location.search).get("id")) {
  location.href = "/pages/fiches.html"; // le district et l'admin consultent, ils ne remplissent pas
};
const idFiche = new URLSearchParams(location.search).get("id");

const el = (id) => document.getElementById(id);
const champs = {
  csps: el("csps"), type: el("type"), debut: el("debut"), fin: el("fin"), obs: el("obs"),
};
let produits = [];
let fiche = null; // fiche existante (modification)

const iso = (d) => d.toISOString().slice(0, 10);
function calculerFin() {
  if (!champs.debut.value) return;
  const [a, m, j] = champs.debut.value.split("-").map(Number);
  const fin = champs.type.value === "mensuel"
    ? new Date(Date.UTC(a, m, 0))            // dernier jour du mois
    : new Date(Date.UTC(a, m - 1, j + 6));   // début + 6 jours
  champs.fin.value = iso(fin);
}
function majAide() {
  el("aide-periode").textContent = champs.type.value === "mensuel"
    ? "Mensuelle : du 1er au dernier jour du mois."
    : "Hebdomadaire : du premier au dernier jour de la semaine (7 jours).";
}
champs.type.addEventListener("change", () => { majAide(); calculerFin(); });
champs.debut.addEventListener("change", calculerFin);

function afficherProduits(lignes = []) {
  const parId = new Map(lignes.map((l) => [l.produit_id, l]));
  el("zone-produits").innerHTML = `
    <div class="table-wrap"><table class="table-saisie">
      <thead><tr><th>Produit</th><th>DMEG / FS</th><th>ASBC PLUS 5 km</th><th>Nb ASBC ACR</th></tr></thead>
      <tbody>${produits.map((p) => {
        const l = parId.get(p.id) || {};
        const champ = (nom, lib) =>
          `<td data-label="${lib}"><input type="number" min="0" step="1" inputmode="numeric"
             data-produit="${p.id}" data-champ="${nom}" value="${l[nom] ?? 0}" aria-label="${echapper(p.designation)} ${lib}"></td>`;
        return `<tr><th scope="row">${echapper(p.designation)}</th>
          ${champ("dmeg_fs", "DMEG / FS")}${champ("asbc_plus_5km", "ASBC PLUS 5 km")}${champ("nb_asbc_acr", "Nb ASBC ACR")}</tr>`;
      }).join("")}</tbody>
    </table></div>`;
}

function lireLignes() {
  const lignes = new Map();
  document.querySelectorAll("[data-produit]").forEach((i) => {
    const id = Number(i.dataset.produit);
    if (!lignes.has(id)) lignes.set(id, { produit_id: id });
    lignes.get(id)[i.dataset.champ] = i.value === "" ? 0 : Number(i.value);
  });
  return [...lignes.values()];
}

function montrerErreur(msg) {
  el("erreur").textContent = msg;
  el("erreur").hidden = !msg;
}

function bloquerSiTransmise() {
  const lectureSeule = moi.role !== "agent";
  const verrou = lectureSeule || (fiche && fiche.statut === "transmis");
  document.querySelector(".barre-fiche").hidden = lectureSeule;
  document.querySelectorAll("#form-fiche input, #form-fiche select, #form-fiche textarea, #form-fiche button")
    .forEach((x) => { x.disabled = verrou; });
  const info = el("info-statut");
  info.hidden = !fiche;
  if (fiche) {
    info.textContent = lectureSeule
      ? "Consultation seule."
      : verrou
      ? "Fiche transmise : elle n'est plus modifiable."
      : "Brouillon — pas encore transmis.";
  }
}

function corps() {
  const c = {
    type_fiche: champs.type.value,
    date_debut: champs.debut.value,
    date_fin: champs.fin.value,
    observations: champs.obs.value.trim() || null,
    lignes: lireLignes(),
  };
  if (moi.role !== "agent") c.csps_id = Number(champs.csps.value) || null;
  if (!fiche) c.client_uuid = crypto.randomUUID?.() ?? undefined;
  return c;
}

async function enregistrer(transmettre) {
  montrerErreur("");
  if (!champs.debut.value || !champs.fin.value) return montrerErreur("Indique la période (du … au …).");
  const boutons = document.querySelectorAll(".barre-fiche button");
  boutons.forEach((b) => (b.disabled = true));
  try {
    const c = corps();
    fiche = fiche
      ? await api(`/api/fiches/${fiche.id}`, { methode: "PUT", corps: c })
      : await api("/api/fiches", { methode: "POST", corps: c });
    if (transmettre) {
      if (!confirm("Transmettre la fiche ? Tu ne pourras plus la modifier.")) {
        toast("Brouillon enregistré");
        history.replaceState(null, "", `?id=${fiche.id}`);
        return;
      }
      fiche = await api(`/api/fiches/${fiche.id}/transmettre`, { methode: "POST" });
      toast("Fiche transmise");
      location.href = "/pages/fiches.html";
      return;
    }
    toast("Brouillon enregistré");
    history.replaceState(null, "", `?id=${fiche.id}`);
  } catch (e) {
    montrerErreur(e.message);
  } finally {
    boutons.forEach((b) => (b.disabled = false));
    bloquerSiTransmise();
  }
}

el("btn-brouillon").addEventListener("click", () => enregistrer(false));
el("btn-transmettre").addEventListener("click", () => enregistrer(true));
el("form-fiche").addEventListener("submit", (e) => e.preventDefault());

async function demarrer() {
  majAide();
  try {
    produits = await api("/api/produits");
    produits.sort((a, b) => a.ordre - b.ordre || a.id - b.id);

    if (moi.role !== "agent") {
      const liste = await api("/api/csps");
      champs.csps.innerHTML = liste.map((c) => `<option value="${c.id}">${echapper(c.nom)}</option>`).join("");
      el("bloc-csps").hidden = false;
    }

    if (idFiche) {
      fiche = await api(`/api/fiches/${idFiche}`);
      // un produit désactivé depuis peut rester dans une fiche existante
      for (const l of fiche.lignes) {
        if (!produits.some((p) => p.id === l.produit_id)) produits.push(l.produit);
      }
      champs.type.value = fiche.type_fiche;
      champs.debut.value = fiche.date_debut;
      champs.fin.value = fiche.date_fin;
      champs.obs.value = fiche.observations || "";
      if (moi.role !== "agent") { champs.csps.value = fiche.csps_id; champs.csps.disabled = true; }
      majAide();
    } else {
      champs.debut.value = iso(new Date());
      calculerFin();
    }
    afficherProduits(fiche ? fiche.lignes : []);
    bloquerSiTransmise();
  } catch (e) {
    el("zone-produits").innerHTML = `<p class="erreur">${echapper(e.message)}</p>`;
  }
}
demarrer();
