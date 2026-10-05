from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.app.api.api_v1.api import api_router
from apps.api.app.api.deps import get_db
from packages.config.settings import settings

app = FastAPI(
    title="AI Job Application Agent API",
    version="0.1.0",
)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health_check():  # type: ignore[no-untyped-def]
    return {"status": "ok"}


@app.get("/ready")
def ready_check(db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]  # noqa: B008
    # Check DB
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        return {"status": "error", "component": "database", "message": str(e)}

    # Check Redis
    try:
        r = Redis.from_url(settings.REDIS_URL)
        r.ping()
    except Exception as e:
        return {"status": "error", "component": "redis", "message": str(e)}

    return {"status": "ready"}


app.include_router(api_router, prefix="/api/v1")
