from fastapi import APIRouter

from apps.api.app.api.deps import CurrentUser
from packages.schemas.models import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: CurrentUser) -> UserResponse:
    """Get current user."""
    return current_user  # type: ignore[return-value]
