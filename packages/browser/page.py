import uuid
from typing import Any

from packages.browser.errors import BrowserNavigationError, BrowserPolicyViolation
from packages.browser.policies import BrowserSecurityPolicy
from packages.browser.tracing import BrowserTracer


class BrowserPage:
    """
    Encapsulates a Playwright Page to prevent arbitrary code execution leaks.
    Only exposes strictly typed, policy-enforced primitives.
    """

    def __init__(self, raw_page: Any, session_id: uuid.UUID, tracer: BrowserTracer):
        self._page = raw_page
        self._session_id = session_id
        self._tracer = tracer

    async def _setup_security_routing(self) -> None:
        """Enforces security policies natively via Playwright request interception."""

        async def handle_route(route: Any) -> None:
            if route.request.is_navigation_request():
                try:
                    BrowserSecurityPolicy.validate_navigation_url(route.request.url)
                    await route.continue_()
                except BrowserPolicyViolation as e:
                    self._tracer.record_event(
                        self._session_id,
                        "navigation_blocked",
                        page_url=route.request.url,
                        metadata={"reason": str(e)},
                    )
                    await route.abort("accessdenied")
            else:
                await route.continue_()

        await self._page.route("**/*", handle_route)

    async def navigate(self, url: str) -> None:
        """Navigates to a URL safely using the policy engine."""
        safe_url = BrowserSecurityPolicy.validate_navigation_url(url)

        self._tracer.record_event(self._session_id, "navigation_started", page_url=safe_url)

        try:
            # Enforce navigation timeouts from config in actual implementation
            await self._page.goto(safe_url, wait_until="domcontentloaded")

            final_url = self._page.url

            self._tracer.record_event(self._session_id, "navigation_completed", page_url=final_url)
        except Exception as e:
            self._tracer.record_event(
                self._session_id, "navigation_failed", page_url=safe_url, metadata={"error": str(e)}
            )
            raise BrowserNavigationError(f"Navigation failed: {str(e)}") from e

    async def get_url(self) -> str:
        """Returns the current URL."""
        return str(self._page.url)

    async def get_title(self) -> str:
        """Returns the page title."""
        return str(await self._page.title())

    async def get_visible_text(self) -> str:
        """Extracts visible text. Safe internal primitive."""
        return str(await self._page.evaluate("document.body.innerText"))

    async def screenshot(self, path: str) -> None:
        """Takes a safe screenshot to a controlled path."""
        await self._page.screenshot(path=path)

    async def click_element(self, element_id: str) -> None:
        """Clicks an element by its tracked logical ID."""
        locator = self._page.locator(f'[data-job-agent-id="{element_id}"]')
        await locator.click(timeout=5000)

    async def fill_element(self, element_id: str, text: str) -> None:
        """Fills text into an element by its tracked logical ID."""
        locator = self._page.locator(f'[data-job-agent-id="{element_id}"]')
        await locator.fill(text, timeout=5000)

    async def select_option(self, element_id: str, option_value: str) -> None:
        locator = self._page.locator(f'[data-job-agent-id="{element_id}"]')
        await locator.select_option(value=option_value, timeout=5000)

    async def check(self, element_id: str) -> None:
        locator = self._page.locator(f'[data-job-agent-id="{element_id}"]')
        await locator.check(timeout=5000)

    async def uncheck(self, element_id: str) -> None:
        locator = self._page.locator(f'[data-job-agent-id="{element_id}"]')
        await locator.uncheck(timeout=5000)

    async def upload_file(self, element_id: str, file_path: str) -> None:
        locator = self._page.locator(f'[data-job-agent-id="{element_id}"]')
        await locator.set_input_files(file_path, timeout=5000)

    async def press_key(self, key: str) -> None:
        await self._page.keyboard.press(key)

    async def scroll(self, direction: str) -> None:
        if direction == "down":
            await self._page.mouse.wheel(0, 500)
        elif direction == "up":
            await self._page.mouse.wheel(0, -500)
        elif direction == "bottom":
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif direction == "top":
            await self._page.evaluate("window.scrollTo(0, 0)")

    async def refresh(self) -> None:
        await self._page.reload()

    async def go_back(self) -> None:
        await self._page.go_back()

    async def go_forward(self) -> None:
        await self._page.go_forward()

    # Note: `page.evaluate`, `page.locator`, etc. are STRICTLY omitted from the public interface.
    # Future phases will implement Typed Actions (click, fill) here, guarded by policies.
