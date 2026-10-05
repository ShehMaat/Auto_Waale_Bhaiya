import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from apps.api.app.api.api_v1.endpoints.workflow import (
    approve_decision,
    get_workflow_review,
    start_workflow,
)
from packages.application.workflow.graph import route_page_completion
from packages.application.workflow.state import ApplicationWorkflowState
from packages.db.models.application import Application
from packages.schemas.enums import ApplicationStatus


def test_cross_user_workflow_access_denied(monkeypatch: Any) -> None:
    # Setup mock DB
    mock_db = MagicMock()
    mock_app = Application(id=uuid.uuid4(), user_id=uuid.uuid4())

    mock_db.query().filter().first.return_value = mock_app

    class MockUser:
        id = uuid.uuid4()

    current_user = MockUser()

    with pytest.raises(HTTPException) as excinfo:
        start_workflow(mock_app.id, mock_db, current_user)
    assert excinfo.value.status_code == 403

    with pytest.raises(HTTPException) as excinfo:
        get_workflow_review(mock_app.id, mock_db, current_user)
    assert excinfo.value.status_code == 404

    with pytest.raises(HTTPException) as excinfo:
        approve_decision(mock_app.id, uuid.uuid4(), "DECISION", mock_db, current_user)
    assert excinfo.value.status_code == 404


def test_submit_unreachable() -> None:
    # Verify there is no way for the orchestrator to route to SUBMITTED
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status=ApplicationStatus.SUBMITTING.value,
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

    # Actually, the transition rule blocks this entirely, but let's test if route_page_completion
    # would ever push us to SUBMITTED. It only pushes to 'inspect_page', 'transition_page', or 'prepare_review'  # noqa: E501
    next_node = route_page_completion(state)
    assert str(next_node) != "submit_application"
    assert str(next_node) != "SUBMITTED"
