"""Integration tests for C-3 booster — admin interview translation.

Endpoints under test:
  POST /admin/artist-interviews/{id}/translate?target_locale=en

Strategy: direct function calls with AsyncMock DB + MagicMock admin user.
Mock mode: LLM_GATEWAY_API_KEY not set → mock translations returned.

Test count: 3
  1. POST translate 201 — creates new interview row in target locale
  2. POST translate 409 — conflict: interview already exists for (artist_id, target_locale)
  3. POST translate 422 — same locale rejected
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_interviews import admin_translate_interview
from app.core.errors import ApiError
from app.models.artist_interview import ArtistInterview


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_interview(locale: str = "ko") -> MagicMock:
    row = MagicMock(spec=ArtistInterview)
    row.id = uuid.uuid4()
    row.artist_id = uuid.uuid4()
    row.locale = locale
    row.title = "작가 인터뷰"
    row.body_markdown = "**Q. 작품 활동을 시작하게 된 계기는 무엇인가요?**\n\n어릴 때부터 색과 형태에 매료되어 있었습니다."
    row.status = "published"
    row.llm_model = "gemma4-e4b"
    row.llm_input_summary = None
    row.reviewed_by_admin_id = None
    row.reviewed_at = None
    row.review_note = None
    row.artist_consent_at = datetime.now(timezone.utc)
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ─── Test 1: POST translate 201 — success ─────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_translate_interview_success():
    """POST /{id}/translate creates a new admin_review interview in target locale."""
    admin = _make_admin()
    source = _make_interview(locale="ko")
    db = _make_db()

    # First db.execute returns source interview
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = source
    # Second db.execute returns None (no existing interview for target locale)
    conflict_result = MagicMock()
    conflict_result.scalar_one_or_none.return_value = None

    db.execute.side_effect = [source_result, conflict_result]

    # Mock the LLM client translate_text
    with patch("app.api.admin_interviews.LLMGatewayClient") as MockClient:
        mock_client = MagicMock()
        mock_client.translate_text = AsyncMock(side_effect=[
            "[MOCK en] 작가 인터뷰",          # title translation
            "[MOCK en] **Q. When did...**",   # body translation
        ])
        MockClient.return_value = mock_client

        # Mock db.refresh to populate the new interview
        new_interview = _make_interview(locale="en")
        new_interview.status = "admin_review"
        db.refresh.side_effect = lambda obj: None

        with patch("app.api.admin_interviews._row_to_out") as mock_out:
            mock_out.return_value = {
                "id": str(uuid.uuid4()),
                "locale": "en",
                "status": "admin_review",
            }
            result = await admin_translate_interview(
                interview_id=str(source.id),
                target_locale="en",
                admin=admin,
                db=db,
                _rl=None,
            )

    assert result["data"]["status"] == "admin_review"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


# ─── Test 2: POST translate 409 — conflict ─────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_translate_interview_conflict_409():
    """POST /{id}/translate returns 409 if interview already exists for target locale."""
    admin = _make_admin()
    source = _make_interview(locale="ko")
    existing = _make_interview(locale="en")
    db = _make_db()

    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = source
    conflict_result = MagicMock()
    conflict_result.scalar_one_or_none.return_value = existing

    db.execute.side_effect = [source_result, conflict_result]

    with pytest.raises(ApiError) as exc_info:
        await admin_translate_interview(
            interview_id=str(source.id),
            target_locale="en",
            admin=admin,
            db=db,
            _rl=None,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "ALREADY_EXISTS"


# ─── Test 3: POST translate 422 — same locale ─────────────────────────────────


@pytest.mark.asyncio
async def test_admin_translate_interview_same_locale_422():
    """POST /{id}/translate returns 422 if source and target locale are identical."""
    admin = _make_admin()
    source = _make_interview(locale="ko")
    db = _make_db()

    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = source
    db.execute.return_value = source_result

    with pytest.raises(ApiError) as exc_info:
        await admin_translate_interview(
            interview_id=str(source.id),
            target_locale="ko",  # same as source
            admin=admin,
            db=db,
            _rl=None,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "SAME_LOCALE"
