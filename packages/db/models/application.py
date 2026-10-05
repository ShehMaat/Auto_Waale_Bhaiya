import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class Application(TimestampedBase):
    __tablename__ = "applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String)  # ApplicationStatus
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[Optional[str]] = mapped_column(String)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    form_data_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)


class ApplicationEvent(TimestampedBase):
    __tablename__ = "application_events"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    event_type: Mapped[str] = mapped_column(String)
    previous_state: Mapped[Optional[str]] = mapped_column(String)
    new_state: Mapped[str] = mapped_column(String)
    actor_type: Mapped[str] = mapped_column(String)
    source: Mapped[Optional[str]] = mapped_column(String)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("autonomous_runs.id", ondelete="SET NULL")
    )
    queue_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("application_queue_items.id", ondelete="SET NULL")
    )
    correlation_id: Mapped[str] = mapped_column(String, index=True)
    reason_category: Mapped[Optional[str]] = mapped_column(String)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)


class ApplicationWorkflow(TimestampedBase):
    __tablename__ = "application_workflows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, unique=True
    )
    browser_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("browser_sessions.id", ondelete="SET NULL"), index=True
    )
    current_page_index: Mapped[int] = mapped_column(default=0)
    validation_errors_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    last_error: Mapped[Optional[str]] = mapped_column(String)
    retry_count: Mapped[int] = mapped_column(default=0)


class PreSubmissionSnapshot(TimestampedBase):
    __tablename__ = "pre_submission_snapshots"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    browser_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("browser_sessions.id", ondelete="SET NULL")
    )
    snapshot_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_valid: Mapped[bool] = mapped_column(default=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class ApplicationSubmission(TimestampedBase):
    __tablename__ = "application_submissions"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pre_submission_snapshots.id", ondelete="CASCADE")
    )
    browser_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("browser_sessions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String)  # SUBMITTED, FAILED, UNKNOWN
    verification_status: Mapped[str] = mapped_column(String)  # VERIFIED, UNVERIFIED
    verification_evidence: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
