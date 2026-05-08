"""이메일 인증 서비스 — Phase 11 D-3.

이메일+비밀번호 가입 후 계정 인증 메일 발송.
magic_link.py 패턴을 재활용하되 User-facing 인증 플로우에 맞게 조정.

- generate_verification_token(): secrets.token_urlsafe(32) (256비트 엔트로피, 43자)
- send_verification_email(): 이메일 미설정 시 graceful (log only)
- 24시간 만료, 5분 cooldown은 호출자(auth.py)에서 관리
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from app.services.email.base import EmailMessage
from app.services.email.factory import get_email_provider

log = logging.getLogger(__name__)

# 인증 링크 유효 시간
_VERIFY_EXPIRE_HOURS = 24

# 재발송 cooldown (분)
RESEND_COOLDOWN_MINUTES = 5

# 프론트엔드 기본 URL
_FRONTEND_BASE = "https://domo.art"


def generate_verification_token() -> str:
    """URL-safe 인증 토큰 생성. 43자 (256비트 엔트로피)."""
    return secrets.token_urlsafe(32)


def verification_expires_at() -> datetime:
    """현재 시각 기준 24시간 후 만료 시각 반환."""
    return datetime.now(timezone.utc) + timedelta(hours=_VERIFY_EXPIRE_HOURS)


async def send_verification_email(
    *,
    email: str,
    display_name: str,
    token: str,
    frontend_base_url: str = _FRONTEND_BASE,
) -> dict:
    """이메일 인증 메일 발송.

    이메일 제공자 미설정(mock) 또는 발송 실패 시 graceful — 회원가입 자체는 정상 처리.

    Returns:
        {"sent": True, "provider": "mock"|"resend"|"smtp"}
        {"sent": False, "reason": "..."}
    """
    verify_url = f"{frontend_base_url}/auth/verify?token={token}"

    html_body = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
  <h2 style="color:#1a1a1a;">Domo 이메일 인증</h2>
  <p>안녕하세요, <strong>{display_name}</strong>님!</p>
  <p>Domo 가입을 완료하려면 아래 버튼을 클릭하여 이메일을 인증해주세요.</p>
  <p>
    <a href="{verify_url}"
       style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
              border-radius:6px;text-decoration:none;font-weight:bold;">
      이메일 인증하기
    </a>
  </p>
  <p style="color:#666;font-size:12px;">
    이 링크는 <strong>24시간</strong> 동안 유효합니다.<br>
    본인이 가입하지 않은 경우 이 이메일을 무시하셔도 됩니다.
  </p>
</div>
"""
    text_body = (
        f"Domo 이메일 인증\n\n"
        f"안녕하세요, {display_name}님!\n\n"
        f"다음 링크를 클릭하여 이메일을 인증해주세요 (24시간 유효):\n\n"
        f"{verify_url}\n\n"
        f"본인이 가입하지 않은 경우 이 이메일을 무시하셔도 됩니다."
    )

    provider = get_email_provider()
    try:
        message_id = await provider.send(
            EmailMessage(
                to=email,
                subject="[Domo] 이메일 인증을 완료해주세요",
                html=html_body,
                text=text_body,
                tags=["email_verification"],
            )
        )
        log.info(
            "verification_email_sent | to=%s provider=%s msg_id=%s",
            email,
            provider.name,
            message_id,
        )
        return {"sent": True, "provider": provider.name}
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "verification_email_send_failed | to=%s error=%s",
            email,
            exc,
            exc_info=True,
        )
        return {"sent": False, "reason": str(exc)}
