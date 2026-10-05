import uuid
from typing import Any

from packages.application.workflow.orchestrator import ApplicationWorkflowOrchestrator


def test_concurrent_workflow_lock(monkeypatch: Any) -> None:
    app_id = str(uuid.uuid4())

    # We want to simulate that exactly one acquires the lock.
    # Since PG advisory locks in Python require separate db sessions or threads,
    # we will mock the lock acquisition logic to simulate thread overlapping.

    lock_state = {"acquired": False, "executions": 0}

    class MockSession:
        def __enter__(self: Any) -> Any:
            return self

        def __exit__(self: Any, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

        def execute(self: Any, query: Any, params: Any = None) -> Any:
            class MockResult:
                def scalar(self: Any) -> Any:
                    if lock_state["acquired"]:
                        return False
                    lock_state["acquired"] = True
                    return True

            return MockResult()

        def query(self: Any, *args: Any, **kwargs: Any) -> Any:
            return self

        def filter(self: Any, *args: Any, **kwargs: Any) -> Any:
            return self

        def first(self: Any) -> Any:
            class MockRecord:
                id = uuid.uuid4()
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

    # Mock the graph invoke so we can count executions
    async def mock_ainvoke(*args: Any, **kwargs: Any) -> Any:
        lock_state["executions"] += 1
        return {"status": "TEST_COMPLETE"}

    orc1 = ApplicationWorkflowOrchestrator(app_id)
    orc1.app.ainvoke = mock_ainvoke  # type: ignore[method-assign]

    orc2 = ApplicationWorkflowOrchestrator(app_id)
    orc2.app.ainvoke = mock_ainvoke  # type: ignore[method-assign]

    res1 = orc1.run_sync()
    res2 = orc2.run_sync()

    # The first one to run grabs the lock and executes
    assert res1.get("status") == "TEST_COMPLETE"
    assert res2.get("status") == "LOCKED"

    # Exactly one execution occurred
    assert lock_state["executions"] == 1


def test_different_applications_can_execute_concurrently(monkeypatch: Any) -> None:
    app_id_1 = str(uuid.uuid4())
    app_id_2 = str(uuid.uuid4())

    locks = set()
    executions = 0

    class MockSession:
        def __init__(self: Any, lock_id: Any = None) -> None:
            self.lock_id = lock_id

        def __enter__(self: Any) -> Any:
            return self

        def __exit__(self: Any, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

        def execute(self: Any, query: Any, params: Any = None) -> Any:
            self.lock_id = params["lock_id"]

            class MockResult:
                def scalar(self_inner: Any) -> Any:
                    if self.lock_id in locks:
                        return False
                    locks.add(self.lock_id)
                    return True

            return MockResult()

        def query(self: Any, *args: Any, **kwargs: Any) -> Any:
            return self

        def filter(self: Any, *args: Any, **kwargs: Any) -> Any:
            return self

        def first(self: Any) -> Any:
            class MockRecord:
                id = uuid.uuid4()
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

    async def mock_ainvoke(*args: Any, **kwargs: Any) -> Any:
        nonlocal executions
        executions += 1
        return {"status": "TEST_COMPLETE"}

    orc1 = ApplicationWorkflowOrchestrator(app_id_1)
    orc1.app.ainvoke = mock_ainvoke  # type: ignore[method-assign]

    orc2 = ApplicationWorkflowOrchestrator(app_id_2)
    orc2.app.ainvoke = mock_ainvoke  # type: ignore[method-assign]

    res1 = orc1.run_sync()
    res2 = orc2.run_sync()

    assert res1.get("status") == "TEST_COMPLETE"
    assert res2.get("status") == "TEST_COMPLETE"
    assert executions == 2
