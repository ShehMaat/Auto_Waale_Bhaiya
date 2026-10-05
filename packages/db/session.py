from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.config.settings import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():  # type: ignore[no-untyped-def]
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
