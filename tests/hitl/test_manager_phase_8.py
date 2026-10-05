import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.db.base import Base
from packages.db.models.candidate import User
from packages.hitl.manager import HITLManager
from packages.schemas.enums import HITLRequestStatus, HITLRequestType
from packages.schemas.hitl import HITLRequestCreate


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_hitl_manager_phase_8_invalidation(db_session):
    manager = HITLManager(db_session)

    # Create test user
    user_id = uuid.uuid4()
    app_id = uuid.uuid4()

    user = User(id=user_id, email="test@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    # Create requests for the application
    req1 = manager.create_request(
        HITLRequestCreate(
            application_id=app_id,
            workflow_id=uuid.uuid4(),
            user_id=user_id,
            request_type=HITLRequestType.AUTHENTICATION,
            title="Auth",
            description="Need OTP",
            required_action="Provide OTP",
        )
    )

    req2 = manager.create_request(
        HITLRequestCreate(
            application_id=app_id,
            workflow_id=uuid.uuid4(),
            user_id=user_id,
            request_type=HITLRequestType.SENSITIVE_FIELD,
            title="Salary",
            description="Confirm Salary",
            required_action="Confirm",
        )
    )

    # Mark req2 as VIEWED
    manager.mark_viewed(req2.id, user_id)

    # Invalidate all for app_id
    invalidated_count = manager.invalidate_application_requests(app_id)
    assert invalidated_count == 2

    # Verify status
    db_req1 = manager.get_request(req1.id, user_id)
    db_req2 = manager.get_request(req2.id, user_id)
    assert db_req1.status == HITLRequestStatus.EXPIRED
    assert db_req2.status == HITLRequestStatus.EXPIRED
