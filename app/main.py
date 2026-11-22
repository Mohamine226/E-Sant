from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (enregistre les tables)
from .database import Base, engine, get_db
from .routers import auth, csps, produits, utilisateurs

Base.metadata.create_all(bind=engine)

app = FastAPI(title="E-Santé")

app.include_router(auth.router)
app.include_router(produits.router)
app.include_router(csps.router)
app.include_router(utilisateurs.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "base_de_donnees": "connectée"}


# Le site : toujours EN DERNIER
CLIENT_DIR = Path(__file__).resolve().parent.parent / "client"
app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")