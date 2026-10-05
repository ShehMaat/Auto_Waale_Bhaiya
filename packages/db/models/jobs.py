import uuid
from datetime import datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class JobSource(TimestampedBase):
    __tablename__ = "job_sources"

    name: Mapped[str] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String)  # Cast from JobSourceType enum
    base_url: Mapped[str] = mapped_column(String)


class Job(TimestampedBase):
    __tablename__ = "jobs"

    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_sources.id", ondelete="SET NULL")
    )
    source_job_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)
    work_mode: Mapped[Optional[str]] = mapped_column(String)  # Cast from WorkMode
    employment_type: Mapped[Optional[str]] = mapped_column(String)  # Cast from EmploymentType
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String)
    salary: Mapped[Optional[str]] = mapped_column(String)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fingerprint_hash: Mapped[Optional[str]] = mapped_column(String, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String, index=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    extracted_requirements: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)

    # Embedding Support
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))
    embedding_model: Mapped[Optional[str]] = mapped_column(String)
    embedding_dimension: Mapped[Optional[int]] = mapped_column(Integer)
    embedding_version: Mapped[Optional[str]] = mapped_column(String)


class JobSourcePayload(TimestampedBase):
    __tablename__ = "job_source_payloads"

    canonical_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_sources.id", ondelete="CASCADE"), index=True
    )
    source_job_id: Mapped[str] = mapped_column(String, index=True)
    payload_hash: Mapped[str] = mapped_column(String, index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source_id", "source_job_id", name="uix_job_source_payload_source_job"),
    )


class JobMatchScore(TimestampedBase):
    __tablename__ = "job_match_scores"

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column()
    reasoning: Mapped[Optional[str]] = mapped_column(Text)

    # Versioning & Reproducibility
    matching_version: Mapped[str] = mapped_column(String, default="v1")
    scoring_config_version: Mapped[str] = mapped_column(String, default="v1.0")
    embedding_model: Mapped[Optional[str]] = mapped_column(String)
    embedding_version: Mapped[Optional[str]] = mapped_column(String)
    candidate_profile_version: Mapped[Optional[str]] = mapped_column(String)
    job_content_hash: Mapped[Optional[str]] = mapped_column(String)
