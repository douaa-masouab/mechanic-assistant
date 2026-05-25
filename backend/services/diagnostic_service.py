import os
import csv
import json
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai

from backend.schemas import DiagnosticRequest, DiagnosticResponse, Etape

# Chargement des variables d'environnement
load_dotenv()

# Chemins absolus vers les fichiers de données du projet
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OBD_PATH = os.path.join(BASE_DIR, "data", "obd_codes.json")
CSV_OBD_PATH = os.path.join(BASE_DIR, "data", "code-OBD.csv")
VEHICLES_PATH = os.path.join(BASE_DIR, "data", "vehicles.json")


def _charger_obd_db():
    """Charge la base OBD depuis JSON puis fusionne le CSV s'il existe."""
    db = {}

    if os.path.exists(OBD_PATH):
        with open(OBD_PATH, "r", encoding="utf-8") as f:
            try:
                db = json.load(f)
            except json.JSONDecodeError:
                db = {}

    if os.path.exists(CSV_OBD_PATH):
        csv_text = None
        try:
            with open(CSV_OBD_PATH, "r", encoding="utf-8") as f:
                csv_text = f.read()
        except UnicodeDecodeError:
            with open(CSV_OBD_PATH, "r", encoding="cp1252", errors="replace") as f:
                csv_text = f.read()

        if csv_text is not None:
            reader = csv.DictReader(csv_text.splitlines(), delimiter=';')
            for row in reader:
                code = row.get("Code", "").strip().upper()
                description = row.get("Signification", "").strip()
                systeme = row.get("Systeme", "").strip()
                if not code:
                    continue

                if code not in db:
                    db[code] = {
                        "description": description,
                        "causes": [],
                        "etapes": [],
                        "systeme": systeme
                    }
                else:
                    if description and not db[code].get("description"):
                        db[code]["description"] = description
                    if systeme:
                        db[code]["systeme"] = systeme

    return db


# Chargement unique au moment de l'import du module
OBD_DB = _charger_obd_db()

with open(VEHICLES_PATH, "r", encoding="utf-8") as f:
    VEHICLES_DB = json.load(f)

# Configuration de Gemini si la clé est fournie
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _vehicule_existe(marque: str, modele: str, annee: int) -> bool:
    """Vérifie la présence du couple marque / modèle / année dans le catalogue.
    Retourne ``True`` si le véhicule est connu dans la base locale, sinon ``False``.
    """
    for v in VEHICLES_DB:
        if (
            v["marque"].lower() == marque.lower()
            and v["modele"].lower() == modele.lower()
            and v["annee"] == annee
        ):
            return True
    return False


def get_all_obd_codes() -> dict:
    """Retourne la base OBD chargée depuis JSON et CSV."""
    return OBD_DB


def _diagnostiquer_ia(code: str, marque: str, modele: str, annee: int) -> DiagnosticResponse:
    """Interroge l'API Gemini pour générer un diagnostic complet sous format JSON structuré en français."""
    prompt = f"""
    En tant que mécanicien automobile expert et assistant virtuel, fournissez un diagnostic technique très détaillé en français pour le code d'erreur OBD-II et le véhicule suivants :
    - Code OBD-II : {code}
    - Véhicule : {marque} {modele} ({annee})

    Votre réponse doit être un objet JSON unique valide contenant EXACTEMENT la structure suivante :
    {{
        "code_obd": "{code}",
        "description": "Une description très claire, professionnelle et précise du problème en français.",
        "causes_possibles": [
            "Cause potentielle 1 en français",
            "Cause potentielle 2 en français",
            "Cause potentielle 3 en français"
        ],
        "solutions": [
            {{
                "titre": "Titre étape 1 en français (ex. Inspecter les fusibles)",
                "description": "Description pas à pas de l'action à réaliser en français, simple, claire et didactique."
            }},
            {{
                "titre": "Titre étape 2 en français",
                "description": "Description détaillée de l'action en français..."
            }}
        ]
    }}

    Renvoyez uniquement le code JSON brut. N'ajoutez aucun texte explicatif avant ou après, ni de bloc de code markdown du type ```json ```. Assurez-vous que le JSON soit parfaitement valide.
    """
    
    # Utilisation du modèle flash rapide et optimisé pour le texte structuré
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    text = response.text.strip()
    
    # Nettoyage d'éventuels formaterurs markdown
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Parse du JSON
    data = json.loads(text)
    
    solutions = [
        Etape(titre=e["titre"], description=e["description"]) 
        for e in data.get("solutions", [])
    ]
    
    return DiagnosticResponse(
        code_obd=code,
        description=data.get("description", "Diagnostic intelligent généré par l'IA."),
        causes_possibles=data.get("causes_possibles", []),
        solutions=solutions,
        vehicule_valide=True,
    )


