from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_check(client: TestClient) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/ready")
    assert response.status_code == 200
    # It might return ready or error depending on local services,
    # but the endpoint itself should respond 200.
    data = response.json()
    assert "status" in data
