"""Newsletter open/click tracking API — Phase 9 L-B (L-4 Newsletter open rate).

GET /api/newsletter/track/open   — 1x1 투명 PNG 반환 + open 이벤트 DB 기록
GET /api/newsletter/track/click  — 302 redirect + click 이벤트 DB 기록

두 엔드포인트 모두 인증 없음 — 이메일 클라이언트에서 직접 호출된다.
중복 open 이벤트 허용 (Gmail pre-fetch 포함).
click 이벤트는 url 파라미터 필수.
"""
from __future__ import annotations

import hashlib
import logging
import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/newsletter", tags=["newsletter-tracking"])

# 1x1 투명 PNG 최소 바이너리 (표준 PNG 구조)
# PNG 시그니처(8) + IHDR 청크(25) + IDAT 청크(12+zlib) + IEND 청크(12)
_TRANSPARENT_1X1_PNG: bytes = bytes([
    # PNG 시그니처
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    # IHDR: 길이=13, 타입="IHDR"
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    # width=1, height=1, bitdepth=8, colortype=6(RGBA), compression=0, filter=0, interlace=0
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00,
    # IHDR CRC
    0x1F, 0x15, 0xC4, 0x89,
    # IDAT: 길이=11, 타입="IDAT", zlib 압축 1x1 RGBA(0,0,0,0)
    0x00, 0x00, 0x00, 0x0B, 0x49, 0x44, 0x41, 0x54,
    0x78, 0x9C, 0x62, 0x00, 0x00, 0x00, 0x02, 0x00,
    0x01,
    # IDAT CRC
    0xE5, 0x27, 0xDE, 0xFC,
    # IEND: 길이=0, 타입="IEND"
    0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
    # IEND CRC
    0xAE, 0x42, 0x60, 0x82,
])


async def _record_event(
    db: AsyncSession,
    issue_id: str,
    user_id: str | None,
    event_type: str,
    url: str | None,
    request: Request,
) -> None:
    """newsletter_events 테이블에 이벤트 기록 (오류 시 silently skip)."""
    from sqlalchemy import text

    # IP SHA-256 (GDPR 준수)
    client_host = (request.client.host if request.client else None) or ""
    ip_hash = hashlib.sha256(client_host.encode()).hexdigest() if client_host else None
    user_agent = request.headers.get("user-agent", "")[:500] or None

    try:
        await db.execute(
            text(
                "INSERT INTO newsletter_events "
                "(id, issue_id, user_id, event_type, url, user_agent, ip_hash, created_at) "
                "VALUES (gen_random_uuid(), :issue_id, :user_id, :event_type, :url, "
                "        :user_agent, :ip_hash, now())"
            ),
            {
                "issue_id": issue_id,
                "user_id": user_id or None,
                "event_type": event_type,
                "url": url,
                "user_agent": user_agent,
                "ip_hash": ip_hash,
            },
        )
        await db.commit()
        log.debug(
            "[newsletter-track] issue=%s user=%s type=%s",
            issue_id, user_id, event_type,
        )
    except Exception as exc:
        log.warning("[newsletter-track] record_event failed: %s", exc)
        try:
            await db.rollback()
        except Exception:
            pass


@router.get("/track/open")
async def track_open(
    issue: Annotated[str, Query(description="Newsletter issue UUID")],
    user: Annotated[str | None, Query(description="Subscriber user UUID")] = None,
    request: Request = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> Response:
    """1x1 투명 PNG 반환 + open 이벤트 기록.

    이메일 클라이언트가 이미지를 로드할 때 호출된다.
    중복 open 이벤트 허용 (Gmail 프리페치 포함).
    """
    await _record_event(
        db=db,
        issue_id=issue,
        user_id=user,
        event_type="open",
        url=None,
        request=request,
    )

    return Response(
        content=_TRANSPARENT_1X1_PNG,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/track/click")
async def track_click(
    issue: Annotated[str, Query(description="Newsletter issue UUID")],
    url: Annotated[str, Query(description="URL-encoded destination URL")],
    user: Annotated[str | None, Query(description="Subscriber user UUID")] = None,
    request: Request = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """클릭 이벤트 기록 후 원본 URL로 302 redirect.

    url 파라미터는 URL-encoded 된 목적지 URL.
    """
    # URL 디코딩 (쿼리 파라미터는 FastAPI가 자동 decode)
    destination = url.strip()
    if not destination:
        destination = "/"

    await _record_event(
        db=db,
        issue_id=issue,
        user_id=user,
        event_type="click",
        url=destination,
        request=request,
    )

    return RedirectResponse(url=destination, status_code=302)
