import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from packages.application.workflow.nodes import WorkflowNodes
from packages.application.workflow.state import ApplicationWorkflowState
from packages.schemas.enums import ApplicationStatus

logger = logging.getLogger(__name__)


def route_after_validation(
    state: ApplicationWorkflowState,
) -> Literal["inspect_validation_errors", "handle_user_input", "handle_challenge", "prepare_review"]:
    """Decide where to go after executing actions."""
    if state.get("challenge_state"):
        return "handle_challenge"
    if state.get("status") == ApplicationStatus.READY_FOR_REVIEW.value:
        return "prepare_review"
    if state.get("status") == ApplicationStatus.WAITING_FOR_USER.value or state.get("waiting_field_ids"):
        return "handle_user_input"
    return "inspect_validation_errors"


def route_start(
    state: ApplicationWorkflowState,
) -> Literal["start_browser_session", "authorize_submission"]:
    """Determine where to start depending on if we are resuming an approved application."""
    if state.get("is_approved"):
        return "authorize_submission"
    return "start_browser_session"


def route_page_completion(
    state: ApplicationWorkflowState,
) -> Literal["inspect_page", "transition_page", "prepare_review", "handle_user_input"]:
    """Determine if we should transition, retry, or finish."""
    retry_count = state.get("retry_count", 0)
    
    if state.get("status") == ApplicationStatus.WAITING_FOR_USER.value:
        return "handle_user_input"

    if state.get("validation_errors"):
        if retry_count >= 3:
            return "handle_user_input"
        return "inspect_page"

    if state.get("status") in (ApplicationStatus.READY_FOR_REVIEW.value, ApplicationStatus.FAILED.value):
        return "prepare_review"
        
    if state.get("has_next_page"):
        print("DEBUG: route_page_completion -> transition_page")
        return "transition_page"

    print("DEBUG: route_page_completion -> prepare_review")
    return "prepare_review"


def build_application_graph() -> StateGraph[Any]:
    """Builds and returns the uncompiled LangGraph StateGraph."""
    nodes = WorkflowNodes()
    workflow = StateGraph(ApplicationWorkflowState)

    # Add Nodes
    workflow.add_node("load_application", nodes.load_application)
    workflow.add_node("start_browser_session", nodes.start_browser_session)
    workflow.add_node("inspect_page", nodes.inspect_page)
    workflow.add_node("detect_forms", nodes.detect_forms)
    workflow.add_node("classify_fields", nodes.classify_fields)
    workflow.add_node("retrieve_candidate_values", nodes.retrieve_candidate_values)
    workflow.add_node("make_field_decisions", nodes.make_field_decisions)
    workflow.add_node("prepare_actions", nodes.prepare_actions)
    workflow.add_node("validate_actions", nodes.validate_actions)
    workflow.add_node("execute_actions", nodes.execute_actions)
    workflow.add_node("inspect_validation_errors", nodes.inspect_validation_errors)
    workflow.add_node("transition_page", nodes.transition_page)
    workflow.add_node("prepare_review", nodes.prepare_review)
    workflow.add_node("handle_challenge", nodes.handle_challenge)
    workflow.add_node("handle_user_input", nodes.handle_user_input)
    workflow.add_node("authorize_submission", nodes.authorize_submission)
    workflow.add_node("submit", nodes.submit)
    workflow.add_node("verify_outcome", nodes.verify_outcome)
    workflow.add_node("persist_history", nodes.persist_history)

    # Add Edges
    workflow.add_edge(START, "load_application")

    workflow.add_conditional_edges(
        "load_application",
        route_start,
        {
            "start_browser_session": "start_browser_session",
            "authorize_submission": "authorize_submission",
        },
    )
    workflow.add_edge("start_browser_session", "inspect_page")

    # Page inspection loop
    workflow.add_edge("inspect_page", "detect_forms")
    workflow.add_edge("detect_forms", "classify_fields")
    workflow.add_edge("classify_fields", "retrieve_candidate_values")
    workflow.add_edge("retrieve_candidate_values", "make_field_decisions")
    workflow.add_edge("make_field_decisions", "prepare_actions")
    workflow.add_edge("prepare_actions", "validate_actions")
    workflow.add_edge("validate_actions", "execute_actions")

    workflow.add_conditional_edges(
        "execute_actions",
        route_after_validation,
        {
            "inspect_validation_errors": "inspect_validation_errors",
            "handle_user_input": "handle_user_input",
            "handle_challenge": "handle_challenge",
        },
    )

    workflow.add_conditional_edges(
        "inspect_validation_errors",
        route_page_completion,
        {
            "inspect_page": "inspect_page",
            "transition_page": "transition_page",
            "prepare_review": "prepare_review",
            "handle_user_input": "handle_user_input",
        },
    )

    # If transition successful, inspect the new page
    workflow.add_edge("transition_page", "inspect_page")

    # Submission path
    workflow.add_edge("authorize_submission", "submit")
    workflow.add_edge("submit", "verify_outcome")
    workflow.add_edge("verify_outcome", "persist_history")
    workflow.add_edge("persist_history", END)

    # Terminal nodes (HitL or End of Flow)
    workflow.add_edge("handle_challenge", END)
    workflow.add_edge("handle_user_input", END)
    workflow.add_edge("prepare_review", END)

    return workflow


# For easy import and compilation
application_graph = build_application_graph()
