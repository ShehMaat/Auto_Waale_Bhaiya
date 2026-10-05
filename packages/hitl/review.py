import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from packages.db.models.form import (
    ApplicationFormFieldModel,
    ApplicationFormModel,
    FieldDecisionModel,
)
from packages.db.models.hitl import HITLRequestModel
from packages.schemas.enums import (
    DecisionType,
    FieldRequirement,
    FieldSensitivity,
    HITLRequestStatus,
    ReviewSessionStatus,
)
from packages.schemas.hitl import ReviewCompletenessResult


class ReviewManager:
    def __init__(self, db_session: Session):
        self.db = db_session

    def calculate_completeness(self, application_id: uuid.UUID) -> ReviewCompletenessResult:
        """
        Deterministically checks if the application is READY_FOR_REVIEW.
        Final submission is strictly blocked.
        """
        blocking_items = []
        warnings = []
        resolved_items: list[str] = []

        # 1. Check for any unresolved HITL requests
        stmt_hitl = select(HITLRequestModel).where(
            and_(
                HITLRequestModel.application_id == application_id,
                HITLRequestModel.status.in_(
                    [
                        HITLRequestStatus.PENDING,
                        HITLRequestStatus.VIEWED,
                        HITLRequestStatus.RESPONDING,
                    ]
                ),
            )
        )
        unresolved_hitl = self.db.execute(stmt_hitl).scalars().all()
        for req in unresolved_hitl:
            blocking_items.append(f"Unresolved HITL Request: {req.request_type} - {req.title}")

        # 2. Check for form fields that are REQUIRED but have no value or are stuck on ASK_USER / PAUSE  # noqa: E501
        stmt_fields = (
            select(ApplicationFormFieldModel)
            .join(
                ApplicationFormModel, ApplicationFormFieldModel.form_id == ApplicationFormModel.id
            )
            .where(ApplicationFormModel.application_id == application_id)
        )
        fields = self.db.execute(stmt_fields).scalars().all()

        # Need to join with decisions, but for simplicity we fetch decisions for these fields
        if fields:
            field_ids = [f.id for f in fields]
            stmt_decisions = select(FieldDecisionModel).where(
                FieldDecisionModel.field_id.in_(field_ids)
            )
            decisions = self.db.execute(stmt_decisions).scalars().all()
            decision_map = {d.field_id: d for d in decisions}

            for field in fields:
                dec = decision_map.get(field.id)
                field_data = field.field_data_json or {}
                field_name = field_data.get("name") or field.element_id
                classification = field_data.get("classification") or {}
                is_required = classification.get("requirement") == FieldRequirement.REQUIRED.value

                if not dec:
                    if is_required:
                        blocking_items.append(f"Missing decision for required field: {field_name}")
                    continue

                # If a field is explicitly blocked, that's a hard block or warning.
                if dec.decision_type == DecisionType.BLOCK:
                    warnings.append(f"Field {field_name} was blocked by security policy.")

                if dec.decision_type == DecisionType.ASK_USER:
                    blocking_items.append(f"Field {field_name} requires user input.")

                if field.sensitivity in [
                    FieldSensitivity.CHALLENGE,
                    FieldSensitivity.AUTHENTICATION,
                ]:
                    # Challenges should be handled by HITL. If there is no resolved HITL for this, it's a block.  # noqa: E501
                    # We assume the ChallengeManager creates HITL requests for these.
                    pass

        is_complete = len(blocking_items) == 0
        status = ReviewSessionStatus.READY if is_complete else ReviewSessionStatus.INCOMPLETE

        return ReviewCompletenessResult(
            application_id=application_id,
            status=status,
            complete=is_complete,
            blocking_items=blocking_items,
            warnings=warnings,
            resolved_items=resolved_items,
        )
