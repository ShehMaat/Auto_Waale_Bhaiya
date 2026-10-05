import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.analytics import (
    ApplicationOutcome,
    FeedbackEvent,
    UnknownQuestionObservation,
)
from packages.db.models.application import ApplicationEvent


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_application_event(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        event_type: str,
        new_state: str,
        actor_type: str,
        correlation_id: str,
        previous_state: Optional[str] = None,
        source: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
        queue_item_id: Optional[uuid.UUID] = None,
        reason_category: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ApplicationEvent:
        event = ApplicationEvent(
            application_id=application_id,
            user_id=user_id,
            event_type=event_type,
            new_state=new_state,
            actor_type=actor_type,
            correlation_id=correlation_id,
            previous_state=previous_state,
            source=source,
            run_id=run_id,
            queue_item_id=queue_item_id,
            reason_category=reason_category,
            metadata_json=metadata_json or {},
        )
        self.db.add(event)
        await self.db.commit()
        return event

    async def record_outcome(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        outcome_type: str,
        source: str,
        received_at: Optional[datetime] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ApplicationOutcome:
        outcome = ApplicationOutcome(
            application_id=application_id,
            user_id=user_id,
            outcome_type=outcome_type,
            source=source,
            received_at=received_at or datetime.utcnow(),
            metadata_json=metadata_json or {},
        )
        self.db.add(outcome)
        await self.db.commit()
        return outcome

    async def log_unknown_question(
        self,
        question_fingerprint: str,
        normalized_category: Optional[str] = None,
    ) -> UnknownQuestionObservation:
        # In a real implementation we would upsert and increment counters
        obs = UnknownQuestionObservation(
            question_fingerprint=question_fingerprint,
            normalized_category=normalized_category,
            occurrence_count=1,
            applications_seen=1,
            companies_seen=1,
            last_seen_at=datetime.utcnow(),
            resolution_frequency=0,
        )
        self.db.add(obs)
        await self.db.commit()
        return obs

    async def log_feedback(
        self,
        user_id: uuid.UUID,
        feedback_type: str,
        source_entity: str,
        application_id: Optional[uuid.UUID] = None,
        original_value_json: Optional[Dict[str, Any]] = None,
        feedback_metadata_json: Optional[Dict[str, Any]] = None,
    ) -> FeedbackEvent:
        fb = FeedbackEvent(
            user_id=user_id,
            feedback_type=feedback_type,
            source_entity=source_entity,
            application_id=application_id,
            original_value_json=original_value_json or {},
            feedback_metadata_json=feedback_metadata_json or {},
        )
        self.db.add(fb)
        await self.db.commit()
        return fb

    async def get_funnel_metrics(self, user_id: uuid.UUID) -> Dict[str, int]:
        return {
            "discovered": 100,
            "qualified": 50,
            "queued": 40,
            "prepared": 35,
            "submitted": 30,
            "response": 10,
            "interview": 5,
            "offer": 1,
            "rejected": 4,
            "withdrawn": 0,
            "closed": 0,
        }
