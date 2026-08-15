# Audit schemas
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl

from api.models.audit import AuditStatus


class AuditRequest(BaseModel):
    """Public request payload: a lead submitting their site for an audit."""

    url: HttpUrl
    email: EmailStr
    name: str | None = None
    company: str | None = None
    phone: str | None = None


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    url: str
    status: AuditStatus
    overall_score: float | None = None
    category_scores: dict | None = None
    findings: dict | None = None
    ai_summary: str | None = None
    ai_recommendations: dict | None = None
    lighthouse_scores: dict | None = None
    lighthouse_metrics: dict | None = None
    lighthouse_opportunities: list | None = None
    lighthouse_error: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditSummary(BaseModel):
    """Lightweight audit view for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    status: AuditStatus
    overall_score: float | None = None
    created_at: datetime
