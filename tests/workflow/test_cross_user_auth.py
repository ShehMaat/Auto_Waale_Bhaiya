import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from apps.api.app.api.api_v1.endpoints.workflow import (
    abort_workflow,
    answer_workflow,
    approve_decision,
    get_workflow_events,
    get_workflow_review,
    pause_workflow,
    reject_workflow,
    resume_workflow,
    start_workflow,
)
from packages.db.models.application import Application


def test_cross_user_workflow_all_endpoints(monkeypatch: Any) -> None:
    mock_db = MagicMock()
    app_id = uuid.uuid4()
    # Mock application belongs to user A
    mock_app = Application(id=app_id, user_id=uuid.uuid4())
    mock_db.query().filter().first.return_value = mock_app

    class MockUser:
        id = uuid.uuid4()  # User B

    current_user = MockUser()

    # 1. START workflow
    with pytest.raises(HTTPException) as excinfo:
        start_workflow(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 403

    # 2. GET review
    with pytest.raises(HTTPException) as excinfo:
        get_workflow_review(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 404

    # 3. APPROVE
    with pytest.raises(HTTPException) as excinfo:
        approve_decision(app_id, uuid.uuid4(), "DECISION", mock_db, current_user)
    assert excinfo.value.status_code == 404

    # 4. PAUSE
    with pytest.raises(HTTPException) as excinfo:
        pause_workflow(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 404

    # 5. RESUME
    with pytest.raises(HTTPException) as excinfo:
        resume_workflow(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 404

    # 6. ABORT
    with pytest.raises(HTTPException) as excinfo:
        abort_workflow(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 404

    # 7. ANSWER
    with pytest.raises(HTTPException) as excinfo:
        answer_workflow(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 404

    # 8. REJECT
    with pytest.raises(HTTPException) as excinfo:
        reject_workflow(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 404

    # 9. GET events
    with pytest.raises(HTTPException) as excinfo:
        get_workflow_events(app_id, mock_db, current_user)
    assert excinfo.value.status_code == 404
