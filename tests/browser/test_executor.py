import uuid
from typing import Generator, Tuple
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.browser.executor import ActionExecutor
from packages.db.base import Base
from packages.db.models.browser import BrowserSessionModel
from packages.schemas.browser_actions import (
    ClickAction,
    FillAction,
    NavigateAction,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def setup_user_session(db_session: Session) -> Tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    b_session = BrowserSessionModel(id=session_id, user_id=user_id, state="ACTIVE")
    db_session.add(b_session)
    db_session.commit()
    return user_id, str(session_id)


@pytest.mark.asyncio
async def test_execute_navigate(
    db_session: Session, setup_user_session: Tuple[uuid.UUID, str]
) -> None:
    user_id, session_id = setup_user_session
    page = AsyncMock()
    action = NavigateAction(session_id=session_id, url="https://google.com")

    result = await ActionExecutor.execute(action, page, db_session, user_id)
    assert result["status"] == "SUCCESS"
    page.navigate.assert_awaited_once_with("https://google.com")


@pytest.mark.asyncio
async def test_execute_cross_user_authorization(
    db_session: Session, setup_user_session: Tuple[uuid.UUID, str]
) -> None:
    _, session_id = setup_user_session
    page = AsyncMock()
    action = ClickAction(session_id=session_id, element_id="el-1")

    # Attempt execution with a DIFFERENT user_id
    malicious_user_id = uuid.uuid4()

    with pytest.raises(PermissionError, match="not authorized"):
        await ActionExecutor.execute(action, page, db_session, malicious_user_id)


@pytest.mark.asyncio
async def test_execute_idempotency(
    db_session: Session, setup_user_session: Tuple[uuid.UUID, str]
) -> None:
    user_id, session_id = setup_user_session
    page = AsyncMock()

    action = ClickAction(session_id=session_id, element_id="el-1")

    # First execution succeeds
    result1 = await ActionExecutor.execute(action, page, db_session, user_id)
    assert result1["status"] == "SUCCESS"
    page.click_element.assert_awaited_once_with("el-1")

    # Second execution is blocked as DUPLICATE, click_element NOT called again
    result2 = await ActionExecutor.execute(action, page, db_session, user_id)
    assert result2["status"] == "DUPLICATE"
    page.click_element.assert_awaited_once()  # Still only 1 call


@pytest.mark.asyncio
async def test_execute_challenge_protection(db_session: Session) -> None:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    b_session = BrowserSessionModel(id=session_id, user_id=user_id, state="WAITING_FOR_USER")
    db_session.add(b_session)
    db_session.commit()

    page = AsyncMock()
    action = FillAction(session_id=str(session_id), element_id="el-1", text="test")

    with pytest.raises(PermissionError, match="Session is locked in challenge state"):
        await ActionExecutor.execute(action, page, db_session, user_id)
