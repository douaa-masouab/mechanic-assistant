import os
import json
import uuid
import re
from typing import Dict, List, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

from backend.schemas import ChatRequest, ChatResponse
from backend.database import create_or_update_user, save_user_history

load_dotenv()

# Chemins vers les bases locales
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OBD_PATH = os.path.join(BASE_DIR, "data", "obd_codes.json")
VEHICLES_PATH = os.path.join(BASE_DIR, "data", "vehicles.json")

try:
    with open(OBD_PATH, "r", encoding="utf-8") as f:
        OBD_DB = json.load(f)
except Exception:
    OBD_DB = {}

try:
    with open(VEHICLES_PATH, "r", encoding="utf-8") as f:
        VEHICLES_DB = json.load(f)
except Exception:
    VEHICLES_DB = []

# Config de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Dictionnaire de stockage en mémoire pour l'historique des sessions
SESSIONS_HISTORY: Dict[str, List[dict]] = {}

# Base de données enrichie de détails supplémentaires (symptômes + conseils) par code OBD
OBD_DETAILS = {
    "P0300": {
        "symptoms": ["Vibrations et secousses du moteur au ralenti", "Hésitations à l'accélération", "Perte de puissance notable", "Témoin moteur clignotant", "Surconsommation de carburant", "Odeur d'essence à l'échappement"],
        "tip": "Remplacez les bougies tous les 30 000 à 60 000 km selon le constructeur. Inspectez les fils de bougies et les bobines d'allumage à chaque révision."
    },
    "P0171": {
        "symptoms": ["Mode dégradé activé", "Ralenti instable ou irrégulier", "Hésitations lors de l'accélération", "Témoin moteur allumé en continu", "Surconsommation légère de carburant"],
        "tip": "Nettoyez le capteur MAF tous les 20 000 km. Remplacez le filtre à air selon les préconisations du constructeur. Vérifiez l'étanchéité du collecteur d'admission à chaque vidange."
    },
    "P0420": {
        "symptoms": ["Témoin moteur allumé", "Légère perte de puissance", "Odeur d'œuf pourri à l'échappement", "Augmentation des émissions polluantes", "Bruit métallique sous le véhicule"],
        "tip": "Utilisez du carburant de bonne qualité pour préserver le catalyseur. Effectuez un contrôle des émissions tous les 2 ans. Remplacez le catalyseur au-delà de 150 000 km si nécessaire."
    },
    "P0700": {
        "symptoms": ["Mode dégradé activé", "Passages de vitesses brutaux", "Boîte bloquée sur un rapport", "Témoin de boîte allumé", "Fuites d'huile"],
        "tip": "Vidangez l'huile de boîte automatique tous les 60 000 km. Ne dépassez jamais la charge tractable maximale."
    }
}

SYMPTOM_ADVICE = {
    "fumée": "La fumée indique souvent un défaut de combustion ou un problème d'émission. Pour le code P0420, cela peut signifier que le catalyseur est usé ou que la sonde lambda en aval est défectueuse.",
    "fumee": "La fumée indique souvent un défaut de combustion ou un problème d'émission. Pour le code P0420, cela peut signifier que le catalyseur est usé ou que la sonde lambda en aval est défectueuse.",
    "bruit": "Un bruit anormal peut venir d'un composant moteur défectueux, d'un capteur HS ou d'un problème d'échappement. Précisez si c'est un claquement, un sifflement ou un cognement.",
    "démarrage": "Un démarrage difficile peut provenir d'un mauvais apport en carburant, d'un capteur de position défectueux ou d'un allumage irrégulier.",
    "demarrage": "Un démarrage difficile peut provenir d'un mauvais apport en carburant, d'un capteur de position défectueux ou d'un allumage irrégulier.",
    "ralenti": "Un ralenti instable est souvent lié à un capteur de débit d'air, à une sonde lambda ou à une arrivée d'air parasite.",
    "perte de puissance": "Une perte de puissance peut indiquer un catalyseur bouché, un capteur d'oxygène défectueux ou un souci de combustion.",
    "témoin moteur": "Un témoin moteur allumé peut être causé par un capteur défaillant ou un problème de combustion. Donnez-moi la couleur de la fumée ou d'autres symptômes.",
    "temoin moteur": "Un témoin moteur allumé peut être causé par un capteur défaillant ou un problème de combustion. Donnez-moi la couleur de la fumée ou d'autres symptômes."
}

