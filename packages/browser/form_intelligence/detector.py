import uuid
from typing import List

from packages.schemas.browser_actions import PageModel
from packages.schemas.form import FormField, FormModel, FormSection


class FormDetector:
    """
    Deterministically identifies structured forms from a Phase 3B PageModel.
    """

    def __init__(self) -> None:
        pass

    def detect(self, page_model: PageModel) -> FormModel:
        """
        Groups raw DOM elements into a coherent FormModel structure.
        Uses heuristics like visible inputs, labels, semantic structure.
        """
        fields: List[FormField] = []

        # In a real heuristic approach, we'd look for input clustering and labels.
        # For Phase 3C, we transform input elements into FormFields.
        for el in page_model.elements:
            if not el.metadata.is_interactive and el.metadata.tag_name not in [
                "input",
                "select",
                "textarea",
            ]:
                # We skip purely non-interactive elements unless they are labels tied to an input.
                continue

            field = FormField(
                field_id=str(uuid.uuid4()),
                element_id=el.element_id,
                form_id="primary-form",
                label=el.metadata.aria_label or el.metadata.text,
                name=el.metadata.name,
                placeholder=el.metadata.placeholder,
                value=el.metadata.value,
                input_type=el.metadata.input_type or (el.metadata.tag_name if el.metadata.tag_name in ["button", "a"] else None),
                role=el.metadata.role,
                visible=el.metadata.is_visible,
                interactive=el.metadata.is_interactive,
                is_required=el.metadata.is_required,
                options=[{"value": opt, "label": opt} for opt in el.metadata.options],
            )
            fields.append(field)

        return FormModel(
            form_id="primary-form",
            snapshot_id=page_model.snapshot_id,
            page_url=page_model.url,
            title=page_model.title,
            sections=[
                FormSection(section_id="default-section", title="Default Section", fields=fields)
            ],
            fields=fields,
        )
