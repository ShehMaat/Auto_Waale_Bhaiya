from packages.browser.policies import BrowserSecurityPolicy
from packages.schemas.browser_actions import (
    BrowserAction,
    CheckAction,
    ClickAction,
    FillAction,
    GoBackAction,
    GoForwardAction,
    NavigateAction,
    PageModel,
    PressKeyAction,
    RefreshAction,
    ScrollAction,
    SelectOptionAction,
    UncheckAction,
    UploadFileAction,
    WaitAction,
)


class ActionValidator:
    """
    Validates typed LLM actions against the current PageModel and SecurityPolicy.
    Prevents the LLM from executing invalid or unsafe commands.
    """

    @classmethod
    def validate(cls, action: BrowserAction, page_model: PageModel) -> bool:
        """
        Validates the action. Raises ValueError or BrowserPolicyViolation if invalid.
        Returns True if valid.
        """
        # 1. Snapshot Security
        if getattr(action, "snapshot_id", None) is not None:
            if action.snapshot_id != page_model.snapshot_id:
                raise ValueError("Action rejected: snapshot_id is stale or invalid.")

        # 2. Navigation Actions
        if isinstance(action, NavigateAction):
            BrowserSecurityPolicy.validate_navigation_url(action.url)
            return True

        # 3. Parameter-bound Actions
        elif isinstance(action, WaitAction):
            if action.duration_ms < 0 or action.duration_ms > 10000:
                raise ValueError("Wait duration must be between 0 and 10000 ms")
            return True

        elif isinstance(action, (RefreshAction, GoBackAction, GoForwardAction, ScrollAction)):
            return True

        elif isinstance(action, PressKeyAction):
            if len(action.key) > 50:
                raise ValueError("Key string is too long")
            return True

        # 4. Element-bound Actions
        elif isinstance(
            action,
            (
                ClickAction,
                FillAction,
                SelectOptionAction,
                CheckAction,
                UncheckAction,
                UploadFileAction,
            ),
        ):
            target_element = next(
                (el for el in page_model.elements if el.element_id == action.element_id), None
            )

            if not target_element:
                raise ValueError(f"Element ID '{action.element_id}' not found in current PageModel")

            if not target_element.metadata.is_interactive:
                raise ValueError(f"Element ID '{action.element_id}' is not interactive")

            if not target_element.metadata.is_visible:
                raise ValueError(f"Element ID '{action.element_id}' is not visible")

            # Sensitivity Protection
            if target_element.metadata.sensitivity in ("SENSITIVE", "AUTHENTICATION"):
                raise ValueError(
                    f"Action blocked: Element is classified as {target_element.metadata.sensitivity}. "  # noqa: E501
                    "Autonomous interaction requires explicit human verification."
                )

            if isinstance(action, ClickAction):
                if target_element.metadata.is_submit:
                    raise ValueError(
                        "Action blocked: Autonomous submission is prohibited in Phase 3B."
                    )

            if isinstance(action, FillAction):
                if len(action.text) > 5000:
                    raise ValueError("Fill text exceeds maximum length of 5000 characters")

            if isinstance(action, SelectOptionAction):
                if target_element.metadata.tag_name != "select":
                    raise ValueError(
                        "Target element for SelectOptionAction must be a <select> tag."
                    )

            return True

        raise ValueError(f"Unknown action type: {type(action)}")
