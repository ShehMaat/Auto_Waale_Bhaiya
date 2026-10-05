import uuid
from unittest.mock import AsyncMock

import pytest

from packages.browser.page import BrowserPage


@pytest.mark.asyncio
async def test_page_safe_navigation() -> None:
    raw_page = AsyncMock()
    raw_page.url = "https://www.google.com"

    tracer = AsyncMock()
    session_id = uuid.uuid4()

    page = BrowserPage(raw_page, session_id, tracer)

    await page.navigate("https://www.google.com")

    raw_page.goto.assert_called_once_with("https://www.google.com", wait_until="domcontentloaded")
    assert tracer.record_event.call_count == 2
    # First call is navigation_started, second is navigation_completed


@pytest.mark.asyncio
async def test_page_navigation_blocked_scheme() -> None:
    raw_page = AsyncMock()
    tracer = AsyncMock()
    session_id = uuid.uuid4()

    page = BrowserPage(raw_page, session_id, tracer)

    from packages.browser.errors import BrowserPolicyViolation

    with pytest.raises(BrowserPolicyViolation, match="Blocked dangerous scheme"):
        await page.navigate("file:///etc/passwd")

    raw_page.goto.assert_not_called()
    assert tracer.record_event.call_count == 0
    # First is started (Wait, validate throws BEFORE started? Actually validate is called before
    # started.)
    # Let me check the page implementation:
    # safe_url = BrowserSecurityPolicy.validate_navigation_url(url) -> Raises violation directly!
    # Wait, my test asserts BrowserNavigationError, but validate_navigation_url raises
    # BrowserPolicyViolation.
    # Ah, the validate_navigation_url is not inside the try-except in page.navigate.
    with pytest.raises(BrowserPolicyViolation):
        await page.navigate("file:///etc/passwd")
