from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    target_type: str = Field(..., pattern="^(post|comment|user)$")
    target_id: UUID
    reason: str
    description: str | None = None


class ReportOut(BaseModel):
    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    description: str | None
    status: str
    handled_by: UUID | None
    handled_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportResolveRequest(BaseModel):
    action: str = Field(..., pattern="^(issue_warning|dismiss)$")
    note: str | None = None


class WarningOut(BaseModel):
    id: UUID
    user_id: UUID
    reason: str
    report_id: UUID | None
    issued_by: UUID | None
    is_active: bool
    appealed: bool
    appeal_note: str | None
    cancelled_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AppealRequest(BaseModel):
    note: str
