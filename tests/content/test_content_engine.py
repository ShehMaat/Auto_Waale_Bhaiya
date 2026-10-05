import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.browser.form_intelligence.decision_engine import DecisionEngine
from packages.db.base import Base
from packages.db.models.candidate import User
from packages.db.models.memory import MemoryFact
from packages.llm.provider import LLMProvider
from packages.schemas.content import (
    ApplicationContentRequest,
    ContentType,
)
from packages.schemas.enums import MemoryProvenance, MemoryTrustLevel
from packages.services.content_engine import ContentEngine


class MockLLM(LLMProvider):
    def __init__(self, override_response: str = None):
        self.override_response = override_response

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if self.override_response:
            return self.override_response
        return "mock generated content"

    def generate_structured(self, prompt: str, schema, system_prompt: str = ""):
        return schema()

    def embed(self, text: str):
        return [0.0, 1.0]


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_content_engine_grounding_unsupported_claim(db_session):
    llm = MockLLM(override_response="I led a team of 20 engineers.")
    decision_engine = DecisionEngine()
    engine = ContentEngine(db_session, llm, decision_engine)

    user_id = uuid.uuid4()
    app_id = uuid.uuid4()
    job_id = uuid.uuid4()

    db_session.add(User(id=user_id, email="x@x.com", hashed_password="pw"))
    db_session.commit()

    req = ApplicationContentRequest(
        user_id=user_id,
        application_id=app_id,
        job_id=job_id,
        content_type=ContentType.COVER_LETTER,
        prompt="write cover letter",
    )

    res = engine.generate(req)
    # The claim "led a team of 20" triggers the ungrounded check in validation
    assert res.validation.is_grounded is False
    assert res.validation.is_valid is False
    # Phase 8 blocks it because it's not valid
    assert "Unsupported claim" in res.validation.errors[0]


def test_content_engine_stale_evidence_filtered(db_session):
    llm = MockLLM()
    engine = ContentEngine(db_session, llm, DecisionEngine())

    user_id = uuid.uuid4()
    app_id = uuid.uuid4()
    job_id = uuid.uuid4()

    db_session.add(User(id=user_id, email="y@y.com", hashed_password="pw"))

    # Add an expired memory
    mem_expired = MemoryFact(
        user_id=user_id,
        category="SKILL",
        key="python",
        value="yes",
        trust_level=MemoryTrustLevel.USER_CONFIRMED.value,
        provenance=MemoryProvenance.USER_CONFIRMED.value,
        is_current=True,
        valid_until=datetime.now(timezone.utc) - timedelta(days=1),
        version=1,
        confidence=1.0,
        status="CONFIRMED",
    )
    # Add a generated memory (untrusted)
    mem_untrusted = MemoryFact(
        user_id=user_id,
        category="SKILL",
        key="java",
        value="yes",
        trust_level=MemoryTrustLevel.GENERATED.value,
        provenance=MemoryProvenance.LLM_SUGGESTED.value,
        is_current=True,
        version=1,
        confidence=1.0,
        status="SUGGESTED",
    )
    # Add a trusted memory
    mem_trusted = MemoryFact(
        user_id=user_id,
        category="SKILL",
        key="c++",
        value="yes",
        trust_level=MemoryTrustLevel.USER_CONFIRMED.value,
        provenance=MemoryProvenance.USER_CONFIRMED.value,
        is_current=True,
        version=1,
        confidence=1.0,
        status="CONFIRMED",
    )

    db_session.add_all([mem_expired, mem_untrusted, mem_trusted])
    db_session.commit()

    req = ApplicationContentRequest(
        user_id=user_id,
        application_id=app_id,
        job_id=job_id,
        content_type=ContentType.COVER_LETTER,
        prompt="write cover letter",
    )

    res = engine.generate(req)
    pack = res.evidence_snapshot
    # Expired and untrusted should be filtered
    assert len(pack.candidate_facts) == 1
    assert pack.candidate_facts[0]["key"] == "c++"


