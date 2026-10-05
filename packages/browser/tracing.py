import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from packages.db.models.browser import BrowserEventModel


class BrowserTracer:
    """Handles structured observability and telemetry for the browser subsystem."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session

    def record_event(
        self,
        session_id: uuid.UUID,
        event_type: str,
        page_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Records a browser event to the database, ensuring secret redaction."""
        if metadata:
            metadata = self._redact_metadata(metadata)
        else:
            metadata = {}

        if self.db_session:
            event = BrowserEventModel(
                session_id=session_id,
                event_type=event_type,
                page_url=page_url,
                metadata_json=metadata,
                timestamp=datetime.utcnow(),
            )
            self.db_session.add(event)
            self.db_session.commit()

        # Here we could also push to structured application logs or Sentry if configured.

    def _redact_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Deeply redacts sensitive keys from metadata dictionaries."""
        redacted: Dict[str, Any] = {}
        sensitive_keys = {"password", "token", "secret", "cookie", "authorization", "otp", "2fa"}

        for k, v in metadata.items():
            is_sensitive = any(sk in k.lower() for sk in sensitive_keys)

            if is_sensitive:
                redacted[k] = "[REDACTED]"
            elif isinstance(v, dict):
                redacted[k] = self._redact_metadata(v)
            elif isinstance(v, list):
                redacted[k] = [self._redact_metadata(i) if isinstance(i, dict) else i for i in v]
            else:
                redacted[k] = v

        return redacted