SYSTEM_PROMPT = """
Tu es "Mechanic Assistant", l'assistant de diagnostic automobile expert et convivial.
Ton but est de fournir un diagnostic technique de niveau professionnel, hautement structuré, très conversationnel et convivial.

Tu dois toujours répondre comme un assistant capable de discuter naturellement, sans paraître mécanique.
Tu dois impérativement utiliser des balises spéciales (custom XML tags) pour afficher des fiches interactives à l'utilisateur à des moments clés. Voici les 4 balises que tu DOIS utiliser :

1️⃣ BALISE DE SYNTHÈSE DE DIAGNOSTIC :
Dès que l'utilisateur te fournit un code erreur OBD-II (ex: P0300, P0171, P0420) ou un symptôme clair, effectue l'analyse et insère TOUJOURS au tout début de ta réponse la balise suivante :
<diagnostic code="[CODE_OBD]" title="[TITRE_DE_L_ERREUR]" severity="[moderate ou critical]" price="[ESTIMATION_COUT_EX_80DH-500DH]" time="[DUREE_ESTIMEE_EX_30min-2h]" steps="[NB_ETAPES_EX_4 étapes]" causes="[CAUSE1|CAUSE2|CAUSE3]"/>

Exemple exact :
<diagnostic code="P0171" title="Mélange trop pauvre — Banque 1" severity="moderate" price="80DH — 500DH" time="30 min — 2h" steps="4 étapes" causes="Fuite d'air au collecteur d'admission|Capteur MAF encrassé ou défectueux|Injecteurs partiellement bouchés|Pression de carburant insuffisante|Joint de collecteur défectueux"/>

En dehors de la balise, salue l'utilisateur chaleureusement et invite-le à cliquer sur "Guidage étape par étape" ou à te poser ses questions.

2️⃣ BALISE D'ÉTAPE DE RÉPARATION ACTIVE :
Dès que l'utilisateur demande le guidage étape par étape ou valide une étape précédente, tu dois formater l'étape actuelle en utilisant TOUJOURS la balise suivante :
<step number="[NUMERO_ETAPE]" title="[TITRE_ETAPE]" difficulty="[easy, medium, ou hard]" time="[DUREE_ESTIMEE_EX_10-15 min]" tools="[OUTIL1|OUTIL2]">[DESCRIPTION_DETAILLEE_DE_L_ACTION]</step>

Exemple exact :
<step number="1" title="Nettoyage du capteur MAF" difficulty="easy" time="10-15 min" tools="Spray nettoyant MAF|Tournevis">Démontez le capteur MAF et nettoyez-le avec un spray spécifique MAF. Laissez sécher complètement avant remontage. C'est la cause la plus fréquente du code P0171.</step>

En dehors de la balise, écris une courte phrase d'accompagnement positive (pas de gros paragraphes répétant la description).

3️⃣ BALISE DE RÉSOLUTION ET SUCCÈS :
Dès que l'utilisateur te signale que son problème est résolu, conclus impérativement le diagnostic en insérant la balise suivante :
<success maintenance="[CONSEIL_D_ENTRETIEN_PREVENTIF]">[TEXTE_FELICITATIONS_ET_EFFACEMENT_CODE]</success>

Exemple exact :
<success maintenance="Nettoyez le capteur MAF tous les 20 000 km. Remplacez le filtre à carburant selon les préconisations du constructeur.">Le diagnostic du code P0171 est terminé et votre problème est résolu. Pensez à effacer le code défaut avec votre scanner OBD-II.</success>

4️⃣ BALISE DE DÉTAILS SUPPLÉMENTAIRES :
Dès que l'utilisateur te demande "plus d'infos" ou "plus de détails" sur un code, insère la balise de détails supplémentaires suivante :
<detailsinfo code="[CODE_OBD]" symptoms="[SYMPTOME1|SYMPTOME2|SYMPTOME3]" tip="[CONSEIL_D_ENTRETIEN_COMPLET]"/>

Exemple exact :
<detailsinfo code="P0700" symptoms="Mode dégradé activé|Passages de vitesses brutaux|Boîte bloquée sur un rapport|Témoin de boîte allumé|Fuites d'huile" tip="Vidangez l'huile de boîte automatique tous les 60 000 km. Ne dépassez jamais la charge tractable maximale."/>

En dehors de la balise, écris une courte phrase d'accompagnement.

Directives supplémentaires :
- Si l'utilisateur mentionne un véhicule dans la discussion ou via les métadonnées de notification, intègre spécifiquement les particularités techniques de son modèle.
- Reste toujours concis, extrêmement professionnel et utilise un ton rassurant.
"""

