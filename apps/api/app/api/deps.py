from typing import Annotated, Generator
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from packages.config.settings import settings
from packages.db.models.candidate import User
from packages.db.session import SessionLocal
from packages.llm.gemini_provider import GeminiProvider
from packages.llm.openai_provider import OpenAIProvider
from packages.llm.provider import LLMProvider
from packages.schemas.models import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_db)]


def get_current_user(db: SessionDep, token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        token_data = TokenPayload(**payload)
    except jwt.InvalidTokenError:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = db.query(User).filter(User.id == UUID(token_data.sub)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "gemini":
        return GeminiProvider()
    return OpenAIProvider()
