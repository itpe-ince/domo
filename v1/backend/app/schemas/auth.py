from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class GoogleLoginRequest(BaseModel):
    id_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    status: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    country_code: str | None = None
    language: str
    is_minor: bool
    warning_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class StandardResponse(BaseModel):
    data: dict | list | None = None
