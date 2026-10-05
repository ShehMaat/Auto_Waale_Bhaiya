import uuid
from typing import Any, Optional

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session as DBSession

from packages.browser.errors import BrowserSessionError, BrowserStartupError
from packages.browser.session import BrowserSession
from packages.browser.tracing import BrowserTracer
from packages.config.settings import settings


class BrowserManager:
    """
    Singleton manager for the Playwright lifecycle.
    Spawns completely isolated `BrowserSession` contexts.
    """

    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "BrowserManager":
        if not cls._instance:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._playwright: Optional[Any] = None
        self._browser: Optional[Any] = None
        self._active_sessions: dict[uuid.UUID, BrowserSession] = {}
        self._initialized = True

    async def start(self) -> None:
        """Starts the underlying Chromium engine."""
        if self._browser:
            return

        if not settings.BROWSER_ENABLED:
            raise BrowserStartupError("Browser automation is disabled in configuration.")

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.BROWSER_HEADLESS,
                # args=["--disable-dev-shm-usage", "--no-sandbox"]  # Depending on docker env
            )
        except Exception as e:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            raise BrowserStartupError(f"Failed to launch browser: {str(e)}") from e

    async def create_session(
        self, user_id: uuid.UUID, db_session: DBSession, target_domain: Optional[str] = None, application_id: Optional[uuid.UUID] = None
    ) -> BrowserSession:
        """
        Creates a completely isolated browser context representing one session.
        Prevents leaking storage state, cookies, and history across users.
        """
        if not self._browser:
            await self.start()

        if len(self._active_sessions) >= settings.BROWSER_MAX_SESSIONS:
            raise BrowserSessionError(
                f"Maximum concurrent sessions ({settings.BROWSER_MAX_SESSIONS}) reached"
            )

        tracer = BrowserTracer(db_session=db_session)

        try:
            assert self._browser is not None
            # Create isolated context
            raw_context = await self._browser.new_context(
                ignore_https_errors=False,  # Enforce secure origins
                bypass_csp=False,  # Do not break target security boundaries
                no_viewport=False,
            )

            if settings.BROWSER_TRACE_ENABLED:
                await raw_context.tracing.start(screenshots=True, snapshots=True, sources=False)

            session = BrowserSession(
                raw_context=raw_context,
                user_id=user_id,
                db_session=db_session,
                tracer=tracer,
                target_domain=target_domain,
                application_id=application_id,
            )

            self._active_sessions[session.session_id] = session
            return session

        except Exception as e:
            raise BrowserSessionError(f"Failed to create isolated session: {str(e)}") from e

    async def get_session(self, session_id: uuid.UUID) -> BrowserSession:
        """Retrieves an active session."""
        session = self._active_sessions.get(session_id)
        if not session:
            raise BrowserSessionError("Session not found or already closed")
        return session

    async def close_session(self, session_id: uuid.UUID) -> None:
        """Closes a session and cleans it from tracking."""
        session = self._active_sessions.get(session_id)
        if session:
            await session.close()
            del self._active_sessions[session_id]

    async def stop(self) -> None:
        """Shuts down all sessions and the browser engine."""
        for session in list(self._active_sessions.values()):
            await session.close()
        self._active_sessions.clear()

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
