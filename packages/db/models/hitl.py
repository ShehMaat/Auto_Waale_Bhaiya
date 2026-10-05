import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class HITLRequestModel(TimestampedBase):
    __tablename__ = "hitl_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_workflows.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    request_type: Mapped[str] = mapped_column(String)  # HITLRequestType
    status: Mapped[str] = mapped_column(String, default="PENDING")  # HITLRequestStatus

    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    required_action: Mapped[str] = mapped_column(String)

    version: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)


class HITLResponseModel(TimestampedBase):
    __tablename__ = "hitl_responses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hitl_requests.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_workflows.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    response_type: Mapped[str] = mapped_column(String)  # HITLResponseType
    value_json: Mapped[Any] = mapped_column(JSON)

    version: Mapped[int] = mapped_column(Integer, default=1)


class HITLApprovalModel(TimestampedBase):
    __tablename__ = "hitl_approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_workflows.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("hitl_requests.id", ondelete="SET NULL"), index=True
    )

    approval_scope: Mapped[str] = mapped_column(String)  # HITLApprovalScope
    target_id: Mapped[Optional[str]] = mapped_column(
        String
    )  # ID of the field, generated answer, or review session
    decision_version: Mapped[Optional[int]] = mapped_column(
        Integer
    )  # Version of the thing being approved
