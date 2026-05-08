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


# ─── C-1: 비밀번호 재설정 스키마 ───────────────────────────────────────────

class PasswordResetRequestBody(BaseModel):
    """비밀번호 재설정 요청 (이메일 발송)."""
    email: EmailStr


class PasswordResetBody(BaseModel):
    """비밀번호 재설정 토큰 검증 + 새 비밀번호 설정."""
    token: str = Field(min_length=10, max_length=64)
    new_password: str = Field(min_length=8, max_length=200)


class StandardResponse(BaseModel):
    data: dict | list | None = None


# ─── C-2: GitHub OAuth + 매직링크 스키마 ───────────────────────────────────────

class GitHubLoginRequest(BaseModel):
    """GitHub OAuth 로그인 요청."""

    code: str
    redirect_uri: str


class MagicLinkRequest(BaseModel):
    """매직링크 요청 (이메일 입력만으로 발송)."""

    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    """매직링크 토큰 검증 요청.

    display_name: 신규 사용자만 필수. 기존 사용자는 null 허용.
    """

    token: str = Field(min_length=10, max_length=64)
    display_name: str | None = Field(default=None, min_length=3, max_length=50)
