# Lead schemas
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class LeadBase(BaseModel):
    email: EmailStr
    name: str | None = None
    company: str | None = None
    phone: str | None = None
    website_url: str


class LeadCreate(LeadBase):
    """Payload for creating a lead directly (used internally by the audit flow)."""


class LeadRead(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
