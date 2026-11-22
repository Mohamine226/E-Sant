import { deconnecter, echapper, exigerConnexion } from "./api.js";

// Pages de l'application. `pret: false` = affichée en grisé « bientôt ».
const MENU = [
  { id: "dashboard", texte: "Tableau de bord", href: "/pages/dashboard.html",
    roles: ["agent", "district", "admin"], pret: true },
  { id: "saisie", texte: "Nouvelle fiche", href: "/pages/saisie.html",
    roles: ["agent", "district", "admin"], pret: true },
  { id: "fiches", texte: "Historique", href: "/pages/fiches.html",
    roles: ["agent", "district", "admin"], pret: true },
  { id: "admin", texte: "Administration", href: "/pages/admin.html",
    roles: ["admin"], pret: true },
];

export const LIBELLES_ROLES = {
  agent: "Agent CSPS",
  district: "District",
  admin: "Administrateur",
};

// Construit le menu et l'en-tête autour de <main id="contenu">.
// `roles` (facultatif) : rôles autorisés sur la page. Retourne l'utilisateur connecté.
export function monterLayout({ actif, titre, roles }) {
  const utilisateur = exigerConnexion();

  if (roles && !roles.includes(utilisateur.role)) {
    window.location.href = "/pages/dashboard.html";
    throw new Error("Accès refusé");
  }

  const liens = MENU.filter((m) => m.roles.includes(utilisateur.role))
    .map((m) =>
      m.pret
        ? `<a class="menu-lien ${m.id === actif ? "actif" : ""}" href="${m.href}">${echapper(m.texte)}</a>`
        : `<span class="menu-lien desactive" title="Bientôt disponible">${echapper(m.texte)}<small>bientôt</small></span>`
    )
    .join("");

  const app = document.createElement("div");
  app.className = "app";
  app.innerHTML = `
    <aside class="menu" id="menu">
      <div class="marque">E-Santé</div>
      <nav>${liens}</nav>
      <button class="btn-deconnexion" id="btn-deconnexion" type="button">Déconnexion</button>
    </aside>
    <div class="principal">
      <header class="entete">
        <button class="btn-burger" id="btn-burger" type="button" aria-label="Ouvrir le menu">☰</button>
        <h1>${echapper(titre)}</h1>
        <div class="profil">
          <span>${echapper(utilisateur.nom_complet)}</span>
          <span class="badge-role">${echapper(LIBELLES_ROLES[utilisateur.role] || utilisateur.role)}</span>
        </div>
      </header>
    </div>
    <div class="voile" id="voile"></div>
  `;

  app.querySelector(".principal").appendChild(document.getElementById("contenu"));
  document.body.prepend(app);

  const basculer = () => app.classList.toggle("menu-ouvert");
  app.querySelector("#btn-burger").addEventListener("click", basculer);
  app.querySelector("#voile").addEventListener("click", basculer);
  app.querySelector("#btn-deconnexion").addEventListener("click", deconnecter);

  return utilisateur;
}

// Petit message temporaire en bas à droite.
export function toast(message, type = "info") {
  let zone = document.getElementById("toasts");
  if (!zone) {
    zone = document.createElement("div");
    zone.id = "toasts";
    zone.setAttribute("aria-live", "polite");
    document.body.appendChild(zone);
  }
  const element = document.createElement("div");
  element.className = `toast ${type}`;
  element.textContent = message;
  zone.appendChild(element);
  setTimeout(() => element.remove(), 4000);
}
