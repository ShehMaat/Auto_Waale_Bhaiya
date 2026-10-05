import uuid

from packages.application.workflow.graph import route_after_validation, route_page_completion
from packages.application.workflow.state import ApplicationWorkflowState
from packages.schemas.enums import ApplicationStatus


def test_hitl_unknown_mandatory_field() -> None:
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
        waiting_field_ids=["f1"],  # Missing input
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    # After validation, if there's waiting fields, route to handle_user_input
    next_node = route_after_validation(state)
    assert next_node == "handle_user_input"


def test_hitl_sensitive_field() -> None:
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
        waiting_field_ids=["f_sensitive"],
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    next_node = route_after_validation(state)
    assert next_node == "handle_user_input"


def test_hitl_captcha() -> None:
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
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state="CAPTCHA",
    )

    next_node = route_after_validation(state)
    assert next_node == "handle_challenge"


def test_hitl_otp_2fa() -> None:
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
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state="OTP",
    )

    next_node = route_after_validation(state)
    assert next_node == "handle_challenge"


def test_completed_application_to_review() -> None:
    state = ApplicationWorkflowState(
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
        validation_errors=[],
        action_ids=[],
        decision_ids=[],
        last_error=None,
        retry_count=0,
        challenge_state=None,
    )

    next_node = route_page_completion(state)
    assert next_node == "prepare_review"
