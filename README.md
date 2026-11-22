# CommuData+

Plateforme web de collecte et d'analyse des données communautaires de santé (ASBC, paludisme, CPS) pour les districts sanitaires du Burkina Faso.

Pensée pour le terrain : saisie fiable, même avec une connexion instable, et résultats prêts à exporter.

## Fonctionnalités

**MVP**
- Authentification avec rôles (ICP, district, administrateur)
- Saisie des activités communautaires avec quantités (sensibilisation, paludisme, CPS)
- Saisie hors ligne avec synchronisation automatique au retour du réseau
- Tableau de bord : indicateurs clés et graphique de tendance
- Gestion des ASBC (liste, recherche, ajout, modification)
- Export des données en fichier Excel (.xlsx)

**À venir**
- Rapports PDF et analyses détaillées
- Gestion des utilisateurs et des aires sanitaires
- Carte de suivi communautaire

## Technologies

| Couche | Outils |
|---|---|
| Serveur | FastAPI, SQLAlchemy, Alembic |
| Base de données | PostgreSQL |
| Authentification | JWT |
| Export | XlsxWriter, pandas |
| Interface | HTML, Tailwind CSS, JavaScript |
| Hors ligne | PWA (Service Worker, IndexedDB / Dexie.js) |
| Graphiques et carte | Chart.js, Leaflet |

## Structure du projet

```
commudata/
└──  ── app/
    │   └── main.py        # API FastAPI + service du site
    ├── client/            # Interface web (PWA)
    │   ├── index.html
    │   ├── manifest.json
    │   ├── sw.js
    │   ├── css/
    │   ├── js/
    │   └── pages/
    └── requirements.txt
```

## Installation

```bash
git clone https://github.com/TON_UTILISATEUR/commudata.git
cd commudata/backend

python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate

pip install -r requirements.txt
```

Crée un fichier `.env` à la racine de `backend/` (ne jamais le publier) :

```
DATABASE_URL=postgresql://utilisateur:motdepasse@localhost:5432/commudata
SECRET_KEY=change-moi
```

## Lancer le serveur

```bash
uvicorn app.main:app --reload
```

- Site : http://127.0.0.1:8000
- Documentation de l'API : http://127.0.0.1:8000/docs

Toutes les routes de l'API sont préfixées par `/api`.

## Feuille de route

- [x] Structure du projet et serveur FastAPI
- [ ] Base de données et modèles
- [ ] Authentification et rôles
- [ ] Saisie hors ligne et synchronisation
- [ ] Tableau de bord
- [ ] Export Excel
- [ ] Rapports PDF et carte

## Auteur

GNAMBRE Mohamine

## Licence

À définir.