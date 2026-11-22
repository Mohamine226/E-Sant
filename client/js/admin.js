import { api, echapper, getUtilisateur } from "./api.js";
import { LIBELLES_ROLES, monterLayout, toast } from "./layout.js";

monterLayout({ actif: "admin", titre: "Administration", roles: ["admin"] });
const moi = getUtilisateur();

const zone = document.getElementById("zone");
const btnAjouter = document.getElementById("btn-ajouter");
const modale = document.getElementById("modale");
const formModale = document.getElementById("form-modale");
const titreModale = document.getElementById("titre-modale");
const champsModale = document.getElementById("champs-modale");
const erreurModale = document.getElementById("erreur-modale");
const btnEnregistrer = document.getElementById("btn-enregistrer");

const ROLES = Object.entries(LIBELLES_ROLES).map(([valeur, texte]) => ({ valeur, texte }));

let ongletActif = "produits";
let elements = [];
let listeCsps = [];
let definitionsChamps = [];
let actionModale = null;

const badge = (actif) =>
  `<span class="badge-statut ${actif ? "actif" : "inactif"}">${actif ? "Actif" : "Inactif"}</span>`;

const nomCsps = (id) => {
  const csps = listeCsps.find((c) => c.id === id);
  return csps ? csps.nom : "—";
};

// Description de chaque onglet : colonnes, formulaire et routes de l'API.
const ONGLETS = {
  produits: {
    ajout: "Ajouter un produit",
    chemin: "/api/produits",
    peutSupprimer: true,
    entetes: ["Code", "Désignation", "Ordre", "Statut"],
    charger: () => api("/api/produits?inclure_inactifs=true"),
    cellules: (p) => [echapper(p.code), echapper(p.designation), p.ordre, badge(p.actif)],
    titre: (p) => p.designation,
    champs: () => [
      { nom: "code", libelle: "Code (ex. PL006)", type: "text", requis: true, maxlen: 10 },
      { nom: "designation", libelle: "Désignation", type: "text", requis: true, maxlen: 200 },
      { nom: "ordre", libelle: "Ordre d'affichage", type: "number", min: 0, defaut: 0 },
    ],
    corps: (v) => ({ code: v.code, designation: v.designation, ordre: v.ordre ?? 0 }),
  },

  csps: {
    ajout: "Ajouter un CSPS",
    chemin: "/api/csps",
    peutSupprimer: true,
    entetes: ["Nom", "ASBC prévus", "Statut"],
    charger: () => api("/api/csps?inclure_inactifs=true"),
    cellules: (c) => [echapper(c.nom), c.asbc_prevus ?? "—", badge(c.actif)],
    titre: (c) => c.nom,
    champs: () => [
      { nom: "nom", libelle: "Nom du CSPS", type: "text", requis: true, maxlen: 100 },
      { nom: "asbc_prevus", libelle: "ASBC prévus", type: "number", min: 0 },
    ],
    corps: (v) => ({ nom: v.nom, asbc_prevus: v.asbc_prevus }),
  },

  utilisateurs: {
    ajout: "Inscrire un utilisateur",
    chemin: "/api/utilisateurs",
    peutSupprimer: false,
    entetes: ["Identifiant", "Nom", "Rôle", "CSPS", "Statut"],
    charger: async () => {
      listeCsps = await api("/api/csps?inclure_inactifs=true");
      return api("/api/utilisateurs");
    },
    cellules: (u) => [
      echapper(u.identifiant),
      echapper(u.nom_complet),
      echapper(LIBELLES_ROLES[u.role] || u.role),
      echapper(nomCsps(u.csps_id)),
      badge(u.actif),
    ],
    titre: (u) => u.nom_complet,
    champs: (existant) => [
      ...(existant
        ? []
        : [{ nom: "identifiant", libelle: "Identifiant (ou email)", type: "text",
             requis: true, minlen: 3, maxlen: 50 }]),
      { nom: "nom_complet", libelle: "Nom complet", type: "text", requis: true, minlen: 2, maxlen: 120 },
      { nom: "motdepasse", libelle: existant ? "Nouveau mot de passe" : "Mot de passe",
        type: "password", requis: !existant, minlen: 8, maxlen: 128,
        aide: existant ? "Laisse vide pour ne pas le changer" : "8 caractères minimum" },
      { nom: "role", libelle: "Rôle", type: "select", options: ROLES },
      { nom: "csps_id", libelle: "CSPS", type: "select", numerique: true,
        options: [
          { valeur: "", texte: "Aucun" },
          ...listeCsps.filter((c) => c.actif).map((c) => ({ valeur: c.id, texte: c.nom })),
        ],
        aide: "Obligatoire pour un agent" },
    ],
    corps: (v, existant) => {
      if (!existant) {
        return {
          identifiant: v.identifiant,
          nom_complet: v.nom_complet,
          motdepasse: v.motdepasse,
          role: v.role,
          csps_id: v.csps_id,
        };
      }
      const corps = { nom_complet: v.nom_complet, role: v.role, csps_id: v.csps_id };
      if (v.motdepasse) corps.motdepasse = v.motdepasse;
      return corps;
    },
  },
};

// ---------- Liste ----------
async function charger() {
  const onglet = ongletActif;
  zone.innerHTML = `<p class="chargement">Chargement…</p>`;
  try {
    const donnees = await ONGLETS[onglet].charger();
    if (onglet !== ongletActif) return; // l'utilisateur a changé d'onglet entre-temps
    elements = donnees;
    afficherTable();
  } catch (erreur) {
    if (onglet === ongletActif) {
      zone.innerHTML = `<p class="erreur">${echapper(erreur.message)}</p>`;
    }
  }
}

