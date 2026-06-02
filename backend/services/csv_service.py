import os
import csv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CSV_PATH = os.path.join(BASE_DIR, "data", "matriculations.csv")

# Exemples de véhicules pour pré-remplir le fichier CSV s'il est créé automatiquement
MOCK_VEHICLES = [
    {"matriculation": "12345-A-6", "marque": "Peugeot", "modele": "208", "annee": "2020", "carburant": "Diesel"},
    {"matriculation": "67890-B-15", "marque": "Renault", "modele": "Clio", "annee": "2018", "carburant": "Essence"},
    {"matriculation": "24680-D-22", "marque": "Volkswagen", "modele": "Golf", "annee": "2021", "carburant": "Hybride"},
    {"matriculation": "13579-H-44", "marque": "Toyota", "modele": "Yaris", "annee": "2019", "carburant": "Essence"},
    {"matriculation": "99999-W-5", "marque": "BMW", "modele": "Série 3", "annee": "2022", "carburant": "Hybride"},
    {"matriculation": "AA-123-BB", "marque": "Peugeot", "modele": "3008", "annee": "2021", "carburant": "Essence"},
    {"matriculation": "CC-456-DD", "marque": "Renault", "modele": "Captur", "annee": "2019", "carburant": "Diesel"},
    {"matriculation": "EE-789-FF", "marque": "Toyota", "modele": "RAV4", "annee": "2020", "carburant": "Hybride"}
]


def init_csv_file():
    """Initialise le fichier CSV de matriculations avec des données exemples si inexistant."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["matriculation", "marque", "modele", "annee", "carburant"])
                writer.writeheader()
                for v in MOCK_VEHICLES:
                    writer.writerow(v)
            print(f"[CSV_SERVICE] Fichier initialisé avec succès : {CSV_PATH}")
        except Exception as exc:
            print(f"[CSV_SERVICE] Erreur lors de l'initialisation du CSV : {exc}")


def nettoyer_matriculation(plate: str) -> str:
    """Nettoie le numéro de matricule pour comparaison (majuscules, sans tirets, espaces ni kashida/tatweel arabe)."""
    if not plate:
        return ""
    # Retirer les espaces, tirets et kashida/tatweel arabe pour une recherche ultra-robuste
    temp = plate.upper().replace("-", "").replace(" ", "").replace("ـ", "")
    return "".join(c for c in temp if c.isalnum())


def rechercher_vehicule(plate: str) -> dict | None:
    """Recherche un véhicule par sa matriculation dans le fichier CSV."""
    init_csv_file()  # S'assurer que le fichier existe
    target = nettoyer_matriculation(plate)
    if not target:
        return None

    try:
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Nettoyer l'immatriculation stockée pour comparaison robuste
                stored_plate = nettoyer_matriculation(row.get("matriculation", ""))
                if stored_plate == target:
                    return {
                        "matriculation": row.get("matriculation", "").strip(),
                        "marque": row.get("marque", "").strip(),
                        "modele": row.get("modele", "").strip(),
                        "annee": int(row.get("annee", "2020").strip()),
                        "carburant": row.get("carburant", "").strip()
                    }
    except Exception as exc:
        print(f"[CSV_SERVICE] Erreur lors de la recherche dans le CSV : {exc}")
    
    return None

# Initialiser le fichier lors de l'import pour être sûr qu'il existe
init_csv_file()
