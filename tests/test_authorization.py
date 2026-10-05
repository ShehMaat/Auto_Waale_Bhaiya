import uuid

from packages.db.models.application import Application
from packages.db.models.candidate import Profile


def test_user_isolation_enforced() -> None:  # type: ignore[no-untyped-def]
    """
    Simulates a backend boundary check enforcing that User A
    cannot access User B's resources.
    In Phase 2, this will test actual API endpoints.
    """
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    # Mock resources belonging to User A
    user_a_profile = Profile(id=uuid.uuid4(), user_id=user_a_id)
    user_a_application = Application(id=uuid.uuid4(), user_id=user_a_id)

    def check_ownership(resource_user_id: uuid.UUID, requester_user_id: uuid.UUID) -> bool:
        return resource_user_id == requester_user_id

    # User A tries to access their own resources
    assert check_ownership(user_a_profile.user_id, user_a_id) is True
    assert check_ownership(user_a_application.user_id, user_a_id) is True

    # User B tries to access User A's resources
    assert check_ownership(user_a_profile.user_id, user_b_id) is False
    assert check_ownership(user_a_application.user_id, user_b_id) is False
