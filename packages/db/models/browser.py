import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from packages.db.base import Base


class BrowserSessionModel(Base):
    __tablename__ = "browser_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True
    )
    state = Column(String(50), nullable=False, default="CREATED")
    target_domain = Column(String(255), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)


class BrowserEventModel(Base):
    __tablename__ = "browser_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("browser_sessions.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    page_url = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)


from typing import Any, Dict, Optional  # noqa: E402

from sqlalchemy.orm import Mapped, mapped_column  # noqa: E402


class BrowserActionExecutionModel(Base):
    """Tracks executed actions to enforce true idempotency."""

    __tablename__ = "browser_action_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("browser_sessions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., SUCCESS, FAILED
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    result_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("result", JSON, nullable=True)
