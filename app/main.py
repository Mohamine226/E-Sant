from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CommuData+ API")

@app.get("/backend")
async def accueil():
    return {"message": "Bienvenue sur CommuData Léo🎖️"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

CLIENT_DIR = Path(__file__).resolve().parent.parent / "client"
app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")