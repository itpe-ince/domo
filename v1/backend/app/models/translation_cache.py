"""TranslationCache 모델 — Phase 9 L-F 번역 메모리.

LLM Gateway 번역 결과를 DB에 영구 저장해 중복 호출을 차단한다.
SHA-256 해시 기반 O(1) cache lookup + 90일 미사용 자동 cleanup.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TranslationCache(Base):
    """번역 메모리 테이블.

    Primary key: id (UUID)
    Lookup key: (source_hash, source_lang, target_lang) — UNIQUE
    TTL cleanup 기준: last_used_at
    """

    __tablename__ = "translation_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # SHA-256 hex digest of source_text (utf-8 인코딩) — 64자
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_lang: Mapped[str] = mapped_column(String(5), nullable=False)
    target_lang: Mapped[str] = mapped_column(String(5), nullable=False)

    # 원문 전체 — 해시 충돌 방지 + 모델 변경 시 내용 검증용
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)

    # LLM 모델 식별자 (예: gemma4-e4b, mock-gateway)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # cache hit 누적 횟수 (0 = 최초 번역 직후 INSERT)
    hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # TTL cleanup cron 기준 — hit 시마다 갱신
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # cache lookup UNIQUE 인덱스
        UniqueConstraint(
            "source_hash", "source_lang", "target_lang",
            name="uq_translation_cache_hash_langs",
        ),
        # 90일 cleanup cron용
        Index("ix_translation_cache_last_used_at", "last_used_at"),
    )
