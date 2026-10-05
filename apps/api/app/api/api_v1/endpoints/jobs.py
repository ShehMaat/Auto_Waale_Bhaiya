import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.app.api.deps import CurrentUser, get_db
from packages.db.models.jobs import Job, JobMatchScore

router = APIRouter()


@router.get("/ranked")
def get_ranked_jobs(current_user: CurrentUser, db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]  # noqa: B008
    """Returns jobs ranked by match score."""
    scores = (
        db.query(JobMatchScore, Job)
        .join(Job, JobMatchScore.job_id == Job.id)
        .filter(JobMatchScore.user_id == current_user.id)
        .order_by(JobMatchScore.score.desc())
        .all()
    )
    return {
        "jobs": [
            {
                "job_id": s.JobMatchScore.job_id,
                "score": s.JobMatchScore.score,
                "reasoning": s.JobMatchScore.reasoning,
                "title": s.Job.title,
                "company": s.Job.company,
                "location": s.Job.location,
                "work_mode": s.Job.work_mode,
            }
            for s in scores
        ]
    }


@router.get("/{id}/match")
def get_job_match(id: uuid.UUID, current_user: CurrentUser, db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]  # noqa: B008
    """Returns the match explanation for a specific job."""
    score = (
        db.query(JobMatchScore)
        .filter(JobMatchScore.job_id == id, JobMatchScore.user_id == current_user.id)
        .first()
    )
    if not score:
        raise HTTPException(status_code=404, detail="Match score not found")
    return {"job_id": id, "score": score.score, "reasoning": score.reasoning}


@router.post("/discover")
def discover_jobs(source_id: str, current_user: CurrentUser):  # type: ignore[no-untyped-def]
    """Triggers background job discovery for a source."""
    from apps.api.app.core.celery_tasks import discover_jobs_task

    discover_jobs_task.delay(source_id)
    return {"message": f"Discovery queued for source {source_id}"}
