import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy.orm import Session as DBSession

from packages.browser.errors import BrowserClosedError, BrowserSessionError
from packages.browser.page import BrowserPage
from packages.browser.tracing import BrowserTracer
from packages.db.models.browser import BrowserSessionModel


class BrowserSession:
    """
    Represents an isolated browser automation execution session.
    Manages Playwright Context lifecycle.
    """

    def __init__(
        self,
        raw_context: Any,
        user_id: uuid.UUID,
        db_session: DBSession,
        tracer: BrowserTracer,
        target_domain: Optional[str] = None,
        application_id: Optional[uuid.UUID] = None,
    ):
        self._context = raw_context
        self._db_session = db_session
        self._tracer = tracer

        self.session_id = uuid.uuid4()
        self.user_id = user_id
        self.application_id = application_id
        self.state = "STARTING"

        self._pages: List[BrowserPage] = []

        # Persist session start
        db_record = BrowserSessionModel(
            id=self.session_id,
            user_id=user_id,
            application_id=application_id,
            state=self.state,
            target_domain=target_domain,
        )
        self._db_session.add(db_record)
        self._db_session.commit()

        self._update_state("ACTIVE")

    def _update_state(self, new_state: str) -> None:
        """Updates internal state and persists to DB."""
        self.state = new_state
        db_record = (
            self._db_session.query(BrowserSessionModel).filter_by(id=self.session_id).first()
        )
        if db_record:
            db_record.state = new_state  # type: ignore[assignment]
            if new_state in ("CLOSED", "FAILED"):
                db_record.closed_at = datetime.utcnow()  # type: ignore[assignment]
            self._db_session.commit()

        self._tracer.record_event(self.session_id, f"session_{new_state.lower()}")

    async def new_page(self) -> BrowserPage:
        """Creates a new isolated page inside this session's context."""
        if self.state in ("CLOSED", "FAILED"):
            raise BrowserClosedError("Cannot open page in closed session")

        raw_page = await self._context.new_page()
        page = BrowserPage(raw_page, self.session_id, self._tracer)
        await page._setup_security_routing()
        self._pages.append(page)
        return page

    def get_active_page(self) -> Optional[BrowserPage]:
        """Returns the most recent active page, if any."""
        return self._pages[-1] if self._pages else None

    async def pause_for_user(self) -> None:
        """Transitions session to WAITING_FOR_USER, typically upon challenge detection."""
        self._update_state("WAITING_FOR_USER")

    async def resume(self) -> None:
        """Resumes session from WAITING_FOR_USER."""
        if self.state == "WAITING_FOR_USER":
            self._update_state("ACTIVE")
        else:
            raise BrowserSessionError(f"Cannot resume session from state {self.state}")

    async def close(self) -> None:
        """Cleans up the context and finalizes state."""
        try:
            await self._context.close()
            self._update_state("CLOSED")
        except Exception as e:
            self._update_state("FAILED")
            self._tracer.record_event(
                self.session_id, "session_cleanup_error", metadata={"error": str(e)}
            )
