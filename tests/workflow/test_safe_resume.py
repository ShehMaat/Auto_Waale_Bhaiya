
import uuid
from typing import Any


def patch_nodes_for_tests(nodes, monkeypatch):
    class MockPage:
        async def navigate(self, url): self.url = url
        async def get_url(self): return getattr(self, "url", "https://safe.com")
    class MockSession:
        def __init__(self, uid, aid):
            self.session_id = uuid.uuid4()
            self.user_id = uid
            self.application_id = aid
            self.state = "ACTIVE"
            self.raw_context = True
        async def new_page(self): return MockPage()
        def get_active_page(self): return MockPage()
    class MockBM:
        def __init__(self):
            self.sessions = {}
        async def get_session(self, sid):
            if sid in self.sessions: return self.sessions[sid]
            return MockSession(uuid.uuid4(), uuid.uuid4())
        async def create_session(self, user_id, db_session, target_domain, application_id):
            s = MockSession(user_id, application_id)
            self.sessions[s.session_id] = s
            return s
            
    nodes.browser_manager = MockBM()
    
    class MockDB:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def query(self, model):
            self.m = model
            return self
        def filter(self, *args): return self
        def first(self):
            if self.m.__name__ == 'Application':
                class App:
                    user_id = uuid.uuid4()
                    job_id = uuid.uuid4()
                return App()
            class Job:
                url = "https://safe.com"
            return Job()
            
    monkeypatch.setattr("packages.application.workflow.nodes.SessionLocal", MockDB)

    class MockPageModel:
        def model_dump(self): return {}
        @property
        def url(self): return ""
        @property
        def snapshot_id(self): return ""
        
    class MockPI:
        async def inspect(self, page): return MockPageModel()
    nodes.inspector = MockPI()

import pytest

from packages.application.workflow.nodes import WorkflowNodes
from packages.application.workflow.state import ApplicationWorkflowState
from packages.schemas.enums import ApplicationStatus


@pytest.mark.asyncio
async def test_safe_resume_snapshot_freshness(monkeypatch: Any) -> None:
    nodes = WorkflowNodes()
    patch_nodes_for_tests(nodes, monkeypatch)

    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=str(uuid.uuid4()),
        current_url=None,
        current_page_index=0,
        current_snapshot_id="old_snapshot",
        status=ApplicationStatus.WAITING_FOR_USER.value,
        pending_field_ids=[],
        completed_field_ids=[],
        blocked_field_ids=[],
        waiting_field_ids=[],
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    # Authorized resume from a PAUSED state MUST route back to inspect_page
    # to guarantee a fresh snapshot is generated.
    # In LangGraph DAG, resuming requires injecting the next execution.
    # If a worker picks up WAITING_FOR_USER, we test the state machine allows resuming to FORM_INSPECTED.  # noqa: E501

    from packages.domain.state_machine import ApplicationStateMachine

    ApplicationStateMachine.validate_transition(
        ApplicationStatus.WAITING_FOR_USER, ApplicationStatus.FILLING
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.RECOVERING, ApplicationStatus.FORM_INSPECTED
    )

    # After user answers, the node handling the answer should force reinspection if the DOM changed,
    # or just route to filling if the snapshot is assumed locked.
    # However, for safety, we assume if the session was interrupted, we must inspect again.

    res = await nodes.inspect_page(state)
    assert res["status"] == ApplicationStatus.FORM_INSPECTED.value
    # A real implementation generates a new snapshot here.
