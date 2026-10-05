from typing import Any  # noqa: I001
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.db.base import Base
from packages.db.models.candidate import User
from packages.memory.service import MemoryService
from packages.schemas.enums import MemoryProvenance, MemoryStatus, MemoryTrustLevel


@pytest.fixture(scope="module")
def engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture(scope="function")
def db_session(engine: Any) -> Any:
    Session = sessionmaker(bind=engine)
    session = Session()
    # Create test user
    user = User(email="test@example.com", hashed_password="pw")
    session.add(user)
    session.commit()
    session.refresh(user)

    yield session

    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture(scope="function")
def user(db_session: Any) -> Any:
    return db_session.query(User).first()


@pytest.fixture(scope="function")
def memory_service(db_session: Any) -> Any:
    return MemoryService(db_session)


def test_create_and_retrieve_memory(memory_service: Any, user: Any) -> None:
    fact, conflict = memory_service.create_or_update_memory(
        user_id=user.id,
        category="SKILL",
        key="Python",
        value="5 years experience",
        trust_level=MemoryTrustLevel.SYSTEM_DERIVED,
        provenance=MemoryProvenance.RESUME_EXTRACTED,
    )
    assert not conflict
    assert fact.id is not None
    assert fact.version == 1
    assert fact.is_current is True

    retrieved = memory_service.get_memory_by_key(user.id, "Python")
    assert retrieved is not None
    assert retrieved.id == fact.id
    assert retrieved.value == "5 years experience"


def test_versioning_and_conflict(memory_service: Any, user: Any) -> None:
    # Initial fact
    fact1, _ = memory_service.create_or_update_memory(
        user_id=user.id,
        category="SKILL",
        key="Python",
        value="5 years experience",
        trust_level=MemoryTrustLevel.SYSTEM_DERIVED,
        provenance=MemoryProvenance.RESUME_EXTRACTED,
    )

    # Conflict update
    fact2, conflict = memory_service.create_or_update_memory(
        user_id=user.id,
        category="SKILL",
        key="Python",
        value="7 years experience",
        trust_level=MemoryTrustLevel.SYSTEM_DERIVED,
        provenance=MemoryProvenance.RESUME_EXTRACTED,
    )
    assert not conflict  # Since trust level is the same, it creates a new version
    assert fact2.version == 2
    assert fact2.is_current is True
    assert fact2.value == "7 years experience"

    # Verify history
    history = memory_service.get_memory_history(user.id, "Python")
    assert len(history) == 2
    assert history[0].version == 2
    assert history[1].version == 1
    assert history[1].is_current is False


def test_trust_level_conflict(memory_service: Any, user: Any) -> None:
    # High trust fact
    memory_service.create_or_update_memory(
        user_id=user.id,
        category="SKILL",
        key="Docker",
        value="3 years",
        trust_level=MemoryTrustLevel.USER_CONFIRMED,
        provenance=MemoryProvenance.USER_CONFIRMED,
    )

    # Try to override with low trust fact
    fact, conflict = memory_service.create_or_update_memory(
        user_id=user.id,
        category="SKILL",
        key="Docker",
        value="1 year",
        trust_level=MemoryTrustLevel.LLM_INFERRED,
        provenance=MemoryProvenance.LLM_SUGGESTED,
    )
    assert conflict is True
    assert fact.value == "3 years"  # returns the existing fact without overriding


def test_confirm_and_invalidate(memory_service: Any, user: Any) -> None:
    fact, _ = memory_service.create_or_update_memory(
        user_id=user.id,
        category="SKILL",
        key="Kubernetes",
        value="Basic",
        trust_level=MemoryTrustLevel.LLM_INFERRED,
        provenance=MemoryProvenance.LLM_SUGGESTED,
    )
    assert fact.status == MemoryStatus.SUGGESTED.value

    # Confirm
    confirmed = memory_service.confirm_memory(user.id, fact.id)
    assert confirmed.status == MemoryStatus.CONFIRMED.value
    assert confirmed.trust_level == MemoryTrustLevel.USER_CONFIRMED.value

    # Invalidate
    invalidated = memory_service.invalidate_memory(user.id, fact.id)
    assert invalidated.status == MemoryStatus.REJECTED.value
    assert invalidated.is_current is False


def test_staleness(memory_service: Any, user: Any) -> None:
    # Create fact valid until yesterday
    fact, _ = memory_service.create_or_update_memory(
        user_id=user.id,
        category="LOCATION",
        key="Current City",
        value="New York",
        trust_level=MemoryTrustLevel.USER_CONFIRMED,
        provenance=MemoryProvenance.USER_PROVIDED,
        valid_until=datetime.now(timezone.utc) - timedelta(days=1),
    )

    stale_facts = memory_service.check_staleness(user.id)
    assert len(stale_facts) == 1
    assert stale_facts[0].id == fact.id
    assert stale_facts[0].needs_reconfirmation is True


def test_hybrid_search(memory_service: Any, user: Any) -> None:
    memory_service.create_or_update_memory(
        user.id,
        "SKILL",
        "Python",
        "Expert in Python",
        MemoryTrustLevel.SYSTEM_DERIVED,
        MemoryProvenance.RESUME_EXTRACTED,
    )
    memory_service.create_or_update_memory(
        user.id,
        "PROJECT",
        "Data Pipeline",
        "Built with Python",
        MemoryTrustLevel.SYSTEM_DERIVED,
        MemoryProvenance.RESUME_EXTRACTED,
    )
    memory_service.create_or_update_memory(
        user.id,
        "SKILL",
        "Java",
        "Basic knowledge",
        MemoryTrustLevel.SYSTEM_DERIVED,
        MemoryProvenance.RESUME_EXTRACTED,
    )

    results = memory_service.hybrid_search(user.id, "Python")
    assert len(results) == 2
    keys = [r.key for r in results]
    assert "Python" in keys
    assert "Data Pipeline" in keys

    # Category filter
    results_skill = memory_service.hybrid_search(user.id, "Python", category="SKILL")
    assert len(results_skill) == 1
    assert results_skill[0].key == "Python"
