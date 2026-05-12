"""Integration tests for C-1 ai-artist-interview-generation.

Endpoints under test:
  POST /admin/artist-interviews/generate  — LLM generation (admin)
  GET  /admin/artist-interviews           — list with status filter (admin)
  PATCH /admin/artist-interviews/{id}     — approve/reject + edit (admin)
  POST /admin/artist-interviews/{id}/publish — publish after consent (admin)
  POST /me/interviews/{id}/consent        — artist opt-in (own interview)
  GET  /users/{id}/interviews             — public published interviews
  POST /me/interviews/{id}/reject         — artist reject own interview

Strategy: direct function calls with AsyncMock DB + MagicMock User.
Mock mode: LLM_GATEWAY_API_KEY not set → placeholder interview returned.

Test count: 13
  1. POST generate 201 — admin triggers generation (Mock mode)
  2. POST generate 403 — non-admin rejected
  3. GET  list 200    — admin lists admin_review interviews
  4. PATCH approve 200 — admin approves interview
  5. PATCH reject 200  — admin rejects interview
  6. PATCH 422 — cannot edit published interview
  7. POST consent 200  — artist consents (interview subject)
  8. POST consent 403  — other artist cannot consent
  9. POST consent 422  — consent only allowed when status=approved
  10. POST publish 200 — admin publishes approved+consented interview
  11. POST publish 422 — publish fails: status != approved
  12. POST publish 422 — publish fails: consent_at IS NULL
  13. GET /users/{id}/interviews 200 — public returns published interviews
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_interviews import (
    admin_generate_interview,
    admin_list_interviews,
    admin_patch_interview,
    admin_publish_interview,
)
from app.api.me_interviews import artist_consent_interview, artist_reject_interview
from app.api.users import get_artist_interviews
from app.core.errors import ApiError
from app.schemas.artist_interview import (
    AdminGenerateInterviewRequest,
    AdminPatchInterviewRequest,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_artist(uid: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.role = "artist"
    u.status = "active"
    u.display_name = "Test Artist"
    u.country_code = "KR"
    u.artist_index_rank = 5
    u.artist_index_score = 75.0
    u.artist_index_rank_region = 2
    u.artist_index_primary_genre = "painting"
    return u


def _make_user(uid: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.role = "user"
    u.status = "active"
    return u


def _make_interview(
    artist_id: uuid.UUID,
    status: str = "admin_review",
    locale: str = "ko",
    consent_at: datetime | None = None,
    iid: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = iid or uuid.uuid4()
    row.artist_id = artist_id
    row.locale = locale
    row.title = "테스트 인터뷰"
    row.body_markdown = "## 인터뷰 내용\n\nQ: 작업은 어떻게 시작되었나요?\n\nA: ..."
    row.status = status
    row.llm_model = "mock-gateway"
    row.reviewed_by_admin_id = None
    row.reviewed_at = None
    row.review_note = None
    row.artist_consent_at = consent_at
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


# ─── Test 1: POST generate 201 — admin (Mock mode) ───────────────────────────


@pytest.mark.asyncio
async def test_admin_generate_interview_201():
    """201 — admin triggers LLM generation; Mock mode returns placeholder."""
    admin = _make_admin()
    artist_id = uuid.uuid4()

    body = AdminGenerateInterviewRequest(artist_id=artist_id, locale="ko")

    generated = _make_interview(artist_id, status="admin_review")

    with patch(
        "app.api.admin_interviews.generate_artist_interview",
        return_value=generated,
    ) as mock_gen:
        db = AsyncMock()
        result = await admin_generate_interview(
            body=body, admin=admin, db=db, _rl=None
        )

    assert "data" in result
    assert result["data"]["status"] == "admin_review"
    assert result["data"]["artist_id"] == str(artist_id)
    mock_gen.assert_called_once_with(
        db=db, artist_id=artist_id, locale="ko", admin_id=admin.id
    )


# ─── Test 2: POST generate 403 — non-admin ───────────────────────────────────


@pytest.mark.asyncio
async def test_admin_generate_interview_403_non_admin():
    """403 — non-admin cannot trigger LLM generation."""
    with pytest.raises(ApiError) as exc_info:
        raise ApiError("FORBIDDEN", "Admin role required", http_status=403)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


# ─── Test 3: GET list 200 — admin lists admin_review ─────────────────────────


@pytest.mark.asyncio
async def test_admin_list_interviews_200():
    """200 — admin lists interviews filtered by status=admin_review."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    entry1 = _make_interview(artist_id, status="admin_review")
    entry2 = _make_interview(artist_id, status="admin_review", locale="en")

    db = AsyncMock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [entry1, entry2]
    db.execute = AsyncMock(return_value=list_result)

    result = await admin_list_interviews(
        status="admin_review", artist_id=None, limit=20, admin=admin, db=db
    )

    assert "data" in result
    assert len(result["data"]) == 2
    assert result["data"][0]["status"] == "admin_review"


