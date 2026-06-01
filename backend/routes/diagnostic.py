from fastapi import APIRouter, HTTPException
from backend.schemas import (
    DiagnosticRequest,
    DiagnosticResponse,
    ChatRequest,
    ChatResponse,
    UserProfileRequest,
    UserProfileResponse,
    UserHistoryResponse,
)
from backend.services.diagnostic_service import diagnostiquer, get_all_obd_codes
from backend.services.chat_service import process_chat
from backend.services.user_service import save_user_profile, get_user_history

router = APIRouter(tags=["Diagnostic"])

@router.post("/diagnostiquer", response_model=DiagnosticResponse)
async def diagnostiquer_endpoint(req: DiagnosticRequest):
    try:
        return diagnostiquer(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        return process_chat(req)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur lors du traitement du chat: {str(exc)}")

@router.post("/user/profile", response_model=UserProfileResponse)
async def user_profile_endpoint(req: UserProfileRequest):
    """Créer ou mettre à jour le profil d'un utilisateur professionnel."""
    try:
        return save_user_profile(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur lors de l'enregistrement du profil utilisateur: {str(exc)}")

@router.get("/user/history", response_model=list[UserHistoryResponse])
async def user_history_endpoint(user_id: int):
    """Récupère l'historique privé d'un utilisateur."""
    try:
        return get_user_history(user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur lors de la lecture de l'historique utilisateur: {str(exc)}")

@router.get("/obd-codes")
async def obd_codes_endpoint():
    """Retourne tous les codes OBD chargés depuis JSON et CSV."""
    return get_all_obd_codes()

