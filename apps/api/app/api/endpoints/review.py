import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.db.session import get_db
from packages.hitl.review import ReviewManager
from packages.schemas.hitl import ReviewCompletenessResult

router = APIRouter(prefix="/applications", tags=["review"])


from apps.api.app.api.deps import CurrentUser

@router.get("/{application_id}/review/completeness", response_model=ReviewCompletenessResult)
def check_review_completeness(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewCompletenessResult:
    manager = ReviewManager(db)
    # The ReviewManager currently only requires application_id.
    # In a full system, you would assert user_id owns the application before calculating completeness.  # noqa: E501
    return manager.calculate_completeness(application_id)
