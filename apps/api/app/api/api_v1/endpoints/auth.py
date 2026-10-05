from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from apps.api.app.api.deps import SessionDep
from apps.api.app.core.security import create_access_token, get_password_hash, verify_password
from packages.config.settings import settings
from packages.db.models.candidate import User
from packages.schemas.models import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
def login_access_token(db: SessionDep, form_data: OAuth2PasswordRequestForm = Depends()) -> Token:  # noqa: B008
    """OAuth2 compatible token login, get an access token for future requests."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=create_access_token(user.id, expires_delta=access_token_expires),
        token_type="bearer",
    )


@router.post("/register", response_model=UserResponse)
def register_user(db: SessionDep, user_in: UserCreate) -> UserResponse:
    """Register a new user."""
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user  # type: ignore[return-value]
