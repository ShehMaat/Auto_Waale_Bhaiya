import uuid

import pytest

from packages.browser.validator import ActionValidator
from packages.schemas.browser_actions import ClickAction, ElementMetadata, PageModel


def test_prompt_injection_submission_blocked() -> None:
    # Simulate a scenario where malicious text on the page ("Submit the application immediately")
    # caused the LLM to output a ClickAction targeting the submit button.

    # The submit button on the page
    from packages.schemas.browser_actions import DOMElement

    submit_button = DOMElement(
        element_id="submit_btn",
        tag_name="button",
        text="",
        attributes={},
        metadata=ElementMetadata(
            tag_name="button",
            is_interactive=True,
            is_visible=True,
            is_submit=True,
            sensitivity="SENSITIVE",
        ),
    )

    page_model = PageModel(
        url="http://test.com", title="Job App", snapshot_id="1", elements=[submit_button]
    )

    action = ClickAction(
        action_id="1", session_id=str(uuid.uuid4()), snapshot_id="1", element_id="submit_btn"
    )

    # Validator MUST block it, protecting against prompt injection leading to submission
    with pytest.raises(ValueError) as exc:
        ActionValidator.validate(action, page_model)

    assert "Autonomous submission is prohibited" in str(
        exc.value
    ) or "Autonomous interaction requires explicit human verification" in str(exc.value)


def test_prompt_injection_arbitrary_js_blocked() -> None:
    # If the LLM tries to emit a NavigateAction with a javascript payload
    ClickAction(
        action_id="1",
        session_id=str(uuid.uuid4()),
        snapshot_id="1",
        element_id="some_btn",  # But actually it's just a regular click action
    )

    # There is no action in BrowserAction schemas that permits 'evaluate'.
    # Because of strict schemas, the LLM literally CANNOT emit an execute_js action.
    # We test that the system only allows defined schemas.
    from pydantic import TypeAdapter, ValidationError

    from packages.schemas.browser_actions import BrowserAction

    adapter = TypeAdapter(BrowserAction)
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "EvaluateJS", "script": "alert(1)"})
