from backend.schemas import UserProfileRequest, UserProfileResponse
from backend.database import create_or_update_user, get_user_history as db_get_user_history


def save_user_profile(req: UserProfileRequest) -> UserProfileResponse:
    user = create_or_update_user(req.email.strip().lower(), req.name.strip(), (req.role or '').strip())
    return UserProfileResponse(
        user_id=user['id'],
        email=user['email'],
        name=user['name'],
        role=user['role']
    )


def get_user_history(user_id: int):
    return db_get_user_history(user_id)
