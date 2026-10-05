import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class ApplicationContent(TimestampedBase):
    __tablename__ = "application_content"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(String, index=True)
    prompt: Mapped[str] = mapped_column(Text)


class ContentVersion(TimestampedBase):
    __tablename__ = "content_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_content.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    generator_version: Mapped[str] = mapped_column(String)
    policy_version: Mapped[str] = mapped_column(String)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))


class ContentGenerationEvent(TimestampedBase):
    __tablename__ = "content_generation_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(String)
    generation_version: Mapped[str] = mapped_column(String)
    policy_version: Mapped[str] = mapped_column(String)
    model_identifier: Mapped[str] = mapped_column(String)
    evidence_references: Mapped[list[str]] = mapped_column(JSON)
    validation_result: Mapped[dict[str, Any]] = mapped_column(JSON)
    decision_result: Mapped[str] = mapped_column(String)
