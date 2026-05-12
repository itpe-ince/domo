"""Unit tests — audit_log service (Phase 11 D-2).

테스트 항목:
  1. record_audit 정상 — DB INSERT + action/actor_id/status 확인
  2. IP/UA 자동 추출 (Request mock)
  3. DB 실패 시 graceful — log.warning 발생, main flow 영향 없음
  4. actor=None → actor_role='system', actor_id=NULL
  5. x-forwarded-for 헤더 → ip_address 자동 추출
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audit_log import record_audit


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _make_user(role: str = "user") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _make_db() -> AsyncMock:
    """add / commit 지원하는 DB session mock."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


def _make_request(
    ip: str = "1.2.3.4",
    ua: str = "TestAgent/1.0",
    forwarded_for: str | None = None,
) -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = ip

    headers: dict[str, str] = {"user-agent": ua}
    if forwarded_for:
        headers["x-forwarded-for"] = forwarded_for

    def _get_header(key: str, default=None):
        return headers.get(key, default)

    req.headers = MagicMock()
    req.headers.get = MagicMock(side_effect=_get_header)
    return req


# ──────────────────────────────────────────────────────────────────────────────
# 1. 정상 INSERT
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_audit_normal():
    """DB에 AuditLog 행 INSERT, commit 호출 확인."""
    db = _make_db()
    actor = _make_user("admin")
    target_id = uuid.uuid4()

    captured_rows = []

    def _add_side_effect(row):
        captured_rows.append(row)

    db.add.side_effect = _add_side_effect

    with patch("app.models.audit_log.AuditLog") as MockAuditLog:
        mock_row = MagicMock()
        MockAuditLog.return_value = mock_row

        await record_audit(
            db,
            actor=actor,
            action="admin.create_user",
            target_type="user",
            target_id=target_id,
            metadata={"email": "test@example.com"},
            status="success",
        )

    # AuditLog 생성자 호출 확인
    MockAuditLog.assert_called_once()
    call_kwargs = MockAuditLog.call_args[1]
    assert call_kwargs["action"] == "admin.create_user"
    assert call_kwargs["actor_id"] == actor.id
    assert call_kwargs["actor_role"] == "admin"
    assert call_kwargs["target_type"] == "user"
    assert call_kwargs["target_id"] == target_id
    assert call_kwargs["status"] == "success"

    # add + commit 호출 확인
    db.add.assert_called_once_with(mock_row)
    db.commit.assert_awaited_once()


# ──────────────────────────────────────────────────────────────────────────────
# 2. IP / UA 자동 추출
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_audit_ip_extraction():
    """Request.client.host → ip_address, user-agent → user_agent 추출."""
    db = _make_db()
    actor = _make_user()
    request = _make_request(ip="192.168.0.1", ua="Mozilla/5.0")

    with patch("app.models.audit_log.AuditLog") as MockAuditLog:
        MockAuditLog.return_value = MagicMock()

        await record_audit(
            db,
            actor=actor,
            action="user.login",
            request=request,
        )

    call_kwargs = MockAuditLog.call_args[1]
    assert call_kwargs["ip_address"] == "192.168.0.1"
    assert call_kwargs["user_agent"] == "Mozilla/5.0"


@pytest.mark.asyncio
async def test_record_audit_x_forwarded_for():
    """x-forwarded-for 헤더 있으면 첫 번째 IP 추출."""
    db = _make_db()
    actor = _make_user()
    request = _make_request(
        ip="10.0.0.1",  # 내부 IP (proxy)
        forwarded_for="203.0.113.1, 10.0.0.1",
    )

    with patch("app.models.audit_log.AuditLog") as MockAuditLog:
        MockAuditLog.return_value = MagicMock()

        await record_audit(
            db,
            actor=actor,
            action="user.login",
            request=request,
        )

    call_kwargs = MockAuditLog.call_args[1]
    # x-forwarded-for 첫 번째 IP (원본 클라이언트)
    assert call_kwargs["ip_address"] == "203.0.113.1"


# ──────────────────────────────────────────────────────────────────────────────
# 3. DB 실패 시 graceful
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_audit_graceful_fail():
    """DB commit 실패 시 log.warning 발생, 함수가 정상 반환 (exception 미전파)."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=RuntimeError("DB connection lost"))

    actor = _make_user()

    with patch("app.models.audit_log.AuditLog") as MockAuditLog:
        MockAuditLog.return_value = MagicMock()

        with patch("app.services.audit_log.log") as mock_log:
            # 예외가 전파되지 않아야 함
            await record_audit(
                db,
                actor=actor,
                action="admin.create_user",
            )

            # log.warning 호출 확인
            mock_log.warning.assert_called_once()
            warning_args = mock_log.warning.call_args[0]
            assert "record_audit failed" in warning_args[0]
            assert "admin.create_user" in warning_args[1]


# ──────────────────────────────────────────────────────────────────────────────
# 4. actor=None → system
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_audit_anonymous_actor():
    """actor=None 시 actor_id=NULL, actor_role='system'."""
    db = _make_db()

    with patch("app.models.audit_log.AuditLog") as MockAuditLog:
        MockAuditLog.return_value = MagicMock()

        await record_audit(
            db,
            actor=None,
            action="system.cleanup",
        )

    call_kwargs = MockAuditLog.call_args[1]
    assert call_kwargs["actor_id"] is None
    assert call_kwargs["actor_role"] == "system"


# ──────────────────────────────────────────────────────────────────────────────
# 5. request=None 시 ip/ua None
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_audit_no_request():
    """request=None 시 ip_address=None, user_agent=None."""
    db = _make_db()
    actor = _make_user()

    with patch("app.models.audit_log.AuditLog") as MockAuditLog:
        MockAuditLog.return_value = MagicMock()

        await record_audit(
            db,
            actor=actor,
            action="user.logout",
            request=None,
        )

    call_kwargs = MockAuditLog.call_args[1]
    assert call_kwargs["ip_address"] is None
    assert call_kwargs["user_agent"] is None
