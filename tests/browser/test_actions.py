import pytest

from packages.browser.validator import ActionValidator
from packages.schemas.browser_actions import (
    ClickAction,
    DOMElement,
    ElementMetadata,
    FillAction,
    NavigateAction,
    PageModel,
    WaitAction,
)


def test_validate_navigate() -> None:
    action = NavigateAction(session_id="s1", url="https://www.google.com")
    model = PageModel(snapshot_id="snap1", url="about:blank", title="Blank", elements=[])
    assert ActionValidator.validate(action, model) is True


def test_validate_click_success() -> None:
    action = ClickAction(session_id="s1", snapshot_id="snap1", element_id="el-1")
    model = PageModel(
        snapshot_id="snap1",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(tag_name="button", is_visible=True, is_interactive=True),
            )
        ],
    )
    assert ActionValidator.validate(action, model) is True


def test_validate_click_missing_element() -> None:
    action = ClickAction(session_id="s1", snapshot_id="snap1", element_id="el-2")
    model = PageModel(snapshot_id="snap1", url="https://google.com", title="Test", elements=[])
    with pytest.raises(ValueError, match="not found"):
        ActionValidator.validate(action, model)


def test_validate_click_not_interactive() -> None:
    action = ClickAction(session_id="s1", snapshot_id="snap1", element_id="el-1")
    model = PageModel(
        snapshot_id="snap1",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(tag_name="div", is_visible=True, is_interactive=False),
            )
        ],
    )
    with pytest.raises(ValueError, match="not interactive"):
        ActionValidator.validate(action, model)


def test_validate_click_not_visible() -> None:
    action = ClickAction(session_id="s1", snapshot_id="snap1", element_id="el-1")
    model = PageModel(
        snapshot_id="snap1",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(tag_name="button", is_visible=False, is_interactive=True),
            )
        ],
    )
    with pytest.raises(ValueError, match="not visible"):
        ActionValidator.validate(action, model)


def test_validate_fill() -> None:
    action = FillAction(session_id="s1", snapshot_id="snap1", element_id="el-1", text="hello")
    model = PageModel(
        snapshot_id="snap1",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(tag_name="input", is_visible=True, is_interactive=True),
            )
        ],
    )
    assert ActionValidator.validate(action, model) is True


def test_validate_fill_too_long() -> None:
    action = FillAction(session_id="s1", snapshot_id="snap1", element_id="el-1", text="a" * 6000)
    model = PageModel(
        snapshot_id="snap1",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(tag_name="input", is_visible=True, is_interactive=True),
            )
        ],
    )
    with pytest.raises(ValueError, match="exceeds maximum length"):
        ActionValidator.validate(action, model)


def test_validate_wait() -> None:
    action = WaitAction(session_id="s1", duration_ms=5000)
    model = PageModel(snapshot_id="snap1", url="https://google.com", title="Test", elements=[])
    assert ActionValidator.validate(action, model) is True


def test_validate_snapshot_stale() -> None:
    action = ClickAction(session_id="s1", snapshot_id="snap-old", element_id="el-1")
    model = PageModel(
        snapshot_id="snap-new",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(tag_name="button", is_visible=True, is_interactive=True),
            )
        ],
    )
    with pytest.raises(ValueError, match="snapshot_id is stale"):
        ActionValidator.validate(action, model)


def test_validate_autonomous_submit_blocked() -> None:
    action = ClickAction(session_id="s1", snapshot_id="snap1", element_id="el-1")
    model = PageModel(
        snapshot_id="snap1",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-1",
                metadata=ElementMetadata(
                    tag_name="button", is_visible=True, is_interactive=True, is_submit=True
                ),
            )
        ],
    )
    with pytest.raises(ValueError, match="Autonomous submission is prohibited"):
        ActionValidator.validate(action, model)


def test_validate_sensitive_field_blocked() -> None:
    action = FillAction(
        session_id="s1", snapshot_id="snap1", element_id="el-pwd", text="mypassword"
    )
    model = PageModel(
        snapshot_id="snap1",
        url="https://google.com",
        title="Test",
        elements=[
            DOMElement(
                element_id="el-pwd",
                metadata=ElementMetadata(
                    tag_name="input",
                    is_visible=True,
                    is_interactive=True,
                    sensitivity="AUTHENTICATION",
                ),
            )
        ],
    )
    with pytest.raises(
        ValueError, match="Autonomous interaction requires explicit human verification"
    ):
        ActionValidator.validate(action, model)
