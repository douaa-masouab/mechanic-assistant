from pydantic import BaseModel, Field
from typing import List, Optional

class DiagnosticRequest(BaseModel):
    code_obd: str = Field(..., description="Code OBD‑II (ex. P0300)")
    marque: str = Field(..., description="Marque du véhicule (ex. Toyota)")
    modele: str = Field(..., description="Modèle du véhicule (ex. Corolla)")
    annee: int = Field(..., description="Année de mise en circulation")

class Etape(BaseModel):
    titre: str
    description: str

class DiagnosticResponse(BaseModel):
    code_obd: str
    description: str
    causes_possibles: List[str]
    solutions: List[Etape]
    vehicule_valide: bool = True
    message: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., description="Message envoyé par l'utilisateur")
    session_id: Optional[str] = Field(None, description="Identifiant unique de la session de chat")
    user_id: Optional[int] = Field(None, description="Identifiant de l'utilisateur enregistré")
    user_email: Optional[str] = Field(None, description="Email de l'utilisateur professionnel")
    user_name: Optional[str] = Field(None, description="Nom de l'utilisateur professionnel")
    user_role: Optional[str] = Field(None, description="Rôle ou fonction de l'utilisateur")
    vehicle: Optional[str] = Field(None, description="Informations du véhicule sélectionné, si disponibles")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Réponse du bot en format Markdown")
    session_id: str = Field(..., description="Identifiant de session de chat retourné")

class UserProfileRequest(BaseModel):
    email: str = Field(..., description="Email professionnel unique de l'utilisateur")
    name: str = Field(..., description="Nom ou nom d'entreprise")
    role: Optional[str] = Field(None, description="Fonction ou poste")

class UserProfileResponse(BaseModel):
    user_id: int
    email: str
    name: str
    role: Optional[str] = None

class UserHistoryResponse(BaseModel):
    id: int
    session_id: Optional[str]
    user_message: str
    bot_reply: str
    vehicle: Optional[str]
    created_at: str

# ─── Auth réelle (app_users) ───────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    name: str = Field(..., description="Prénom ou nom complet")
    email: str = Field(..., description="Adresse email unique")
    password: str = Field(..., description="Mot de passe (min 4 caractères)")

class UserLoginRequest(BaseModel):
    email: str = Field(..., description="Adresse email")
    password: str = Field(..., description="Mot de passe")

class UserAuthResponse(BaseModel):
    user_id: int
    name: str
    email: str

# ─── Immatriculation ───────────────────────────────────────────────────────────

class VehiclePlateResponse(BaseModel):
    matriculation: str
    marque: str
    modele: str
    annee: int
    carburant: str

# ─── Suppression d'historique ──────────────────────────────────────────────────

class UserAuthRequest(BaseModel):
    name: str = Field(..., description="Nom d'utilisateur (ancien système)")
    code: str = Field(..., description="Code d'accès/PIN (ancien système)")
