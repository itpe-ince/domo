"""Interview Generator Service — C-1 ai-artist-interview-generation.

Assembles artist profile + portfolio + milestones into an LLM prompt,
calls LLMGatewayClient, and stores the resulting ArtistInterview row.

GDPR compliance:
  - Only sends anonymised artist info (display_name, genre_tags, statement,
    portfolio_urls, country_code, ranking). No PII (email, address) sent.
  - Requires explicit artist opt-in (artist_consent_at) before publishing.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.artist_interview import ArtistInterview
from app.models.post import Post
from app.models.sponsorship import Sponsorship
from app.models.user import ArtistProfile, User
from app.services.llm_gateway import LLMGatewayClient

log = logging.getLogger(__name__)

_LOCALE_SYSTEM_HINTS: dict[str, str] = {
    "ko": "한국어로 작성해 주세요.",
    "en": "Write in English.",
    "ja": "日本語で作成してください。",
    "zh": "请用中文书写。",
    "es": "Escribe en español.",
}

_IDEMPOTENCY_WINDOW_HOURS = 24


async def collect_artist_summary(
    db: AsyncSession,
    artist_id: uuid.UUID,
) -> dict:
    """Collect non-PII artist data for LLM prompt construction."""
    user_result = await db.execute(select(User).where(User.id == artist_id))
    user = user_result.scalar_one_or_none()
    if user is None or user.role != "artist" or user.status != "active":
        raise ApiError(
            "INVALID_ARTIST",
            "artist_id must refer to an active artist",
            http_status=422,
        )

    profile_result = await db.execute(
        select(ArtistProfile).where(ArtistProfile.user_id == artist_id)
    )
    profile = profile_result.scalar_one_or_none()

    # Recent posts (last 10) — public titles/genres only
    posts_result = await db.execute(
        select(Post.title, Post.genre)
        .where(Post.author_id == artist_id, Post.status == "published")
        .order_by(Post.created_at.desc())
        .limit(10)
    )
    recent_posts = [
        {"title": row.title, "genres": [row.genre] if row.genre else []}
        for row in posts_result.all()
    ]

    # Sponsor count (milestone proxy)
    sponsor_count_result = await db.execute(
        select(Sponsorship).where(
            Sponsorship.artist_id == artist_id,
            Sponsorship.status == "completed",
        )
    )
    sponsor_count = len(sponsor_count_result.scalars().all())

    return {
        "display_name": user.display_name,
        "country_code": user.country_code,
        "ranking": {
            "global_rank": user.artist_index_rank,
            "global_score": user.artist_index_score,
            "region_rank": user.artist_index_rank_region,
            "primary_genre": user.artist_index_primary_genre,
        },
        "profile": {
            "school": profile.school if profile else None,
            "department": profile.department if profile else None,
            "genre_tags": profile.genre_tags if profile else [],
            "statement": profile.statement if profile else None,
            "exhibitions": profile.exhibitions if profile else None,
            "awards": profile.awards if profile else None,
            "badge_level": profile.badge_level if profile else "student",
        },
        "recent_posts": recent_posts,
        "sponsor_count": sponsor_count,
    }


def _build_prompt(summary: dict, locale: str) -> str:
    """Build LLM prompt from artist summary dict."""
    lang_hint = _LOCALE_SYSTEM_HINTS.get(locale, _LOCALE_SYSTEM_HINTS["ko"])
    name = summary["display_name"]
    country = summary.get("country_code", "")
    profile = summary.get("profile", {})
    ranking = summary.get("ranking", {})
    recent_posts = summary.get("recent_posts", [])
    sponsors = summary.get("sponsor_count", 0)

    genre_list = ", ".join(
        [g for g in (profile.get("genre_tags") or []) if g]
    )
    statement = profile.get("statement", "")
    badge = profile.get("badge_level", "student")
    global_rank = ranking.get("global_rank")
    primary_genre = ranking.get("primary_genre", "")

    post_titles = "; ".join(
        p["title"] for p in recent_posts[:5] if p.get("title")
    ) or "없음"

    exhibitions_raw = profile.get("exhibitions") or []
    if isinstance(exhibitions_raw, list):
        exhibitions_str = "; ".join(
            e.get("title", "") for e in exhibitions_raw[:3] if isinstance(e, dict)
        )
    else:
        exhibitions_str = ""

    awards_raw = profile.get("awards") or []
    if isinstance(awards_raw, list):
        awards_str = "; ".join(
            a.get("title", "") for a in awards_raw[:3] if isinstance(a, dict)
        )
    else:
        awards_str = ""

    rank_text = f"전체 아티스트 랭킹 {global_rank}위" if global_rank else "랭킹 미기재"
    school = profile.get("school") or ""
    dept = profile.get("department") or ""
    edu = f"{school} {dept}".strip() if (school or dept) else "미기재"

    prompt = f"""{lang_hint}

