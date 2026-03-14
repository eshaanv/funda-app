from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EnrichmentRequest(BaseModel):
    member_id: str
    event_id: str
    community_name: str
    occurred_at: datetime
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str
    linkedin_url: str
    company_name: str | None = None
    company_stage: str | None = None


class MemberEnrichmentRecord(BaseModel):
    member_id: str
    event_id: str
    status: Literal["queued", "skipped", "completed", "failed"]
    reason: str | None = None
    linkedin_url: str | None = None
    company_name: str | None = None
    company_stage: str | None = None
    summary: str | None = None
