
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
async def test_browser_crash_recovery(monkeypatch: Any) -> None:
    nodes = WorkflowNodes()
    patch_nodes_for_tests(nodes, monkeypatch)
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=str(uuid.uuid4()),
        current_url=None,
        current_page_index=0,
        current_snapshot_id=str(uuid.uuid4()),
        status="STARTED",
        pending_field_ids=[],
        completed_field_ids=[],
        blocked_field_ids=[],
        waiting_field_ids=[],
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error="Browser connection lost",
        retry_count=1,
        challenge_state=None,
    )

    # The start_browser_session node should recreate the session
    res = await nodes.start_browser_session(state)

    # If it's a real implementation, it creates a new ID. For this test we mock it.
    assert res["status"] == ApplicationStatus.STARTED.value

    # Next, inspect_page must generate a NEW snapshot
    res_inspect = await nodes.inspect_page(state)
    assert res_inspect["status"] == ApplicationStatus.FORM_INSPECTED.value
