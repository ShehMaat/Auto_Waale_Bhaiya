import uuid
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.hitl import HITLApprovalModel
from packages.schemas.enums import HITLApprovalScope
from packages.schemas.hitl import HITLApprovalCreate, HITLApprovalRead


class ApprovalManager:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_approval(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        workflow_id: uuid.UUID,
        approval_data: HITLApprovalCreate,
        request_id: Optional[uuid.UUID] = None,
    ) -> HITLApprovalRead:

        # Idempotency / Duplicate protection:
        # User cannot approve the same target version twice for the same app
        stmt = select(HITLApprovalModel).where(
            and_(
                HITLApprovalModel.user_id == user_id,
                HITLApprovalModel.application_id == application_id,
                HITLApprovalModel.approval_scope == approval_data.approval_scope,
                HITLApprovalModel.target_id == approval_data.target_id,
                HITLApprovalModel.decision_version == approval_data.decision_version,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            return HITLApprovalRead.model_validate(existing)

        # Security invariant: NO approval type can be "SUBMIT_APPLICATION"
        if "SUBMIT" in approval_data.approval_scope.value.upper():
            raise ValueError("Final submission approval is strictly prohibited in Phase 3E.")

        approval = HITLApprovalModel(
            user_id=user_id,
            application_id=application_id,
            workflow_id=workflow_id,
            request_id=request_id,
            approval_scope=approval_data.approval_scope,
            target_id=approval_data.target_id,
            decision_version=approval_data.decision_version,
        )
        self.db.add(approval)
        await self.db.flush()

        return HITLApprovalRead.model_validate(approval)

    async def verify_approval(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        scope: HITLApprovalScope,
        target_id: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> bool:
        """
        Verify that an approval exists for the EXACT scope, application, user, and target/version.
        Approvals cannot be reused across applications.
        """
        conditions = [
            HITLApprovalModel.user_id == user_id,
            HITLApprovalModel.application_id == application_id,
            HITLApprovalModel.approval_scope == scope,
        ]

        if target_id is not None:
            conditions.append(HITLApprovalModel.target_id == target_id)

        if expected_version is not None:
            conditions.append(HITLApprovalModel.decision_version == expected_version)

        stmt = select(HITLApprovalModel).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None
