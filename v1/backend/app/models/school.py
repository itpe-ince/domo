import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class School(Base):
    """Verified school/university master table for artist certification."""

    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name_ko: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    # ISO 3166-1 alpha-2 (KR, JP, US, PE, ...)
    email_domain: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # e.g., "snu.ac.kr", "geidai.ac.jp", "limeart.edu"
    school_type: Mapped[str] = mapped_column(String(20), default="university")
    # 'university' | 'art_school' | 'academy' | 'other'
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    # 'active' | 'pending' | 'disabled'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
