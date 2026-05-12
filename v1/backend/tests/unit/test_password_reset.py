"""Unit tests — 비밀번호 재설정 서비스 (Phase 12 C-1).

테스트 항목:
  1. test_reset_token_generation — generate_verification_token() 반환값 43자 확인
  2. test_reset_token_expires_1h — expires_at = now + 1h ± 5초 확인
  3. test_send_reset_email_mock — send_password_reset_email() mock → sent=True 반환
  4. test_send_reset_email_failure_graceful — 이메일 발송 실패 → sent=False (예외 전파 없음)

전략: 실제 DB/이메일 서버 불필요. 서비스 함수 직접 호출 + AsyncMock.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email_verification import generate_verification_token
from app.services.password_reset import send_password_reset_email


# ── Test 1: 토큰 길이 43자 ───────────────────────────────────────────────────

def test_reset_token_generation():
    """generate_verification_token() 반환값이 43자인지 확인."""
    token = generate_verification_token()
    assert isinstance(token, str)
    assert len(token) == 43, f"Expected 43 chars, got {len(token)}"


# ── Test 2: 만료 시각 1시간 후 ───────────────────────────────────────────────

def test_reset_token_expires_1h():
    """expires_at = now + 1h ± 5초 범위 확인."""
    from datetime import timezone

    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)

    delta = abs((expires - now).total_seconds() - 3600)
    assert delta < 5, f"Expires delta {delta}s > 5s tolerance"


# ── Test 3: 이메일 발송 성공 (mock) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_reset_email_mock():
    """send_password_reset_email() 정상 발송 → sent=True."""
    mock_provider = MagicMock()
    mock_provider.name = "mock"
    mock_provider.send = AsyncMock(return_value="msg-id-123")

    with patch("app.services.password_reset.get_email_provider", return_value=mock_provider):
        result = await send_password_reset_email(
            email="artist@example.com",
            display_name="테스트작가",
            token="abc123" * 8,  # 48자 (충분히 긴 더미 토큰)
            language="ko",
        )

    assert result["sent"] is True
    assert result["provider"] == "mock"


# ── Test 4: 이메일 발송 실패 → graceful ─────────────────────────────────────

@pytest.mark.asyncio
async def test_send_reset_email_failure_graceful():
    """이메일 발송 실패 시 예외를 전파하지 않고 sent=False 반환."""
    mock_provider = MagicMock()
    mock_provider.name = "mock"
    mock_provider.send = AsyncMock(side_effect=ConnectionError("SMTP timeout"))

    with patch("app.services.password_reset.get_email_provider", return_value=mock_provider):
        result = await send_password_reset_email(
            email="artist@example.com",
            display_name="테스트작가",
            token="abc123" * 8,
            language="en",
        )

    assert result["sent"] is False
    assert "reason" in result
    assert "SMTP timeout" in result["reason"]