def _find_last_marker(history: List[dict], prefix: str) -> str:
    for h in reversed(history):
        text = h["parts"][0] if h.get("parts") else ""
        if prefix in text:
            return text.split(":")[-1].replace("]", "").strip()
    return ""


def _get_current_obd(message: str, history: List[dict]) -> str:
    obd_match = re.search(r"\b[PBCUA]\d{4}\b", message.upper())
    if obd_match:
        return obd_match.group(0)
    return _find_last_marker(history, "[SYSTEM:FALLBACK_OBD:")


def _get_last_vehicle(history: List[dict]) -> str:
    return _find_last_marker(history, "[SYSTEM:VEHICLE:")


def _store_obd_code(history: List[dict], code: str):
    if code:
        history.append({"role": "user", "parts": [f"[SYSTEM:FALLBACK_OBD:{code}]"]})


def _store_vehicle(history: List[dict], vehicle: str):
    if vehicle:
        history.append({"role": "user", "parts": [f"[SYSTEM:VEHICLE:{vehicle}]"]})


def _get_current_step(history: List[dict]) -> int:
    step = _find_last_marker(history, "[SYSTEM:FALLBACK_STEP:")
    return int(step) if step.isdigit() else 0


def _store_step(history: List[dict], step: int):
    history.append({"role": "user", "parts": [f"[SYSTEM:FALLBACK_STEP:{step}]"]})


def _render_step_card(step: dict, number: int) -> str:
    tools = step.get("tools", "Outils génériques").replace(",", "|")
    return f'<step number="{number}" title="{step.get("titre", "Étape")}" difficulty="{step.get("difficulty", "medium")}" time="{step.get("time", "10-15 min")}" tools="{tools}">{step.get("description", "Effectuez cette étape.")}</step>'


