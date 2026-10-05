from typing import Any, Dict, List, Optional, TypedDict


class PipelineState(TypedDict):
    """LangGraph state for the Phase 11 Autonomous Pipeline."""
    
    run_id: str
    user_id: str
    search_policy_id: Optional[str]
    search_policy_version: Optional[int]
    status: str
    
    # Discovery Phase
    discovered_jobs: List[Dict[str, Any]]
    normalized_jobs: List[Dict[str, Any]]
    canonical_jobs: List[Dict[str, Any]]
    
    # Processing Phase
    current_job: Optional[Dict[str, Any]]
    current_job_index: int
    
    # Matching and Eligibility Phase
    match_result: Optional[Dict[str, Any]]
    hard_constraints_passed: bool
    eligibility_status: Optional[str]
    
    # Ranking and Queue Phase
    queued_jobs: List[Dict[str, Any]]
    rejected_jobs: List[Dict[str, Any]]
    
    # Limits
    max_jobs: int
    max_applications: int
    
    # Stats
    jobs_processed: int
    applications_queued: int
    applications_submitted: int
    
    errors: List[str]
