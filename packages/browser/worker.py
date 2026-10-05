import logging
import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from packages.browser.errors import (
    ActionValidationError,
    BrowserClosedError,
    BrowserPolicyViolation,
    BrowserSessionError,
    SessionOwnershipError,
    StaleSnapshotError,
)
from packages.browser.executor import ActionExecutor
from packages.browser.manager import BrowserManager
from packages.browser.validator import ActionValidator
from packages.schemas.browser_actions import BrowserAction, PageModel

logger = logging.getLogger(__name__)


class BrowserWorker:
    """
    Phase 5 Browser Worker Execution Boundary.
    Ensures safe execution of validated actions, handles staleness, and tracks telemetry.
    """

    def __init__(self, manager: BrowserManager, db_session: Session):
        self.manager = manager
        self.db = db_session

    async def execute_actions_safely(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        session_id: uuid.UUID,
        actions: List[BrowserAction],
        page_model: PageModel,
    ) -> Dict[str, Any]:
        """
        Hardened execution boundary.
        1. Loads the authorized session
        2. Validates requested actions
        3. Executes and halts on state-changing actions
        """
        try:
            session = await self.manager.get_session(session_id)
        except BrowserSessionError as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            raise

        if session.user_id != user_id:
            raise SessionOwnershipError(
                "Session ownership verification failed. Cross-user access denied."
            )

        if session.application_id and session.application_id != application_id:
            raise SessionOwnershipError(
                "Session application isolation failed. Cross-application access denied."
            )

        page = session.get_active_page()
        if not page:
            raise BrowserClosedError("Session has no active page. It may have crashed.")

        executed_actions = 0

        for action in actions:
            # Validate Action
            try:
                # Validator throws ValueError on failure
                ActionValidator.validate(action, page_model)
            except ValueError as e:
                if "stale" in str(e).lower() or "not found in current pagemodel" in str(e).lower():
                    raise StaleSnapshotError(str(e)) from e
                raise ActionValidationError(str(e)) from e

            # Execute Action
            try:
                result = await ActionExecutor.execute(action, page, self.db, user_id)
                if result["status"] not in ("SUCCESS", "DUPLICATE"):
                    return {"status": "FAILED", "error": result.get("error")}
                executed_actions += 1
            except BrowserPolicyViolation as e:
                logger.error(f"Policy violation during execution: {e}")
                return {"status": "FAILED", "error": str(e)}
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                return {"status": "FAILED", "error": str(e)}

            # Snapshot consistency check:
            # Actions like Click, Navigate, Refresh change the DOM.
            # We must stop processing further actions in this batch to force a re-inspect.
            state_changing = [
                "ClickAction",
                "NavigateAction",
                "RefreshAction",
                "GoBackAction",
                "GoForwardAction",
                "UploadFileAction",
                "SelectOptionAction",
                "CheckAction",
                "UncheckAction"
            ]
            if action.__class__.__name__ in state_changing:
                break

        return {"status": "SUCCESS", "executed_count": executed_actions}
