import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.app.api.deps import CurrentUser, get_db
from packages.db.models.application import Application, ApplicationWorkflow, PreSubmissionSnapshot
from packages.db.models.jobs import Job

router = APIRouter()

class ApplicationResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    status: str
    title: str
    company: str
    location: Optional[str] = None
    started_at: Optional[str] = None

class ApplicationDetailResponse(ApplicationResponse):
    current_page_index: Optional[int] = None
    last_error: Optional[str] = None
    validation_errors_json: list = []
    pre_submission_snapshot_id: Optional[uuid.UUID] = None

@router.get("/", response_model=List[ApplicationResponse])
def list_applications(current_user: CurrentUser, db: Session = Depends(get_db)):
    applications = (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    
    return [
        {
            "id": app.Application.id,
            "job_id": app.Application.job_id,
            "status": app.Application.status,
            "title": app.Job.title,
            "company": app.Job.company,
            "location": app.Job.location,
            "started_at": app.Application.started_at.isoformat() if app.Application.started_at else None,
        }
        for app in applications
    ]

@router.get("/{application_id}", response_model=ApplicationDetailResponse)
def get_application(application_id: uuid.UUID, current_user: CurrentUser, db: Session = Depends(get_db)):
    app_record = (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.id == application_id, Application.user_id == current_user.id)
        .first()
    )
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")
        
    workflow = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == application_id).first()
    snapshot = db.query(PreSubmissionSnapshot).filter(PreSubmissionSnapshot.application_id == application_id).order_by(PreSubmissionSnapshot.created_at.desc()).first()
    
    return {
        "id": app_record.Application.id,
        "job_id": app_record.Application.job_id,
        "status": app_record.Application.status,
        "title": app_record.Job.title,
        "company": app_record.Job.company,
        "location": app_record.Job.location,
        "started_at": app_record.Application.started_at.isoformat() if app_record.Application.started_at else None,
        "current_page_index": workflow.current_page_index if workflow else 0,
        "last_error": workflow.last_error if workflow else None,
        "validation_errors_json": workflow.validation_errors_json if workflow else [],
        "pre_submission_snapshot_id": snapshot.id if snapshot else None
    }
