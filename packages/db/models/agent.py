import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import TimestampedBase


class AgentRun(TimestampedBase):
    __tablename__ = "agent_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String)  # AgentRunStatus
    current_node: Mapped[Optional[str]] = mapped_column(String)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_info: Mapped[Optional[str]] = mapped_column(String)
    retry_count: Mapped[int] = mapped_column(default=0)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)


class AgentState(TimestampedBase):
    __tablename__ = "agent_states"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    checkpoint_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
