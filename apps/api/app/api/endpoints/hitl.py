import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from packages.db.models.hitl import HITLRequestModel
from packages.db.session import get_db
from packages.hitl.manager import HITLManager
from packages.schemas.hitl import HITLRequestRead, HITLResponseCreate

router = APIRouter(prefix="/applications", tags=["hitl"])


from apps.api.app.api.deps import CurrentUser

def sanitize_request(req: HITLRequestModel) -> HITLRequestModel:
    safe_keys = ["field", "options", "prompt", "message"]
    if isinstance(req.context_json, dict):
        req.context_json = {k: v for k, v in req.context_json.items() if k in safe_keys}
    return req


@router.get("/{application_id}/hitl", response_model=List[HITLRequestRead])
def list_hitl_requests(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> List[HITLRequestRead]:
    stmt = select(HITLRequestModel).where(
        and_(HITLRequestModel.application_id == application_id, HITLRequestModel.user_id == current_user.id)
    )
    result = db.execute(stmt)
    return [HITLRequestRead.model_validate(sanitize_request(req)) for req in result.scalars().all()]


@router.get("/hitl/{request_id}", response_model=HITLRequestRead)
def get_hitl_request(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> HITLRequestRead:
    manager = HITLManager(db)
    req = manager.get_request(request_id, current_user.id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return HITLRequestRead.model_validate(sanitize_request(req))


@router.post("/hitl/{request_id}/view")
def mark_request_viewed(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    manager = HITLManager(db)
    success = manager.mark_viewed(request_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or not in PENDING state")
    db.commit()
    return {"status": "success"}


@router.post("/hitl/{request_id}/respond")
def respond_to_request(
    request_id: uuid.UUID,
    response_data: HITLResponseCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    manager = HITLManager(db)
    try:
        manager.submit_response(request_id, current_user.id, response_data)
        db.commit()
        return {"status": "success"}
    except ValueError as e:
        db.rollback()
        err_str = str(e).lower()
        if "not found or unauthorized" in err_str:
            raise HTTPException(status_code=404, detail=str(e))  # noqa: B904
        raise HTTPException(status_code=400, detail=str(e))  # noqa: B904


@router.post("/hitl/{request_id}/cancel")
def cancel_request(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    manager = HITLManager(db)
    success = manager.cancel_request(request_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or cannot be cancelled")
    db.commit()
    return {"status": "success"}
