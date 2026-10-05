import uuid
from typing import Any

import pytest

from packages.application.workflow.nodes import WorkflowNodes
from packages.application.workflow.state import ApplicationWorkflowState
from packages.db.models.application import Application
from packages.db.models.jobs import Job
from packages.schemas.enums import ApplicationStatus


@pytest.fixture
def mock_db_session(monkeypatch: Any) -> Any:
    class MockSession:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def query(self, model):
            self.current_model = model
            return self
        def filter(self, *args):
            return self
        def first(self):
            if self.current_model == Application:
                if not hasattr(self.__class__, "_cached_app"):
                    class MockApp:
                        user_id = uuid.uuid4()
                        job_id = uuid.uuid4()
                    self.__class__._cached_app = MockApp()
                return self.__class__._cached_app
            elif self.current_model == Job:
                class MockJob:
                    url = "https://safe-domain.com/job"
                return MockJob()
            return None

    monkeypatch.setattr("packages.application.workflow.nodes.SessionLocal", MockSession)
    return MockSession

@pytest.fixture
def mock_browser_manager(monkeypatch: Any) -> Any:
    class MockPage:
        async def navigate(self, url):
            self.url = url
        async def get_url(self):
            return getattr(self, "url", "https://safe-domain.com/job")

    class MockSession:
        def __init__(self, user_id, application_id):
            self.session_id = uuid.uuid4()
            self.user_id = user_id
            self.application_id = application_id
            self.state = "ACTIVE"
            self.raw_context = True
            
        async def new_page(self):
            return MockPage()
            
        def get_active_page(self):
            return MockPage()

    class MockBrowserManager:
        def __init__(self):
            self.sessions = {}
        
        async def get_session(self, session_id):
            if session_id in self.sessions:
                return self.sessions[session_id]
            raise Exception("Session not found")
            
        async def create_session(self, user_id, db_session, target_domain, application_id):
            session = MockSession(user_id=user_id, application_id=application_id)
            self.sessions[session.session_id] = session
            return session

    mock_manager = MockBrowserManager()
    monkeypatch.setattr("packages.application.workflow.nodes.BrowserManager", lambda: mock_manager)
    return mock_manager

@pytest.mark.asyncio
async def test_new_browser_session_creation(mock_db_session: Any, mock_browser_manager: Any) -> None:
    # A. New browser session creation
    nodes = WorkflowNodes()
    nodes.browser_manager = mock_browser_manager
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id="",
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="STARTED",
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
    
    res = await nodes.start_browser_session(state)
    assert res["status"] == ApplicationStatus.STARTED.value
    assert "browser_session_id" in res
    assert res["current_url"] == "https://safe-domain.com/job"

@pytest.mark.asyncio
async def test_session_reattachment(mock_db_session: Any, mock_browser_manager: Any) -> None:
    # B. Session reattachment
    nodes = WorkflowNodes()
    nodes.browser_manager = mock_browser_manager
    app_id = uuid.uuid4()
    
    # We must manually inject the same user_id into DB mock so they match
    with mock_db_session() as db:
        app = db.query(Application).first()
        user_id = app.user_id
    
    session = await mock_browser_manager.create_session(user_id, None, "https://safe-domain.com/job", app_id)
    
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(app_id),
        user_id="",
        browser_session_id=str(session.session_id),
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="STARTED",
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
    
    res = await nodes.start_browser_session(state)
    assert res["status"] == ApplicationStatus.STARTED.value
    assert res["browser_session_id"] == str(session.session_id) # Should be reused

@pytest.mark.asyncio
async def test_dead_session_recovery(mock_db_session: Any, mock_browser_manager: Any) -> None:
    # C. Dead session recovery
    nodes = WorkflowNodes()
    nodes.browser_manager = mock_browser_manager
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id="",
        browser_session_id=str(uuid.uuid4()), # Fake session
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="STARTED",
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
    
    res = await nodes.start_browser_session(state)
    assert res["status"] == ApplicationStatus.STARTED.value
    assert res["browser_session_id"] != state["browser_session_id"] # Recreated

@pytest.mark.asyncio
async def test_cross_user_session_rejection(mock_db_session: Any, mock_browser_manager: Any) -> None:
    # D. Cross-user session rejection
    nodes = WorkflowNodes()
    nodes.browser_manager = mock_browser_manager
    app_id = uuid.uuid4()
    
    # Session belongs to DIFFERENT user
    session = await mock_browser_manager.create_session(uuid.uuid4(), None, "https://safe-domain.com/job", app_id)
    
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(app_id),
        user_id="",
        browser_session_id=str(session.session_id),
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="STARTED",
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
    
    res = await nodes.start_browser_session(state)
    assert res["status"] == ApplicationStatus.STARTED.value
    assert res["browser_session_id"] != str(session.session_id) # Rejected and recreated

@pytest.mark.asyncio
async def test_missing_application(monkeypatch: Any, mock_browser_manager: Any) -> None:
    # E. Missing application
    nodes = WorkflowNodes()
    nodes.browser_manager = mock_browser_manager
    
    class MockSessionFail:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def query(self, model): return self
        def filter(self, *args): return self
        def first(self): return None
        
    monkeypatch.setattr("packages.application.workflow.nodes.SessionLocal", MockSessionFail)
    
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id="",
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="STARTED",
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
    
    res = await nodes.start_browser_session(state)
    assert res["status"] == ApplicationStatus.FAILED.value
    assert "Application not found" in res["last_error"]

@pytest.mark.asyncio
async def test_browser_disabled(mock_db_session: Any, monkeypatch: Any) -> None:
    # F. Browser disabled
    nodes = WorkflowNodes()
    
    class MockFailingManager:
        async def get_session(self, session_id):
            raise Exception("Session not found")
        async def create_session(self, *args, **kwargs):
            raise Exception("Browser automation is disabled in configuration.")
            
    nodes.browser_manager = MockFailingManager()
    
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id="",
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="STARTED",
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
    
    res = await nodes.start_browser_session(state)
    assert res["status"] == ApplicationStatus.FAILED.value
    assert "Browser automation is disabled in configuration." in res["last_error"]
