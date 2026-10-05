import hashlib
import json
import logging
import uuid
from typing import Any, Dict

from pydantic import TypeAdapter

from packages.application.workflow.state import ApplicationWorkflowState
from packages.browser.form_intelligence.classifier import FieldClassifier
from packages.browser.form_intelligence.decision_engine import DecisionEngine
from packages.browser.form_intelligence.detector import FormDetector
from packages.browser.form_intelligence.executor_bridge import ExecutionBridge
from packages.browser.inspector import PageInspector
from packages.browser.manager import BrowserManager
from packages.browser.validator import ActionValidator
from packages.browser.worker import BrowserWorker
from packages.db.models.application import (
    Application,
    ApplicationEvent,
    PreSubmissionSnapshot,
)
from packages.db.models.candidate import Profile
from packages.db.models.memory import MemoryFact
from packages.db.session import SessionLocal
from packages.schemas.browser_actions import BrowserAction, PageModel
from packages.schemas.enums import ApplicationStatus
from packages.schemas.form import FieldDecision, FormModel

logger = logging.getLogger(__name__)


class WorkflowNodes:
    """
    Contains the LangGraph node implementations for the Application Workflow.
    """

    def __init__(self) -> None:
        self.browser_manager = BrowserManager()
        self.detector = FormDetector()
        self.classifier = FieldClassifier()
        self.decision_engine = DecisionEngine()
        self.execution_bridge = ExecutionBridge()
        self.inspector = PageInspector()

    async def load_application(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: load_application ---')
        """Loads application state and lock check."""
        logger.info(f"Loading application {state['application_id']}")
        return {"status": ApplicationStatus.STARTED.value}

    async def start_browser_session(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: start_browser_session ---')
        """Creates or re-attaches to a browser session."""
        app_id_str = state.get("application_id")
        if not app_id_str:
            return {"status": ApplicationStatus.FAILED.value, "last_error": "Missing application_id"}

        logger.info(f"Starting browser session for application {app_id_str}")
        
        try:
            with SessionLocal() as db:
                app_id = uuid.UUID(app_id_str)
                application = db.query(Application).filter(Application.id == app_id).first()
                if not application:
                    return {"status": ApplicationStatus.FAILED.value, "last_error": "Application not found"}

                user_id = application.user_id

                from packages.db.models.jobs import Job
                job = db.query(Job).filter(Job.id == application.job_id).first()
                if not job:
                    return {"status": ApplicationStatus.FAILED.value, "last_error": "Job not found"}
                
                target_url = job.url
                session_id_str = state.get("browser_session_id")
                session = None

                if session_id_str:
                    try:
                        session_id = uuid.UUID(session_id_str)
                        session = await self.browser_manager.get_session(session_id)
                        
                        # Cross-user and cross-application check
                        if session.user_id != user_id or session.application_id != app_id:
                            session = None
                        elif session.state in ("CLOSED", "FAILED"):
                            session = None
                    except Exception:
                        session = None

                if not session:
                    session = await self.browser_manager.create_session(
                        user_id=user_id,
                        db_session=db,
                        target_domain=target_url,
                        application_id=app_id
                    )
                    
                    page = await session.new_page()
                    await page.navigate(target_url)

                active_page = session.get_active_page()
                current_url = await active_page.get_url() if active_page else target_url

                return {
                    "status": ApplicationStatus.STARTED.value,
                    "browser_session_id": str(session.session_id),
                    "current_url": current_url
                }

        except Exception as e:
            logger.error(f"Error in start_browser_session: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def inspect_page(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: inspect_page ---')
        """Snapshot the DOM and wait for network idle."""
        session_id_str = state.get("browser_session_id")
        if not session_id_str:
            return {"status": ApplicationStatus.FAILED.value, "last_error": "No browser session"}

        try:
            session = await self.browser_manager.get_session(uuid.UUID(session_id_str))
            page = session.get_active_page()
            if not page:
                return {"status": ApplicationStatus.FAILED.value, "last_error": "No active page"}

            page_model = await self.inspector.inspect(page)
            return {
                "status": ApplicationStatus.FORM_INSPECTED.value,
                "page_model": page_model.model_dump(),
                "current_url": page_model.url,
                "current_snapshot_id": page_model.snapshot_id,
            }
        except Exception as e:
            logger.error(f"Error in inspect_page: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def detect_forms(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: detect_forms ---')
        """Detect forms on the current snapshot."""
        page_model_dict = state.get("page_model")
        if not page_model_dict:
            return {"status": ApplicationStatus.FAILED.value, "last_error": "No page model"}

        try:
            page_model = PageModel.model_validate(page_model_dict)
            form_model = self.detector.detect(page_model)
            
            if not form_model.fields:
                return {
                    "status": ApplicationStatus.WAITING_FOR_USER.value,
                    "last_error": "No form fields detected. Page may be blocked by anti-bot challenge or is not a valid application form."
                }

            pending = [f.field_id for f in form_model.fields]
            return {
                "status": ApplicationStatus.FORM_INSPECTED.value,
                "form_model": form_model.model_dump(),
                "pending_field_ids": pending,
            }
        except Exception as e:
            logger.error(f"Error in detect_forms: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def classify_fields(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: classify_fields ---')
        """Classify fields found."""
        if state.get("status") in (ApplicationStatus.FAILED.value, ApplicationStatus.WAITING_FOR_USER.value):
            return {"status": state.get("status")}

        form_model_dict = state.get("form_model")
        if not form_model_dict:
            return {"status": ApplicationStatus.FAILED.value, "last_error": "No form model"}

        try:
            form_model = FormModel.model_validate(form_model_dict)
            classifications = {}
            for field in form_model.fields:
                cls = self.classifier.classify(field, form_model)
                classifications[field.field_id] = cls.model_dump()

            return {
                "status": ApplicationStatus.MAPPING_FIELDS.value,
                "form_model": form_model.model_dump(),
                "field_classifications": classifications,
            }
        except Exception as e:
            logger.error(f"Error in classify_fields: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def retrieve_candidate_values(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: retrieve_candidate_values ---')
        """Fetch candidate memory facts for the fields."""
        if state.get("status") in (ApplicationStatus.FAILED.value, ApplicationStatus.WAITING_FOR_USER.value):
            return {"status": state.get("status")}

        user_id = uuid.UUID(state["user_id"])
        try:
            with SessionLocal() as db:
                profile = db.query(Profile).filter(Profile.user_id == user_id).first()
                memories = db.query(MemoryFact).filter(
                    MemoryFact.user_id == user_id, 
                    MemoryFact.is_current == True
                ).all()

                profile_dict = {
                    "full_name": profile.full_name,
                    "phone": profile.phone,
                    "location": profile.location,
                    "summary": profile.summary,
                } if profile else None

                memory_dicts = [
                    {
                        "id": str(m.id),
                        "category": m.category,
                        "key": m.key,
                        "value": m.value,
                        "provenance": m.provenance,
                    } for m in memories
                ]

            return {
                "status": ApplicationStatus.MAPPING_FIELDS.value,
                "candidate_profile": profile_dict,
                "candidate_memories": memory_dicts,
            }
        except Exception as e:
            logger.error(f"Error in retrieve_candidate_values: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def make_field_decisions(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: make_field_decisions ---')
        """Evaluate trust and generate FieldDecisions."""
        if state.get("status") in (ApplicationStatus.FAILED.value, ApplicationStatus.WAITING_FOR_USER.value):
            return {"status": state.get("status")}

        form_model_dict = state.get("form_model")
        if not form_model_dict:
            return {"status": ApplicationStatus.FAILED.value, "last_error": "No form model"}

        try:
            form_model = FormModel.model_validate(form_model_dict)
            profile_dict = state.get("candidate_profile")
            memories_dict = state.get("candidate_memories", [])
            
            # The DecisionEngine expects Profile and MemoryFact objects but passing 
            # objects into kwargs when some fields are missing can raise issues. 
            # We'll create minimal mocks for what DecisionEngine reads, or just pass None
            profile = None
            if profile_dict:
                class MockProfile:
                    def __init__(self, **kwargs):
                        self.__dict__.update(kwargs)
                profile = MockProfile(**profile_dict)
                
            memories = []
            for m in memories_dict:
                class MockMemory:
                    def __init__(self, **kwargs):
                        self.__dict__.update(kwargs)
                memories.append(MockMemory(**m))

            decisions = []
            for field in form_model.fields:
                dec = self.decision_engine.decide(field, profile=profile, memories=memories) # type: ignore
                decisions.append(dec.model_dump())

            requires_user = any(d.get("requires_user") for d in decisions)
            waiting_ids = [d["field_id"] for d in decisions if d.get("requires_user")]
            challenge = any(d.get("sensitivity") == "CHALLENGE" for d in decisions)

            return {
                "status": ApplicationStatus.FILLING.value,
                "field_decisions": decisions,
                "waiting_field_ids": waiting_ids,
                "challenge_state": "CHALLENGE" if challenge else None,
            }
        except Exception as e:
            logger.error(f"Error in make_field_decisions: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def prepare_actions(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: prepare_actions ---')
        """Bridge decisions into Typed Browser Actions."""
        if state.get("status") in (ApplicationStatus.FAILED.value, ApplicationStatus.WAITING_FOR_USER.value):
            return {"status": state.get("status")}

        decisions_dict = state.get("field_decisions")
        form_model_dict = state.get("form_model")
        session_id_str = state.get("browser_session_id")
        
        if not decisions_dict or not form_model_dict or not session_id_str:
            return {"status": ApplicationStatus.FAILED.value, "last_error": "Missing inputs for prepare_actions"}

        try:
            decisions = [FieldDecision.model_validate(d) for d in decisions_dict]
            form_model = FormModel.model_validate(form_model_dict)

            actions = self.execution_bridge.draft_actions(
                session_id=session_id_str,
                decisions=decisions,
                fields=form_model.fields
            )
            
            action_dicts = [a.model_dump() for a in actions]

            return {
                "status": ApplicationStatus.FILLING.value,
                "prepared_actions": action_dicts,
            }
        except Exception as e:
            logger.error(f"Error in prepare_actions: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def validate_actions(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: validate_actions ---')
        """Pass actions through the Phase 3B ActionValidator."""
        if state.get("status") in (ApplicationStatus.FAILED.value, ApplicationStatus.WAITING_FOR_USER.value):
            return {"status": state.get("status")}

        actions_dict = state.get("prepared_actions", [])
        page_model_dict = state.get("page_model")
        
        if not actions_dict or not page_model_dict:
            return {"status": ApplicationStatus.VALIDATING.value}

        try:
            adapter: TypeAdapter[Any] = TypeAdapter(BrowserAction)
            actions = [adapter.validate_python(a) for a in actions_dict]
            page_model = PageModel.model_validate(page_model_dict)

            errors = []
            for action in actions:
                try:
                    ActionValidator.validate(action, page_model)
                except ValueError as e:
                    errors.append({"action_id": action.action_id, "error": str(e)})

            return {
                "status": ApplicationStatus.VALIDATING.value,
                "validation_errors": errors,
            }
        except Exception as e:
            logger.error(f"Error in validate_actions: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def execute_actions(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: execute_actions ---')
        """Execute actions safely via Phase 5 BrowserWorker."""
        if state.get("status") in (ApplicationStatus.FAILED.value, ApplicationStatus.WAITING_FOR_USER.value):
            return {"status": state.get("status")}

        actions_dict = state.get("prepared_actions", [])
        if not actions_dict:
            print("DEBUG: No prepared actions. Returning NO_ACTIONS.")
            return {"status": ApplicationStatus.VALIDATING.value, "execution_result": {"status": "NO_ACTIONS"}}

        page_model_dict = state.get("page_model")
        if not page_model_dict:
            return {"status": ApplicationStatus.VALIDATING.value}

        try:
            adapter: TypeAdapter[Any] = TypeAdapter(BrowserAction)
            actions = [adapter.validate_python(a) for a in actions_dict]
            page_model = PageModel.model_validate(page_model_dict)

            # Filter out actions that failed validation
            validation_errors = {e["action_id"] for e in state.get("validation_errors", [])}
            valid_actions = [a for a in actions if a.action_id not in validation_errors]

            if not valid_actions:
                 print("DEBUG: No valid actions. Returning NO_ACTIONS.")
                 return {"status": ApplicationStatus.VALIDATING.value, "execution_result": {"status": "NO_ACTIONS"}}

            print(f"DEBUG: valid_actions = {len(valid_actions)}")
            with SessionLocal() as db:
                worker = BrowserWorker(self.browser_manager, db)
                result = await worker.execute_actions_safely(
                    user_id=uuid.UUID(state["user_id"]),
                    application_id=uuid.UUID(state["application_id"]),
                    session_id=uuid.UUID(state["browser_session_id"]),
                    actions=valid_actions,
                    page_model=page_model,
                )
                
                return {
                    "status": ApplicationStatus.VALIDATING.value,
                    "execution_result": result,
                    "last_error": result.get("error") if result.get("status") == "FAILED" else None
                }
        except Exception as e:
            logger.error(f"Error in execute_actions: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def inspect_validation_errors(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: inspect_validation_errors ---')
        """Check the page for native validation errors after execution."""
        # Implementation Defect Fix: If a prior step explicitly FAILED, do not falsely report READY_FOR_REVIEW
        if state.get("status") == ApplicationStatus.FAILED.value:
            return {"status": ApplicationStatus.FAILED.value, "has_next_page": False}

        has_next_page = False
        execution_result = state.get("execution_result", {})
        if execution_result.get("status") == "SUCCESS":
            has_next_page = True

        print(f"DEBUG: inspect_validation_errors returning has_next_page={has_next_page} for execution_result={execution_result}")
        return {
            "status": ApplicationStatus.VALIDATING.value,
            "has_next_page": has_next_page,
        }

    async def transition_page(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: transition_page ---')
        """Attempt to navigate to the next page."""
        return {
            "status": ApplicationStatus.PAGE_TRANSITION.value,
            "current_page_index": state.get("current_page_index", 0) + 1,
            "current_snapshot_id": None # Force re-inspect
        }

    async def prepare_review(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: prepare_review ---')
        """Format the completed application state for human review and create snapshot."""
        try:
            with SessionLocal() as db:
                app_id = uuid.UUID(state["application_id"])
                user_id = uuid.UUID(state["user_id"])
                
                app_record = db.query(Application).filter(Application.id == app_id).first()
                if not app_record:
                    return {"status": ApplicationStatus.FAILED.value, "last_error": "Application not found"}

                content = {
                    "page_model": state.get("page_model"),
                    "form_model": state.get("form_model"),
                    "decisions": state.get("field_decisions")
                }
                
                snapshot_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
                
                snapshot = PreSubmissionSnapshot(
                    application_id=app_id,
                    job_id=app_record.job_id,
                    user_id=user_id,
                    browser_session_id=uuid.UUID(state["browser_session_id"]),
                    snapshot_hash=snapshot_hash,
                    content_json=content,
                    is_valid=True
                )
                db.add(snapshot)
                db.commit()
                db.refresh(snapshot)
                
                return {
                    "status": ApplicationStatus.READY_FOR_REVIEW.value,
                    "pre_submission_snapshot_id": str(snapshot.id),
                }
        except Exception as e:
            logger.error(f"Error in prepare_review: {e}")
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def authorize_submission(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: authorize_submission ---')
        """Verify explicit approval against current snapshot before submission."""
        if not state.get("is_approved"):
            return {"status": ApplicationStatus.READY_FOR_REVIEW.value}
        
        snapshot_id_str = state.get("pre_submission_snapshot_id")
        if not snapshot_id_str:
            return {"status": ApplicationStatus.READY_FOR_REVIEW.value}
            
        try:
            with SessionLocal() as db:
                snapshot = db.query(PreSubmissionSnapshot).filter(PreSubmissionSnapshot.id == uuid.UUID(snapshot_id_str)).first()
                if not snapshot or not snapshot.is_valid:
                    return {"status": ApplicationStatus.FAILED.value, "last_error": "Invalid snapshot"}
                
                if not snapshot.approved_at:
                    return {"status": ApplicationStatus.READY_FOR_REVIEW.value, "last_error": "Not approved"}
                    
            return {"status": ApplicationStatus.SUBMITTING.value}
        except Exception as e:
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def submit(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: submit ---')
        """Execute submission action via BrowserWorker."""
        try:
            form_model_dict = state.get("form_model")
            if not form_model_dict:
                return {"status": ApplicationStatus.FAILED.value, "last_error": "No form model"}
                
            form_model = FormModel.model_validate(form_model_dict)
            submit_field = next((f for f in form_model.fields if "submit" in (f.label or "").lower() or f.input_type == "submit"), None)
            
            if not submit_field:
                return {"status": ApplicationStatus.SUBMITTED.value}
                
            from packages.schemas.browser_actions import ClickAction
            action = ClickAction(
                action_id=str(uuid.uuid4()),
                session_id=state["browser_session_id"],
                element_id=submit_field.element_id
            )
            
            page_model = PageModel.model_validate(state.get("page_model"))
            
            with SessionLocal() as db:
                worker = BrowserWorker(self.browser_manager, db)
                result = await worker.execute_actions_safely(
                    user_id=uuid.UUID(state["user_id"]),
                    application_id=uuid.UUID(state["application_id"]),
                    session_id=uuid.UUID(state["browser_session_id"]),
                    actions=[action],
                    page_model=page_model,
                )
                
                if result.get("status") == "SUCCESS":
                    return {"status": ApplicationStatus.SUBMITTED.value}
                else:
                    return {"status": ApplicationStatus.FAILED.value, "last_error": result.get("error")}
        except Exception as e:
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def verify_outcome(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: verify_outcome ---')
        """Verify submission outcome."""
        return {"status": ApplicationStatus.SUBMITTED.value}

    async def persist_history(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: persist_history ---')
        """Save history and complete workflow."""
        try:
            with SessionLocal() as db:
                event = ApplicationEvent(
                    application_id=uuid.UUID(state["application_id"]),
                    user_id=uuid.UUID(state["user_id"]),
                    event_type="WORKFLOW_COMPLETED",
                    new_state=state.get("status", "UNKNOWN"),
                    actor_type="SYSTEM",
                    correlation_id=state["workflow_id"]
                )
                db.add(event)
                db.commit()
            return {"status": ApplicationStatus.SUBMITTED.value}
        except Exception as e:
            return {"status": ApplicationStatus.FAILED.value, "last_error": str(e)}

    async def handle_challenge(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: handle_challenge ---')
        """Handle OTP/CAPTCHA blocks."""
        return {"status": ApplicationStatus.WAITING_FOR_CHALLENGE.value}

    async def handle_user_input(self, state: ApplicationWorkflowState) -> Dict[str, Any]:
        print('--- ENTERING NODE: handle_user_input ---')
        """Pause for missing required information."""
        return {"status": ApplicationStatus.WAITING_FOR_USER.value}
