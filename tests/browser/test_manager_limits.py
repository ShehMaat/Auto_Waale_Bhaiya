import uuid

import pytest

from packages.browser.errors import BrowserSessionError
from packages.browser.manager import BrowserManager
from packages.config.settings import settings


@pytest.mark.asyncio
async def test_manager_max_sessions_limit() -> None:
    manager = BrowserManager()

    # Mock playwright launch
    manager._browser = True  # bypass await self.start()

    # Fake settings
    original_max = settings.BROWSER_MAX_SESSIONS
    settings.BROWSER_MAX_SESSIONS = 2

    try:
        user_id = uuid.uuid4()
        # Create 2 sessions
        manager._active_sessions[uuid.uuid4()] = "session1"
        manager._active_sessions[uuid.uuid4()] = "session2"

        with pytest.raises(BrowserSessionError, match="Maximum concurrent sessions .* reached"):
            await manager.create_session(user_id=user_id, db_session=None)
    finally:
        settings.BROWSER_MAX_SESSIONS = original_max
        manager._active_sessions.clear()
        manager._browser = None
