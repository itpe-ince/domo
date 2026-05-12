"""Unit tests — newsletter_tracking.py + newsletter_composer.inject_tracking (Phase 9 L-B, L-4).

테스트 범위:
  - inject_tracking: open tracking pixel 삽입 확인
  - inject_tracking: 외부 링크 click tracking 변환 확인
  - inject_tracking: Domo 내부 URL skip 확인
  - track_open API: 1x1 PNG Content-Type + _record_event 호출
  - track_click API: 302 redirect Location 헤더 확인
  - track_click API: url 파라미터로 DB 이벤트 기록
"""
from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.newsletter_composer import inject_tracking


# ──────────────────────────────────────────────────────────────────────────────
# 1. inject_tracking — open tracking pixel
# ──────────────────────────────────────────────────────────────────────────────

def test_inject_tracking_pixel_inserted():
    """inject_tracking: </body> 직전에 tracking pixel img 태그가 삽입된다."""
    html = "<html><body><p>Hello</p></body></html>"
    result = inject_tracking(html, issue_id="issue-001", user_id="user-abc")
    assert "track/open" in result
    assert "issue=issue-001" in result
    assert "user=user-abc" in result
    assert '<img src=' in result
    # pixel은 </body> 직전에 위치해야 함
    pixel_pos = result.index("track/open")
    body_close_pos = result.index("</body>")
    assert pixel_pos < body_close_pos


def test_inject_tracking_pixel_no_body_tag():
    """inject_tracking: </body> 없는 HTML에도 pixel이 추가된다."""
    html = "<p>Hello</p>"
    result = inject_tracking(html, issue_id="issue-002", user_id="user-xyz")
    assert "track/open" in result
    assert result.endswith(">")  # img 태그로 끝나거나 그 뒤 내용 없음


# ──────────────────────────────────────────────────────────────────────────────
# 2. inject_tracking — click tracking 링크 변환
# ──────────────────────────────────────────────────────────────────────────────

def test_inject_tracking_external_link_wrapped():
    """외부 링크 <a href>가 click tracking URL로 변환된다."""
    html = '<html><body><a href="https://external.com/article">Read more</a></body></html>'
    result = inject_tracking(html, issue_id="issue-003", user_id="user-qrs")
    assert "track/click" in result
    assert "issue=issue-003" in result
    # 원본 URL이 인코딩되어 포함되어야 함
    assert "external.com" in result or "https%3A" in result


def test_inject_tracking_internal_url_skipped():
    """Domo 내부 URL(api_base_url 포함)은 클릭 트래킹으로 변환하지 않는다."""
    with patch("app.services.newsletter_composer.get_settings") as mock_settings:
        mock_settings.return_value.api_base_url = "http://localhost:3710/v1"
        html = '<html><body><a href="http://localhost:3710/v1/something">Internal</a></body></html>'
        result = inject_tracking(html, issue_id="issue-004", user_id="user-int")

    # 내부 링크는 그대로 유지 (track/click 변환 없음)
    assert "track/click" not in result
    assert "http://localhost:3710/v1/something" in result


# ──────────────────────────────────────────────────────────────────────────────
# 3. track_open API — 1x1 PNG 반환
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_track_open_returns_png():
    """GET /newsletter/track/open → Content-Type: image/png, 정상 응답."""
    from app.api.newsletter_tracking import track_open, _TRANSPARENT_1X1_PNG

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    mock_request = MagicMock()
    mock_request.client = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {"user-agent": "TestMailClient/1.0"}

    response = await track_open(
        issue="issue-open-001",
        user="user-sub-001",
        request=mock_request,
        db=mock_db,
    )

    assert response.media_type == "image/png"
    assert response.body == _TRANSPARENT_1X1_PNG
    assert response.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# 4. track_click API — 302 redirect
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_track_click_redirects():
    """GET /newsletter/track/click → 302 redirect to destination URL."""
    from app.api.newsletter_tracking import track_click

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    mock_request = MagicMock()
    mock_request.client = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {}

    destination = "https://domo.art/artists/alice"

    response = await track_click(
        issue="issue-click-001",
        url=destination,
        user="user-sub-002",
        request=mock_request,
        db=mock_db,
    )

    assert response.status_code == 302
    assert response.headers["location"] == destination


@pytest.mark.asyncio
async def test_track_click_records_url_in_db():
    """click 이벤트 기록 시 url 파라미터가 DB INSERT에 포함된다."""
    from app.api.newsletter_tracking import _record_event

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    mock_request = MagicMock()
    mock_request.client = MagicMock()
    mock_request.client.host = "10.0.0.1"
    mock_request.headers = {}

    await _record_event(
        db=mock_db,
        issue_id="issue-record-001",
        user_id="user-sub-003",
        event_type="click",
        url="https://external.com/article",
        request=mock_request,
    )

    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args
    params = call_args[0][1]  # positional args[1] = params dict
    assert params["event_type"] == "click"
    assert params["url"] == "https://external.com/article"
    assert params["issue_id"] == "issue-record-001"
