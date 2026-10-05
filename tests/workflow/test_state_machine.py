import pytest

from packages.domain.state_machine import ApplicationStateMachine, InvalidTransitionError
from packages.schemas.enums import ApplicationStatus


def test_valid_state_transitions() -> None:
    # Test valid transitions defined in Phase 3D
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.STARTED, ApplicationStatus.AUTHENTICATING
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.AUTHENTICATING, ApplicationStatus.WAITING_FOR_CHALLENGE
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.FORM_INSPECTED, ApplicationStatus.MAPPING_FIELDS
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.MAPPING_FIELDS, ApplicationStatus.FILLING
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.FILLING, ApplicationStatus.VALIDATING
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.VALIDATING, ApplicationStatus.READY_FOR_REVIEW
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.VALIDATING, ApplicationStatus.PAGE_TRANSITION
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.PAGE_TRANSITION, ApplicationStatus.FORM_INSPECTED
    )
    ApplicationStateMachine.validate_transition(
        ApplicationStatus.VALIDATING, ApplicationStatus.RECOVERING
    )


def test_invalid_transition_rejected() -> None:
    # A random jump should be blocked
    with pytest.raises(InvalidTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.STARTED, ApplicationStatus.READY_FOR_REVIEW
        )

    with pytest.raises(InvalidTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.MAPPING_FIELDS, ApplicationStatus.SUBMITTING
        )


def test_submission_state_unreachable() -> None:
    # No direct path from VALIDATING to SUBMITTING should exist
    with pytest.raises(InvalidTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.VALIDATING, ApplicationStatus.SUBMITTING
        )

    with pytest.raises(InvalidTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.READY_FOR_REVIEW, ApplicationStatus.SUBMITTED
        )
