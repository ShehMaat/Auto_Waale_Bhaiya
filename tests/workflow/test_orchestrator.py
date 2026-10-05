import uuid

import pytest

from packages.application.workflow.nodes import WorkflowNodes
from packages.application.workflow.state import ApplicationWorkflowState
from packages.schemas.enums import ApplicationStatus


@pytest.mark.asyncio
async def test_start_workflow() -> None:
    nodes = WorkflowNodes()
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
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

    result = await nodes.load_application(state)
    assert result["status"] == ApplicationStatus.STARTED.value


@pytest.mark.asyncio
async def test_process_fields() -> None:
    nodes = WorkflowNodes()
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="FORM_INSPECTED",
        pending_field_ids=["f1"],
        completed_field_ids=[],
        blocked_field_ids=[],
        waiting_field_ids=[],
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state=None,
        form_model={"form_id": "mock", "snapshot_id": "mock", "page_url": "mock", "sections": [], "fields": [], "metadata": {}},
    )

    res1 = await nodes.classify_fields(state)
    assert res1["status"] == ApplicationStatus.MAPPING_FIELDS.value

    # We do not test retrieve_candidate_values here since it touches DB and requires valid UUIDs.
    # It is tested via integration tests.


@pytest.mark.asyncio
async def test_execute_safe_actions() -> None:
    nodes = WorkflowNodes()
    state = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status="FILLING",
        pending_field_ids=["f1"],
        completed_field_ids=[],
        blocked_field_ids=[],
        waiting_field_ids=[],
        validation_errors=[],
        action_ids=["a1"],
        decision_ids=["d1"],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    res = await nodes.validate_actions(state)
    assert res["status"] == ApplicationStatus.VALIDATING.value

    res_exec = await nodes.execute_actions(state)
    assert res_exec["status"] == ApplicationStatus.VALIDATING.value


@pytest.mark.asyncio
async def test_reinspect_after_transition() -> None:
    from packages.application.workflow.graph import route_page_completion

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
        validation_errors=[{"error": "bad"}],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    # If there are validation errors, we must go back to inspect_page
    next_node = route_page_completion(state)
    assert next_node == "inspect_page"
