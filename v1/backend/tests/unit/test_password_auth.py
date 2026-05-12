"""Unit tests — 이메일+비밀번호 인증 (Phase 11 D-3).

테스트 항목:
  1. validate_password — 8자 미만 → PASSWORD_TOO_SHORT
  2. validate_password — 2종 조합 → PASSWORD_WEAK
  3. validate_password — 3종 조합 → 통과
  4. validate_password — 72바이트 초과 → PASSWORD_TOO_LONG
  5. bcrypt hash 생성 및 verify 일치
  6. bcrypt 다른 비밀번호 → verify 불일치
  7. generate_verification_token() 길이 확인
  8. verification_expires_at() 24시간 후 확인

전략: auth.api validate_password 직접 호출 + security.py hash/verify + email_verification 서비스.
실제 DB/이메일 서버 불필요.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta

import pytest

from app.api.auth import validate_password
from app.core.errors import ApiError
from app.core.security import hash_password, verify_password
from app.services.email_verification import (
    generate_verification_token,
    verification_expires_at,
)


# ── 1. validate_password — 8자 미만 ──────────────────────────────────────────

def test_validate_password_too_short():
    with pytest.raises(ApiError) as exc_info:
        validate_password("Ab1!")
    assert exc_info.value.code == "PASSWORD_TOO_SHORT"


# ── 2. validate_password — 2종 조합 (약함) ───────────────────────────────────

def test_validate_password_weak_two_classes():
    # 소문자 + 숫자만 (대문자/특수문자 없음)
    with pytest.raises(ApiError) as exc_info:
        validate_password("abcdefg1")
    assert exc_info.value.code == "PASSWORD_WEAK"


# ── 3. validate_password — 3종 조합 → 통과 ──────────────────────────────────

def test_validate_password_valid_three_classes():
    # 소문자 + 대문자 + 숫자 (3종)
    validate_password("Abcdef12")  # 예외 없이 통과해야 함


def test_validate_password_valid_four_classes():
    # 모든 4종
    validate_password("Abcdef1!")


# ── 4. validate_password — 72바이트 초과 ─────────────────────────────────────

def test_validate_password_too_long():
    # bcrypt 72바이트 한도 초과 (ASCII 73자 이상)
    long_pw = "Abcdef1!" * 10  # 80자 = 80바이트
    with pytest.raises(ApiError) as exc_info:
        validate_password(long_pw)
    assert exc_info.value.code == "PASSWORD_TOO_LONG"


# ── 5. bcrypt hash 생성 및 verify 일치 ───────────────────────────────────────

def test_hash_and_verify_match():
    plain = "Secure!Pass9"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


# ── 6. bcrypt 다른 비밀번호 → verify 불일치 ──────────────────────────────────

def test_hash_and_verify_mismatch():
    hashed = hash_password("Correct!Pass9")
    assert verify_password("Wrong!Pass99", hashed) is False


# ── 7. generate_verification_token 길이 ──────────────────────────────────────

def test_generate_verification_token_length():
    token = generate_verification_token()
    # secrets.token_urlsafe(32) → base64url 43자
    assert len(token) == 43
    # URL-safe 문자만 포함 (base64url charset)
    import re
    assert re.match(r"^[A-Za-z0-9_-]+$", token)


def test_generate_verification_token_unique():
    """연속 두 번 호출 시 다른 토큰 생성."""
    t1 = generate_verification_token()
    t2 = generate_verification_token()
    assert t1 != t2


# ── 8. verification_expires_at — 24시간 후 ───────────────────────────────────

def test_verification_expires_at_24h():
    before = datetime.now(timezone.utc)
    expires = verification_expires_at()
    after = datetime.now(timezone.utc)

    # 24시간(±1초 허용)
    assert expires >= before + timedelta(hours=24)
    assert expires <= after + timedelta(hours=24, seconds=1)
