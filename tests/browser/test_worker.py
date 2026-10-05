import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.browser.errors import SessionOwnershipError
from packages.browser.worker import BrowserWorker, StaleSnapshotError
from packages.schemas.browser_actions import ClickAction, PageModel


@pytest.mark.asyncio
async def test_worker_ownership_verification() -> None:
    mock_manager = AsyncMock()
    mock_db = MagicMock()
    worker = BrowserWorker(mock_manager, mock_db)

    mock_session = MagicMock()
    mock_session.user_id = uuid.uuid4()
    mock_manager.get_session.return_value = mock_session

    with pytest.raises(SessionOwnershipError):
        await worker.execute_actions_safely(
            user_id=uuid.uuid4(),
            application_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            actions=[],
            page_model=PageModel(
                url="http://test.com", title="Test", snapshot_id="123", elements=[]
            ),
        )


@pytest.mark.asyncio
async def test_worker_stale_snapshot() -> None:
    mock_manager = AsyncMock()
    mock_db = MagicMock()
    worker = BrowserWorker(mock_manager, mock_db)

    user_id = uuid.uuid4()
    mock_session = MagicMock()
    mock_session.user_id = user_id
    mock_session.application_id = uuid.uuid4()
    mock_session.get_active_page = MagicMock(return_value=AsyncMock())
    mock_manager.get_session.return_value = mock_session

    action = ClickAction(
        action_id="1", session_id=str(uuid.uuid4()), snapshot_id="stale", element_id="btn"
    )

    page_model = PageModel(url="http://test.com", title="Test", snapshot_id="fresh", elements=[])

    with pytest.raises(StaleSnapshotError):
        await worker.execute_actions_safely(
            user_id=user_id,
            application_id=mock_session.application_id,
            session_id=uuid.uuid4(),
            actions=[action],
            page_model=page_model,
        )
