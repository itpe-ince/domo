"""Pydantic schemas for DM messaging endpoints — B'-2."""
from __future__ import annotations

from pydantic import BaseModel, Field


class StartConversationRequest(BaseModel):
    target_user_id: str = Field(..., description="UUID of the user to DM.")


class SendMessageRequest(BaseModel):
    body: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Plain-text message body. Max 2000 chars.",
    )


class EditMessageRequest(BaseModel):
    body: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Replacement plain-text body.",
    )


class ReportConversationRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Abuse report reason.",
    )
