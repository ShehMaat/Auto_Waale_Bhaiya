import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from packages.db.models.application import Application, ApplicationWorkflow
from packages.db.models.candidate import User
from packages.db.models.jobs import Job
from packages.hitl.manager import HITLManager
from packages.schemas.enums import HITLRequestStatus, HITLRequestType, HITLResponseType
from packages.schemas.hitl import HITLRequestCreate, HITLResponseCreate


def test_hitl_request_lifecycle(db_session: Session) -> None:
    # Setup mock data
    user_id = uuid.uuid4()
    app_id = uuid.uuid4()
    wf_id = uuid.uuid4()

    # 1. Insert required FK entities
    user = User(id=user_id, email="test@hitl.com", hashed_password="test")
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        source_job_id="test_job_1",
        title="Test Job",
        company="Test",
        description="Test",
        url="http://test.com",
    )
    db_session.add_all([user, job])
    db_session.flush()

    app = Application(id=app_id, user_id=user_id, job_id=job_id, status="STARTED")
    wf = ApplicationWorkflow(id=wf_id, application_id=app_id)
    db_session.add_all([app, wf])
    db_session.flush()

    manager = HITLManager(db_session)

    # 2. Create Request
    req_data = HITLRequestCreate(
        application_id=app_id,
        workflow_id=wf_id,
        user_id=user_id,
        request_type=HITLRequestType.UNKNOWN_FIELD,
        title="Need candidate salary",
        description="What is expected salary?",
        required_action="Provide a number",
    )

    created_req = manager.create_request(req_data)
    assert created_req.status == HITLRequestStatus.PENDING

    # 3. Mark Viewed
    success = manager.mark_viewed(created_req.id, user_id)
    assert success

    req_viewed = manager.get_request(created_req.id, user_id)
    assert req_viewed is not None
    assert req_viewed.status == HITLRequestStatus.VIEWED
    assert req_viewed.version == 2

    # 4. Respond
    resp_data = HITLResponseCreate(
        response_type=HITLResponseType.NUMBER, value_json=100000, expected_version=2
    )

    success = manager.submit_response(created_req.id, user_id, resp_data)
    assert success

    req_resolved = manager.get_request(created_req.id, user_id)
    assert req_resolved is not None
    assert req_resolved.status == HITLRequestStatus.RESOLVED
    assert req_resolved.resolved_at is not None
    assert req_resolved.version == 3


def test_hitl_optimistic_concurrency(db_session: Session) -> None:
    # Setup mock data
    user_id = uuid.uuid4()
    app_id = uuid.uuid4()
    wf_id = uuid.uuid4()
    job_id = uuid.uuid4()

    user = User(id=user_id, email="test2@hitl.com", hashed_password="test")
    job = Job(
        id=job_id,
        source_job_id="test_job_2",
        title="Test Job 2",
        company="Test 2",
        description="Test 2",
        url="http://test.com",
    )
    db_session.add_all([user, job])
    db_session.flush()

    app = Application(id=app_id, user_id=user_id, job_id=job_id, status="STARTED")
    wf = ApplicationWorkflow(id=wf_id, application_id=app_id)
    db_session.add_all([app, wf])
    db_session.flush()

    manager = HITLManager(db_session)

    req_data = HITLRequestCreate(
        application_id=app_id,
        workflow_id=wf_id,
        user_id=user_id,
        request_type=HITLRequestType.CAPTCHA,
        title="Captcha",
        description="Solve",
        required_action="Solve",
    )
    created = manager.create_request(req_data)

    resp_data = HITLResponseCreate(
        response_type=HITLResponseType.BOOLEAN,
        value_json=True,
        expected_version=999,  # Wrong version
    )

    with pytest.raises(ValueError, match="Version conflict"):
        manager.submit_response(created.id, user_id, resp_data)


def test_hitl_expiration(db_session: Session) -> None:
    user_id = uuid.uuid4()
    app_id = uuid.uuid4()
    wf_id = uuid.uuid4()
    job_id = uuid.uuid4()

    user = User(id=user_id, email="expire@hitl.com", hashed_password="test")
    job = Job(
        id=job_id,
        source_job_id="test_job_3",
        title="Test Job 3",
        company="Test 3",
        description="Test 3",
        url="http://test.com",
    )
    db_session.add_all([user, job])
    db_session.flush()

    app = Application(id=app_id, user_id=user_id, job_id=job_id, status="STARTED")
    wf = ApplicationWorkflow(id=wf_id, application_id=app_id)
    db_session.add_all([app, wf])
    db_session.flush()

    manager = HITLManager(db_session)

    past_time = datetime.now(timezone.utc) - timedelta(hours=1)

    req_data = HITLRequestCreate(
        application_id=app_id,
        workflow_id=wf_id,
        user_id=user_id,
        request_type=HITLRequestType.OTP,
        title="OTP",
        description="OTP",
        required_action="OTP",
        expires_at=past_time,
    )
    created = manager.create_request(req_data)

    # Should expire stale
    expired_count = manager.expire_stale_requests()
    assert expired_count >= 1

    # Attempting to respond should fail
    resp_data = HITLResponseCreate(
        response_type=HITLResponseType.TEXT, value_json="123456", expected_version=2
    )

    with pytest.raises(ValueError, match="Cannot respond to request in EXPIRED state"):
        manager.submit_response(created.id, user_id, resp_data)
