import os
import sys

# Ajouter le dossier racine du projet au chemin Python pour exécuter ce script directement.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routes.diagnostic import router as diagnostic_router

app = FastAPI(
    title="Assistant IA Diagnostic Automobile",
    description="API REST pour diagnostiquer les codes OBD‑II et guider les réparations.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS autorisé pour le front‑end (ajuster en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnostic_router, prefix="/api")

# Servir le frontend depuis le dossier frontend/
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def serve_index():
    """Servir la page d'accueil du chatbot."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Monter les assets statiques (CSS, JS)
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
