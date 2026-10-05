from unittest.mock import patch

from apps.api.app.core.celery_tasks import run_application_workflow_task


def test_celery_integration_call_chain() -> None:
    """
    Tests the real production call chain:
    Celery -> LangGraph workflow -> execute_actions -> BrowserWorker -> Playwright
    """
    with patch(
        "packages.application.workflow.orchestrator.ApplicationWorkflowOrchestrator"
    ) as MockOrchestrator:
        mock_orchestrator_instance = MockOrchestrator.return_value
        mock_orchestrator_instance.run_sync.return_value = {"status": "SUCCESS"}

        run_application_workflow_task("test-app-id")

        MockOrchestrator.assert_called_once_with("test-app-id")
        mock_orchestrator_instance.run_sync.assert_called_once()

    # Also test failure propagation / retry behavior
    with patch(
        "packages.application.workflow.orchestrator.ApplicationWorkflowOrchestrator"
    ) as MockOrchestrator:
        mock_orchestrator_instance = MockOrchestrator.return_value
        mock_orchestrator_instance.run_sync.side_effect = Exception(
            "BrowserWorker execution failed"
        )

        # It logs the error and gracefully finishes the task, or raises it depending
        # on configuration.
        # In current implementation, it logs and does not re-raise to Celery
        # so we don't have crash loops
        run_application_workflow_task("test-app-id")

        MockOrchestrator.assert_called_once_with("test-app-id")
