import { echapper } from "./api.js";
import { LIBELLES_ROLES, monterLayout } from "./layout.js";

const utilisateur = monterLayout({ actif: "dashboard", titre: "Tableau de bord" });

document.getElementById("bienvenue").innerHTML = `
  <h2>Bienvenue, ${echapper(utilisateur.nom_complet)}</h2>
  <p>Connecté en tant que ${echapper(LIBELLES_ROLES[utilisateur.role] || utilisateur.role)}.
     La saisie des fiches et les statistiques seront disponibles prochainement.</p>
`;

const raccourcis = [];
if (utilisateur.role === "admin") {
  raccourcis.push({
    titre: "Administration",
    texte: "Gérer les produits et les CSPS, inscrire et désactiver les utilisateurs.",
    href: "/pages/admin.html",
  });
}

document.getElementById("raccourcis").innerHTML = raccourcis
  .map(
    (r) => `
    <a class="carte carte-lien" href="${r.href}">
      <h2>${echapper(r.titre)}</h2>
      <p>${echapper(r.texte)}</p>
    </a>`
  )
  .join("");