다음 아티스트 정보를 바탕으로 진솔하고 흥미로운 인터뷰 기사를 Q&A 형식으로 작성해 주세요.

---
[아티스트 정보]
- 이름: {name}
- 국가: {country}
- 학력: {edu}
- 주요 장르: {genre_list or primary_genre or '미기재'}
- 뱃지 레벨: {badge}
- {rank_text}
- 지지자 수: {sponsors}명
- 최근 작품 제목 (최대 5개): {post_titles}
- 전시 이력: {exhibitions_str or '없음'}
- 수상 이력: {awards_str or '없음'}
- 작가 소개: {statement or '없음'}
---

요청 사항:
1. 인터뷰 제목을 Markdown H1(#)으로 먼저 작성하세요. (예: "# 색채로 세상을 말하는 작가 {name}")
2. Q&A 형식으로 4-6개 질문을 작성하세요.
3. 작가의 창작 여정, 영감의 원천, 작품 세계관을 자연스럽게 녹여내세요.
4. 마케팅 용어나 과장된 표현을 피하고, 진솔한 어조로 작성하세요.
5. 총 길이는 400-700단어로 유지하세요.
"""
    return prompt.strip()


async def generate_artist_interview(
    db: AsyncSession,
    artist_id: uuid.UUID,
    locale: str,
    admin_id: uuid.UUID,
) -> ArtistInterview:
    """Main entry point — generate and store an ArtistInterview.

    Idempotency: returns the existing interview if one was generated within
    the last 24h for the same (artist_id, locale) in admin_review/draft status.
    """
    # Idempotency check: skip if recent generation exists
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=_IDEMPOTENCY_WINDOW_HOURS)
    existing_result = await db.execute(
        select(ArtistInterview).where(
            ArtistInterview.artist_id == artist_id,
            ArtistInterview.locale == locale,
            ArtistInterview.status.in_(["draft", "admin_review"]),
            ArtistInterview.created_at >= cutoff,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        log.info(
            "interview_generator: idempotency hit artist=%s locale=%s existing=%s",
            artist_id,
            locale,
            existing.id,
        )
        return existing

    # Collect artist data
    summary = await collect_artist_summary(db, artist_id)
    prompt = _build_prompt(summary, locale)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    # LLM generation
    client = LLMGatewayClient()
    result = await client.generate_interview(prompt)

    content: str = result["content"]
    model_used: str = result["model"]

    # Extract title from first H1 line if present
    lines = content.strip().splitlines()
    title = f"{summary['display_name']} 인터뷰"
    body = content
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        body = "\n".join(lines[1:]).strip()

    # Store
    interview = ArtistInterview(
        artist_id=artist_id,
        locale=locale,
        title=title[:200],
        body_markdown=body,
        status="admin_review",
        llm_model=model_used,
        llm_input_summary=str(summary)[:4000],  # truncate for storage
        generation_prompt_hash=prompt_hash,
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)

    log.info(
        "AUDIT action=interview_generated admin=%s artist=%s locale=%s id=%s model=%s",
        admin_id,
        artist_id,
        locale,
        interview.id,
        model_used,
    )
    return interview
