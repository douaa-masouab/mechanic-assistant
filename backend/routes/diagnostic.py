from fastapi import APIRouter, HTTPException
from backend.schemas import (
    DiagnosticRequest,
    DiagnosticResponse,
    ChatRequest,
    ChatResponse,
    UserProfileRequest,
    UserProfileResponse,
    UserHistoryResponse,
    UserAuthRequest,
    UserAuthResponse,
    UserRegisterRequest,
    UserLoginRequest,
    VehiclePlateResponse,
)
from backend.services.diagnostic_service import diagnostiquer, get_all_obd_codes
from backend.services.chat_service import process_chat
from backend.services.user_service import save_user_profile
from backend.database import (
    verify_registered_user,
    register_user,
    login_user,
    get_user_history,
    delete_history_entry,
    delete_all_user_history,
)
from backend.services.csv_service import rechercher_vehicule

router = APIRouter(tags=["Diagnostic"])


# ─── Diagnostic OBD ────────────────────────────────────────────────────────────

@router.post("/diagnostiquer", response_model=DiagnosticResponse)
async def diagnostiquer_endpoint(req: DiagnosticRequest):
    try:
        return diagnostiquer(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ─── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        return process_chat(req)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement du chat: {str(exc)}")


# ─── Profil utilisateur (compatibilité) ────────────────────────────────────────

@router.post("/user/profile", response_model=UserProfileResponse)
async def user_profile_endpoint(req: UserProfileRequest):
    try:
        return save_user_profile(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Historique ────────────────────────────────────────────────────────────────

@router.get("/user/history", response_model=list[UserHistoryResponse])
async def user_history_endpoint(user_id: int):
    """Récupère l'historique privé d'un utilisateur connecté."""
    try:
        return get_user_history(user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/user/history/{entry_id}")
async def delete_history_entry_endpoint(entry_id: int, user_id: int):
    """Supprime une entrée d'historique appartenant à l'utilisateur."""
    try:
        deleted = delete_history_entry(entry_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Entrée introuvable ou non autorisée.")
        return {"success": True, "deleted_id": entry_id}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/user/history")
async def delete_all_history_endpoint(user_id: int):
    """Supprime tout l'historique d'un utilisateur."""
    try:
        delete_all_user_history(user_id)
        return {"success": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Codes OBD ─────────────────────────────────────────────────────────────────

@router.get("/obd-codes")
async def obd_codes_endpoint():
    return get_all_obd_codes()


# ─── Authentification réelle (app_users) ───────────────────────────────────────

@router.post("/auth/register", response_model=UserAuthResponse)
async def register_endpoint(req: UserRegisterRequest):
    """Inscription d'un nouvel utilisateur (Nom + Email + Mot de passe)."""
    if len(req.password.strip()) < 4:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 4 caractères.")
    try:
        user = register_user(req.name, req.email, req.password)
        return UserAuthResponse(user_id=user["id"], name=user["name"], email=user["email"])
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'inscription: {str(exc)}")


@router.post("/auth/login", response_model=UserAuthResponse)
async def login_endpoint(req: UserLoginRequest):
    """Connexion par Email + Mot de passe."""
    try:
        user = login_user(req.email, req.password)
        return UserAuthResponse(user_id=user["id"], name=user["name"], email=user["email"])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la connexion: {str(exc)}")


# ─── Recherche par immatriculation ─────────────────────────────────────────────

@router.get("/vehicle/plate", response_model=VehiclePlateResponse)
async def vehicle_plate_endpoint(matriculation: str):
    """Recherche un véhicule par sa plaque marocaine dans le fichier CSV."""
    try:
        vehicle = rechercher_vehicule(matriculation)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Immatriculation introuvable dans la base de données.")
        return VehiclePlateResponse(**vehicle)
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(exc)}")