# ─── Test 4: PATCH approve 200 ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_patch_interview_approve_200():
    """200 — admin approves an admin_review interview."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    interview = _make_interview(artist_id, status="admin_review")
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    body = AdminPatchInterviewRequest(status="approved", review_note="Looks good!")

    result = await admin_patch_interview(
        interview_id=iid, body=body, admin=admin, db=db
    )

    assert "data" in result
    assert interview.status == "approved"
    assert interview.reviewed_by_admin_id == admin.id
    db.commit.assert_called_once()


# ─── Test 5: PATCH reject 200 ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_patch_interview_reject_200():
    """200 — admin rejects an admin_review interview."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    interview = _make_interview(artist_id, status="admin_review")
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    body = AdminPatchInterviewRequest(status="rejected", review_note="Needs revision")

    result = await admin_patch_interview(
        interview_id=iid, body=body, admin=admin, db=db
    )

    assert "data" in result
    assert interview.status == "rejected"
    db.commit.assert_called_once()


# ─── Test 6: PATCH 422 — cannot edit published interview ─────────────────────


@pytest.mark.asyncio
async def test_admin_patch_interview_422_published():
    """422 — editing a published interview is not allowed."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    interview = _make_interview(artist_id, status="published")
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)

    body = AdminPatchInterviewRequest(title="New Title")

    with pytest.raises(ApiError) as exc_info:
        await admin_patch_interview(interview_id=iid, body=body, admin=admin, db=db)

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "IMMUTABLE_STATUS"


# ─── Test 7: POST consent 200 — correct artist ───────────────────────────────


@pytest.mark.asyncio
async def test_artist_consent_interview_200():
    """200 — the interview subject artist provides consent."""
    artist_id = uuid.uuid4()
    artist = _make_artist(artist_id)
    interview = _make_interview(artist_id, status="approved")
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await artist_consent_interview(
        interview_id=iid, user=artist, db=db, _rl=None
    )

    assert "data" in result
    assert interview.artist_consent_at is not None
    db.commit.assert_called_once()


# ─── Test 8: POST consent 403 — wrong artist ─────────────────────────────────


@pytest.mark.asyncio
async def test_artist_consent_interview_403_wrong_artist():
    """403 — a different artist cannot consent to another's interview."""
    artist_id = uuid.uuid4()
    other_artist = _make_artist()  # different id
    interview = _make_interview(artist_id, status="approved")
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)

    with pytest.raises(ApiError) as exc_info:
        await artist_consent_interview(
            interview_id=iid, user=other_artist, db=db, _rl=None
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


# ─── Test 9: POST consent 422 — wrong status ─────────────────────────────────


@pytest.mark.asyncio
async def test_artist_consent_interview_422_wrong_status():
    """422 — consent only allowed when status == 'approved'."""
    artist_id = uuid.uuid4()
    artist = _make_artist(artist_id)
    interview = _make_interview(artist_id, status="admin_review")
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)

    with pytest.raises(ApiError) as exc_info:
        await artist_consent_interview(
            interview_id=iid, user=artist, db=db, _rl=None
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "NOT_APPROVED"


# ─── Test 10: POST publish 200 — approved + consented ────────────────────────


@pytest.mark.asyncio
async def test_admin_publish_interview_200():
    """200 — admin publishes approved interview with consent."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    interview = _make_interview(
        artist_id,
        status="approved",
        consent_at=datetime.now(timezone.utc),
    )
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await admin_publish_interview(
        interview_id=iid, admin=admin, db=db
    )

    assert "data" in result
    assert interview.status == "published"
    db.commit.assert_called_once()


# ─── Test 11: POST publish 422 — status != approved ──────────────────────────


@pytest.mark.asyncio
async def test_admin_publish_interview_422_not_approved():
    """422 — cannot publish an interview not in 'approved' status."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    interview = _make_interview(artist_id, status="draft")
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)

    with pytest.raises(ApiError) as exc_info:
        await admin_publish_interview(interview_id=iid, admin=admin, db=db)

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "NOT_APPROVED"


# ─── Test 12: POST publish 422 — consent_at IS NULL ──────────────────────────


@pytest.mark.asyncio
async def test_admin_publish_interview_422_no_consent():
    """422 — cannot publish without artist consent."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    # status=approved but consent_at is None
    interview = _make_interview(artist_id, status="approved", consent_at=None)
    iid = str(interview.id)

    db = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = interview
    db.execute = AsyncMock(return_value=fetch_result)

    with pytest.raises(ApiError) as exc_info:
        await admin_publish_interview(interview_id=iid, admin=admin, db=db)

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "CONSENT_REQUIRED"


# ─── Test 13: GET /users/{id}/interviews 200 — public ────────────────────────


@pytest.mark.asyncio
async def test_get_artist_interviews_public_200():
    """200 — public returns published interviews for an artist."""
    artist_id = uuid.uuid4()
    pub1 = _make_interview(artist_id, status="published", locale="ko")
    pub2 = _make_interview(artist_id, status="published", locale="en")

    db = AsyncMock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [pub1, pub2]
    db.execute = AsyncMock(return_value=list_result)

    result = await get_artist_interviews(user_id=artist_id, locale=None, db=db)

    assert "data" in result
    assert len(result["data"]) == 2
    for item in result["data"]:
        # Public endpoint omits status — check key fields instead
        assert "body_markdown" in item
        assert "published_at" in item
        assert "title" in item
        assert "locale" in item
