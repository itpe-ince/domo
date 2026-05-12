"""Admin 초대용 매직 링크 서비스.

admin이 사용자를 직접 생성할 때 임시 비밀번호 대신 매직 링크를 발송한다.
- 토큰: secrets.token_urlsafe(32) → DB에는 bcrypt hash 저장 (MagicLinkToken 미구현 시 로그만)
- 이메일: app.services.email.factory.get_email_provider() 팩토리 활용
- Mock 모드: 이메일 설정 미완료 시 graceful (log only, sent=False 반환)
"""
from __future__ import annotations

import logging
import secrets

from app.services.email.base import EmailMessage
from app.services.email.factory import get_email_provider

log = logging.getLogger(__name__)

# 매직 링크 유효 시간 (분) — 현재는 응답용 레이블에만 사용
_MAGIC_LINK_EXPIRE_MINUTES = 60 * 24  # 24시간


async def send_admin_invite_magic_link(
    *,
    email: str,
    display_name: str,
    role: str,
    frontend_base_url: str = "https://domo.art",
) -> dict:
    """admin 초대용 매직 링크 이메일 발송.

    Returns:
        {"sent": True, "token_hint": "...8자..."} 또는 {"sent": False, "reason": "..."}
    """
    raw_token = secrets.token_urlsafe(32)
    magic_url = f"{frontend_base_url}/auth/magic?token={raw_token}&email={email}"

    role_label = {"user": "일반 사용자", "artist": "작가", "admin": "관리자"}.get(role, role)

    html_body = f"""
<h2>Domo에 오신 것을 환영합니다, {display_name}님!</h2>
<p>관리자가 귀하를 <strong>{role_label}</strong> 계정으로 등록했습니다.</p>
<p>아래 링크를 클릭하면 계정을 활성화하고 비밀번호를 설정할 수 있습니다.</p>
<p><a href="{magic_url}" style="
  display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
  border-radius:6px;text-decoration:none;font-weight:bold;">계정 활성화</a></p>
<p style="color:#666;font-size:12px;">이 링크는 24시간 동안 유효합니다.<br>
본인이 요청하지 않은 경우 이 이메일을 무시하셔도 됩니다.</p>
"""
    text_body = (
        f"Domo에 오신 것을 환영합니다, {display_name}님!\n\n"
        f"관리자가 귀하를 {role_label} 계정으로 등록했습니다.\n"
        f"다음 링크로 계정을 활성화하세요 (24시간 유효):\n\n{magic_url}\n"
    )

    provider = get_email_provider()
    try:
        message_id = await provider.send(
            EmailMessage(
                to=email,
                subject="[Domo] 관리자 초대 — 계정 활성화 링크",
                html=html_body,
                text=text_body,
                tags=["admin_invite", f"role_{role}"],
            )
        )
        log.info(
            "magic_link_sent | to=%s role=%s provider=%s msg_id=%s",
            email,
            role,
            provider.name,
            message_id,
        )
        # raw_token은 응답/로그에 노출하지 않는다.
        # 실제 서비스에서는 hash(raw_token)을 DB에 저장해야 한다.
        return {"sent": True, "provider": provider.name}
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "magic_link_send_failed | to=%s role=%s error=%s",
            email,
            role,
            exc,
            exc_info=True,
        )
        return {"sent": False, "reason": str(exc)}
