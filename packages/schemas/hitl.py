import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from packages.schemas.enums import (
    HITLApprovalScope,
    HITLRequestStatus,
    HITLRequestType,
    HITLResponseType,
    ReviewSessionStatus,
)


class HITLRequestBase(BaseModel):
    application_id: uuid.UUID
    workflow_id: uuid.UUID
    request_type: HITLRequestType
    title: str
    description: str
    context_json: dict[str, Any] = Field(default_factory=dict)
    required_action: str
    priority: int = 0
    expires_at: Optional[datetime] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class HITLRequestCreate(HITLRequestBase):
    user_id: uuid.UUID


class HITLRequestRead(HITLRequestBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: HITLRequestStatus
    version: int
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HITLResponseBase(BaseModel):
    response_type: HITLResponseType
    value_json: Any


class HITLResponseCreate(HITLResponseBase):
    expected_version: int


class HITLResponseRead(HITLResponseBase):
    id: uuid.UUID
    request_id: uuid.UUID
    application_id: uuid.UUID
    workflow_id: uuid.UUID
    user_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HITLApprovalBase(BaseModel):
    approval_scope: HITLApprovalScope
    target_id: Optional[str] = None
    decision_version: Optional[int] = None


class HITLApprovalCreate(HITLApprovalBase):
    pass


class HITLApprovalRead(HITLApprovalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    application_id: uuid.UUID
    workflow_id: uuid.UUID
    request_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewCompletenessResult(BaseModel):
    application_id: uuid.UUID
    status: ReviewSessionStatus
    complete: bool
    blocking_items: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    resolved_items: list[str] = Field(default_factory=list)
