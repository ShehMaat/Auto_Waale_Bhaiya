from typing import Dict, Set

from packages.schemas.enums import ApplicationStatus

# Valid transitions from each state
VALID_TRANSITIONS: Dict[ApplicationStatus, Set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.QUALIFIED,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.QUALIFIED: {
        ApplicationStatus.READY,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.READY: {
        ApplicationStatus.STARTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
        ApplicationStatus.REJECTED_BY_USER,
    },
    ApplicationStatus.STARTED: {
        ApplicationStatus.FORM_INSPECTED,
        ApplicationStatus.AUTHENTICATING,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.AUTHENTICATING: {
        ApplicationStatus.FORM_INSPECTED,
        ApplicationStatus.WAITING_FOR_CHALLENGE,
        ApplicationStatus.WAITING_FOR_USER,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.FORM_INSPECTED: {
        ApplicationStatus.MAPPING_FIELDS,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.MAPPING_FIELDS: {
        ApplicationStatus.FILLING,
        ApplicationStatus.WAITING_FOR_USER,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.FILLING: {
        ApplicationStatus.VALIDATING,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.VALIDATING: {
        ApplicationStatus.RECOVERING,
        ApplicationStatus.PAGE_TRANSITION,
        ApplicationStatus.WAITING_FOR_CHALLENGE,
        ApplicationStatus.WAITING_FOR_USER,
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.PAGE_TRANSITION: {
        ApplicationStatus.FORM_INSPECTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.RECOVERING: {
        ApplicationStatus.PAGE_TRANSITION,
        ApplicationStatus.FORM_INSPECTED,
        ApplicationStatus.WAITING_FOR_USER,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.WAITING_FOR_USER: {
        ApplicationStatus.FILLING,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
        ApplicationStatus.REJECTED_BY_USER,
    },
    ApplicationStatus.WAITING_FOR_CHALLENGE: {
        ApplicationStatus.FILLING,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
        ApplicationStatus.REJECTED_BY_USER,
    },
    ApplicationStatus.READY_FOR_REVIEW: {
        ApplicationStatus.SUBMITTING,
        ApplicationStatus.FILLING,
        ApplicationStatus.REJECTED_BY_USER,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.SUBMITTING: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.UNKNOWN,
    },
    ApplicationStatus.SUBMITTED: set(),  # Terminal
    ApplicationStatus.FAILED: set(),  # Terminal
    ApplicationStatus.UNKNOWN: set(),  # Terminal
    ApplicationStatus.REJECTED_BY_USER: set(),  # Terminal
}

TERMINAL_STATES = {
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.FAILED,
    ApplicationStatus.UNKNOWN,
    ApplicationStatus.REJECTED_BY_USER,
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


class ApplicationStateMachine:
    """Centralized state machine validation for Applications."""

    @staticmethod
    def validate_transition(
        current_state: ApplicationStatus, next_state: ApplicationStatus
    ) -> bool:
        """Validates if a transition is allowed."""
        if current_state not in VALID_TRANSITIONS:
            raise ValueError(f"Unknown current state: {current_state}")

        if next_state not in VALID_TRANSITIONS[current_state]:
            raise InvalidTransitionError(
                f"Cannot transition from {current_state.value} to {next_state.value}"
            )
        return True

    @staticmethod
    def is_terminal(state: ApplicationStatus) -> bool:
        """Checks if the state is terminal."""
        return state in TERMINAL_STATES
