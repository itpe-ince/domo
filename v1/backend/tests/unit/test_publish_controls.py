"""10 unit tests for publish-controls logic — PDCA #8 §B-13.

Pure logic tests: no DB, no async, no network.
Tests cover:
  - _visibility_filter_for_viewer (4 cases)
  - PostPublishRequest.publish_at validator (3 cases)
  - publish_at=None immediate publish (1 case)
  - Pydantic Literal visibility enum (1 case)
  - PostPublishRequest full fields (1 case)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from pydantic import ValidationError

from app.api.posts import _visibility_filter_for_viewer
from app.models.post import Post
from app.schemas.series import PostPublishRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_viewer(*, user_id: uuid.UUID | None = None) -> MagicMock:
    v = MagicMock()
    v.id = user_id or uuid.uuid4()
    return v


# ---------------------------------------------------------------------------
# Test 1 — viewer=None → only 'public' clause
# ---------------------------------------------------------------------------


def test_visibility_filter_public_viewer_none():
    result = _visibility_filter_for_viewer(
        viewer=None,
        author_id_col=MagicMock(),
        viewing_self=False,
    )
    # Should compile to a simple equality expression (Post.visibility == 'public')
    # We verify by checking the string representation contains 'public'
    clause_str = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "public" in clause_str
    # Must NOT mention followers_only
    assert "followers_only" not in clause_str


# ---------------------------------------------------------------------------
# Test 2 — follower path: returns or_() with followers_only branch
# ---------------------------------------------------------------------------


def test_visibility_filter_follower():
    viewer = _make_viewer()
    followee_ids = [uuid.uuid4(), uuid.uuid4()]
    result = _visibility_filter_for_viewer(
        viewer=viewer,
        author_id_col=Post.author_id,
        viewing_self=False,
        followee_ids=followee_ids,
    )
    # or_() expression — should include both visibility values
    clause_str = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "public" in clause_str
    assert "followers_only" in clause_str


# ---------------------------------------------------------------------------
# Test 3 — non-follower (followee_ids=None, viewer set) → subquery path
# ---------------------------------------------------------------------------


def test_visibility_filter_non_follower():
    viewer = _make_viewer()
    result = _visibility_filter_for_viewer(
        viewer=viewer,
        author_id_col=Post.author_id,
        viewing_self=False,
        followee_ids=None,
    )
    # Should return an or_() clause (public OR followers_only via subquery)
    # The result should NOT be sa.true()
    assert not isinstance(result, sa.sql.elements.True_)
    clause_str = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "public" in clause_str
    assert "followers_only" in clause_str


# ---------------------------------------------------------------------------
# Test 4 — viewing_self=True → sa.true() (unrestricted)
# ---------------------------------------------------------------------------


def test_visibility_filter_self():
    viewer = _make_viewer()
    result = _visibility_filter_for_viewer(
        viewer=viewer,
        author_id_col=MagicMock(),
        viewing_self=True,
    )
    assert isinstance(result, sa.sql.elements.True_)


# ---------------------------------------------------------------------------
# Test 5 — publish_at too soon (< now+5min) → ValidationError TOO_SOON
# ---------------------------------------------------------------------------


def test_publish_at_too_soon():
    too_soon = datetime.now(timezone.utc) + timedelta(minutes=3)
    with pytest.raises(ValidationError) as exc_info:
        PostPublishRequest(publish_at=too_soon)
    assert "TOO_SOON" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 6 — publish_at too far (> now+365days) → ValidationError TOO_FAR
# ---------------------------------------------------------------------------


def test_publish_at_too_far():
    too_far = datetime.now(timezone.utc) + timedelta(days=366)
    with pytest.raises(ValidationError) as exc_info:
        PostPublishRequest(publish_at=too_far)
    assert "TOO_FAR" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 7 — publish_at valid (now+10min) → passes Pydantic
# ---------------------------------------------------------------------------


def test_publish_at_valid():
    valid_dt = datetime.now(timezone.utc) + timedelta(minutes=10)
    req = PostPublishRequest(publish_at=valid_dt)
    assert req.publish_at is not None
    assert req.publish_at.tzinfo is not None


# ---------------------------------------------------------------------------
# Test 8 — publish_at=None (immediate publish) → passes
# ---------------------------------------------------------------------------


def test_publish_at_none_immediate():
    req = PostPublishRequest(publish_at=None)
    assert req.publish_at is None
    assert req.visibility == "public"
    assert req.comments_enabled is True
    assert req.series_ids == []


# ---------------------------------------------------------------------------
# Test 9 — Literal visibility enum: valid / invalid
# ---------------------------------------------------------------------------


def test_pydantic_visibility_enum():
    # Valid values
    for vis in ("public", "followers_only", "unlisted"):
        req = PostPublishRequest(visibility=vis)
        assert req.visibility == vis

    # Invalid value → ValidationError
    with pytest.raises(ValidationError):
        PostPublishRequest(visibility="invalid")


# ---------------------------------------------------------------------------
# Test 10 — PostPublishRequest with all fields
# ---------------------------------------------------------------------------


def test_post_publish_request_full():
    sid1 = uuid.uuid4()
    sid2 = uuid.uuid4()
    publish_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    req = PostPublishRequest(
        publish_at=publish_at,
        visibility="followers_only",
        comments_enabled=False,
        series_ids=[sid1, sid2],
    )
    assert req.visibility == "followers_only"
    assert req.comments_enabled is False
    assert len(req.series_ids) == 2
    assert req.series_ids[0] == sid1
    assert req.series_ids[1] == sid2

    # series_ids must be UUID objects (not strings after Pydantic coercion)
    assert isinstance(req.series_ids[0], uuid.UUID)