def _get_fallback_reply(message: str, history: List[dict]) -> str:
    """Simulation de secours haut de gamme intégrant les fiches interactives de diagnostic, d'étape et de succès."""
    msg_lower = message.lower()
    
    detected_vehicle = None
    veh_match = re.search(r"\[VEHICULE:\s*([^\]]+)\]", message)
    if veh_match:
        detected_vehicle = veh_match.group(1)
    else:
        # Prise en charge des notifications de véhicule venant du frontend
        veh_match = re.search(r"\[NOTIFICATION V[ÉE]HICULE\]\s*(.*)", message, re.IGNORECASE)
        if veh_match:
            detected_vehicle = veh_match.group(1).strip()

    if detected_vehicle:
        _store_vehicle(history, detected_vehicle)
    else:
        detected_vehicle = _get_last_vehicle(history)

    current_obd = _get_current_obd(message, history)
    info = OBD_DB.get(current_obd, {}) if current_obd else {}
    etapes = info.get("etapes", []) if info else []
    
    is_plus_infos = any(k in msg_lower for k in ["plus d'infos", "plus d'informations", "plus de détails", "details", "donne-moi plus", "explique"])
    is_step_done = any(k in msg_lower for k in ["j'ai effectué", "effectuée", "suivant", "fait l'étape", "fait l etape", "terminé", "terminée"])
    is_start_guidage = any(k in msg_lower for k in ["guidage", "guide-moi", "guide moi", "commençons le guidage", "démarrons le guidage"]) and not is_step_done
    if not is_step_done and "étape suivante" in msg_lower:
        is_step_done = True
    is_resolved = any(k in msg_lower for k in ["résolu", "probleme resolu", "problème résolu", "ça marche", "c'est réparé", "réparé", "résolution", "résoudre"])
    is_direct_solution = any(k in msg_lower for k in ["solution", "immédiat", "maintenant", "vite", "répare", "répare-moi", "urgent", "s'il te plaît"]) and not is_plus_infos
    is_why_question = any(k in msg_lower for k in ["pourquoi", "cause", "causes", "explique", "explication", "comment ça se fait"])
    is_general_problem = any(phrase in msg_lower for phrase in ["j'ai un problème", "j'ai des problèmes", "j'ai un souci", "j'ai un probleme", "j'ai des probleme"])

    if is_general_problem and not is_start_guidage and not is_plus_infos and not is_step_done and not is_resolved:
        if current_obd:
            return f"Je comprends que vous avez un problème avec le code **{current_obd}**. Décrivez-moi précisément le symptôme : démarrage difficile, bruit, fumée, perte de puissance ou témoin moteur allumé ?"
        return "Je suis là pour vous aider comme un vrai chatbot. Décrivez-moi votre symptôme en phrases naturelles : fumée, bruit métallique, démarrage difficile, perte de puissance, témoin moteur allumé, etc."

    salutations = ["bonjour", "salut", "hello", "hi", "hey", "commencer", "aide"]
    is_salutation = any(s in msg_lower for s in salutations) and len(message) < 30

    if is_salutation:
        return "Bonjour ! Je suis **MécaBot AI**, votre mécanicien expert. Dites-moi simplement ce que vous constatez sur votre véhicule, ou donnez-moi un code OBD-II comme `P0171`."

    # Détection de symptôme naturel pour relance conversationnelle
    for symptom, advice in SYMPTOM_ADVICE.items():
        if symptom in msg_lower and not is_start_guidage and not is_plus_infos and not is_step_done and not is_resolved:
            if current_obd:
                return f"Je vois un symptôme de type **{symptom}** associé au code **{current_obd}**. {advice} Précisez la couleur de la fumée, le comportement du moteur ou si le témoin reste allumé."
            return f"{advice} Si vous avez un code OBD, indiquez-le-moi pour que je puisse affiner le diagnostic par rapport à votre véhicule."

    if is_direct_solution and current_obd:
        answer = f"Voici une solution rapide pour le code **{current_obd}** :"
        if current_obd == "P0420":
            answer += " contrôlez le catalyseur et la sonde lambda aval, puis remplacez le catalyseur si la réparation est justifiée."
        elif current_obd == "P0300":
            answer += " vérifiez les bougies, bobines et faisceaux d'allumage. Remplacez les bougies usées et testez chaque cylindre."
        else:
            answer += " commencez par une inspection visuelle rapide des connecteurs, durites et capteurs autour du moteur."
        return answer

    if current_obd and not is_start_guidage and not is_plus_infos and not is_step_done and not is_resolved:
        _store_obd_code(history, current_obd)

        desc = info.get("description", "Code d'anomalie moteur détecté affectant les performances du groupe motopropulseur.")
        causes = info.get("causes", ["Capteur encrassé ou défectueux", "Câblage corrodé ou déconnecté", "Prise d'air sur le collecteur"])
        causes_str = "|".join(causes)
        severity = "critical" if current_obd in ["P0300", "P0700"] else "moderate"
        price_est = "120DH — 600DH" if severity == "critical" else "80DH — 300DH"
        time_est = "1h — 3h" if severity == "critical" else "30 min — 2h"
        steps_count = f"{len(etapes) if etapes else 2} étapes"
        vehicle_note = f" pour votre **{detected_vehicle}**" if detected_vehicle else ""

        reply = f'<diagnostic code="{current_obd}" title="{desc}" severity="{severity}" price="{price_est}" time="{time_est}" steps="{steps_count}" causes="{causes_str}"/>\n\n'
        reply += f"J'ai bien reçu le code **{current_obd}**{vehicle_note}. Je peux vous conseiller rapidement ou vous guider étape par étape."
        return reply

    if is_plus_infos:
        if not current_obd:
            current_obd = _find_last_marker(history, "[SYSTEM:FALLBACK_OBD:") or "P0171"
        details = OBD_DETAILS.get(current_obd, {
            "symptoms": ["Témoin moteur allumé", "Perte de performance", "Ralenti instable", "Surconsommation de carburant"],
            "tip": "Effectuez un entretien régulier selon les préconisations du constructeur. Faites scanner votre véhicule tous les 6 mois."
        })
        symptoms_str = "|".join(details["symptoms"])
        tip = details["tip"]
        return f'<detailsinfo code="{current_obd}" symptoms="{symptoms_str}" tip="{tip}"/>\n\nVoici les détails supplémentaires pour le code **{current_obd}**.'

    if is_start_guidage:
        if not current_obd:
            return "Pour démarrer le guidage, saisissez d'abord un code OBD-II ou sélectionnez un code existant dans le chat."

        _store_obd_code(history, current_obd)
        _store_step(history, 1)

        if etapes:
            step = etapes[0]
            return _render_step_card({
                "titre": step.get("titre", "Première étape"),
                "description": step.get("description", "Réalisez cette première étape."),
                "difficulty": step.get("difficulty", "easy"),
                "time": step.get("time", "10-15 min"),
                "tools": step.get("tools", "Spray nettoyant MAF|Tournevis")
            }, 1) + "\n\nDémarrons le guidage. Réalisez cette étape et dites-moi lorsque c'est fait."
        return _render_step_card({
            "titre": "Inspection visuelle initiale",
            "description": "Ouvrez le capot et vérifiez les connexions, durites et capteurs autour du moteur.",
            "difficulty": "easy",
            "time": "10-15 min",
            "tools": "Lampe de poche|Gants"
        }, 1) + "\n\nDémarrons le guidage. Réalisez cette étape et indiquez-moi si vous avez besoin de continuer."

    if is_step_done:
        current_step = _get_current_step(history)
        if current_step == 0:
            return "Je n'ai pas de guidage en cours. Commencez d'abord par un code OBD et demandez le guidage étape par étape."
        next_step = current_step + 1
        _store_step(history, next_step)

        if etapes and next_step <= len(etapes):
            step = etapes[next_step - 1]
            return _render_step_card({
                "titre": step.get("titre", f"Étape {next_step}"),
                "description": step.get("description", "Continuez avec cette action."),
                "difficulty": step.get("difficulty", "medium"),
                "time": step.get("time", "15-30 min"),
                "tools": step.get("tools", "Outils appropriés")
            }, next_step) + f"\n\nTrès bien. Voici l'étape {next_step}. Réalisez-la puis confirmez si elle est terminée."
        if next_step == 2:
            return _render_step_card({
                "titre": "Recherche de fuites d'air à l'admission",
                "description": "Pulvérisez un nettoyant frein autour des durites d'admission. Si le régime moteur change, vous avez trouvé la fuite.",
                "difficulty": "medium",
                "time": "20-30 min",
                "tools": "Spray détecteur de fuite|Chiffon"
            }, 2) + "\n\nParfait, voici la suite. Faites cette étape et dites-moi si vous avez besoin de l'étape suivante."
        return "Vous avez atteint la fin du guidage de base. Dites-moi si le problème est résolu ou demandez-moi plus de détails techniques."

    if is_resolved:
        if not current_obd:
            current_obd = _find_last_marker(history, "[SYSTEM:FALLBACK_OBD:") or "P0171"
        if current_obd == "P0171":
            return '<success maintenance="Nettoyez le capteur MAF tous les 20 000 km. Remplacez le filtre à carburant selon les préconisations du constructeur.">Le diagnostic du code P0171 est terminé et votre problème est résolu. Pensez à effacer le code défaut avec votre scanner OBD-II.</success>\n\nFélicitations pour cette réparation réussie !'
        return f'<success maintenance="Effectuez un scan régulier de votre véhicule pour prévenir les pannes futures.">Le diagnostic du code {current_obd} est maintenant terminé. N\'oubliez pas d\'effacer le témoin moteur avec votre outil OBD-II.</success>\n\nExcellent travail !'

    if is_why_question and current_obd:
        causes_display = ", ".join(info.get("causes", ["un capteur défectueux", "une prise d'air", "un composant fatigué"]))
        return f'Le code **{current_obd}** signale un dysfonctionnement spécifique : {info.get("description", "un problème moteur général")}. Les causes probables sont {causes_display}. Je peux préciser chaque cause si vous le souhaitez.'

    if is_why_question and not current_obd:
        return "Dites-moi d'abord si vous avez un code OBD ou décrivez le symptôme exact. Je peux alors expliquer pourquoi le problème se produit."

    if detected_vehicle and not current_obd and not is_start_guidage and not is_plus_infos and not is_step_done and not is_resolved:
        return f"J'ai bien enregistré votre véhicule : **{detected_vehicle}**. Décrivez maintenant le symptôme ou donnez-moi un code OBD afin que je vous donne un diagnostic spécifique."

    return "Je suis à votre écoute. Donnez-moi un code OBD-II (ex: `P0171`) ou décrivez le symptôme en mots naturels pour que je vous aide immédiatement."


