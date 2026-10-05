import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.schemas.enums import (
    BrowserActionType,
    DecisionType,
    MemoryProvenance,
    MemoryStatus,
    MemoryTrustLevel,
    RequirementCategory,
    RequirementType,
)


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# User Models
class UserBase(BaseSchema):
    email: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


# Auth Models
class Token(BaseSchema):
    access_token: str
    token_type: str


class TokenPayload(BaseSchema):
    sub: Optional[str] = None


# Decision Contract
class Decision(BaseSchema):
    decision: DecisionType
    field_id: Optional[str] = None
    value: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    provenance: Optional[MemoryProvenance] = None
    reason: Optional[str] = None


# Browser Action Contract
class BrowserAction(BaseSchema):
    action: BrowserActionType
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    timeout: Optional[int] = None
    options: Dict[str, Any] = Field(default_factory=dict)


# Candidate Models
class CandidateProfileSchema(BaseSchema):
    id: UUID
    user_id: UUID
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    links: Dict[str, Any] = Field(default_factory=dict)


class MemoryFactSchema(BaseSchema):
    id: UUID
    category: str
    key: str
    value: str
    normalized_value: Optional[str] = None
    confidence: float
    provenance: MemoryProvenance
    trust_level: MemoryTrustLevel
    status: MemoryStatus
    source: Optional[str] = None

    version: int = 1
    is_current: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    needs_reconfirmation: bool = False

    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None


class CandidateCanonicalModel(BaseSchema):
    profile: CandidateProfileSchema
    facts: List[MemoryFactSchema] = Field(default_factory=list)


class CandidateContext(BaseSchema):
    facts: List[MemoryFactSchema] = Field(default_factory=list)
    relevant_experience: List[MemoryFactSchema] = Field(default_factory=list)
    relevant_projects: List[MemoryFactSchema] = Field(default_factory=list)
    relevant_skills: List[MemoryFactSchema] = Field(default_factory=list)
    conflicts: List[MemoryFactSchema] = Field(default_factory=list)
    stale_items: List[MemoryFactSchema] = Field(default_factory=list)


class MemoryQuery(BaseSchema):
    candidate_id: UUID
    query_text: str
    fact_types: Optional[List[str]] = None
    min_trust: Optional[MemoryTrustLevel] = None
    include_expired: bool = False
    include_superseded: bool = False
    limit: int = 5


# Job Models

# Job Models


class JobRequirementSchema(BaseSchema):
    requirement_id: UUID = Field(default_factory=uuid.uuid4)
    job_id: Optional[UUID] = None
    category: RequirementCategory
    name: str
    normalized_name: Optional[str] = None
    description: Optional[str] = None
    requirement_type: RequirementType
    importance: Optional[float] = None
    required: Optional[bool] = None
    preferred: Optional[bool] = None
    confidence: float
    evidence: Optional[str] = None
    source_text: Optional[str] = None

    # Kept for backwards compatibility
    normalized_value: Optional[str] = None


class JobNormalizedSchema(BaseSchema):
    id: UUID
    source: str
    source_id: UUID
    source_job_id: str
    title: str
    company: str
    canonical_company: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    description: str
    canonical_url: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    posted_at: Optional[datetime] = None
    application_url: Optional[str] = None
    raw_content_hash: Optional[str] = None
    extracted_requirements: Dict[str, Any] = Field(default_factory=dict)


# Match Models
class MatchExplanation(BaseSchema):
    matched_requirements: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    preferred_matches: List[str] = Field(default_factory=list)
    constraint_failures: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    semantic_matches: List[str] = Field(default_factory=list)
    explanation: str


class MatchResult(BaseSchema):
    job_id: UUID
    overall_score: float
    hard_constraint_score: float
    skill_score: float
    experience_score: float
    education_score: float
    semantic_score: float
    preference_score: float
    explanation: MatchExplanation

    # Versioning
    matching_version: str = "v1"
    scoring_config_version: str = "v1.0"
    embedding_model: Optional[str] = None
    embedding_version: Optional[str] = None
    candidate_profile_version: Optional[str] = None
    job_content_hash: Optional[str] = None
