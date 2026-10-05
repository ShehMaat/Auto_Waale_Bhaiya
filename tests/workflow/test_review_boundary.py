import uuid

from packages.application.workflow.graph import route_page_completion
from packages.application.workflow.state import ApplicationWorkflowState
from packages.schemas.enums import ApplicationStatus


def test_ready_for_review_unreachable_if_incomplete() -> None:
    # 1. Validation errors remain -> goes to inspect_page
    state1 = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status=ApplicationStatus.READY_FOR_REVIEW.value,
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

    assert route_page_completion(state1) == "inspect_page"


def test_ready_for_review_reachable_if_complete() -> None:
    # Everything complete, status is set to READY_FOR_REVIEW, no errors
    state2 = ApplicationWorkflowState(
        workflow_id="w1",
        application_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        browser_session_id=None,
        current_url=None,
        current_page_index=0,
        current_snapshot_id=None,
        status=ApplicationStatus.READY_FOR_REVIEW.value,
        pending_field_ids=[],
        completed_field_ids=["f1"],
        blocked_field_ids=["f2_submit"],
        waiting_field_ids=[],
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    assert route_page_completion(state2) == "prepare_review"
