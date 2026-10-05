import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class SearchPolicy(TimestampedBase):
    __tablename__ = "search_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(default=1)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(default=True)


class AutonomousRun(TimestampedBase):
    __tablename__ = "autonomous_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    search_policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("search_policies.id", ondelete="CASCADE")
    )
    search_policy_version: Mapped[int] = mapped_column(default=1)
    max_jobs: Mapped[int] = mapped_column(default=50)
    max_applications: Mapped[int] = mapped_column(default=10)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String)  # CREATED, RUNNING, PAUSED, COMPLETED, FAILED
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ApplicationQueueItem(TimestampedBase):
    __tablename__ = "application_queue_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("autonomous_runs.id", ondelete="SET NULL")
    )
    policy_version: Mapped[int] = mapped_column(default=1)
    match_version: Mapped[Optional[str]] = mapped_column(String)
    eligibility: Mapped[str] = mapped_column(String)
    priority: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String)  # QUEUED, READY, RUNNING, COMPLETED, FAILED
    reason: Mapped[Optional[str]] = mapped_column(String)
    retry_count: Mapped[int] = mapped_column(default=0)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL")
    )
