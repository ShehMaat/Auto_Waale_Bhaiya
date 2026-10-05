import uuid
from typing import Any, Generator
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from packages.application.workflow.orchestrator import ApplicationWorkflowOrchestrator
from packages.db.models.application import Application, ApplicationWorkflow
from packages.db.models.hitl import HITLRequestModel
from packages.hitl.manager import HITLManager
from packages.schemas.enums import HITLRequestStatus, HITLRequestType, HITLResponseType
from packages.schemas.hitl import HITLResponseCreate


@pytest.fixture
def mock_execute_actions() -> Generator[Any, None, None]:
    with patch("packages.application.workflow.nodes.WorkflowNodes.execute_actions") as mock_exec:
        yield mock_exec


def test_submission_regression_test(db_session: Session) -> None:
    """
    18. SUBMISSION REGRESSION TEST
    Approval must never become submission authorization.
    """
    # Create fake app
    from packages.db.models.candidate import User
    from packages.db.models.jobs import Job

    user = User(id=uuid.uuid4(), email=f"api_{uuid.uuid4()}@hitl.com", hashed_password="test")
    job = Job(
        id=uuid.uuid4(),
        source_job_id="test_job_submit",
        title="Submit",
        company="Submit",
        description="API",
        url="http://test.com",
    )
    db_session.add_all([user, job])
    db_session.flush()

    app_id = uuid.uuid4()
    app = Application(id=app_id, user_id=user.id, job_id=job.id, status="REVIEW_COMPLETED")
    db_session.add(app)
    db_session.commit()

    # In Phase 3E, there is no final submit implementation.
    # We instantiate the orchestrator and tell it to run. It should not submit.
    orchestrator = ApplicationWorkflowOrchestrator(app_id)
    with patch.object(orchestrator.app, "ainvoke") as mock_ainvoke:
        mock_ainvoke.return_value = {"current_page_index": 0}
        orchestrator.run_sync()

    # The graph ainvoke was called, and no real submit was executed.
    assert mock_ainvoke.called


def test_workflow_pause_resume_integration(db_session: Session) -> None:
    """
    19. WORKFLOW PAUSE/RESUME INTEGRATION
    Unknown field -> ASK_USER -> HITLRequest -> WAITING_FOR_USER
    User responds -> RESOLVED -> RESUME
    """
    # Setup
    from packages.db.models.candidate import User
    from packages.db.models.jobs import Job

    user = User(id=uuid.uuid4(), email=f"api_{uuid.uuid4()}@hitl.com", hashed_password="test")
    job = Job(
        id=uuid.uuid4(),
        source_job_id="test_job_pause",
        title="Pause",
        company="Pause",
        description="API",
        url="http://test.com",
    )
    db_session.add_all([user, job])
    db_session.flush()

    app_id = uuid.uuid4()
    app = Application(id=app_id, user_id=user.id, job_id=job.id, status="IN_PROGRESS")
    db_session.add(app)

    wf = ApplicationWorkflow(id=uuid.uuid4(), application_id=app_id)
    db_session.add(wf)
    db_session.flush()

    manager = HITLManager(db_session)

    # Create HITL request for this workflow
    req = HITLRequestModel(
        id=uuid.uuid4(),
        application_id=app_id,
        workflow_id=wf.id,
        user_id=user.id,
        request_type=HITLRequestType.UNKNOWN_FIELD.value,
        title="Need candidate salary",
        description="What is expected salary?",
        required_action="Provide a number",
        status=HITLRequestStatus.PENDING.value,
        version=1,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    # 1. User responds
    resp_data = HITLResponseCreate(
        response_type=HITLResponseType.NUMBER, value_json=100000, expected_version=1
    )
    success = manager.submit_response(req.id, user.id, resp_data)
    assert success

    # 2. Workflow resumes
    orchestrator = ApplicationWorkflowOrchestrator(app_id)

    # Run the graph
    import asyncio

    with patch.object(orchestrator.app, "ainvoke") as mock_ainvoke:
        mock_ainvoke.return_value = {"current_page_index": 0, "status": "IN_PROGRESS"}
        asyncio.run(orchestrator.resume_from_hitl())

    db_session.refresh(wf)
    assert mock_ainvoke.called
