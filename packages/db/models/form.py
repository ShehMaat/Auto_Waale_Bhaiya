import uuid
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class ApplicationFormModel(TimestampedBase):
    __tablename__ = "application_forms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("browser_sessions.id", ondelete="SET NULL"), index=True
    )
    url: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="DISCOVERED")
    current_page_index: Mapped[int] = mapped_column(default=0)


class ApplicationFormFieldModel(TimestampedBase):
    __tablename__ = "application_form_fields"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_forms.id", ondelete="CASCADE"), index=True
    )
    element_id: Mapped[str] = mapped_column(String, index=True)  # Links back to Phase 3B element

    # Snapshot tying this field state in time
    snapshot_id: Mapped[str] = mapped_column(String, index=True)

    # Store the JSON representation of FormField
    field_data_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Cached classification for indexing/lookup
    classification_type: Mapped[Optional[str]] = mapped_column(String)
    sensitivity: Mapped[Optional[str]] = mapped_column(String)


class FieldDecisionModel(TimestampedBase):
    __tablename__ = "field_decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_form_fields.id", ondelete="CASCADE"), index=True
    )
    decision_type: Mapped[str] = mapped_column(String, index=True)  # AUTO_FILL, ASK_USER, etc.
    status: Mapped[str] = mapped_column(
        String, default="PENDING"
    )  # PENDING, APPROVED, REJECTED, EXECUTED
    reason: Mapped[Optional[str]] = mapped_column(String)
    confidence: Mapped[Optional[float]] = mapped_column(Float)

    # If the user changed or approved this decision
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Memory facts used to make this decision
    memory_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)

    # The actual intended browser action payload (JSON encoded)
    proposed_action_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)


class GeneratedAnswerModel(TimestampedBase):
    __tablename__ = "generated_answers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_form_fields.id", ondelete="CASCADE"), index=True
    )

    prompt_used: Mapped[str] = mapped_column(String)
    generated_text: Mapped[str] = mapped_column(String)

    # Provenance tracking - which memory facts were cited to build this answer?
    source_memory_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String, default="DRAFT")  # DRAFT, APPROVED, REJECTED


class ApprovalRecord(TimestampedBase):
    __tablename__ = "approval_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("field_decisions.id", ondelete="SET NULL"), index=True
    )

    approval_scope: Mapped[str] = mapped_column(String)  # "DECISION", "DOCUMENT", "SUBMIT"
    approved_data_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
