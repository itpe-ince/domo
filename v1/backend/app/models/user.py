import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    # 'user' | 'artist' | 'admin'
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # 'active' | 'suspended' | 'deleted'

    sns_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sns_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Admin-only credential auth (bcrypt + TOTP 2FA)
    # Regular users authenticate via SNS only; admins MUST use these.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # editor-image-studio PDCA #6-image v1.1 — watermark signature storage key (alembic 0038).
    # OQ-D-B = C, OQ-D-3 = B: pre-stored separate user asset (not avatar reuse).
    # Backend reads directly from storage by key — no external URL fetch (SSRF defense).
    # Populated via POST /v1/users/me/signature; cleared by DELETE /v1/users/me/signature.
    signature_storage_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )

    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ko")
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_minor: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    preferred_genres: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    identity_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    identity_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    gdpr_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # M10 Stripe Customer caching
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )

    # D'-1 artist-tier-release carry-over — sponsor_validity_days.
    # NULL = lifetime (any completed Sponsorship qualifies forever).
    # 1 / 7 / 30 / 90 / 365 = Sponsorship.completed_at must be within N days.
    # Artist-only setting; ignored for subscriber / follower tier checks.
    sponsor_validity_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # A-6 artist-index-v1 — global ranking columns (alembic 0047)
    # score 0-100 (weighted composite), rank/rank_region 1=1위, calc timestamp.
    # Updated hourly by artist_index_cron_loop. NULL = not yet ranked.
    artist_index_score: Mapped[float | None] = mapped_column(
        nullable=True
    )
    artist_index_rank: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    artist_index_rank_region: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    artist_index_calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # G'-8 artist-index-region-genre — region/genre ranking columns (alembic 0051)
    # Region rank: 1-indexed within same country_code group.
    # Genre rank: 1-indexed within same primary_genre group.
    # primary_genre: most-posted genre tag (cron-computed from posts.genre_tags).
    artist_index_score_region: Mapped[float | None] = mapped_column(
        nullable=True
    )
    artist_index_rank_genre: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    artist_index_score_genre: Mapped[float | None] = mapped_column(
        nullable=True
    )
    artist_index_primary_genre: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # B'-1 multi-currency-foundation — user display currency preference (alembic 0061).
    # Supported: USD / KRW / EUR / JPY. Default USD.
    # Updated via PATCH /v1/me/preferences/currency.
    preferred_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USD"
    )

    # M3 GDPR fields (Phase 4)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    gdpr_export_count: Mapped[int] = mapped_column(Integer, default=0)
    privacy_policy_version: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    terms_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    artist_profile: Mapped["ArtistProfile | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="ArtistProfile.user_id"
    )


class ArtistApplication(Base):
    __tablename__ = "artist_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    portfolio_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    school: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_enrolled: Mapped[bool] = mapped_column(Boolean, default=True)
    genre_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    intro_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_images: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    enrollment_proof_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    representative_works: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exhibitions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    awards: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    edu_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    edu_email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # 'pending' | 'approved' | 'rejected'
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ArtistProfile(Base):
    __tablename__ = "artist_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artist_applications.id"), nullable=True
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    school: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_enrolled: Mapped[bool] = mapped_column(Boolean, default=True)
    genre_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    intro_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    portfolio_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    representative_works: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exhibitions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    awards: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    edu_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    edu_email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    badge_level: Mapped[str] = mapped_column(String(20), default="student")
    # 'student' | 'emerging' | 'recommended' | 'popular'
    payout_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    guardian_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(
        back_populates="artist_profile", foreign_keys=[user_id]
    )
