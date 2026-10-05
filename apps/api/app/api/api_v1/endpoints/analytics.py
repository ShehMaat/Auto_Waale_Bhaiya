import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from apps.api.app.api import deps
from packages.db.models.application import Application, ApplicationSubmission
from packages.db.models.jobs import Job, JobSource, JobMatchScore
from packages.db.models.hitl import HITLRequestModel

router = APIRouter()

@router.get("/summary", response_model=Dict[str, Any])
def get_analytics_summary(
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user)
) -> Any:
    user_id = current_user.id

    # 1. Funnel
    discovered = db.query(Job).count() # Just all jobs for this user, or match scores? Match scores imply qualified/discovered.
    # Actually, JobMatchScore is per user.
    discovered_count = db.query(JobMatchScore).filter(JobMatchScore.user_id == user_id).count()
    qualified_count = db.query(JobMatchScore).filter(JobMatchScore.user_id == user_id, JobMatchScore.score >= 0.7).count() # threshold?
    started_count = db.query(Application).filter(Application.user_id == user_id).count()
    ready_count = db.query(Application).filter(Application.user_id == user_id, Application.status == 'READY_FOR_REVIEW').count()
    submitted_count = db.query(Application).filter(Application.user_id == user_id, Application.status == 'SUBMITTED').count()
    
    # Outcomes
    outcomes = db.query(ApplicationSubmission.status, func.count(ApplicationSubmission.id))\
        .join(Application)\
        .filter(Application.user_id == user_id)\
        .group_by(ApplicationSubmission.status)\
        .all()
    outcomes_dict = {status: count for status, count in outcomes}

    # Also include Application status for 'pending' or 'failed'
    app_statuses = db.query(Application.status, func.count(Application.id))\
        .filter(Application.user_id == user_id)\
        .group_by(Application.status)\
        .all()
    app_statuses_dict = {status: count for status, count in app_statuses}
    
    # 3. Source Analytics
    sources = db.query(JobSource.name, func.count(Application.id))\
        .select_from(Application)\
        .join(Job, Application.job_id == Job.id)\
        .join(JobSource, Job.source_id == JobSource.id)\
        .filter(Application.user_id == user_id)\
        .group_by(JobSource.name)\
        .all()
    source_analytics = [{"source": name, "count": count} for name, count in sources]

    # 4. Role Analytics
    roles = db.query(Job.title, func.count(Application.id))\
        .join(Application)\
        .filter(Application.user_id == user_id)\
        .group_by(Job.title)\
        .all()
    role_analytics = [{"role": title, "count": count} for title, count in roles]

    # 5. Match Analytics
    scores = db.query(JobMatchScore.score).filter(JobMatchScore.user_id == user_id).all()
    scores_list = [s[0] for s in scores]
    avg_score = sum(scores_list) / len(scores_list) if scores_list else 0
    match_distribution = {
        "0-20": sum(1 for s in scores_list if s <= 0.2),
        "21-40": sum(1 for s in scores_list if 0.2 < s <= 0.4),
        "41-60": sum(1 for s in scores_list if 0.4 < s <= 0.6),
        "61-80": sum(1 for s in scores_list if 0.6 < s <= 0.8),
        "81-100": sum(1 for s in scores_list if s > 0.8),
    }
    match_analytics = {
        "average": avg_score,
        "count": len(scores_list),
        "distribution": match_distribution
    }

    # 6. HITL Analytics
    hitl_count = db.query(HITLRequestModel).filter(HITLRequestModel.user_id == user_id).count()
    hitl_pending = db.query(HITLRequestModel).filter(HITLRequestModel.user_id == user_id, HITLRequestModel.status == 'PENDING').count()
    apps_with_hitl = db.query(func.count(func.distinct(HITLRequestModel.application_id)))\
        .filter(HITLRequestModel.user_id == user_id)\
        .scalar() or 0

    hitl_analytics = {
        "total_requests": hitl_count,
        "pending_requests": hitl_pending,
        "applications_requiring_intervention": apps_with_hitl
    }

    # 7. Agent Effectiveness
    completion_rate = submitted_count / started_count if started_count > 0 else 0
    failed_count = app_statuses_dict.get("FAILED", 0)
    failure_rate = failed_count / started_count if started_count > 0 else 0
    hitl_rate = apps_with_hitl / started_count if started_count > 0 else 0

    agent_effectiveness = {
        "completion_rate": completion_rate,
        "failure_rate": failure_rate,
        "hitl_rate": hitl_rate
    }

    return {
        "funnel": {
            "discovered": discovered_count,
            "qualified": qualified_count,
            "started": started_count,
            "ready_for_review": ready_count,
            "submitted": submitted_count,
        },
        "outcomes": outcomes_dict,
        "source_analytics": source_analytics,
        "role_analytics": role_analytics,
        "match_analytics": match_analytics,
        "hitl_analytics": hitl_analytics,
        "agent_effectiveness": agent_effectiveness
    }
