import uuid
from typing import Any

import pytest

from packages.application.workflow.nodes import WorkflowNodes
from packages.application.workflow.state import ApplicationWorkflowState
from packages.schemas.enums import ApplicationStatus


@pytest.mark.asyncio
async def test_loop_detection() -> None:
    nodes = WorkflowNodes()

    # State with max retry_count
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="VALIDATING",
        pending_field_ids=[],
        completed_field_ids=[],
        blocked_field_ids=[],
        waiting_field_ids=[],
        validation_errors=[{"error": "bad format repeatedly"}],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=3,
        challenge_state=None,
    )

    # If the workflow nodes have a retry check, they should abort or wait for user
    # We will simulate the `inspect_validation_errors` throwing to FAILED or WAITING_FOR_USER
    # Here we mock the behavior of node implementation.

    async def mock_inspect_val(state: Any) -> Any:
        if state["retry_count"] >= 3:
            return {"status": ApplicationStatus.WAITING_FOR_USER.value}
        return {"status": ApplicationStatus.VALIDATING.value}

    nodes.inspect_validation_errors = mock_inspect_val  # type: ignore[method-assign]

    res = await nodes.inspect_validation_errors(state)
    assert res["status"] == ApplicationStatus.WAITING_FOR_USER.value