function afficherTable() {
  const def = ONGLETS[ongletActif];
  if (!elements.length) {
    zone.innerHTML = `<p class="vide">Aucun élément pour le moment.</p>`;
    return;
  }
  const lignes = elements
    .map((el) => {
      const cellules = def.cellules(el).map((c) => `<td>${c}</td>`).join("");
      const estMoi = ongletActif === "utilisateurs" && el.id === moi.id;
      const boutons = [
        `<button class="btn-leger" data-action="modifier" data-id="${el.id}">Modifier</button>`,
        estMoi
          ? ""
          : `<button class="btn-leger" data-action="basculer" data-id="${el.id}">${el.actif ? "Désactiver" : "Activer"}</button>`,
        def.peutSupprimer
          ? `<button class="btn-leger danger" data-action="supprimer" data-id="${el.id}">Supprimer</button>`
          : "",
      ].join("");
      return `<tr class="${el.actif ? "" : "ligne-inactive"}">${cellules}<td><div class="actions">${boutons}</div></td></tr>`;
    })
    .join("");

  zone.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr>${def.entetes.map((e) => `<th>${e}</th>`).join("")}<th>Actions</th></tr></thead>
        <tbody>${lignes}</tbody>
      </table>
    </div>`;
}

zone.addEventListener("click", async (evenement) => {
  const bouton = evenement.target.closest("button[data-action]");
  if (!bouton) return;
  const el = elements.find((x) => x.id === Number(bouton.dataset.id));
  if (!el) return;
  const def = ONGLETS[ongletActif];

  try {
    switch (bouton.dataset.action) {
      case "modifier":
        ouvrirModale(el);
        break;
      case "basculer":
        await api(`${def.chemin}/${el.id}`, { methode: "PATCH", corps: { actif: !el.actif } });
        toast(el.actif ? "Désactivé" : "Activé");
        await charger();
        break;
      case "supprimer":
        if (!confirm(`Supprimer « ${def.titre(el)} » ? Cette action est définitive.`)) return;
        await api(`${def.chemin}/${el.id}`, { methode: "DELETE" });
        toast("Supprimé");
        await charger();
        break;
    }
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
});

// ---------- Fenêtre d'ajout / de modification ----------
function champHtml(champ, valeur) {
  const id = `champ-${champ.nom}`;
  const courante = valeur ?? champ.defaut ?? "";
  let saisie;
  if (champ.type === "select") {
    const options = champ.options
      .map(
        (o) =>
          `<option value="${echapper(o.valeur)}" ${String(o.valeur) === String(courante) ? "selected" : ""}>${echapper(o.texte)}</option>`
      )
      .join("");
    saisie = `<select id="${id}" name="${champ.nom}">${options}</select>`;
  } else {
    saisie = `<input id="${id}" name="${champ.nom}" type="${champ.type}" value="${echapper(courante)}"
      ${champ.requis ? "required" : ""}
      ${champ.min !== undefined ? `min="${champ.min}"` : ""}
      ${champ.minlen ? `minlength="${champ.minlen}"` : ""}
      ${champ.maxlen ? `maxlength="${champ.maxlen}"` : ""}
      autocomplete="off">`;
  }
  const aide = champ.aide ? `<small>${echapper(champ.aide)}</small>` : "";
  return `<label for="${id}">${echapper(champ.libelle)}</label>${saisie}${aide}`;
}

function ouvrirModale(existant = null) {
  const def = ONGLETS[ongletActif];
  definitionsChamps = def.champs(existant);
  titreModale.textContent = existant ? `Modifier : ${def.titre(existant)}` : def.ajout;
  champsModale.innerHTML = definitionsChamps
    .map((c) => champHtml(c, existant ? existant[c.nom] : undefined))
    .join("");
  erreurModale.hidden = true;

  actionModale = (valeurs) =>
    existant
      ? api(`${def.chemin}/${existant.id}`, { methode: "PATCH", corps: def.corps(valeurs, existant) })
      : api(def.chemin, { methode: "POST", corps: def.corps(valeurs, null) });

  modale.showModal();
  const premier = champsModale.querySelector("input, select");
  if (premier) premier.focus();
}

function lireValeurs() {
  const valeurs = {};
  for (const champ of definitionsChamps) {
    const element = formModale.querySelector(`[name="${champ.nom}"]`);
    let valeur = element.value;
    if (champ.type !== "password") valeur = valeur.trim();
    if (champ.type === "number" || champ.numerique) {
      valeur = valeur === "" ? null : Number(valeur);
    }
    valeurs[champ.nom] = valeur;
  }
  return valeurs;
}

formModale.addEventListener("submit", async (evenement) => {
  evenement.preventDefault();
  if (!actionModale) return;
  erreurModale.hidden = true;
  btnEnregistrer.disabled = true;
  try {
    await actionModale(lireValeurs());
    modale.close();
    toast("Enregistré");
    await charger();
  } catch (erreur) {
    erreurModale.textContent = erreur.message;
    erreurModale.hidden = false;
  } finally {
    btnEnregistrer.disabled = false;
  }
});

document.getElementById("btn-annuler").addEventListener("click", () => modale.close());
btnAjouter.addEventListener("click", () => ouvrirModale());

// ---------- Onglets ----------
function selectionner(nom) {
  ongletActif = nom;
  document.querySelectorAll("[data-onglet]").forEach((b) =>
    b.setAttribute("aria-selected", String(b.dataset.onglet === nom))
  );
  btnAjouter.textContent = ONGLETS[nom].ajout;
  charger();
}

document.querySelectorAll("[data-onglet]").forEach((b) =>
  b.addEventListener("click", () => selectionner(b.dataset.onglet))
);

selectionner("produits");
