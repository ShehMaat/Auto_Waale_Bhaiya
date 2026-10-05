import uuid
from typing import Any

import pytest

from packages.application.workflow.orchestrator import ApplicationWorkflowOrchestrator
from packages.schemas.enums import ApplicationStatus


@pytest.mark.asyncio
async def test_end_to_end_workflow_integration(monkeypatch: Any) -> None:
    # A mocked full run through the graph to ensure it reaches READY_FOR_REVIEW
    # We will simulate the graph nodes by forcing state changes that route it correctly.

    app_id = str(uuid.uuid4())
    orchestrator = ApplicationWorkflowOrchestrator(app_id)

    # We want to trace the path the workflow takes.
    # Instead of running the full nodes (which lack a real DB connection here),
    # we can invoke the compiled graph with mocked node functions if necessary,
    # but the orchestrator's graph has real node functions.
    # We will just patch the WorkflowNodes methods to return desired states.

    async def mock_load(self: Any, state: Any) -> Any:
        return {"status": "STARTED"}

    async def mock_start(self: Any, state: Any) -> Any:
        return {"status": "STARTED", "browser_session_id": "s1"}

    async def mock_inspect(self: Any, state: Any) -> Any:
        return {"status": "FORM_INSPECTED"}

    async def mock_detect(self: Any, state: Any) -> Any:
        return {"status": "FORM_INSPECTED"}

    async def mock_classify(self: Any, state: Any) -> Any:
        return {"status": "MAPPING_FIELDS"}

    async def mock_retrieve(self: Any, state: Any) -> Any:
        return {"status": "MAPPING_FIELDS"}

    async def mock_decide(self: Any, state: Any) -> Any:
        return {"status": "FILLING"}

    async def mock_prepare(self: Any, state: Any) -> Any:
        return {"status": "FILLING"}

    async def mock_validate(self: Any, state: Any) -> Any:
        return {"status": "VALIDATING"}

    async def mock_execute(self: Any, state: Any) -> Any:
        return {"status": "VALIDATING"}

    async def mock_err(self: Any, state: Any) -> Any:
        # Fake that we completed everything and have no errors, and are ready for review
        return {"status": ApplicationStatus.READY_FOR_REVIEW.value, "validation_errors": []}

    async def mock_transition(self: Any, state: Any) -> Any:
        return {"status": "PAGE_TRANSITION"}

    async def mock_review(self: Any, state: Any) -> Any:
        return {"status": ApplicationStatus.READY_FOR_REVIEW.value}

    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.load_application", mock_load
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.start_browser_session", mock_start
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.inspect_page", mock_inspect
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.detect_forms", mock_detect
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.classify_fields", mock_classify
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.retrieve_candidate_values", mock_retrieve
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.make_field_decisions", mock_decide
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.prepare_actions", mock_prepare
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.validate_actions", mock_validate
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.execute_actions", mock_execute
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.inspect_validation_errors", mock_err
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.transition_page", mock_transition
    )
    monkeypatch.setattr(
        "packages.application.workflow.nodes.WorkflowNodes.prepare_review", mock_review
    )

    # We must patch the DB dependencies in the Orchestrator
    class MockSession:
        def __enter__(self: Any) -> Any:
            return self

        def __exit__(self: Any, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

        def execute(self: Any, query: Any, params: Any = None) -> Any:
            class MockResult:
                def scalar(self: Any) -> Any:
                    return True  # successfully locked

            return MockResult()

        def query(self: Any, *args: Any, **kwargs: Any) -> Any:
            return self

        def filter(self: Any, *args: Any, **kwargs: Any) -> Any:
            return self

        def first(self: Any) -> Any:
            # return fake workflow record
            class MockRecord:
                id = uuid.uuid4()
                user_id = uuid.uuid4()
                user_id = uuid.uuid4()
                browser_session_id = None
                current_page_index = 0
                validation_errors_json: list[Any] = []

            return MockRecord()

        def add(self: Any, *args: Any) -> None:
            pass

        def commit(self: Any) -> None:
            pass

        def rollback(self: Any) -> None:
            pass

    monkeypatch.setattr("packages.application.workflow.orchestrator.SessionLocal", MockSession)

    # Re-instantiate so the patched nodes are picked up in graph building
    from packages.application.workflow.graph import build_application_graph

    orchestrator.app = build_application_graph().compile()

    final_state = await orchestrator.run_async()

    assert final_state["status"] == ApplicationStatus.READY_FOR_REVIEW.value
    # Assert we never reach submit
    assert final_state["status"] != ApplicationStatus.SUBMITTED.value