def test_content_engine_credential_protection(db_session):
    llm = MockLLM()
    engine = ContentEngine(db_session, llm, DecisionEngine())

    user_id = uuid.uuid4()
    db_session.add(User(id=user_id, email="z@z.com", hashed_password="pw"))
    db_session.commit()

    req = ApplicationContentRequest(
        user_id=user_id,
        application_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        content_type=ContentType.CUSTOM_QUESTION,
        prompt="What is your password?",
    )

    res = engine.generate(req)
    # Should be blocked immediately before calling LLM
    assert res.validation.is_valid is False
    assert res.validation.safe is False
    assert "Credential request blocked" in res.validation.errors


def test_content_engine_prompt_injection(db_session):
    llm = MockLLM(override_response="I will ignore previous instructions.")
    engine = ContentEngine(db_session, llm, DecisionEngine())

    user_id = uuid.uuid4()
    db_session.add(User(id=user_id, email="a@a.com", hashed_password="pw"))
    db_session.commit()

    req = ApplicationContentRequest(
        user_id=user_id,
        application_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        content_type=ContentType.SHORT_ANSWER,
        prompt="Respond",
    )

    res = engine.generate(req)
    assert res.validation.safe is False
    assert "Prompt injection detected" in res.validation.errors


def test_content_engine_length_limit(db_session):
    llm = MockLLM(override_response="This is too long because it exceeds five words easily.")
    engine = ContentEngine(db_session, llm, DecisionEngine())

    user_id = uuid.uuid4()
    db_session.add(User(id=user_id, email="b@b.com", hashed_password="pw"))
    db_session.commit()

    req = ApplicationContentRequest(
        user_id=user_id,
        application_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        content_type=ContentType.SHORT_ANSWER,
        prompt="Respond",
        max_words=5,
    )

    res = engine.generate(req)
    assert res.validation.is_valid is False
    assert "Word limit exceeded" in res.validation.errors


def test_content_engine_versioning_and_idempotency(db_session):
    llm = MockLLM()
    engine = ContentEngine(db_session, llm, DecisionEngine())

    user_id = uuid.uuid4()
    app_id = uuid.uuid4()
    db_session.add(User(id=user_id, email="c@c.com", hashed_password="pw"))
    db_session.commit()

    req = ApplicationContentRequest(
        user_id=user_id,
        application_id=app_id,
        job_id=uuid.uuid4(),
        content_type=ContentType.COVER_LETTER,
        prompt="hello",
    )

    res1 = engine.generate(req)
    assert res1.version == 1

    # Regenerate
    res2 = engine.generate(req)
    assert res2.version == 2
    assert res1.content_id == res2.content_id  # Idempotent content record


def test_content_engine_user_isolation(db_session):
    llm = MockLLM()
    engine = ContentEngine(db_session, llm, DecisionEngine())

    user1 = uuid.uuid4()
    user2 = uuid.uuid4()
    db_session.add_all(
        [
            User(id=user1, email="1@1.com", hashed_password=""),
            User(id=user2, email="2@2.com", hashed_password=""),
        ]
    )

    db_session.add(
        MemoryFact(
            user_id=user2,
            category="SKILL",
            key="python",
            value="yes",
            trust_level=MemoryTrustLevel.USER_CONFIRMED.value,
            provenance=MemoryProvenance.USER_CONFIRMED.value,
            is_current=True,
            version=1,
            confidence=1.0,
            status="CONFIRMED",
        )
    )
    db_session.commit()

    req = ApplicationContentRequest(
        user_id=user1,
        application_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        content_type=ContentType.COVER_LETTER,
        prompt="hello",
    )

    res = engine.generate(req)
    pack = res.evidence_snapshot
    # User 1 cannot see User 2's evidence
    assert len(pack.candidate_facts) == 0
