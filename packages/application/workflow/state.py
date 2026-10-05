from typing import Any, Dict, Optional, TypedDict


class ApplicationWorkflowState(TypedDict):
    """
    State representation for the Application Workflow Orchestrator (LangGraph).
    This tracks the progress through an application form.
    """

    workflow_id: str
    application_id: str
    user_id: str

    browser_session_id: Optional[str]
    current_url: Optional[str]
    current_page_index: int
    current_snapshot_id: Optional[str]
    pre_submission_snapshot_id: Optional[str]
    is_approved: bool

    status: str

    # Form Intelligence Tracking
    pending_field_ids: list[str]
    completed_field_ids: list[str]
    blocked_field_ids: list[str]
    waiting_field_ids: list[str]

    # Validation & Actions
    validation_errors: list[dict[str, Any]]
    action_ids: list[str]
    decision_ids: list[str]

    # Failure recovery
    last_error: Optional[str]
    retry_count: int
    challenge_state: Optional[str]

    page_model: Optional[Dict[str, Any]]
    form_model: Optional[Dict[str, Any]]
    field_classifications: Optional[Dict[str, Any]]
    candidate_profile: Optional[Dict[str, Any]]
    candidate_memories: Optional[list[Dict[str, Any]]]
    field_decisions: Optional[list[Dict[str, Any]]]
    prepared_actions: Optional[list[Dict[str, Any]]]
    execution_result: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    has_next_page: Optional[bool]
