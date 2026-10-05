import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from packages.db.models.hitl import HITLRequestModel, HITLResponseModel
from packages.schemas.enums import HITLRequestStatus
from packages.schemas.hitl import HITLRequestCreate, HITLRequestRead, HITLResponseCreate


class HITLManager:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_request(self, request_data: HITLRequestCreate) -> HITLRequestRead:
        # Idempotency check: if there is already a PENDING request for this workflow and type
        stmt = select(HITLRequestModel).where(
            and_(
                HITLRequestModel.workflow_id == request_data.workflow_id,
                HITLRequestModel.request_type == request_data.request_type,
                HITLRequestModel.status == HITLRequestStatus.PENDING,
            )
        )
        result = self.db.execute(stmt)
        existing = result.scalars().first()
        if existing:
            return HITLRequestRead.model_validate(existing)

        new_req = HITLRequestModel(
            application_id=request_data.application_id,
            workflow_id=request_data.workflow_id,
            user_id=request_data.user_id,
            request_type=request_data.request_type,
            title=request_data.title,
            description=request_data.description,
            context_json=request_data.context_json,
            required_action=request_data.required_action,
            priority=request_data.priority,
            expires_at=request_data.expires_at,
            metadata_json=request_data.metadata_json,
            status=HITLRequestStatus.PENDING,
            version=1,
        )
        self.db.add(new_req)
        self.db.flush()
        return HITLRequestRead.model_validate(new_req)

    def get_request(self, request_id: uuid.UUID, user_id: uuid.UUID) -> Optional[HITLRequestModel]:
        stmt = select(HITLRequestModel).where(
            and_(HITLRequestModel.id == request_id, HITLRequestModel.user_id == user_id)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def mark_viewed(self, request_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            update(HITLRequestModel)
            .where(
                and_(
                    HITLRequestModel.id == request_id,
                    HITLRequestModel.user_id == user_id,
                    HITLRequestModel.status == HITLRequestStatus.PENDING,
                )
            )
            .values(status=HITLRequestStatus.VIEWED, version=HITLRequestModel.version + 1)
        )
        result = self.db.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount > 0
        return False

    def submit_response(
        self, request_id: uuid.UUID, user_id: uuid.UUID, response_data: HITLResponseCreate
    ) -> bool:
        req = self.get_request(request_id, user_id)
        if not req:
            raise ValueError("Request not found or unauthorized")

        if req.version != response_data.expected_version:
            raise ValueError("Version conflict. Optimistic lock failed.")

        if req.status not in (
            HITLRequestStatus.PENDING,
            HITLRequestStatus.VIEWED,
            HITLRequestStatus.RESPONDING,
        ):
            raise ValueError(f"Cannot respond to request in {req.status} state")

        if req.expires_at and req.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            req.status = HITLRequestStatus.EXPIRED
            self.db.flush()
            raise ValueError("Request has expired")

        # Create response
        new_resp = HITLResponseModel(
            request_id=req.id,
            application_id=req.application_id,
            workflow_id=req.workflow_id,
            user_id=req.user_id,
            response_type=response_data.response_type,
            value_json=response_data.value_json,
        )

        self.db.add(new_resp)

        # Update request status
        req.status = HITLRequestStatus.RESOLVED
        req.resolved_at = datetime.now(timezone.utc)
        req.resolved_by = user_id
        req.version += 1

        self.db.flush()
        return True

    def cancel_request(self, request_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            update(HITLRequestModel)
            .where(
                and_(
                    HITLRequestModel.id == request_id,
                    HITLRequestModel.user_id == user_id,
                    HITLRequestModel.status.in_(
                        [
                            HITLRequestStatus.PENDING,
                            HITLRequestStatus.VIEWED,
                            HITLRequestStatus.RESPONDING,
                        ]
                    ),
                )
            )
            .values(status=HITLRequestStatus.CANCELLED, version=HITLRequestModel.version + 1)
        )
        result = self.db.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount > 0
        return False

    def expire_stale_requests(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(HITLRequestModel)
            .where(
                and_(
                    HITLRequestModel.status.in_(
                        [
                            HITLRequestStatus.PENDING,
                            HITLRequestStatus.VIEWED,
                            HITLRequestStatus.RESPONDING,
                        ]
                    ),
                    HITLRequestModel.expires_at < now,
                )
            )
            .values(status=HITLRequestStatus.EXPIRED, version=HITLRequestModel.version + 1)
        )
        result = self.db.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0

    def invalidate_application_requests(self, application_id: uuid.UUID) -> int:
        """
        Phase 8: Approvals and requests expire immediately if the underlying state changes
        (e.g., fresh snapshot, updated evidence).
        """
        stmt = (
            update(HITLRequestModel)
            .where(
                and_(
                    HITLRequestModel.application_id == application_id,
                    HITLRequestModel.status.in_(
                        [
                            HITLRequestStatus.PENDING,
                            HITLRequestStatus.VIEWED,
                            HITLRequestStatus.RESPONDING,
                            HITLRequestStatus.RESOLVED,
                        ]
                    ),
                )
            )
            .values(status=HITLRequestStatus.EXPIRED, version=HITLRequestModel.version + 1)
        )
        result = self.db.execute(stmt)
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0
