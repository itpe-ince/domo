"""PasswordResetToken model — Phase 12 C-1.

별도 테이블 설계 이유:
- users 테이블 오염 방지 (이미 인증 관련 컬럼 5개)
- 재설정 요청 내역(IP, 발송 시각, 사용 여부) 별도 감사 추적
- 복수의 미사용 토큰 관리 및 재발급 시 일괄 무효화 용이
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # secrets.token_urlsafe(32) → 43자 URL-safe 문자열
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    # NULL = 미사용, NOT NULL = 1회 사용됨 (재사용 차단)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 발급 시각 + 1시간
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="password_reset_tokens")
