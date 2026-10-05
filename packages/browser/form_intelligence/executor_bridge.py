import uuid
from typing import List, Optional

from packages.schemas.browser_actions import (
    BrowserAction,
    CheckAction,
    ClickAction,
    FillAction,
    SelectOptionAction,
    UploadFileAction,
)
from packages.schemas.enums import DecisionType
from packages.schemas.form import FieldDecision, FormField


class ExecutionBridge:
    """
    Translates Form Intelligence Decisions into valid Phase 3B BrowserActions.
    Ensures safe mapping and strictly blocks unapproved decisions.
    """

    def __init__(self) -> None:
        pass

    def draft_actions(
        self, session_id: str, decisions: List[FieldDecision], fields: List[FormField]
    ) -> List[BrowserAction]:
        """
        Takes approved decisions and builds a sequence of strictly typed BrowserActions.
        """
        actions: List[BrowserAction] = []

        # Create a lookup for fields
        field_map = {f.field_id: f for f in fields}
        for dec in decisions:
            print("DECISION:", dec.field_id, dec.decision_type, dec.reason)
            f = field_map.get(dec.field_id)
            if f:
                print("FIELD:", f.name, f.label, f.input_type)

        for dec in decisions:
            if dec.decision_type not in [DecisionType.AUTO_FILL, DecisionType.CONFIRM]:
                # Action isn't ready or approved to be filled
                continue

            field = field_map.get(dec.field_id)
            if not field:
                continue

            action = self._create_action(session_id, dec, field)
            if action:
                actions.append(action)

        return actions

    def _create_action(
        self, session_id: str, decision: FieldDecision, field: FormField
    ) -> Optional[BrowserAction]:
        if not decision.proposed_action or "value" not in decision.proposed_action:
            return None

        value = decision.proposed_action["value"]
        
        input_type = (field.input_type or "").lower()
        role = (field.role or "").lower()

        # If the field already has this value, no action is needed
        if field.value == str(value):
            return None
            
        # For file inputs, the browser sets value to C:\fakepath\...
        # If it has any value, we assume it's already uploaded.
        if input_type == "file" and field.value:
            return None

        # 0. Click
        if decision.proposed_action.get("action_type") == "click":
            return ClickAction(
                action_id=str(uuid.uuid4()),
                session_id=session_id,
                element_id=field.element_id
            )

        # 1. Checkboxes
        if input_type == "checkbox" or role == "checkbox":
            if str(value).lower() in ["true", "1", "yes", "checked"]:
                return CheckAction(
                    action_id=str(uuid.uuid4()), session_id=session_id, element_id=field.element_id
                )
            return None  # We could also support UncheckAction

        # 2. Selects
        if field.options or input_type == "select":
            return SelectOptionAction(
                action_id=str(uuid.uuid4()),
                session_id=session_id,
                element_id=field.element_id,
                option_value=str(value),
            )

        # 3. File Uploads (Phase 3B integration)
        if input_type == "file":
            # Value must be a valid document_id, NOT a filesystem path.
            # Document mapping is handled downstream by ActionExecutor.
            return UploadFileAction(
                action_id=str(uuid.uuid4()),
                session_id=session_id,
                element_id=field.element_id,
                document_id=str(value),
            )

        # 4. Fallback to Fill
        return FillAction(
            action_id=str(uuid.uuid4()),
            session_id=session_id,
            element_id=field.element_id,
            text=str(value),
        )
