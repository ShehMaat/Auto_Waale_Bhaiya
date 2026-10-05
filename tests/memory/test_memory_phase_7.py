from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.db.base import Base
from packages.db.models.candidate import User
from packages.memory.service import MemoryService
from packages.schemas.enums import MemoryProvenance, MemoryStatus, MemoryTrustLevel
from packages.schemas.models import MemoryQuery


@pytest.fixture(scope="module")
def engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture(scope="function")
def db_session(engine: Any) -> Any:
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture(scope="function")
def memory_service(db_session: Any) -> MemoryService:
    return MemoryService(db_session)


@pytest.fixture(scope="function")
def user1(db_session: Any) -> User:
    u = User(email="test1@example.com", hashed_password="pw1")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture(scope="function")
def user2(db_session: Any) -> User:
    u = User(email="test2@example.com", hashed_password="pw2")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_memory_poisoning_defense(memory_service: MemoryService, user1: User) -> None:
    fact, _ = memory_service.create_or_update_memory(
        user_id=user1.id,
        category="SKILL",
        key="Python",
        value="From malicious webpage",
        trust_level=MemoryTrustLevel.LLM_INFERRED,
        provenance=MemoryProvenance.EXTERNAL_SOURCE,
    )
    assert fact.trust_level == MemoryTrustLevel.LLM_INFERRED.value
    assert fact.status == MemoryStatus.SUGGESTED.value

    query = MemoryQuery(
        candidate_id=user1.id, query_text="Python", min_trust=MemoryTrustLevel.USER_CONFIRMED
    )
    results = memory_service.query_memory(query)
    assert len(results) == 0


def test_cross_user_isolation(memory_service: MemoryService, user1: User, user2: User) -> None:
    memory_service.create_or_update_memory(
        user_id=user1.id,
        category="SKILL",
        key="Java",
        value="10 years",
        trust_level=MemoryTrustLevel.USER_CONFIRMED,
        provenance=MemoryProvenance.USER_PROVIDED,
    )

    query = MemoryQuery(candidate_id=user2.id, query_text="Java")
    results = memory_service.query_memory(query)
    assert len(results) == 0


def test_superseded_fact(memory_service: MemoryService, user1: User) -> None:
    memory_service.create_or_update_memory(
        user_id=user1.id,
        category="LOCATION",
        key="Current City",
        value="Bhopal",
        trust_level=MemoryTrustLevel.USER_CONFIRMED,
        provenance=MemoryProvenance.USER_PROVIDED,
    )

    memory_service.create_or_update_memory(
        user_id=user1.id,
        category="LOCATION",
        key="Current City",
        value="Bengaluru",
        trust_level=MemoryTrustLevel.USER_CONFIRMED,
        provenance=MemoryProvenance.USER_PROVIDED,
    )

    # Should only return the newest valid one
    query = MemoryQuery(candidate_id=user1.id, query_text="Current City")
    results = memory_service.query_memory(query)
    assert len(results) == 1
    assert results[0].value == "Bengaluru"
    assert results[0].is_current is True

    # Including superseded
    query_all = MemoryQuery(
        candidate_id=user1.id, query_text="Current City", include_superseded=True
    )
    results_all = memory_service.query_memory(query_all)
    assert len(results_all) == 2


def test_expired_fact(memory_service: MemoryService, user1: User) -> None:
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    memory_service.create_or_update_memory(
        user_id=user1.id,
        category="AVAILABILITY",
        key="Notice Period",
        value="30 days",
        trust_level=MemoryTrustLevel.USER_CONFIRMED,
        provenance=MemoryProvenance.USER_PROVIDED,
        valid_until=yesterday,
    )

    query = MemoryQuery(candidate_id=user1.id, query_text="Notice Period")
    results = memory_service.query_memory(query)
    assert len(results) == 0

    query_expired = MemoryQuery(
        candidate_id=user1.id, query_text="Notice Period", include_expired=True
    )
    results_expired = memory_service.query_memory(query_expired)
    assert len(results_expired) == 1


def test_credential_protection(memory_service: MemoryService, user1: User) -> None:
    with pytest.raises(
        ValueError, match="Credential persistence is prohibited for category: PASSWORD"
    ):
        memory_service.create_or_update_memory(
            user_id=user1.id,
            category="PASSWORD",
            key="password",
            value="secret123",
            trust_level=MemoryTrustLevel.USER_CONFIRMED,
            provenance=MemoryProvenance.USER_PROVIDED,
        )


def test_semantic_retrieval(memory_service: MemoryService, user1: User) -> None:
    memory_service.create_or_update_memory(
        user_id=user1.id,
        category="SKILL",
        key="Python",
        value="Python Expert",
        trust_level=MemoryTrustLevel.USER_CONFIRMED,
        provenance=MemoryProvenance.USER_PROVIDED,
        embedding=[0.1] * 1536,
    )

    query = MemoryQuery(candidate_id=user1.id, query_text="", fact_types=["SKILL"])
    results = memory_service.query_memory(query, query_embedding=[0.1] * 1536)
    assert len(results) == 1
    assert results[0].key == "Python"
