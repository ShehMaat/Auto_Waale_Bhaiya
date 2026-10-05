import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.browser.errors import SessionOwnershipError
from packages.browser.worker import BrowserWorker
from packages.schemas.browser_actions import PageModel


@pytest.mark.asyncio
async def test_worker_cross_application_isolation() -> None:
    mock_manager = AsyncMock()
    mock_db = MagicMock()
    worker = BrowserWorker(mock_manager, mock_db)

    user_id = uuid.uuid4()
    app_a = uuid.uuid4()
    app_b = uuid.uuid4()
    session_id = uuid.uuid4()

    class MockSession:
        def __init__(self):
            self.user_id = user_id
            self.application_id = app_a

        def get_active_page(self):
            return None

    mock_manager.get_session.return_value = MockSession()

    # Authorized access (same user, same app)
    # Just checking it doesn't raise SessionOwnershipError for app_a
    # We will get BrowserClosedError since page=None but that means ownership passed
    from packages.browser.errors import BrowserClosedError

    with pytest.raises(BrowserClosedError):
        await worker.execute_actions_safely(
            user_id=user_id,
            application_id=app_a,
            session_id=session_id,
            actions=[],
            page_model=PageModel(
                url="http://test.com", title="Test", snapshot_id="123", elements=[]
            ),
        )

    # Unauthorized access (same user, different app)
    with pytest.raises(SessionOwnershipError, match="Cross-application access denied"):
        await worker.execute_actions_safely(
            user_id=user_id,
            application_id=app_b,
            session_id=session_id,
            actions=[],
            page_model=PageModel(
                url="http://test.com", title="Test", snapshot_id="123", elements=[]
            ),
        )
