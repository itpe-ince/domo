import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
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

    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ko")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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
