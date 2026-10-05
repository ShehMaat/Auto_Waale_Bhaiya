import asyncio
import uuid
from typing import Any, Dict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.browser.page import BrowserPage
from packages.db.models.browser import BrowserActionExecutionModel, BrowserSessionModel
from packages.schemas.browser_actions import (
    BrowserAction,
    CheckAction,
    ClickAction,
    FillAction,
    GoBackAction,
    GoForwardAction,
    NavigateAction,
    PressKeyAction,
    RefreshAction,
    ScrollAction,
    SelectOptionAction,
    UncheckAction,
    UploadFileAction,
    WaitAction,
)


class ActionExecutor:
    """
    Executes fully validated BrowserActions safely against the BrowserPage.
    Enforces authorization and true database-backed idempotency.
    """

    @classmethod
    async def execute(
        cls, action: BrowserAction, page: BrowserPage, db_session: Session, user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Executes a typed action safely.
        Enforces cross-user authorization and exact-once idempotency.
        """
        # 1. Authorization: Verify session ownership
        session_uuid = uuid.UUID(action.session_id)
        session_record = db_session.query(BrowserSessionModel).filter_by(id=session_uuid).first()
        if not session_record or session_record.user_id != user_id:
            raise PermissionError("User is not authorized to execute actions on this session.")

        # Challenge Protection: Block autonomous actions if human intervention is required
        if session_record.state == "WAITING_FOR_USER":
            raise PermissionError(
                "Session is locked in challenge state (WAITING_FOR_USER). Autonomous execution blocked."  # noqa: E501
            )

        # 2. Idempotency: Transactional claim
        try:
            exec_record = BrowserActionExecutionModel(
                action_id=action.action_id, session_id=session_uuid, status="STARTED"
            )
            db_session.add(exec_record)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
            prev = (
                db_session.query(BrowserActionExecutionModel)
                .filter_by(action_id=action.action_id)
                .first()
            )
            return {"status": "DUPLICATE", "previous_result": prev.result_json if prev else None}

        # 3. Execution Phase
        try:
            print(f"EXECUTING ACTION: {action}")
            if isinstance(action, NavigateAction):
                await page.navigate(action.url)
            elif isinstance(action, ClickAction):
                await page.click_element(action.element_id)
            elif isinstance(action, FillAction):
                await page.fill_element(action.element_id, action.text)
            elif isinstance(action, WaitAction):
                await asyncio.sleep(action.duration_ms / 1000.0)
            elif isinstance(action, SelectOptionAction):
                await page.select_option(action.element_id, action.option_value)
            elif isinstance(action, CheckAction):
                await page.check(action.element_id)
            elif isinstance(action, UncheckAction):
                await page.uncheck(action.element_id)
            elif isinstance(action, UploadFileAction):
                import os
                import tempfile

                from packages.common.storage import MinioStorageProvider
                from packages.db.models.candidate import Document

                try:
                    doc_uuid = uuid.UUID(action.document_id)
                except (ValueError, TypeError, AttributeError):
                    raise ValueError(f"Invalid document_id format: {action.document_id}")

                doc = db_session.query(Document).filter_by(id=doc_uuid).first()
                if not doc or str(doc.user_id) != str(user_id):
                    raise PermissionError("Document not found or unauthorized.")

                # Check file size (e.g., max 10MB)
                if doc.file_size > 10 * 1024 * 1024:
                    raise ValueError("File exceeds maximum allowed upload size.")

                storage = MinioStorageProvider()  # type: ignore
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp_path = tmp.name

                try:
                    if not storage.download_file(doc.storage_key, tmp_path):
                        raise RuntimeError(f"Failed to download document {doc.id}")

                    await page.upload_file(action.element_id, tmp_path)
                except Exception as e:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    raise e
                # Note: We intentionally don't unlink here on success because the browser needs the file 
                # on disk when the form is submitted. The OS will clean up /tmp eventually, or we can clean it on session close.
            elif isinstance(action, PressKeyAction):
                await page.press_key(action.key)
            elif isinstance(action, ScrollAction):
                await page.scroll(action.direction)
            elif isinstance(action, RefreshAction):
                await page.refresh()
            elif isinstance(action, GoBackAction):
                await page.go_back()
            elif isinstance(action, GoForwardAction):
                await page.go_forward()
            else:
                raise ValueError(f"Unknown action type: {type(action)}")

            # Update record as SUCCESS
            exec_record.status = "SUCCESS"
            exec_record.result_json = {"status": "SUCCESS"}
            db_session.commit()
            return {"status": "SUCCESS"}

        except Exception as e:
            exec_record.status = "FAILED"
            exec_record.result_json = {"status": "FAILED", "error": str(e)}
            db_session.commit()
            raise