def _diagnostic_fallback(code: str, marque: str, modele: str, annee: int) -> DiagnosticResponse:
    """Génère un diagnostic de secours complet et professionnel en français si Gemini n'est pas activé."""
    # Si le code est dans notre mini base statique, on l'utilise
    if code in OBD_DB:
        info = OBD_DB[code]
        solutions = [Etape(titre=e["titre"], description=e["description"]) for e in info.get("etapes", [])]
        return DiagnosticResponse(
            code_obd=code,
            description=info.get("description", ""),
            causes_possibles=info.get("causes", []),
            solutions=solutions,
            vehicule_valide=True,
            message="Diagnostic fourni à partir de la base de données certifiée locale."
        )

    # Sinon, on fournit un diagnostic simulé très réaliste et utile pour la démonstration
    lettre = code[0] if code else "P"
    
    if lettre == "P":
        desc = f"Code générique du groupe motopropulseur (moteur/boîte) détecté pour votre {marque} {modele}. Ce type de défaut affecte généralement la gestion des émissions, de l'admission ou de l'allumage."
        causes = [
            "Capteur moteur encrassé ou défectueux (débitmètre, sonde lambda)",
            "Prise d'air ou fuite de dépression dans le collecteur d'admission",
            "Bougie(s) d'allumage ou bobine(s) fatiguée(s)",
            "Faisceau de câblage usé ou mauvais contact"
        ]
        solutions = [
            Etape(
                titre="Inspecter visuellement les composants sous le capot",
                description="Recherchez des durites d'admission fissurées, des fils électriques débranchés ou corrodés près des bobines d'allumage et des capteurs."
            ),
            Etape(
                titre="Vérifier les données en temps réel avec un scanner OBD",
                description="Mesurez la valeur du débit d'air (MAF) et les corrections de carburant à court/long terme pour localiser l'anomalie."
            ),
            Etape(
                titre="Contrôler le système d'allumage",
                description="Démontez les bougies et vérifiez l'écartement de l'électrode ainsi que la coloration de la tête de bougie."
            )
        ]
    else:
        desc = f"Code défaut générique de châssis ou habitacle ({code}) pour votre {marque} {modele}. Lié le plus souvent au système de freinage ABS/ESP ou à un problème de communication réseau."
        causes = [
            "Capteur de vitesse de roue ABS encrassé ou hors d'usage",
            "Baisse de tension au niveau de la batterie principale du véhicule",
            "Interruption ou perturbation de la liaison sur le bus CAN"
        ]
        solutions = [
            Etape(
                titre="Mesurer la tension de la batterie",
                description="Contrôlez au voltmètre que la tension est supérieure à 12,5 V à l'arrêt et supérieure à 13,8 V moteur tournant."
            ),
            Etape(
                titre="Inspecter et nettoyer les capteurs de roue",
                description="Démontez les roues pour accéder aux capteurs ABS, nettoyez-les avec un chiffon doux pour enlever la poussière de frein."
            )
        ]
        
    return DiagnosticResponse(
        code_obd=code,
        description=desc,
        causes_possibles=causes,
        solutions=solutions,
        vehicule_valide=True,
        message="[DÉMO] Clé API Gemini non configurée. Diagnostic standardisé de secours en français."
    )


def diagnostiquer(req: DiagnosticRequest) -> DiagnosticResponse:
    """Analyse le code OBD‑II et renvoie une réponse structurée.
    
    1️⃣ Détermine si le véhicule est présent dans le catalogue local.
    2️⃣ Utilise la base locale ou appelle l'IA (Gemini / Simulation) de manière transparente.
    3️⃣ Renvoie un diagnostic structuré au format attendu.
    """
    code = req.code_obd.strip().upper()
    
    # 1️⃣ Validation du véhicule (certification locale)
    vehicule_certifie = _vehicule_existe(req.marque, req.modele, req.annee)
    
    # 2️⃣ Diagnostic
    # Option A : Le code est connu localement
    if code in OBD_DB:
        info = OBD_DB[code]
        solutions = [Etape(titre=e["titre"], description=e["description"]) for e in info.get("etapes", [])]
        
        msg = "Diagnostic certifié à partir de notre base locale."
        if not vehicule_certifie:
            msg += " Note : Ce véhicule n'est pas référencé dans notre catalogue certifié, mais le diagnostic reste applicable."
            
        return DiagnosticResponse(
            code_obd=code,
            description=info.get("description", "Défaut détecté."),
            causes_possibles=info.get("causes", []),
            solutions=solutions,
            vehicule_valide=vehicule_certifie,
            message=msg
        )
    
    # Option B : Le code est absent localement, utilisation de Gemini si configuré
    if GEMINI_API_KEY:
        try:
            res = _diagnostiquer_ia(code, req.marque, req.modele, req.annee)
            res.vehicule_valide = vehicule_certifie
            msg = "Diagnostic généré en temps réel par l'IA Gemini."
            if not vehicule_certifie:
                msg += " Note : Véhicule hors catalogue certifié local."
            res.message = msg
            return res
        except Exception as e:
            # En cas de problème réseau ou d'API, fallback sur la simulation intelligente
            res = _diagnostic_fallback(code, req.marque, req.modele, req.annee)
            res.vehicule_valide = vehicule_certifie
            res.message = f"Erreur API Gemini ({str(e)}). Repli sur le diagnostic de démonstration."
            return res
    else:
        # Option C : Pas de clé API Gemini, simulation réaliste
        res = _diagnostic_fallback(code, req.marque, req.modele, req.annee)
        res.vehicule_valide = vehicule_certifie
        if not vehicule_certifie:
            res.message = "Véhicule hors catalogue certifié. " + (res.message or "")
        return res

