import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class ApplicationOutcome(TimestampedBase):
    __tablename__ = "application_outcomes"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    outcome_type: Mapped[str] = mapped_column(String)  # RESPONSE, INTERVIEW, OFFER, REJECTION
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)


class UnknownQuestionObservation(TimestampedBase):
    __tablename__ = "unknown_question_observations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_fingerprint: Mapped[str] = mapped_column(String, index=True)
    normalized_category: Mapped[Optional[str]] = mapped_column(String)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    applications_seen: Mapped[int] = mapped_column(Integer, default=1)
    companies_seen: Mapped[int] = mapped_column(Integer, default=1)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolution_frequency: Mapped[int] = mapped_column(Integer, default=0)


class FeedbackEvent(TimestampedBase):
    __tablename__ = "feedback_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    feedback_type: Mapped[str] = mapped_column(String)
    source_entity: Mapped[str] = mapped_column(String)
    original_value_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    feedback_metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)


class AnalyticsSnapshot(TimestampedBase):
    __tablename__ = "analytics_snapshots"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    metric_type: Mapped[str] = mapped_column(String)
    dimension: Mapped[str] = mapped_column(String)
    value: Mapped[int] = mapped_column(Integer, default=0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "user_id", "metric_type", "dimension", "calculated_at", name="uq_analytics_snapshot"
        ),
    )
