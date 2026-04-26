import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'school' | 'genre' | 'country' | 'custom'
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunityMember(Base):
    __tablename__ = "community_members"

    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member")
    # 'owner' | 'admin' | 'member'
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommunityComment(Base):
    __tablename__ = "community_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    # 'active' | 'deleted' | 'hidden'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
