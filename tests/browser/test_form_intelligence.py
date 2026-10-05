import uuid

import pytest

from packages.browser.form_intelligence.classifier import FieldClassifier
from packages.browser.form_intelligence.decision_engine import DecisionEngine
from packages.browser.form_intelligence.detector import FormDetector
from packages.browser.form_intelligence.executor_bridge import ExecutionBridge
from packages.db.models.candidate import Profile
from packages.db.models.memory import MemoryFact
from packages.schemas.browser_actions import DOMElement, ElementMetadata, PageModel
from packages.schemas.enums import DecisionType, FieldSensitivity, FieldType
from packages.schemas.form import FieldClassification, FieldDecision, FormField


@pytest.fixture
def detector() -> FormDetector:
    return FormDetector()


@pytest.fixture
def classifier() -> FieldClassifier:
    return FieldClassifier(llm=None)


@pytest.fixture
def engine() -> DecisionEngine:
    return DecisionEngine()


@pytest.fixture
def bridge() -> ExecutionBridge:
    return ExecutionBridge()


def test_form_detection(detector: FormDetector) -> None:
    page = PageModel(
        snapshot_id="snap-123",
        url="http://jobs.com",
        title="Apply",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(
                    tag_name="input",
                    is_visible=True,
                    is_interactive=True,
                    input_type="text",
                    aria_label="First Name",
                ),
            ),
            DOMElement(
                element_id="el-2",
                metadata=ElementMetadata(
                    tag_name="div", is_visible=True, is_interactive=False, text="Not an input"
                ),
            ),
        ],
    )

    form = detector.detect(page)
    assert len(form.fields) == 1
    assert form.fields[0].label == "First Name"
    assert form.fields[0].element_id == "el-1"


def test_field_classification(classifier: FieldClassifier) -> None:
    # Deterministic test
    field_email = FormField(
        field_id="1", element_id="el-1", form_id="f1", input_type="email", label="Email Address"
    )
    field_pass = FormField(
        field_id="2", element_id="el-2", form_id="f1", input_type="password", label="Password"
    )
    field_salary = FormField(
        field_id="3", element_id="el-3", form_id="f1", input_type="text", label="Expected Salary"
    )

    cls_email = classifier.classify(field_email)
    cls_pass = classifier.classify(field_pass)
    cls_salary = classifier.classify(field_salary)

    assert cls_email.field_type == FieldType.EMAIL

    assert cls_pass.field_type == FieldType.PASSWORD
    assert cls_pass.sensitivity == FieldSensitivity.AUTHENTICATION

    assert cls_salary.field_type == FieldType.EXPECTED_SALARY
    assert cls_salary.sensitivity == FieldSensitivity.SENSITIVE


def test_decision_engine_submission_blocked(engine: DecisionEngine) -> None:
    field = FormField(
        field_id="1",
        element_id="el-1",
        form_id="f1",
        input_type="submit",
        label="Submit Application",
    )
    # Fake a classification
    field.classification = FieldClassification(field_type=FieldType.UNKNOWN, confidence=0.0)

    decision = engine.decide(field, None, [])
    assert decision.decision_type == DecisionType.BLOCK
    assert "submission is blocked" in decision.reason


def test_decision_engine_challenge_blocked(engine: DecisionEngine) -> None:
    field = FormField(field_id="1", element_id="el-1", form_id="f1", label="Captcha")
    field.classification = FieldClassification(
        field_type=FieldType.CAPTCHA, confidence=1.0, sensitivity=FieldSensitivity.CHALLENGE
    )

    decision = engine.decide(field, None, [])
    assert decision.decision_type == DecisionType.PAUSE
    assert decision.requires_user is True


def test_decision_engine_sensitive_ask_user(engine: DecisionEngine) -> None:
    field = FormField(field_id="1", element_id="el-1", form_id="f1", label="Salary")
    field.classification = FieldClassification(
        field_type=FieldType.EXPECTED_SALARY, confidence=1.0, sensitivity=FieldSensitivity.SENSITIVE
    )

    # Even with a candidate value mapped...
    profile = Profile(id=uuid.uuid4(), user_id=uuid.uuid4())
    memories = [
        MemoryFact(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=FieldType.EXPECTED_SALARY.value,
            key=FieldType.EXPECTED_SALARY.value,
            value="100000",
            trust_level="USER_CONFIRMED",
            confidence=1.0,
            provenance="USER_CONFIRMED",
            status="CONFIRMED",
        )
    ]

    decision = engine.decide(field, profile, memories)
    assert decision.decision_type == DecisionType.ASK_USER
    assert decision.requires_user is True
    assert decision.sensitivity == FieldSensitivity.SENSITIVE


def test_decision_engine_auto_fill(engine: DecisionEngine) -> None:
    field = FormField(field_id="1", element_id="el-1", form_id="f1", label="First Name")
    field.classification = FieldClassification(field_type=FieldType.FIRST_NAME, confidence=1.0)

    profile = Profile(id=uuid.uuid4(), user_id=uuid.uuid4(), full_name="Alice Smith")

    decision = engine.decide(field, profile, [])
    assert decision.decision_type == DecisionType.AUTO_FILL
    assert decision.proposed_action is not None
    assert decision.proposed_action["value"] == "Alice"


