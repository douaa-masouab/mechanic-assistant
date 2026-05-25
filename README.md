# Mechanic Assistant

Assistant Virtuel de Diagnostic Intelligent pour automobiles.

## Description

Mechanic Assistant est une application web professionnelle conçue pour aider les techniciens et les ateliers à diagnostiquer les codes OBD-II, analyser les symptômes et guider les réparations avec un historique utilisateur privé.

## Fonctionnalités

- Diagnostic OBD-II et recommandations de réparation
- Conversation chatbot intelligente avec historique de session
- Espace utilisateur professionnel avec profil et historique privé
- Base de données SQLite pour stocker les profils et l'historique
- Interface frontend professionnelle avec sélection de véhicule et visualisation des codes OBD
- Intégration d'une API de génération de texte (Gemini) pour les réponses dynamiques

## Structure du projet

- `backend/`
  - `app.py` : application FastAPI
  - `database.py` : gestion SQLite
  - `routes/diagnostic.py` : endpoints API
  - `schemas.py` : modèles Pydantic
  - `services/` : logique métier et traitement du chat
- `frontend/`
  - `index.html` : interface utilisateur principale
  - `assets/app.js` : logique frontend et appels API
  - `assets/style.css` : styles visuels
- `data/` : données OBD et véhicules
- `requirements.txt` : dépendances Python

## Installation

1. Crée un environnement virtuel Python :
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Installe les dépendances :
   ```powershell
   pip install -r requirements.txt
   ```
3. Crée un fichier `.env` basé sur `.env.example` et ajoute la clé API Gemini :
   ```env
   GEMINI_API_KEY=ta_cle_api
   ```

## Lancement

```powershell
python backend/app.py
```

Puis ouvre `http://localhost:8000/` dans ton navigateur.

## Endpoints principaux

- `POST /api/chat` : conversation chatbot
- `POST /api/diagnostiquer` : diagnostic OBD
- `POST /api/user/profile` : enregistrer/mette à jour un profil utilisateur
- `GET /api/user/history` : récupérer l'historique d'un utilisateur
- `GET /api/obd-codes` : liste des codes OBD disponibles

## Notes

- Le backend enregistre les données localement avec SQLite.
- Le frontend stocke temporairement les informations de session et l'utilisateur dans `localStorage`.
- Pour une utilisation professionnelle, ajoute une authentification et sécurise la clé API.

---

© 2026 Mechanic Assistant
