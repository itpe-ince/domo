"""PostEngagementCache model — G'-9 post-engagement-cache.

Stores pre-aggregated 24h engagement metrics per post, updated hourly by
post_engagement_cron_loop (R-5 격리 — separate cron, separate AsyncSessionLocal).

Replaces inline subquery counting in A-3 feed_scoring.py for performance.
Cache miss → graceful degrade to inline fallback.

engagement_score formula:
  likes × 1 + comments × 2 + bookmarks × 1.5 + bids × 5 + shares × 3
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PostEngagementCache(Base):
    __tablename__ = "post_engagement_cache"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # 24h rolling window counts
    like_count_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bookmark_count_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bid_count_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    share_count_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Weighted aggregate: likes×1 + comments×2 + bookmarks×1.5 + bids×5 + shares×3
    engagement_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Partial index: only cache rows with actual engagement (saves index space)
        Index(
            "ix_post_engagement_cache_score_partial",
            "engagement_score",
            postgresql_where="engagement_score > 0",
        ),
    )
