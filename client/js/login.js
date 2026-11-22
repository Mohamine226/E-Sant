const btnConnexion = document.getElementById("btn-connexion");
const form = document.getElementById("form-connexion");
const erreur = document.getElementById("erreur");

// Le bouton « Se connecter » révèle le formulaire
btnConnexion.addEventListener("click", () => {
  btnConnexion.hidden = true;
  form.hidden = false;
  document.getElementById("identifiant").focus();
});

function afficherErreur(message) {
  erreur.textContent = message;
  erreur.hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  erreur.hidden = true;

  const bouton = form.querySelector("button[type=submit]");
  bouton.disabled = true;

  try {
    const reponse = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identifiant: form.identifiant.value.trim(),
        motdepasse: form.motdepasse.value,
      }),
    });

    if (!reponse.ok) {
      afficherErreur(
        reponse.status === 401
          ? "Identifiant ou mot de passe incorrect."
          : "Connexion impossible. Réessaie plus tard."
      );
      return;
    }

    const data = await reponse.json();
    localStorage.setItem("token", data.access_token);
    window.location.href = "/pages/dashboard.html";
  } catch (err) {
    afficherErreur("Pas de connexion au serveur. Vérifie ton réseau.");
  } finally {
    bouton.disabled = false;
  }
});