import random
import string
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.notification import Notification
from app.models.school import School
from app.models.user import ArtistApplication, ArtistProfile, User
from app.schemas.artist import ArtistApplicationCreate, ArtistApplicationOut
from app.schemas.artist_index import ArtistIndexEntry, ArtistRankingResponse
from app.services.artist_index_scoring import derive_tier_badge
from app.services.cache import cache
from app.services.kyc import require_kyc_verified

# In-memory store for dev (Redis in production)
_edu_verification_codes: dict[str, dict] = {}

_ARTIST_INDEX_CACHE_TTL = 3600  # 1 hour

router = APIRouter(prefix="/artists", tags=["artists"])


@router.post("/apply")
async def apply_artist(
    body: ArtistApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role == "artist":
        raise ApiError(
            "CONFLICT", "You are already an artist", http_status=409
        )

    # KYC gate — configurable via system_settings.kyc_enforcement
    await require_kyc_verified(user, db)

    # 진행 중 신청 있는지 확인
    existing = await db.execute(
        select(ArtistApplication).where(
            ArtistApplication.user_id == user.id,
            ArtistApplication.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise ApiError(
            "CONFLICT", "You already have a pending application", http_status=409
        )

    application = ArtistApplication(
        user_id=user.id,
        school=body.school,
        department=body.department,
        graduation_year=body.graduation_year,
        is_enrolled=body.is_enrolled,
        genre_tags=body.genre_tags,
        portfolio_urls=body.portfolio_urls,
        intro_video_url=body.intro_video_url,
        enrollment_proof_url=body.enrollment_proof_url,
        representative_works=[w.model_dump() for w in body.representative_works],
        exhibitions=[e.model_dump() for e in body.exhibitions] if body.exhibitions else None,
        awards=[a.model_dump() for a in body.awards] if body.awards else None,
        statement=body.statement,
        status="pending",
    )
    db.add(application)

    # 관리자에게 알림 (모든 admin 대상)
    admin_result = await db.execute(select(User).where(User.role == "admin"))
    admins = admin_result.scalars().all()
    for admin in admins:
        db.add(
            Notification(
                user_id=admin.id,
                type="artist_application_received",
                title="새 작가 심사 신청",
                body=f"{user.display_name}님이 작가 심사를 신청했습니다.",
                link=f"/admin/applications/{application.id}",
            )
        )

    await db.commit()
    await db.refresh(application)
    return {"data": ArtistApplicationOut.model_validate(application).model_dump(mode="json")}


@router.get("/apply/me")
async def my_application(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArtistApplication)
        .where(ArtistApplication.user_id == user.id)
        .order_by(ArtistApplication.created_at.desc())
    )
    apps = result.scalars().all()
    return {
        "data": [
            ArtistApplicationOut.model_validate(a).model_dump(mode="json") for a in apps
        ]
    }


# ─── School Email Verification ──────────────────────────────────────────


class EduEmailRequest(BaseModel):
    edu_email: str


class EduVerifyRequest(BaseModel):
    edu_email: str
    code: str


@router.post("/verify-edu/send")
async def send_edu_verification(
    body: EduEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send verification code to school email."""
    email = body.edu_email.strip().lower()
    domain = email.split("@")[-1] if "@" in email else ""

    # Check domain against schools table
    school_result = await db.execute(
        select(School).where(School.email_domain == domain, School.status == "active")
    )
    school = school_result.scalar_one_or_none()
    if not school:
        raise ApiError(
            "INVALID_DOMAIN",
            f"'{domain}'은(는) 등록된 학교 도메인이 아닙니다. 관리자에게 학교 등록을 요청해주세요.",
            http_status=422,
        )

    # Generate 6-digit code
    code = "".join(random.choices(string.digits, k=6))
    _edu_verification_codes[email] = {
        "code": code,
        "user_id": str(user.id),
        "school_id": str(school.id),
        "expires": datetime.now(timezone.utc).timestamp() + 300,  # 5 min
    }

    # Send email (mock mode logs to console)
    from app.services.email import EmailMessage, get_email_provider
    provider = get_email_provider()
    await provider.send(
        EmailMessage(
            to=email,
            subject="[Domo Lounge] 학교 이메일 인증 코드",
            html=f"<p>인증 코드: <strong>{code}</strong></p><p>5분 이내에 입력해주세요.</p>",
            text=f"인증 코드: {code}\n\n5분 이내에 입력해주세요.",
        )
    )

    return {"data": {"message": f"인증 코드가 {email}로 발송되었습니다.", "school_name": school.name_ko}}


@router.post("/verify-edu/confirm")
async def confirm_edu_verification(
    body: EduVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm verification code and mark email as verified."""
    email = body.edu_email.strip().lower()
    stored = _edu_verification_codes.get(email)

    if not stored:
        raise ApiError("CODE_NOT_FOUND", "인증 코드를 먼저 요청해주세요.", http_status=422)
    if stored["user_id"] != str(user.id):
        raise ApiError("FORBIDDEN", "본인이 요청한 코드만 확인 가능합니다.", http_status=403)
    if datetime.now(timezone.utc).timestamp() > stored["expires"]:
        del _edu_verification_codes[email]
        raise ApiError("CODE_EXPIRED", "인증 코드가 만료되었습니다. 다시 요청해주세요.", http_status=422)
    if stored["code"] != body.code:
        raise ApiError("CODE_INVALID", "인증 코드가 일치하지 않습니다.", http_status=422)

    # Mark verified on pending application
    app_result = await db.execute(
        select(ArtistApplication).where(
            ArtistApplication.user_id == user.id,
            ArtistApplication.status == "pending",
        ).order_by(ArtistApplication.created_at.desc())
    )
    app_obj = app_result.scalar_one_or_none()
    if app_obj:
        app_obj.edu_email = email
        app_obj.edu_email_verified_at = datetime.now(timezone.utc)

    del _edu_verification_codes[email]
    await db.commit()
    return {"data": {"verified": True, "edu_email": email}}


# ─── Artist Index endpoints (A-6) ─────────────────────────────────────────────


@router.get("/index")
async def get_artist_index(
    region: str | None = Query(None, description="Filter by country_code (ISO 3166-1 alpha-2)"),
    genre: str | None = Query(None, description="Filter by primary genre tag"),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, description="Opaque cursor: base10 rank offset"),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("artist_index_read"),
):
    """GET /v1/artists/index — Public global ranking list.

    Returns ranked artists ordered by artist_index_rank ASC.
    Anonymous access allowed (no auth required).
    Rate limit: artist_index_read (60/min anon, 120/min logged-in).

    Filters:
      - region: country_code (e.g. "KR", "PE", "US")
      - genre: artist_profiles.genre_tags contains this value
    """
    # Cache key encodes all query dimensions: region, genre, limit, cursor.
    _region_part = region.upper() if region else "all"
    _genre_part = genre or "all"
    cache_key = f"artists:index:{_region_part}:{_genre_part}:{limit}:{cursor or 'start'}"
    cached = await cache.get_json(cache_key, prefix="artists")
    if cached is not None:
        return cached

    # Cursor is a rank offset (integer)
    rank_offset = 0
    if cursor:
        try:
            rank_offset = int(cursor)
        except ValueError:
            rank_offset = 0

    # Build query with optional filters.
    # G'-8: when region= filter active → sort by rank_region;
    #        when genre= filter active → sort by rank_genre;
    #        both → sort by region rank (primary) then genre rank (secondary);
    #        neither → sort by global rank (original behaviour).
    stmt = (
        select(User, ArtistProfile)
        .join(ArtistProfile, ArtistProfile.user_id == User.id, isouter=True)
        .where(
            User.role == "artist",
            User.status == "active",
            User.deleted_at.is_(None),
            User.artist_index_rank.is_not(None),
        )
    )

    if region:
        stmt = stmt.where(User.country_code == region.upper())

    if genre:
        # Match against artist_index_primary_genre (cron-computed) OR genre_tags contains
        from sqlalchemy import or_
        from sqlalchemy.dialects.postgresql import ARRAY
        from sqlalchemy import Text, cast
        stmt = stmt.where(
            or_(
                User.artist_index_primary_genre == genre,
                ArtistProfile.genre_tags.contains(cast([genre], ARRAY(Text))),
            )
        )

    # Ordering: prefer region/genre rank columns when filters are active
    if region and not genre:
        if rank_offset > 0:
            stmt = stmt.where(User.artist_index_rank_region > rank_offset)
        stmt = stmt.order_by(User.artist_index_rank_region.asc()).limit(limit + 1)
    elif genre and not region:
        if rank_offset > 0:
            stmt = stmt.where(User.artist_index_rank_genre > rank_offset)
        stmt = stmt.order_by(User.artist_index_rank_genre.asc()).limit(limit + 1)
    elif region and genre:
        if rank_offset > 0:
            stmt = stmt.where(User.artist_index_rank_region > rank_offset)
        stmt = stmt.order_by(
            User.artist_index_rank_region.asc(),
            User.artist_index_rank_genre.asc(),
        ).limit(limit + 1)
    else:
        if rank_offset > 0:
            stmt = stmt.where(User.artist_index_rank > rank_offset)
        stmt = stmt.order_by(User.artist_index_rank.asc()).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    entries = []
    for user_row, profile_row in rows:
        # Primary genre: prefer cron-computed artist_index_primary_genre,
        # fall back to first tag from artist_profiles.genre_tags.
        primary_genre = user_row.artist_index_primary_genre
        if not primary_genre and profile_row and profile_row.genre_tags:
            primary_genre = profile_row.genre_tags[0]

        entries.append(
            ArtistIndexEntry(
                user_id=str(user_row.id),
                username=user_row.display_name,
                avatar_url=user_row.avatar_url,
                country=user_row.country_code,
                primary_genre=primary_genre,
                score=user_row.artist_index_score or 0.0,
                rank=user_row.artist_index_rank,
                tier_badge=derive_tier_badge(user_row.artist_index_rank),
                rank_region=user_row.artist_index_rank_region,
                rank_genre=user_row.artist_index_rank_genre,
            )
        )

    next_cursor = None
    if has_more and entries:
        # Use region/genre rank as cursor when those filters are active
        if region and not genre:
            next_cursor = str(entries[-1].rank_region) if entries[-1].rank_region else str(entries[-1].rank)
        elif genre and not region:
            next_cursor = str(entries[-1].rank_genre) if entries[-1].rank_genre else str(entries[-1].rank)
        else:
            next_cursor = str(entries[-1].rank)

    # Double-wrap: apiFetch<ArtistIndexListResponse> unwraps json.data → ArtistIndexListResponse
    # So the envelope must be {"data": {"data": [...], "next_cursor": ..., "total": ...}}
    response = {
        "data": {
            "data": [e.model_dump() for e in entries],
            "next_cursor": next_cursor,
            "total": None,  # Full count expensive — omitted; use has_more pattern
        }
    }
    await cache.set_json(cache_key, response, _ARTIST_INDEX_CACHE_TTL, prefix="artists")
    return response


@router.get("/{user_id}/index")
async def get_artist_ranking(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("artist_index_read"),
):
    """GET /v1/artists/{user_id}/index — Individual artist ranking.

    Returns score, rank, tier_badge, and last_calculated_at for one artist.
    Used by public artist profile page badge display.
    """
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Artist not found", http_status=404)

    result = await db.execute(
        select(User).where(
            User.id == uid,
            User.role == "artist",
            User.status == "active",
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise ApiError("NOT_FOUND", "Artist not found", http_status=404)

    if user.artist_index_rank is None:
        raise ApiError(
            "NOT_RANKED",
            "This artist has not been ranked yet. Rankings are calculated hourly.",
            http_status=404,
        )

    return {
        "data": ArtistRankingResponse(
            score=user.artist_index_score or 0.0,
            rank=user.artist_index_rank,
            rank_region=user.artist_index_rank_region,
            rank_genre=user.artist_index_rank_genre,
            primary_genre=user.artist_index_primary_genre,
            tier_badge=derive_tier_badge(user.artist_index_rank),
            last_calculated_at=user.artist_index_calculated_at,
        ).model_dump(mode="json")
    }


@router.get("/schools/search")
async def search_schools(
    q: str = Query("", min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Public: search schools for artist apply form autocomplete."""
    result = await db.execute(
        select(School)
        .where(
            School.status == "active",
            (School.name_ko.ilike(f"%{q}%") | School.name_en.ilike(f"%{q}%")),
        )
        .order_by(School.name_en.asc())
        .limit(10)
    )
    schools = result.scalars().all()
    return {
        "data": [
            {
                "id": str(s.id),
                "name_ko": s.name_ko,
                "name_en": s.name_en,
                "email_domain": s.email_domain,
                "country_code": s.country_code,
            }
            for s in schools
        ]
    }
