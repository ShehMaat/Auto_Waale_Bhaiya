from fastapi import APIRouter

from apps.api.app.api.api_v1.endpoints import (
    agent,
    applications,
    auth,
    documents,
    jobs,
    memory,
    profile,
    users,
    workflow,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(workflow.router, prefix="/applications", tags=["workflow"])

from apps.api.app.api.endpoints import hitl, review
from apps.api.app.api.api_v1.endpoints import analytics
api_router.include_router(hitl.router)
api_router.include_router(review.router)
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
