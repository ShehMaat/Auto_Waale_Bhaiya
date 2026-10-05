import asyncio
import logging
import uuid
from typing import Any, Dict

from sqlalchemy import text

from packages.application.workflow.graph import application_graph
from packages.db.models.application import Application, ApplicationWorkflow
from packages.db.session import SessionLocal

logger = logging.getLogger(__name__)


class ApplicationWorkflowOrchestrator:
    """
    Entry point for running Phase 3D Application Workflows.
    Manages DB locking, state persistence, and LangGraph execution.
    """

    def __init__(self, application_id: str | uuid.UUID):
        if isinstance(application_id, uuid.UUID):
            self.application_id = application_id
        else:
            self.application_id = uuid.UUID(application_id)
        # Compile graph here, could inject a custom checkpointer if needed
        self.app = application_graph.compile()

    def run_sync(self) -> Dict[str, Any]:
        """
        Executes the workflow synchronously, applying a database lock to prevent
        concurrent execution on the same application.
        """
        return asyncio.run(self.run_async())

    async def run_async(self) -> Dict[str, Any]:
        """Async execution core."""
        with SessionLocal() as db:
            # Postgres advisory lock (64-bit integer derived from UUID)
            lock_id = hash(str(self.application_id)) % ((2**63) - 1)
            try:
                # Try to acquire lock without waiting (Postgres only)
                bind = getattr(db, "get_bind", lambda: None)()
                if bind and bind.dialect.name == "sqlite":
                    locked: bool | None = True
                else:
                    locked = db.execute(
                        text("SELECT pg_try_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id}
                    ).scalar()

                if not locked:
                    logger.warning(f"Workflow for app {self.application_id} is already running.")
                    return {"status": "LOCKED"}

                # Fetch or create workflow state
                workflow_record = (
                    db.query(ApplicationWorkflow)
                    .filter(ApplicationWorkflow.application_id == self.application_id)
                    .first()
                )

                if not workflow_record:
                    workflow_record = ApplicationWorkflow(
                        id=uuid.uuid4(), application_id=self.application_id
                    )
                    db.add(workflow_record)
                    db.commit()

                application_record = (
                    db.query(Application)
                    .filter(Application.id == self.application_id)
                    .first()
                )
                if not application_record:
                    raise ValueError(f"Application {self.application_id} not found")

                user_id = str(application_record.user_id)

                # Build initial state dict
                initial_state = {
                    "workflow_id": str(workflow_record.id),
                    "application_id": str(self.application_id),
                    "user_id": user_id,
                    "browser_session_id": str(workflow_record.browser_session_id)
                    if workflow_record.browser_session_id
                    else None,
                    "current_page_index": workflow_record.current_page_index,
                    "validation_errors": workflow_record.validation_errors_json,
                    "status": "STARTED",
                }

                # Execute langgraph workflow
                logger.info(f"Invoking graph for app {self.application_id}")

                # In Langgraph, invoke runs the graph until END or an interrupt
                final_state = await self.app.ainvoke(initial_state)

                # Save state back
                workflow_record.current_page_index = final_state.get("current_page_index", 0)
                workflow_record.validation_errors_json = final_state.get("validation_errors", [])

                if final_state.get("browser_session_id"):
                    workflow_record.browser_session_id = final_state.get("browser_session_id")

                db.commit()
                return final_state

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                db.rollback()
                raise

    async def resume_from_hitl(self) -> Dict[str, Any]:
        """
        Resumes the workflow after a HITL request has been resolved.
        Ensures that stale snapshots are cleared.
        """
        with SessionLocal() as db:
            lock_id = hash(str(self.application_id)) % ((2**63) - 1)
            try:
                # Try to acquire lock without waiting (Postgres only)
                bind = getattr(db, "get_bind", lambda: None)()
                if bind and bind.dialect.name == "sqlite":
                    locked: bool | None = True
                else:
                    locked = db.execute(
                        text("SELECT pg_try_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id}
                    ).scalar()

                if not locked:
                    logger.warning(f"Workflow for app {self.application_id} is already running.")
                    return {"status": "LOCKED"}

                workflow_record = (
                    db.query(ApplicationWorkflow)
                    .filter(ApplicationWorkflow.application_id == self.application_id)
                    .first()
                )

                if not workflow_record:
                    raise ValueError("Workflow record not found")

                application_record = (
                    db.query(Application)
                    .filter(Application.id == self.application_id)
                    .first()
                )
                if not application_record:
                    raise ValueError(f"Application {self.application_id} not found")

                user_id = str(application_record.user_id)

                initial_state = {
                    "workflow_id": str(workflow_record.id),
                    "application_id": str(self.application_id),
                    "user_id": user_id,
                    "browser_session_id": str(workflow_record.browser_session_id)
                    if workflow_record.browser_session_id
                    else None,
                    "current_page_index": workflow_record.current_page_index,
                    "validation_errors": workflow_record.validation_errors_json,
                    "status": "STARTED",
                    # CRITICAL: Force a fresh snapshot
                    "current_snapshot_id": None,
                }

                logger.info(f"Resuming graph from HITL for app {self.application_id}")

                final_state = await self.app.ainvoke(initial_state)

                workflow_record.current_page_index = final_state.get("current_page_index", 0)
                workflow_record.validation_errors_json = final_state.get("validation_errors", [])

                if final_state.get("browser_session_id"):
                    workflow_record.browser_session_id = final_state.get("browser_session_id")

                db.commit()
                return final_state

            except Exception as e:
                logger.error(f"Workflow resume failed: {e}")
                db.rollback()
                raise
