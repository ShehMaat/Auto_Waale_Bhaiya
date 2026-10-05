import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.app.api import deps
from apps.api.app.core.celery_tasks import run_application_workflow_task
from packages.db.models.application import Application
from packages.db.models.form import ApprovalRecord

router = APIRouter()


@router.post("/{application_id}/workflow/start", response_model=Dict[str, Any])
def start_workflow(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    """
    Start the application workflow process via Celery.
    """
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    if app_record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this application")

    # Kick off background task
    task = run_application_workflow_task.delay(str(application_id))

    return {"message": "Workflow started", "task_id": task.id}


@router.get("/{application_id}/workflow/review", response_model=Dict[str, Any])
def get_workflow_review(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    """
    Fetch the review representation of the application.
    """
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")

    return {"status": "READY_FOR_REVIEW", "fields": []}  # Stub for frontend


@router.post("/{application_id}/workflow/approve", response_model=Dict[str, Any])
def approve_decision(
    application_id: uuid.UUID,
    decision_id: uuid.UUID,
    approval_scope: str,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    """
    Approve a specific field decision or generated answer.
    """
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")

    # Idempotent check
    existing = (
        db.query(ApprovalRecord)
        .filter(
            ApprovalRecord.decision_id == decision_id, ApprovalRecord.user_id == current_user.id
        )
        .first()
    )

    if not existing:
        approval = ApprovalRecord(
            id=uuid.uuid4(),
            user_id=current_user.id,
            application_id=application_id,
            decision_id=decision_id,
            approval_scope=approval_scope,
        )
        db.add(approval)
        db.commit()

    # Could trigger workflow resume here
    return {"message": "Approved successfully"}


@router.post("/{application_id}/workflow/pause", response_model=Dict[str, Any])
def pause_workflow(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404)
    return {"message": "Paused"}


@router.post("/{application_id}/workflow/resume", response_model=Dict[str, Any])
def resume_workflow(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404)
    return {"message": "Resumed"}


@router.post("/{application_id}/workflow/abort", response_model=Dict[str, Any])
def abort_workflow(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404)
    return {"message": "Aborted"}


@router.post("/{application_id}/workflow/answer", response_model=Dict[str, Any])
def answer_workflow(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404)
    return {"message": "Answered"}


@router.post("/{application_id}/workflow/reject", response_model=Dict[str, Any])
def reject_workflow(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404)
    return {"message": "Rejected"}


@router.get("/{application_id}/workflow/events", response_model=Dict[str, Any])
def get_workflow_events(
    application_id: uuid.UUID,
    db: Session = Depends(deps.get_db),  # noqa: B008
    current_user: Any = Depends(deps.get_current_user),  # noqa: B008
) -> Any:
    from packages.db.models.application import ApplicationEvent
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or app_record.user_id != current_user.id:
        raise HTTPException(status_code=404)
    
    events = (
        db.query(ApplicationEvent)
        .filter(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.occurred_at.desc())
        .all()
    )
    
    return {
        "events": [
            {
                "id": str(e.id),
                "occurred_at": e.occurred_at.isoformat(),
                "event_type": e.event_type,
                "previous_state": e.previous_state,
                "new_state": e.new_state,
                "actor_type": e.actor_type,
                "source": e.source,
                "reason_category": e.reason_category,
                "metadata_json": e.metadata_json,
            }
            for e in events
        ]
    }