def process_chat(req: ChatRequest) -> ChatResponse:
    """Traitement de la requête conversationnelle."""
    session_id = req.session_id
    if not session_id:
        session_id = str(uuid.uuid4())

    if session_id not in SESSIONS_HISTORY:
        SESSIONS_HISTORY[session_id] = []

    history = SESSIONS_HISTORY[session_id]
    user_message = req.message.strip()

    user_id = req.user_id
    if not user_id and req.user_email:
        profile_name = (req.user_name or "Invité").strip() or "Invité"
        profile_role = (req.user_role or "").strip()
        user = create_or_update_user(req.user_email.strip().lower(), profile_name, profile_role)
        user_id = user["id"]
        history.append({"role": "system", "parts": [f"[SYSTEM:USER:{user_id}:{req.user_email.strip().lower()}]"]})
    
    # Enregistrer le message utilisateur
    history.append({"role": "user", "parts": [user_message]})

    vehicle_info = req.vehicle.strip() if req.vehicle else None

    # Option A: Gemini AI
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT
            )
            
            chat = model.start_chat(history=[])
            
            for msg in history[:-1]:
                # Écarter les marqueurs internes système du vrai flux Gemini
                if "[SYSTEM:" in msg["parts"][0]:
                    continue
                chat.history.append(
                    genai.types.Content(
                        role="user" if msg["role"] == "user" else "model",
                        parts=[genai.types.Part.from_text(text=msg["parts"][0])]
                    )
                )
            
            response = chat.send_message(user_message)
            reply = response.text.strip()
            
            history.append({"role": "model", "parts": [reply]})
            
            if user_id:
                save_user_history(
                    user_id=user_id,
                    message=user_message,
                    response=reply,
                    session_id=session_id,
                    vehicle=vehicle_info,
                )

            if len(history) > 40:
                SESSIONS_HISTORY[session_id] = history[-40:]
            else:
                SESSIONS_HISTORY[session_id] = history
                
            return ChatResponse(reply=reply, session_id=session_id)
            
        except Exception as e:
            # Fallback en cas d'erreur de clé ou réseau
            reply = _get_fallback_reply(user_message, history)
            history.append({"role": "model", "parts": [reply]})

            if user_id:
                save_user_history(
                    user_id=user_id,
                    message=user_message,
                    response=reply,
                    session_id=session_id,
                    vehicle=vehicle_info,
                )

            SESSIONS_HISTORY[session_id] = history
            return ChatResponse(reply=reply, session_id=session_id)
    else:
        # Option B: Fallback simulation locale
        reply = _get_fallback_reply(user_message, history)
        history.append({"role": "model", "parts": [reply]})

        if user_id:
            save_user_history(
                user_id=user_id,
                message=user_message,
                response=reply,
                session_id=session_id,
                vehicle=vehicle_info,
            )

        SESSIONS_HISTORY[session_id] = history
        return ChatResponse(reply=reply, session_id=session_id)
