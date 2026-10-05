import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from packages.browser.errors import BrowserStartupError
from packages.browser.manager import BrowserManager


@pytest.mark.asyncio
async def test_manager_singleton() -> None:
    manager1 = BrowserManager()
    manager2 = BrowserManager()
    assert manager1 is manager2


@pytest.mark.asyncio
@patch("packages.browser.manager.async_playwright")
async def test_manager_startup_success(mock_playwright: Any) -> None:
    mock_pw_instance = AsyncMock()
    mock_browser = AsyncMock()
    mock_pw_instance.chromium.launch.return_value = mock_browser
    mock_playwright.return_value.start = AsyncMock(return_value=mock_pw_instance)

    manager = BrowserManager()
    # Reset state for test isolation
    manager._browser = None

    await manager.start()

    assert manager._playwright is not None
    assert manager._browser is not None


@pytest.mark.asyncio
async def test_manager_disabled_in_settings(monkeypatch: Any) -> None:
    monkeypatch.setattr("packages.browser.manager.settings.BROWSER_ENABLED", False)
    manager = BrowserManager()
    manager._browser = None

    with pytest.raises(BrowserStartupError, match="Browser automation is disabled"):
        await manager.start()


@pytest.mark.asyncio
@patch("packages.browser.manager.async_playwright")
async def test_create_session(mock_playwright: Any) -> None:
    mock_pw_instance = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_pw_instance.chromium.launch.return_value = mock_browser
    mock_playwright.return_value.start = AsyncMock(return_value=mock_pw_instance)

    manager = BrowserManager()
    manager._browser = None
    await manager.start()

    from unittest.mock import MagicMock

    db_session_mock = MagicMock()
    user_id = uuid.uuid4()

    # We need to mock BrowserTracer and BrowserSessionModel properly if needed,
    # or just let them act as simple objects.
    with (
        patch("packages.browser.session.BrowserSessionModel"),
        patch("packages.browser.manager.BrowserTracer"),
    ):
        session = await manager.create_session(user_id, db_session_mock)
        assert session.user_id == user_id
        assert session.state == "ACTIVE"
        assert session.session_id in manager._active_sessions

        await manager.close_session(session.session_id)
        assert session.session_id not in manager._active_sessions
