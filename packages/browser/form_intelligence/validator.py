from typing import Any, List

from pydantic import BaseModel

from packages.schemas.form import FormField


class ValidationError(BaseModel):
    field_id: str
    error_message: str


class FormValidator:
    """
    Validates candidate data against form field constraints before execution.
    """

    def __init__(self) -> None:
        pass

    def validate_field(self, field: FormField, proposed_value: Any) -> List[ValidationError]:
        errors: List[ValidationError] = []
        if proposed_value is None or proposed_value == "":
            return errors  # Required check is handled at workflow level or if specifically needed

        val_str = str(proposed_value)

        # 1. Type constraints
        if field.input_type == "email":
            if "@" not in val_str or "." not in val_str:
                errors.append(
                    ValidationError(field_id=field.field_id, error_message="Invalid email format")
                )
        elif field.input_type == "number":
            if not val_str.isdigit():
                errors.append(
                    ValidationError(field_id=field.field_id, error_message="Value must be a number")
                )
        elif field.input_type == "url":
            if not val_str.startswith("http"):
                errors.append(
                    ValidationError(field_id=field.field_id, error_message="Invalid URL format")
                )

        # 2. Length constraints (Phase 6 feature)
        # Assuming FormField has minlength/maxlength or we extract it,
        # but since we didn't add it to schema yet,
        # we can validate based on semantic type

        # 3. Option compatibility
        if field.options:
            valid_options = [opt["value"].lower() for opt in field.options] + [
                opt["label"].lower() for opt in field.options
            ]
            if val_str.lower() not in valid_options:
                errors.append(
                    ValidationError(
                        field_id=field.field_id,
                        error_message=f"Value '{val_str}' not found in available options.",
                    )
                )

        return errors
