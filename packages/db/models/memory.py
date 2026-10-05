import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class MemoryFact(TimestampedBase):
    __tablename__ = "memory_facts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)

    provenance: Mapped[str] = mapped_column(String)  # Cast from MemoryProvenance
    trust_level: Mapped[str] = mapped_column(String)  # Cast from MemoryTrustLevel
    status: Mapped[str] = mapped_column(String)  # Cast from MemoryStatus
    source: Mapped[Optional[str]] = mapped_column(String)

    # Versioning & Validity
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    needs_reconfirmation: Mapped[bool] = mapped_column(Boolean, default=False)

    # Semantic Search
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))
    embedding_model: Mapped[Optional[str]] = mapped_column(String)
    embedding_dimension: Mapped[Optional[int]] = mapped_column(Integer)

    # Unique identification for idempotency
    content_hash: Mapped[Optional[str]] = mapped_column(String, index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "key", "version", name="uix_memory_fact_version"),
        UniqueConstraint(
            "user_id", "source", "provenance", "content_hash", name="uix_memory_fact_identity"
        ),
    )
