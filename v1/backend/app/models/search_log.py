import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SearchLog(Base):
    __tablename__ = "search_logs"
    __table_args__ = (
        Index("idx_search_logs_user", "user_id", "created_at"),
        Index("idx_search_logs_query", "query", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    tab: Mapped[str] = mapped_column(String(20), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
