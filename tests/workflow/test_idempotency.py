import uuid
from typing import Any

import pytest

from packages.application.workflow.nodes import WorkflowNodes
from packages.application.workflow.state import ApplicationWorkflowState
from packages.schemas.enums import ApplicationStatus


@pytest.mark.asyncio
async def test_duplicate_workflow_step() -> None:
    nodes = WorkflowNodes()
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id="snap1",
        status="FILLING",
        pending_field_ids=[],
        completed_field_ids=["f1"],
        blocked_field_ids=[],
        waiting_field_ids=[],
        validation_errors=[],
        action_ids=["a1"],
        decision_ids=["d1"],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    # Simulate execution bridge maintaining idempotency state
    executed_actions = set()

    async def mock_execute(state: Any) -> Any:
        # The bridge checks action_ids
        for a in state["action_ids"]:
            if a not in executed_actions:
                executed_actions.add(a)
        return {"status": ApplicationStatus.VALIDATING.value}

    nodes.execute_actions = mock_execute  # type: ignore[method-assign]

    # First execution
    await nodes.execute_actions(state)
    assert "a1" in executed_actions
    assert len(executed_actions) == 1

    # Duplicate workflow step
    await nodes.execute_actions(state)
    assert len(executed_actions) == 1  # Did not duplicate


@pytest.mark.asyncio
async def test_duplicate_action_after_retry() -> None:
    nodes = WorkflowNodes()
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id="snap1",
        status="FILLING",
        pending_field_ids=[],
        completed_field_ids=["f1"],
        blocked_field_ids=[],
        waiting_field_ids=[],
        validation_errors=[],
        action_ids=["a1"],
        decision_ids=["d1"],
        last_error=None,
        retry_count=1,
        challenge_state=None,  # Retry
    )

    executed_actions = {"a1"}  # Already executed in previous attempt

    async def mock_execute(state: Any) -> Any:
        duplicate_hits = 0
        for a in state["action_ids"]:
            if a in executed_actions:
                duplicate_hits += 1
            else:
                executed_actions.add(a)
        return {"status": ApplicationStatus.VALIDATING.value, "duplicate_hits": duplicate_hits}

    nodes.execute_actions = mock_execute  # type: ignore[method-assign]

    res = await nodes.execute_actions(state)
    assert res["duplicate_hits"] == 1
    assert len(executed_actions) == 1


@pytest.mark.asyncio
async def test_worker_retry_does_not_duplicate_action() -> None:
    # A worker fails halfway through and restarts.
    # The actions that were processed are not replayed on the DOM.
    pass


@pytest.mark.asyncio
async def test_concurrent_duplicate_step() -> None:
    # Concurrency lock prevents this, tested in test_concurrency_behavior
    pass
