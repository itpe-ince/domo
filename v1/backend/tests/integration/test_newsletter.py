"""Integration tests for C-5 newsletter-digest.

Endpoints under test:
  POST /admin/newsletter/issues/compose    — auto-compose draft (admin)
  GET  /admin/newsletter/issues            — list issues (admin)
  PATCH /admin/newsletter/issues/{id}      — edit body/status (admin)
  POST /admin/newsletter/issues/{id}/send  — transition draft→sending (admin)
  GET  /me/newsletter/preferences          — get own preferences (user)
  PATCH /me/newsletter/preferences         — opt-in/out + frequency (user)
  GET  /newsletter/unsubscribe?token=...   — 1-click unsubscribe (no auth)

Strategy: direct endpoint function calls with AsyncMock DB + MagicMock User.
Mock mode: aws_ses_access_key_id not set → SES mock send (no real AWS calls).

Test count: 10
  1. POST compose 201 — admin triggers auto-compose (Mock SES mode)
  2. GET issues 200  — admin lists issues with status filter
  3. PATCH issue 200 — admin edits body_markdown
  4. POST send 200   — status transition draft→sending
  5. POST send 422   — cannot send a non-draft issue
  6. GET preferences 200  — default (opt-out) preferences returned
  7. PATCH preferences 200 — opt-in + frequency + locale update
  8. GET unsubscribe 200  — valid token → is_subscribed=False
  9. GET unsubscribe 404  — invalid/unknown token
  10. POST compose 403    — non-admin rejected
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_newsletter import (
    admin_compose_issue,
    admin_list_issues,
    admin_patch_issue,
    admin_send_issue,
)
from app.api.me_newsletter import (
    get_my_newsletter_preferences,
    newsletter_unsubscribe,
    patch_my_newsletter_preferences,
)
from app.core.errors import ApiError
from app.schemas.newsletter import (
    AdminPatchIssueRequest,
    PatchNewsletterPreferencesRequest,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user(uid: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.role = "user"
    u.status = "active"
    u.email = "test@example.com"
    u.deleted_at = None
    return u


def _make_issue(
    status: str = "draft",
    locale: str = "ko",
    admin_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.issue_date = date.today()
    row.subject = f"Domo {date.today().strftime('%Y-%m')} Newsletter"
    row.body_markdown = "## Hello\nTest content."
    row.body_html = "<h2>Hello</h2><p>Test content.</p>"
    row.locale = locale
    row.featured_artist_id = None
    row.new_top_artists = []
    row.new_posts_highlight = []
    row.media_coverage_ids = []
    row.status = status
    row.sent_count = 0
    row.failed_count = 0
    row.sent_at = None
    row.created_by_admin_id = admin_id or uuid.uuid4()
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_prefs(
    user_id: uuid.UUID,
    is_subscribed: bool = False,
    frequency: str = "monthly",
    preferred_locale: str = "ko",
    token: str = "valid-token-abc",
) -> MagicMock:
    row = MagicMock()
    row.user_id = user_id
    row.is_subscribed = is_subscribed
    row.frequency = frequency
    row.preferred_locale = preferred_locale
    row.last_sent_at = None
    row.unsubscribe_token = token
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


# ─── Test 1: POST /admin/newsletter/issues/compose — 201 ─────────────────────


@pytest.mark.asyncio
async def test_admin_compose_issue_201():
    """Admin composes a draft newsletter issue using Mock SES mode."""
    admin = _make_admin()
    issue = _make_issue(status="draft", locale="ko", admin_id=admin.id)

    db = AsyncMock()

    # Patch compose_issue to return our mock issue
    with patch(
        "app.api.admin_newsletter.compose_issue",
        new=AsyncMock(return_value=issue),
    ):
        # db.add, db.commit, db.refresh are async-mock-compatible via AsyncMock
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await admin_compose_issue(
            issue_date=date.today(),
            locale="ko",
            admin=admin,
            db=db,
            _rl=None,
        )

    assert result["data"]["status"] == "draft"
    assert result["data"]["locale"] == "ko"
    db.add.assert_called_once_with(issue)
    db.commit.assert_awaited_once()


# ─── Test 2: GET /admin/newsletter/issues — 200 ───────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_issues_200():
    """Admin lists newsletter issues (no filter)."""
    admin = _make_admin()
    issues = [_make_issue(status="draft"), _make_issue(status="sent")]

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = issues
    db.execute = AsyncMock(return_value=mock_result)

    result = await admin_list_issues(
        status=None,
        locale=None,
        limit=20,
        admin=admin,
        db=db,
        _rl=None,
    )

    assert len(result["data"]) == 2
    assert result["data"][0]["status"] == "draft"


# ─── Test 3: PATCH /admin/newsletter/issues/{id} — 200 ───────────────────────


@pytest.mark.asyncio
async def test_admin_patch_issue_200():
    """Admin edits body_markdown of a draft issue."""
    admin = _make_admin()
    issue = _make_issue(status="draft")

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = issue
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    body = AdminPatchIssueRequest(body_markdown="## Updated\nNew content.")
    result = await admin_patch_issue(
        issue_id=issue.id,
        body=body,
        admin=admin,
        db=db,
        _rl=None,
    )

    assert result["data"]["status"] == "draft"
    db.commit.assert_awaited_once()


# ─── Test 4: POST /admin/newsletter/issues/{id}/send — 200 ───────────────────


@pytest.mark.asyncio
async def test_admin_send_issue_200():
    """Admin transitions a draft issue to sending."""
    admin = _make_admin()
    issue = _make_issue(status="draft")

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = issue
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    # issue.status='draft' initially — function applies UPDATE SQL then refreshes;
    # simulate refresh by mutating status to 'sending' (real DB would refresh from row).
    async def _refresh(obj):
        obj.status = "sending"
    db.refresh = _refresh

    result = await admin_send_issue(
        issue_id=issue.id,
        admin=admin,
        db=db,
        _rl=None,
    )

    assert result["data"]["status"] == "sending"
    db.commit.assert_awaited_once()


# ─── Test 5: POST send 422 — non-draft issue ─────────────────────────────────


@pytest.mark.asyncio
async def test_admin_send_issue_422_not_draft():
    """Sending a non-draft issue raises 422."""
    admin = _make_admin()
    issue = _make_issue(status="sent")

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = issue
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ApiError) as exc_info:
        await admin_send_issue(
            issue_id=issue.id,
            admin=admin,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 422
    assert "draft" in exc_info.value.detail.lower()


# ─── Test 6: GET /me/newsletter/preferences — 200 (existing row) ─────────────


@pytest.mark.asyncio
async def test_get_preferences_200_existing():
    """User fetches preferences — existing opt-out row returned."""
    user = _make_user()
    prefs = _make_prefs(user_id=user.id, is_subscribed=False)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = prefs  # existing row
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_my_newsletter_preferences(
        current_user=user,
        db=db,
        _rl=None,
    )

    assert result["data"]["is_subscribed"] is False
    assert result["data"]["frequency"] == "monthly"


# ─── Test 7: PATCH /me/newsletter/preferences — 200 (opt-in) ─────────────────


@pytest.mark.asyncio
async def test_patch_preferences_opt_in_200():
    """User opts in to newsletter and changes frequency."""
    user = _make_user()
    prefs = _make_prefs(user_id=user.id, is_subscribed=False)
    updated_prefs = _make_prefs(
        user_id=user.id,
        is_subscribed=True,
        frequency="weekly",
        preferred_locale="en",
    )

    db = AsyncMock()

    # First execute (get_or_create): existing row returned
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = prefs
    # Second execute (update): no-op
    # Third execute (re-fetch): return updated prefs
    final_result = MagicMock()
    final_result.scalar_one.return_value = updated_prefs

    call_count = 0

    async def _execute(q, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return existing_result  # get_or_create lookup
        elif call_count == 2:
            return MagicMock()  # UPDATE
        else:
            return final_result  # re-fetch

    db.execute = _execute
    db.commit = AsyncMock()

    body = PatchNewsletterPreferencesRequest(
        is_subscribed=True,
        frequency="weekly",
        preferred_locale="en",
    )
    result = await patch_my_newsletter_preferences(
        body=body,
        current_user=user,
        db=db,
        _rl=None,
    )

    assert result["data"]["is_subscribed"] is True
    assert result["data"]["frequency"] == "weekly"
    assert result["data"]["preferred_locale"] == "en"


# ─── Test 8: GET /newsletter/unsubscribe — 200 (valid token) ─────────────────


@pytest.mark.asyncio
async def test_unsubscribe_valid_token_200():
    """Valid unsubscribe token sets is_subscribed=False and returns 200."""
    user_id = uuid.uuid4()
    prefs = _make_prefs(user_id=user_id, is_subscribed=True, token="valid-tok-xyz")

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = prefs
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    result = await newsletter_unsubscribe(token="valid-tok-xyz", db=db)

    assert result["data"]["unsubscribed"] is True
    assert result["data"]["user_id"] == str(user_id)
    db.commit.assert_awaited_once()


# ─── Test 9: GET /newsletter/unsubscribe — 404 (invalid token) ───────────────


@pytest.mark.asyncio
async def test_unsubscribe_invalid_token_404():
    """Unknown unsubscribe token raises 404."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ApiError) as exc_info:
        await newsletter_unsubscribe(token="bad-token", db=db)

    assert exc_info.value.status_code == 404


# ─── Test 10: POST compose 403 — non-admin ────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_compose_issue_403_non_admin():
    """Non-admin user attempting to compose raises 403.

    require_admin_with_2fa checks user.role first — non-admin raises immediately.
    We call require_admin directly to verify the role gate without needing a DB
    for the 2FA check (role check happens before the DB query).
    """
    from app.core.admin_deps import require_admin

    user = _make_user()

    with pytest.raises(ApiError) as exc_info:
        await require_admin(user=user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"
