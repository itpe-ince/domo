"""OG(Open Graph) 미리보기 API — Phase 9 L-B (L-3 OG auto-thumbnail).

POST /api/og/preview
  - 로그인 필수 (current_user)
  - Redis 24시간 캐시 → OG 스크래핑 → 결과 반환
  - httpx/bs4 미설치 시 null 응답 반환 (Mock 모드)
  - 외부 사이트 타임아웃 5초 초과 시 504 반환
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator

from app.api.auth import get_current_user
from app.models.user import User
from app.services.cache import cache
from app.services.og_scraper import scrape_og

router = APIRouter(prefix="/og", tags=["og"])


class OGPreviewRequest(BaseModel):
    """OG 미리보기 요청 스키마."""
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class OGPreviewResponse(BaseModel):
    """OG 미리보기 응답 스키마."""
    title: str | None
    description: str | None
    image_url: str | None
    site_name: str | None
    cached: bool = False


@router.post("/preview", response_model=OGPreviewResponse)
async def og_preview(
    body: OGPreviewRequest,
    current_user: User = Depends(get_current_user),
) -> OGPreviewResponse:
    """URL의 Open Graph 메타태그를 추출하여 반환한다.

    - Redis 캐시 24시간 적용 (동일 URL 두 번째 호출 ≤ 50ms 목표)
    - 외부 사이트 응답 타임아웃 5초 → 504 반환
    - httpx/bs4 미설치 시 null 필드 응답 (422는 반환하지 않음)
    """
    url = body.url

    # 캐시 hit 여부 확인 (캐시 키 직접 조회)
    import hashlib
    cache_key = f"og:cache:{hashlib.sha256(url.encode()).hexdigest()}"

    was_cached = False
    if cache.is_enabled:
        raw = await cache.get(cache_key)
        if raw:
            was_cached = True

    try:
        og_data = await scrape_og(url, cache_client=cache)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("OG preview failed url=%s: %s", url, exc)
        raise HTTPException(status_code=504, detail="External site did not respond in time") from exc

    return OGPreviewResponse(
        title=og_data.title,
        description=og_data.description,
        image_url=og_data.image_url,
        site_name=og_data.site_name,
        cached=was_cached,
    )
