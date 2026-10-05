import uuid

import pytest

from packages.browser.form_intelligence.decision_engine import DecisionEngine
from packages.schemas.enums import DecisionType, FieldSensitivity, FieldType
from packages.schemas.form import FieldClassification, FormField


@pytest.mark.asyncio
async def test_end_to_end_submission_blocking() -> None:
    engine = DecisionEngine()

    # Simulate a submit button field
    mock_field = FormField(
        field_id="test-uuid-1",
        element_id="btn-submit",
        form_id="test-form",
        label="Submit Application",
        input_type="submit",
        name="submit",
        classification=FieldClassification(
            field_type=FieldType.UNKNOWN, confidence=0.0, sensitivity=FieldSensitivity.NORMAL
        ),
    )

    mock_field_apply = FormField(
        field_id="test-uuid-2",
        element_id="btn-apply",
        form_id="test-form",
        label="Complete Application",
        input_type="button",
        name="apply",
        classification=FieldClassification(
            field_type=FieldType.UNKNOWN, confidence=0.0, sensitivity=FieldSensitivity.NORMAL
        ),
    )

    # Validate that the Decision Engine blocks them
    decision1 = engine.decide(mock_field, None, [])
    assert decision1.decision_type == DecisionType.BLOCK

    decision2 = engine.decide(mock_field_apply, None, [])
    assert decision2.decision_type == DecisionType.BLOCK

    from packages.browser.form_intelligence.executor_bridge import ExecutionBridge
    from packages.schemas.form import FieldDecision

    bridge = ExecutionBridge()
    # If we somehow tried to map a BLOCKED decision to an action
    decision = FieldDecision(
        decision_id=str(uuid.uuid4()),
        field_id=str(uuid.uuid4()),
        decision_type=DecisionType.BLOCK,
        reason="bad",
        confidence=1.0,
        source="x",
    )
    action = bridge._create_action("session", decision, mock_field)
    assert action is None
