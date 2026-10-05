import uuid
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    COVER_LETTER = "COVER_LETTER"
    WHY_COMPANY = "WHY_COMPANY"
    WHY_ROLE = "WHY_ROLE"
    PROFESSIONAL_SUMMARY = "PROFESSIONAL_SUMMARY"
    PROJECT_NARRATIVE = "PROJECT_NARRATIVE"
    EXPERIENCE_NARRATIVE = "EXPERIENCE_NARRATIVE"
    ACHIEVEMENT_NARRATIVE = "ACHIEVEMENT_NARRATIVE"
    CUSTOM_QUESTION = "CUSTOM_QUESTION"
    SHORT_ANSWER = "SHORT_ANSWER"
    OTHER = "OTHER"


class GenerationMode(str, Enum):
    DRAFT = "DRAFT"
    REVISE = "REVISE"
    SHORTEN = "SHORTEN"
    EXPAND = "EXPAND"
    REPHRASE = "REPHRASE"
    TAILOR_TO_JOB = "TAILOR_TO_JOB"
    ANSWER_CUSTOM_QUESTION = "ANSWER_CUSTOM_QUESTION"


class Tone(str, Enum):
    PROFESSIONAL = "PROFESSIONAL"
    CONCISE = "CONCISE"
    CONFIDENT = "CONFIDENT"
    TECHNICAL = "TECHNICAL"
    CONVERSATIONAL = "CONVERSATIONAL"
    FORMAL = "FORMAL"


class LengthConstraint(str, Enum):
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"
    CUSTOM_WORD_LIMIT = "CUSTOM_WORD_LIMIT"
    CUSTOM_CHARACTER_LIMIT = "CUSTOM_CHARACTER_LIMIT"


class ClaimValidationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    REJECTED = "REJECTED"


class Claim(BaseModel):
    text: str
    claim_type: str
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float
    supported: bool


class EvidencePack(BaseModel):
    candidate_facts: List[dict[str, Any]] = Field(default_factory=list)
    candidate_projects: List[dict[str, Any]] = Field(default_factory=list)
    candidate_experience: List[dict[str, Any]] = Field(default_factory=list)
    candidate_skills: List[dict[str, Any]] = Field(default_factory=list)
    candidate_achievements: List[dict[str, Any]] = Field(default_factory=list)
    job_requirements: List[str] = Field(default_factory=list)
    job_responsibilities: List[str] = Field(default_factory=list)
    company_context: dict[str, Any] = Field(default_factory=dict)
    prohibited_or_unknown_claims: List[str] = Field(default_factory=list)


class ApplicationContentRequest(BaseModel):
    user_id: uuid.UUID
    application_id: uuid.UUID
    job_id: uuid.UUID
    content_type: ContentType
    prompt: str = ""
    mode: GenerationMode = GenerationMode.DRAFT
    requested_length: LengthConstraint = LengthConstraint.MEDIUM
    tone: Tone = Tone.PROFESSIONAL
    max_words: Optional[int] = None
    max_characters: Optional[int] = None
    candidate_evidence_scope: List[str] = Field(default_factory=list)
    job_evidence_scope: List[str] = Field(default_factory=list)


class ContentValidationResult(BaseModel):
    is_valid: bool
    is_grounded: bool
    safe: bool
    claims: List[Claim] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class GroundingCitation(BaseModel):
    text: str
    source: str
    memory_id: Optional[uuid.UUID] = None


class GenerationMetadata(BaseModel):
    model_identifier: str
    generator_version: str
    policy_version: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ApplicationContentResult(BaseModel):
    content_id: uuid.UUID
    application_id: uuid.UUID
    content: str
    version: int
    validation: ContentValidationResult
    metadata: GenerationMetadata
    evidence_snapshot: EvidencePack
