from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class GoogleLoginRequest(BaseModel):
    id_token: str


# ─── D-3: 이메일+비밀번호 인증 스키마 ─────────────────────────────────────

class RegisterRequest(BaseModel):
    """이메일+비밀번호 회원가입 요청."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=3, max_length=50)


class LoginEmailRequest(BaseModel):
    """이메일+비밀번호 로그인 요청."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class VerifyEmailRequest(BaseModel):
    """이메일 인증 토큰 검증 요청."""
    token: str = Field(min_length=10, max_length=64)


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
    # B'-1 multi-currency-foundation — user preferred display currency
    preferred_currency: str = "USD"
    # 2FA enrollment status (admin only — None for non-admin users)
    totp_enabled_at: datetime | None = None
    # D-3: 이메일 인증 여부 (일반 사용자 전용)
    email_verified: bool = False

    class Config:
        from_attributes = True


class StandardResponse(BaseModel):
    data: dict | list | None = None
