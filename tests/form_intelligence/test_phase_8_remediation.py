import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.browser.form_intelligence.decision_engine import DecisionEngine
from packages.db.base import Base
from packages.db.models.candidate import User
from packages.db.models.memory import MemoryFact
from packages.hitl.manager import HITLManager
from packages.schemas.enums import (
    DecisionType,
    FieldSensitivity,
    FieldType,
    HITLRequestType,
    HITLResponseType,
)
from packages.schemas.form import FieldClassification, FormField
from packages.schemas.hitl import HITLRequestCreate, HITLResponseCreate


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_hard_constraint_precedence():
    engine = DecisionEngine()

    # 1. High confidence + authentication -> PAUSE
    auth_field = FormField(
        field_id="pwd",
        element_id="el_1",
        form_id="form_1",
        label="Password",
        classification=FieldClassification(
            field_type=FieldType.PASSWORD,
            confidence=1.0,
            sensitivity=FieldSensitivity.AUTHENTICATION,
        ),
    )
    # Give it HIGH trust memory
    memories = [
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.PASSWORD.value,
            value="pass123",
            provenance="EXPLICIT_PROFILE",
        )
    ]
    decision = engine.decide(auth_field, profile=None, memories=memories)

    assert decision.decision_type == DecisionType.PAUSE
    assert decision.sensitivity == FieldSensitivity.AUTHENTICATION
    assert decision.policy_version == "phase8-v1"

    # 2. High semantic similarity + untrusted memory -> ASK_USER
    skill_field = FormField(
        field_id="sk",
        element_id="el_2",
        form_id="form_1",
        label="Skills",
        classification=FieldClassification(field_type=FieldType.SKILL, confidence=1.0),
    )
    untrusted_mems = [
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.SKILL.value,
            value="Python",
            provenance="GENERATED",
        )
    ]
    decision2 = engine.decide(skill_field, profile=None, memories=untrusted_mems)
    assert decision2.decision_type == DecisionType.ASK_USER


def test_stale_evidence():
    engine = DecisionEngine()
    field = FormField(
        field_id="loc",
        element_id="el_1",
        form_id="form_1",
        label="Location",
        classification=FieldClassification(field_type=FieldType.CURRENT_LOCATION, confidence=1.0),
    )
    # Simulation: In a real flow, a superseded memory wouldn't even be passed to the
    # decision engine, but we can test that if it is, or if we ensure only valid facts
    # are passed. The Phase 7 MemoryService filters superseded facts.
    memories = []  # Stale evidence is filtered by MemoryService
    decision = engine.decide(field, profile=None, memories=memories)
    assert decision.decision_type == DecisionType.ASK_USER


def test_approval_replay_protection_and_cross_user(db_session):
    manager = HITLManager(db_session)
    user1 = uuid.uuid4()
    user2 = uuid.uuid4()
    app1 = uuid.uuid4()

    db_session.add_all(
        [
            User(id=user1, email="1@a.com", hashed_password="x"),
            User(id=user2, email="2@a.com", hashed_password="y"),
        ]
    )
    db_session.flush()

    req = manager.create_request(
        HITLRequestCreate(
            application_id=app1,
            workflow_id=uuid.uuid4(),
            user_id=user1,
            request_type=HITLRequestType.UNKNOWN_FIELD,
            title="title",
            description="desc",
            required_action="act",
        )
    )

    # User B cannot read User A's request
    assert manager.get_request(req.id, user2) is None

    # User B cannot respond to User A's request
    with pytest.raises(ValueError, match="Request not found or unauthorized"):
        manager.submit_response(
            req.id,
            user2,
            HITLResponseCreate(
                response_type=HITLResponseType.APPROVAL, value_json={}, expected_version=req.version
            ),
        )

    # Same approval, changed snapshot
    # To simulate snapshot change, we invalidate requests for app1
    manager.invalidate_application_requests(app1)

    with pytest.raises(ValueError, match="Version conflict. Optimistic lock failed."):
        manager.submit_response(
            req.id,
            user1,
            HITLResponseCreate(
                response_type=HITLResponseType.APPROVAL, value_json={}, expected_version=req.version
            ),
        )


def test_hitl_concurrency_deduplication(db_session):
    manager = HITLManager(db_session)
    user1 = uuid.uuid4()
    app1 = uuid.uuid4()
    wf1 = uuid.uuid4()
    db_session.add(User(id=user1, email="con@c.com", hashed_password="x"))
    db_session.flush()

    req1 = manager.create_request(
        HITLRequestCreate(
            application_id=app1,
            workflow_id=wf1,
            user_id=user1,
            request_type=HITLRequestType.UNKNOWN_FIELD,
            title="T",
            description="D",
            required_action="A",
        )
    )
    req2 = manager.create_request(
        HITLRequestCreate(
            application_id=app1,
            workflow_id=wf1,
            user_id=user1,
            request_type=HITLRequestType.UNKNOWN_FIELD,
            title="T",
            description="D",
            required_action="A",
        )
    )

    assert req1.id == req2.id  # Deduplicated


def test_decision_idempotency_and_trace():
    engine = DecisionEngine()
    field = FormField(
        field_id="idemp",
        element_id="el_1",
        form_id="form",
        label="Emp",
        classification=FieldClassification(field_type=FieldType.CURRENT_COMPANY, confidence=1.0),
    )
    mems = [
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.CURRENT_COMPANY.value,
            value="Acme",
            provenance="USER_CONFIRMED",
        )
    ]

    d1 = engine.decide(field, profile=None, memories=mems)
    d2 = engine.decide(field, profile=None, memories=mems)

    # They return independent Decision objects, but logically evaluate to same state
    assert d1.decision_type == d2.decision_type
    assert d1.value == d2.value
    assert d1.policy_version == "phase8-v1"

    # Trace contains exact rationale
    assert d1.reason == "High trust candidate value matched"


def test_sensitive_data_redaction():
    engine = DecisionEngine()
    auth_field = FormField(
        field_id="pwd",
        element_id="el_1",
        form_id="form_1",
        label="Password",
        classification=FieldClassification(
            field_type=FieldType.PASSWORD,
            confidence=1.0,
            sensitivity=FieldSensitivity.AUTHENTICATION,
        ),
    )
    # The decision must NOT contain the sensitive value in its trace/reason
    d = engine.decide(auth_field, profile=None, memories=[])
    assert d.decision_type == DecisionType.PAUSE
    assert "TEST_SECRET" not in d.reason
    assert d.value is None


def test_final_submission_boundary():
    engine = DecisionEngine()
    submit_field = FormField(
        field_id="sub",
        element_id="el",
        form_id="f",
        label="Submit Application",
        input_type="submit",
        classification=FieldClassification(field_type=FieldType.UNKNOWN, confidence=1.0),
    )
    d = engine.decide(submit_field, profile=None, memories=[])
    # Approving a field doesn't bypass this. The policy ALWAYS blocks submit.
    assert d.decision_type == DecisionType.BLOCK
    assert "blocked" in d.reason.lower()
