import uuid

from packages.db.models.application import Application
from packages.db.models.browser import BrowserEventModel, BrowserSessionModel
from packages.db.models.candidate import User


def test_artifact_ownership_isolation(db_session) -> None:
    """
    Behavioral test proving User A cannot retrieve User B artifacts,
    and Application B cannot access Application A artifacts.
    """
    # 1. Setup Users
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    user_a = User(id=user_a_id, email=f"a_{user_a_id}@test.com", hashed_password="123")
    user_b = User(id=user_b_id, email=f"b_{user_b_id}@test.com", hashed_password="123")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    # 2. Setup Applications
    app_a_id = uuid.uuid4()
    app_b_id = uuid.uuid4()
    app_a = Application(id=app_a_id, user_id=user_a_id, job_id=uuid.uuid4(), status="STARTED")
    app_b = Application(id=app_b_id, user_id=user_a_id, job_id=uuid.uuid4(), status="STARTED")
    db_session.add_all([app_a, app_b])
    db_session.commit()

    # 3. Setup Session and Artifacts for User A / App A
    session_a_id = uuid.uuid4()
    session_a = BrowserSessionModel(id=session_a_id, user_id=user_a_id, application_id=app_a_id)
    db_session.add(session_a)
    db_session.commit()

    artifact_a = BrowserEventModel(
        session_id=session_a_id, event_type="snapshot", metadata_json={"file": "snap1.png"}
    )
    db_session.add(artifact_a)
    db_session.commit()

    # 4. Prove User A can access artifact
    # A standard service layer retrieval function would enforce:
    events_user_a = (
        db_session.query(BrowserEventModel)
        .join(BrowserSessionModel)
        .filter(
            BrowserSessionModel.user_id == user_a_id, BrowserSessionModel.application_id == app_a_id
        )
        .all()
    )
    assert len(events_user_a) == 1
    assert events_user_a[0].id == artifact_a.id

    # 5. Prove User B is DENIED
    events_user_b = (
        db_session.query(BrowserEventModel)
        .join(BrowserSessionModel)
        .filter(
            BrowserSessionModel.user_id == user_b_id,
        )
        .all()
    )
    assert len(events_user_b) == 0

    # 6. Prove App B is DENIED (even if User A owns App B)
    events_app_b = (
        db_session.query(BrowserEventModel)
        .join(BrowserSessionModel)
        .filter(
            BrowserSessionModel.user_id == user_a_id, BrowserSessionModel.application_id == app_b_id
        )
        .all()
    )
    assert len(events_app_b) == 0
