import uuid

import pytest

from packages.browser.form_intelligence.classifier import FieldClassifier
from packages.browser.form_intelligence.detector import FormDetector
from packages.schemas.browser_actions import DOMElement, ElementMetadata, PageModel


def test_multi_page_form_transition() -> None:
    detector = FormDetector()
    classifier = FieldClassifier(llm=None)

    # Page 1
    snap1_id = str(uuid.uuid4())
    page1 = PageModel(
        snapshot_id=snap1_id,
        url="http://test.com/1",
        title="Page 1",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(
                    tag_name="input", is_visible=True, is_interactive=True, text="First Name"
                ),
            )
        ],
    )
    form1 = detector.detect(page1)
    assert len(form1.fields) == 1
    assert form1.fields[0].label == "First Name"
    c1 = classifier.classify(form1.fields[0], form1)

    # Transition to Page 2
    snap2_id = str(uuid.uuid4())
    page2 = PageModel(
        snapshot_id=snap2_id,
        url="http://test.com/2",
        title="Page 2",
        elements=[
            DOMElement(
                element_id="el-2",
                metadata=ElementMetadata(
                    tag_name="input",
                    is_visible=True,
                    is_interactive=True,
                    text="Years of Experience",
                ),
            )
        ],
    )

    form2 = detector.detect(page2)
    assert len(form2.fields) == 1
    assert form2.fields[0].label == "Years of Experience"
    c2 = classifier.classify(form2.fields[0], form2)

    # Prove they are completely isolated
    assert form1.fields[0].field_id != form2.fields[0].field_id
    assert c1.field_type != c2.field_type


def test_stale_snapshot_rejection() -> None:
    from packages.browser.validator import ActionValidator
    from packages.schemas.browser_actions import ClickAction

    snap_id_old = "old-snap"
    snap_id_new = "new-snap"

    page = PageModel(
        snapshot_id=snap_id_new,
        url="http://test.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="btn",
                metadata=ElementMetadata(tag_name="button", is_visible=True, is_interactive=True),
            )
        ],
    )

    stale_action = ClickAction(session_id="1", snapshot_id=snap_id_old, element_id="btn")

    with pytest.raises(ValueError, match="Action rejected: snapshot_id is stale or invalid."):
        ActionValidator.validate(stale_action, page)
