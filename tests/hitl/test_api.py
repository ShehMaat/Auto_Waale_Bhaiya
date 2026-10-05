import uuid
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.app.api.deps import get_current_user
from apps.api.app.api.endpoints.hitl import (
    router as hitl_router,
)
from apps.api.app.api.endpoints.review import (
    router as review_router,
)
from packages.db.models.hitl import HITLRequestModel
from packages.db.session import get_db
from packages.schemas.enums import HITLRequestStatus, HITLRequestType

app = FastAPI()
app.include_router(hitl_router)
app.include_router(review_router)


@pytest.fixture
def sample_hitl_request(db_session: Session) -> HITLRequestModel:
    from packages.db.models.application import Application, ApplicationWorkflow
    from packages.db.models.candidate import User
    from packages.db.models.jobs import Job

    user_id = uuid.uuid4()
    app_id = uuid.uuid4()
    wf_id = uuid.uuid4()
    job_id = uuid.uuid4()

    user = User(id=user_id, email=f"api_{uuid.uuid4()}@hitl.com", hashed_password="test")
    job = Job(
        id=job_id,
        source_job_id="test_job_api",
        title="API Job",
        company="API",
        description="API",
        url="http://test.com",
    )
    db_session.add_all([user, job])
    db_session.flush()

    app_model = Application(id=app_id, user_id=user_id, job_id=job_id, status="STARTED")
    wf_model = ApplicationWorkflow(id=wf_id, application_id=app_id)
    db_session.add_all([app_model, wf_model])
    db_session.flush()

    req = HITLRequestModel(
        id=uuid.uuid4(),
        application_id=app_id,
        workflow_id=wf_id,
        user_id=user_id,
        request_type=HITLRequestType.UNKNOWN_FIELD.value,
        title="Test Request",
        description="Please provide info",
        context_json={"field": "test", "secret_key": "hidden"},
        required_action="Provide text",
        status=HITLRequestStatus.PENDING.value,
        version=1,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


@pytest.fixture
def authed_client(
    db_session: Session, sample_hitl_request: HITLRequestModel
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    from packages.db.models.candidate import User
    def override_get_current_user() -> User:
        return User(id=sample_hitl_request.user_id)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    from fastapi import HTTPException

    from fastapi import HTTPException
    def override_get_current_user_401() -> "User":
        raise HTTPException(status_code=401, detail="Unauthorized")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user_401

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def another_user_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    from packages.db.models.candidate import User
    def override_get_current_user() -> User:
        return User(id=uuid.uuid4())

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# --- 1. AUTHENTICATION TESTS ---
def test_unauthenticated_access(
    unauthed_client: TestClient, sample_hitl_request: HITLRequestModel
) -> None:
    resp = unauthed_client.get(f"/applications/{sample_hitl_request.application_id}/hitl")
    assert resp.status_code == 401

    resp = unauthed_client.get(f"/applications/hitl/{sample_hitl_request.id}")
    assert resp.status_code == 401

    resp = unauthed_client.post(
        f"/applications/hitl/{sample_hitl_request.id}/respond",
        json={"response_type": "TEXT", "value_json": "A", "expected_version": 1},
    )
    assert resp.status_code == 401

    resp = unauthed_client.get(
        f"/applications/{sample_hitl_request.application_id}/review/completeness"
    )
    assert resp.status_code == 401


# --- 2. CROSS-USER AUTHORIZATION TESTS ---
def test_cross_user_access(
    another_user_client: TestClient, sample_hitl_request: HITLRequestModel
) -> None:
    resp = another_user_client.get(f"/applications/{sample_hitl_request.application_id}/hitl")
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = another_user_client.get(f"/applications/hitl/{sample_hitl_request.id}")
    assert resp.status_code == 404

    resp = another_user_client.post(
        f"/applications/hitl/{sample_hitl_request.id}/respond",
        json={"response_type": "TEXT", "value_json": "A", "expected_version": 1},
    )
    assert resp.status_code == 404


# --- 3. LIFECYCLE & RESPONSE VALIDATION TESTS ---
def test_valid_response(authed_client: TestClient, sample_hitl_request: HITLRequestModel) -> None:
    payload = {"response_type": "TEXT", "value_json": "My Response Data", "expected_version": 1}
    resp = authed_client.post(f"/applications/hitl/{sample_hitl_request.id}/respond", json=payload)
    assert resp.status_code == 200

    resp = authed_client.get(f"/applications/hitl/{sample_hitl_request.id}")
    data = resp.json()
    assert data["status"] == HITLRequestStatus.RESOLVED.value
    assert data["version"] == 2


def test_duplicate_response(
    authed_client: TestClient, sample_hitl_request: HITLRequestModel
) -> None:
    payload = {"response_type": "TEXT", "value_json": "A", "expected_version": 1}
    resp = authed_client.post(f"/applications/hitl/{sample_hitl_request.id}/respond", json=payload)
    assert resp.status_code == 200

    payload2 = {"response_type": "TEXT", "value_json": "B", "expected_version": 1}
    resp2 = authed_client.post(
        f"/applications/hitl/{sample_hitl_request.id}/respond", json=payload2
    )
    assert resp2.status_code == 400


def test_version_conflict(
    authed_client: TestClient, sample_hitl_request: HITLRequestModel, db_session: Session
) -> None:
    sample_hitl_request.version = 2
    db_session.commit()

    payload = {"response_type": "TEXT", "value_json": "A", "expected_version": 1}
    resp = authed_client.post(f"/applications/hitl/{sample_hitl_request.id}/respond", json=payload)
    assert resp.status_code == 400


def test_expiration(
    authed_client: TestClient, sample_hitl_request: HITLRequestModel, db_session: Session
) -> None:
    sample_hitl_request.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    payload = {"response_type": "TEXT", "value_json": "A", "expected_version": 1}
    resp = authed_client.post(f"/applications/hitl/{sample_hitl_request.id}/respond", json=payload)
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


def test_cancellation(authed_client: TestClient, sample_hitl_request: HITLRequestModel) -> None:
    resp = authed_client.post(f"/applications/hitl/{sample_hitl_request.id}/cancel")
    assert resp.status_code == 200

    payload = {"response_type": "TEXT", "value_json": "A", "expected_version": 2}
    resp = authed_client.post(f"/applications/hitl/{sample_hitl_request.id}/respond", json=payload)
    assert resp.status_code == 400


def test_safe_context(authed_client: TestClient, sample_hitl_request: HITLRequestModel) -> None:
    resp = authed_client.get(f"/applications/hitl/{sample_hitl_request.id}")
    data = resp.json()
    assert "secret_key" not in data["context_json"]
