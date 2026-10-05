from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from packages.schemas.enums import (
    DecisionType,
    FieldRequirement,
    FieldSensitivity,
    FieldType,
)


class FieldValidationRule(BaseModel):
    rule_type: str
    value: Any
    message: Optional[str] = None


class FieldClassification(BaseModel):
    field_type: FieldType
    confidence: float
    reason: Optional[str] = None
    sensitivity: FieldSensitivity = FieldSensitivity.NORMAL
    requirement: FieldRequirement = FieldRequirement.UNKNOWN
    signals: List[str] = Field(default_factory=list)


class FormField(BaseModel):
    field_id: str  # logical internal ID mapped from element_id
    element_id: str  # Phase 3B opaque identifier
    form_id: str

    label: Optional[str] = None
    normalized_label: Optional[str] = None
    name: Optional[str] = None
    input_type: Optional[str] = None
    role: Optional[str] = None
    value: Optional[str] = None
    placeholder: Optional[str] = None
    aria_label: Optional[str] = None
    description: Optional[str] = None

    visible: bool = True
    interactive: bool = True
    disabled: bool = False
    readonly: bool = False
    is_required: bool = False

    options: List[Dict[str, str]] = Field(default_factory=list)
    validation_rules: List[FieldValidationRule] = Field(default_factory=list)

    classification: Optional[FieldClassification] = None
    section_name: Optional[str] = None
    page_number: int = 1


class FormSection(BaseModel):
    section_id: str
    title: str
    fields: List[FormField]


class FormModel(BaseModel):
    form_id: str
    snapshot_id: str
    page_url: str
    title: Optional[str] = None
    sections: List[FormSection] = Field(default_factory=list)
    fields: List[FormField] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FieldCandidateValue(BaseModel):
    value: Any
    source: str
    provenance: str
    confidence: float
    memory_ids: List[str] = Field(default_factory=list)


class FieldMapping(BaseModel):
    field_id: str
    candidate_source: str
    memory_ids: List[str] = Field(default_factory=list)
    mapping_confidence: float
    mapping_reason: Optional[str] = None
    value: Any


class FieldDecision(BaseModel):
    decision_id: str
    field_id: str
    decision_type: DecisionType
    reason: str
    confidence: float
    source: str
    provenance: Optional[str] = None
    trust_level: Optional[str] = None
    value: Optional[Any] = None
    memory_ids: List[str] = Field(default_factory=list)
    requires_user: bool = False
    requires_confirmation: bool = False
    generated: bool = False
    sensitivity: FieldSensitivity = FieldSensitivity.NORMAL
    policy_version: str = "phase8-v1"
    proposed_action: Optional[Dict[str, Any]] = None  # To be hydrated into BrowserAction later


class DecisionContext(BaseModel):
    field: FormField
    memory_facts: List[Any] = Field(default_factory=list)  # MemoryFact schemas
    candidate_profile: Optional[Any] = None
    job_requirements: List[Any] = Field(default_factory=list)
    application_state: str = "UNKNOWN"
    workflow_state: str = "UNKNOWN"
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
