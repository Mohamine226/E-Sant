// Fonctions partagées par toutes les pages après la connexion.

export function echapper(valeur) {
  return String(valeur ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function getUtilisateur() {
  try {
    return JSON.parse(localStorage.getItem("utilisateur"));
  } catch {
    return null;
  }
}

export function deconnecter() {
  localStorage.removeItem("token");
  localStorage.removeItem("utilisateur");
  window.location.href = "/";
}

export function exigerConnexion() {
  const utilisateur = getUtilisateur();
  if (!localStorage.getItem("token") || !utilisateur) {
    deconnecter();
    throw new Error("Non connecté");
  }
  return utilisateur;
}

function messageErreur(donnees) {
  if (!donnees || !donnees.detail) return null;
  if (typeof donnees.detail === "string") return donnees.detail;
  if (Array.isArray(donnees.detail)) {
    return donnees.detail
      .map((d) => {
        const champ = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "";
        const message = String(d.msg || "").replace(/^Value error, /, "");
        return champ && champ !== "body" ? `${champ} : ${message}` : message;
      })
      .join(" ; ");
  }
  return null;
}

// Appel à l'API avec le jeton. Lève une Error avec un message lisible en cas de problème.
export async function api(chemin, { methode = "GET", corps } = {}) {
  const token = localStorage.getItem("token");
  const entetes = {};
  if (corps !== undefined) entetes["Content-Type"] = "application/json";
  if (token) entetes["Authorization"] = `Bearer ${token}`;

  let reponse;
  try {
    reponse = await fetch(chemin, {
      method: methode,
      headers: entetes,
      body: corps !== undefined ? JSON.stringify(corps) : undefined,
    });
  } catch {
    throw new Error("Pas de connexion au serveur. Vérifie ton réseau.");
  }

  if (reponse.status === 401) {
    deconnecter();
    throw new Error("Session expirée, reconnecte-toi.");
  }
  if (reponse.status === 204) return null;

  const donnees = await reponse.json().catch(() => null);
  if (!reponse.ok) {
    throw new Error(messageErreur(donnees) || `Erreur ${reponse.status}`);
  }
  return donnees;
}

// "2026-11-16" -> "16/11/2026"
export function formaterDate(iso) {
  return iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—";
}

// "2026-11-22T14:30:12" -> "22/11/2026 14:30"
export function formaterDateHeure(iso) {
  if (!iso) return "—";
  const [jour, heure = ""] = iso.split("T");
  return `${formaterDate(jour)} ${heure.slice(0, 5)}`.trim();
}
