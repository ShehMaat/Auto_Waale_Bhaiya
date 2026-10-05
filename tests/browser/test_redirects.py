import uuid
from unittest.mock import AsyncMock

import pytest

from packages.browser.page import BrowserPage


@pytest.mark.asyncio
async def test_page_redirect_security_blocked() -> None:
    raw_page = AsyncMock()
    tracer = AsyncMock()
    session_id = uuid.uuid4()

    page = BrowserPage(raw_page, session_id, tracer)

    # Extract the route handler that was registered
    await page._setup_security_routing()
    handle_route = raw_page.route.call_args[0][1]

    mock_route = AsyncMock()
    mock_route.request.is_navigation_request.return_value = True
    # Malicious redirect to 127.0.0.1
    mock_route.request.url = "http://127.0.0.1/admin"

    await handle_route(mock_route)

    # It should abort because of policy violation
    mock_route.abort.assert_called_once_with("accessdenied")
    mock_route.continue_.assert_not_called()
    tracer.record_event.assert_called_once()
    assert tracer.record_event.call_args[0][1] == "navigation_blocked"


@pytest.mark.asyncio
async def test_page_redirect_security_allowed() -> None:
    raw_page = AsyncMock()
    tracer = AsyncMock()
    session_id = uuid.uuid4()

    page = BrowserPage(raw_page, session_id, tracer)

    await page._setup_security_routing()
    handle_route = raw_page.route.call_args[0][1]

    mock_route = AsyncMock()
    mock_route.request.is_navigation_request.return_value = True
    # Safe redirect
    mock_route.request.url = "https://safe.example.com/page"

    await handle_route(mock_route)

    mock_route.continue_.assert_called_once()
    mock_route.abort.assert_not_called()
