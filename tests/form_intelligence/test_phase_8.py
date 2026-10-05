import uuid

from packages.browser.form_intelligence.decision_engine import DecisionEngine
from packages.db.models.candidate import Profile
from packages.db.models.memory import MemoryFact
from packages.schemas.enums import DecisionType, FieldRequirement, FieldType
from packages.schemas.form import DecisionContext, FieldClassification, FormField


def test_decision_engine_phase_8_trusted_exact():
    engine = DecisionEngine()
    field = FormField(
        field_id="first_name_1",
        element_id="el_1",
        form_id="form_1",
        label="First Name",
        classification=FieldClassification(
            field_type=FieldType.FIRST_NAME, confidence=1.0, requirement=FieldRequirement.REQUIRED
        ),
    )
    profile = Profile(full_name="Alice Smith")
    decision = engine.decide(field, profile=profile, memories=[])

    assert decision.decision_type == DecisionType.AUTO_FILL
    assert decision.value == "Alice"
    assert decision.trust_level == "HIGH"
    assert decision.policy_version == "phase8-v1"


def test_decision_engine_phase_8_conflict_ask_user():
    engine = DecisionEngine()
    field = FormField(
        field_id="location_1",
        element_id="el_2",
        form_id="form_1",
        label="Current Location",
        classification=FieldClassification(
            field_type=FieldType.CURRENT_LOCATION,
            confidence=1.0,
        ),
    )
    memories = [
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.CURRENT_LOCATION.value,
            value="Bhopal",
            provenance="USER_CONFIRMED",
        ),
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.CURRENT_LOCATION.value,
            value="Bengaluru",
            provenance="USER_CONFIRMED",
        ),
    ]

    decision = engine.decide(field, profile=None, memories=memories)
    assert decision.decision_type == DecisionType.ASK_USER
    assert decision.reason == "Conflicting candidate memory facts found"
    assert decision.source == "MULTIPLE"


def test_decision_engine_phase_8_medium_suggest():
    engine = DecisionEngine()
    field = FormField(
        field_id="title_1",
        element_id="el_3",
        form_id="form_1",
        label="Job Title",
        classification=FieldClassification(
            field_type=FieldType.JOB_TITLE,
            confidence=0.8,
        ),
    )
    memories = [
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.JOB_TITLE.value,
            value="Software Engineer",
            provenance="RESUME_EXTRACTED",
        )
    ]

    decision = engine.decide(field, profile=None, memories=memories)
    assert decision.decision_type == DecisionType.SUGGEST
    assert decision.value == "Software Engineer"
    assert decision.trust_level == "MEDIUM"


def test_decision_engine_phase_8_decision_context():
    engine = DecisionEngine()
    field = FormField(
        field_id="email_1",
        element_id="el_4",
        form_id="form_1",
        label="Email",
        classification=FieldClassification(
            field_type=FieldType.EMAIL,
            confidence=1.0,
        ),
    )
    memories = [
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.EMAIL.value,
            value="bob@example.com",
            provenance="USER_CONFIRMED",
        )
    ]
    context = DecisionContext(field=field, memory_facts=memories)

    decision = engine.decide(field=field, context=context)
    assert decision.decision_type == DecisionType.AUTO_FILL
    assert decision.value == "bob@example.com"
    assert decision.trust_level == "HIGH"
