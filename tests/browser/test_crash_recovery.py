import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.browser.errors import BrowserClosedError
from packages.browser.worker import BrowserWorker
from packages.schemas.browser_actions import ClickAction, PageModel


@pytest.mark.asyncio
async def test_page_crash_recovery() -> None:
    """
    Simulates an actual page crash where session.page becomes None or is unusable,
    verifying that BrowserClosedError is raised to trigger checkpoint recovery.
    """
    mock_manager = AsyncMock()
    mock_db = MagicMock()

    user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    class MockSession:
        def __init__(self):
            self.user_id = user_id
            self.application_id = uuid.uuid4()

        def get_active_page(self):
            return None  # Simulating a crashed/closed page

    mock_manager.get_session.return_value = MockSession()

    worker = BrowserWorker(mock_manager, mock_db)

    action = ClickAction(
        action_id="1", session_id=str(session_id), snapshot_id="123", element_id="btn"
    )

    page_model = PageModel(url="http://test.com", title="Test", snapshot_id="123", elements=[])

    with pytest.raises(
        BrowserClosedError, match="Session has no active page. It may have crashed."
    ):
        await worker.execute_actions_safely(
            user_id=user_id,
            application_id=mock_manager.get_session.return_value.application_id,
            session_id=session_id,
            actions=[action],
            page_model=page_model,
        )