def test_executor_bridge(bridge: ExecutionBridge) -> None:
    field = FormField(field_id="f-1", element_id="el-1", form_id="f1", input_type="text")
    decision = FieldDecision(
        decision_id="d-1",
        field_id="f-1",
        decision_type=DecisionType.AUTO_FILL,
        reason="",
        confidence=1.0,
        source="SYSTEM",
        proposed_action={"value": "Alice"},
    )

    actions = bridge.draft_actions("session-123", [decision], [field])
    assert len(actions) == 1
    assert actions[0].action_type == "fill"
    assert actions[0].text == "Alice"


def test_executor_bridge_checkbox_and_select(bridge: ExecutionBridge) -> None:
    f1 = FormField(field_id="cb-1", element_id="el-1", form_id="f1", input_type="checkbox")
    d1 = FieldDecision(
        decision_id="d1",
        field_id="cb-1",
        decision_type=DecisionType.AUTO_FILL,
        reason="",
        confidence=1.0,
        source="",
        proposed_action={"value": "true"},
    )

    f2 = FormField(field_id="sel-1", element_id="el-2", form_id="f1", input_type="select")
    d2 = FieldDecision(
        decision_id="d2",
        field_id="sel-1",
        decision_type=DecisionType.AUTO_FILL,
        reason="",
        confidence=1.0,
        source="",
        proposed_action={"value": "Option A"},
    )

    actions = bridge.draft_actions("session-123", [d1, d2], [f1, f2])

    assert len(actions) == 2
    assert actions[0].action_type == "check"
    assert actions[1].action_type == "select"


def test_executor_bridge_upload(bridge: ExecutionBridge) -> None:
    f1 = FormField(field_id="up-1", element_id="el-1", form_id="f1", input_type="file")
    d1 = FieldDecision(
        decision_id="d1",
        field_id="up-1",
        decision_type=DecisionType.AUTO_FILL,
        reason="",
        confidence=1.0,
        source="",
        proposed_action={"value": "doc-uuid-123"},
    )

    actions = bridge.draft_actions("session-123", [d1], [f1])
    assert len(actions) == 1
    assert actions[0].action_type == "upload"


def test_decision_engine_fallback_generate(engine: DecisionEngine) -> None:
    field = FormField(field_id="1", element_id="el-1", form_id="f1")
    field.classification = FieldClassification(field_type=FieldType.COVER_LETTER, confidence=1.0)
    decision = engine.decide(field, None, [])
    assert decision.decision_type == DecisionType.GENERATE


def test_decision_engine_unmapped(engine: DecisionEngine) -> None:
    field = FormField(field_id="1", element_id="el-1", form_id="f1")
    field.classification = FieldClassification(field_type=FieldType.START_DATE, confidence=1.0)
    decision = engine.decide(field, None, [])
    assert decision.decision_type == DecisionType.ASK_USER


def test_classifier_additional_rules(classifier: FieldClassifier) -> None:
    # Phone
    f_phone = FormField(field_id="1", element_id="el", form_id="f1", label="Telephone")
    assert classifier.classify(f_phone).field_type == FieldType.PHONE

    # Names
    f_fn = FormField(field_id="2", element_id="el", form_id="f1", label="First Name")
    assert classifier.classify(f_fn).field_type == FieldType.FIRST_NAME

    f_ln = FormField(field_id="3", element_id="el", form_id="f1", label="Last Name")
    assert classifier.classify(f_ln).field_type == FieldType.LAST_NAME

    f_n = FormField(field_id="4", element_id="el", form_id="f1", label="Name ")
    assert classifier.classify(f_n).field_type == FieldType.FULL_NAME

    # Education
    f_edu = FormField(field_id="5", element_id="el", form_id="f1", label="University")
    assert classifier.classify(f_edu).field_type == FieldType.UNIVERSITY

    f_res = FormField(field_id="6", element_id="el", form_id="f1", label="Upload Resume")
    assert classifier.classify(f_res).field_type == FieldType.RESUME

    f_unk = FormField(field_id="7", element_id="el", form_id="f1", label="Random gibberish")
    assert classifier.classify(f_unk).field_type == FieldType.UNKNOWN


def test_decision_engine_unknown_decision(engine: DecisionEngine) -> None:
    f = FormField(field_id="1", element_id="el", form_id="f1")
    # no classification
    f.classification = None

    d = engine.decide(f, None, [])
    assert d.decision_type == DecisionType.ASK_USER


def test_executor_bridge_skip_invalid(bridge: ExecutionBridge) -> None:
    f = FormField(field_id="1", element_id="el", form_id="f1")
    d1 = FieldDecision(
        decision_id="d1",
        field_id="2",
        decision_type=DecisionType.ASK_USER,
        reason="",
        confidence=1.0,
        source="",
    )
    # Field ID mismatch
    d2 = FieldDecision(
        decision_id="d2",
        field_id="999",
        decision_type=DecisionType.AUTO_FILL,
        reason="",
        confidence=1.0,
        source="",
        proposed_action={"value": "a"},
    )
    # No proposed action
    d3 = FieldDecision(
        decision_id="d3",
        field_id="1",
        decision_type=DecisionType.AUTO_FILL,
        reason="",
        confidence=1.0,
        source="",
    )

    actions = bridge.draft_actions("session-123", [d1, d2, d3], [f])
    assert len(actions) == 0
