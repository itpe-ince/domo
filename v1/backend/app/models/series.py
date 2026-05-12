"""Series + PostSeriesMembership models — publish-controls PDCA #8 §B-3.

Series: author-owned collection of posts (gallery curation).
PostSeriesMembership: M:N join with order_index for drag-reorder (OQ-5=A).

CASCADE semantics: deleting a Series removes memberships only; Posts are preserved.
cover_url nullable — frontend falls back to first post thumbnail (OQ-4=C).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Series(Base):
    __tablename__ = "series"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # ix_series_author_id — GET /v1/series?author_id=
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # OQ-4=C: manual first; frontend falls back to first post thumbnail
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["PostSeriesMembership"]] = relationship(
        back_populates="series",
        cascade="all, delete-orphan",
        order_by="PostSeriesMembership.order_index",
    )


class PostSeriesMembership(Base):
    __tablename__ = "post_series_membership"

    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        primary_key=True,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # ix_psm_post_id — POST /v1/posts/{id}/series membership delete
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    series: Mapped["Series"] = relationship(back_populates="memberships")
