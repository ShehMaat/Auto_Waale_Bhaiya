from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.app.main import app
from packages.db.base import Base


@pytest.fixture(scope="module")
def client():  # type: ignore[no-untyped-def]
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_engine() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def mock_db_session(monkeypatch, test_engine) -> None:
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Patch all imports of SessionLocal
    monkeypatch.setattr("packages.db.session.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("packages.db.session.engine", test_engine)

    # Also patch workflow orchestrator if it imported it directly
    try:
        monkeypatch.setattr(
            "packages.application.workflow.orchestrator.SessionLocal", TestingSessionLocal
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "packages.application.workflow.nodes.SessionLocal", TestingSessionLocal
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr("apps.api.app.api.deps.SessionLocal", TestingSessionLocal)
    except AttributeError:
        pass

import pytest_asyncio
from packages.browser.manager import BrowserManager

@pytest_asyncio.fixture(autouse=True)
async def cleanup_browser_manager():
    yield
    manager = BrowserManager()
    if getattr(manager, "_initialized", False):
        await manager.stop()
    manager._initialized = False
    BrowserManager._instance = None
