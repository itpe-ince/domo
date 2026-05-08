"""MagicLinkToken 모델 — Phase 12 C-2 매직링크 가입/로그인 토큰."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MagicLinkToken(Base):
    """매직링크 토큰 테이블 (alembic 0086).

    - 이메일 주소 + secrets.token_urlsafe(32) 토큰 저장
    - 24시간 만료 + 1회용 (is_used)
    - IP 주소 기록 (감사 목적, 차단 아님)
    """

    __tablename__ = "magic_link_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
