"""매직링크 인증 이메일 발송 서비스 — Phase 12 C-2.

사용자 가입/로그인용 매직링크 이메일 발송.
기존 magic_link.py(admin 초대용)와 별도 파일로 분리.

- send_magic_link_email(): graceful (발송 실패해도 200 반환)
"""
from __future__ import annotations

import logging

from app.services.email.base import EmailMessage
from app.services.email.factory import get_email_provider

log = logging.getLogger(__name__)


async def send_magic_link_email(email: str, magic_link_url: str) -> dict:
    """매직링크 인증 이메일 발송.

    Args:
        email: 수신 이메일 주소
        magic_link_url: 클릭 시 검증할 전체 URL

    Returns:
        {"sent": True} 또는 {"sent": False, "reason": "..."}

    Note:
        발송 실패 시 ApiError를 raise하지 않고 graceful 처리.
        이메일 존재 여부를 응답에서 노출하지 않기 위해 항상 200 반환.
    """
    html_body = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
  <h2 style="color:#1a1a1a;">Domo 로그인 링크</h2>
  <p>아래 버튼을 클릭하면 비밀번호 없이 로그인할 수 있습니다.</p>
  <p>
    <a href="{magic_link_url}" style="
      display:inline-block;padding:12px 28px;
      background:#1a1a1a;color:#fff;
      border-radius:8px;text-decoration:none;
      font-weight:bold;font-size:15px;">
      이메일로 로그인
    </a>
  </p>
  <p style="color:#666;font-size:13px;">
    이 링크는 <strong>24시간</strong> 동안 유효하며 <strong>1회</strong>만 사용 가능합니다.<br>
    본인이 요청하지 않은 경우 이 이메일을 무시하셔도 됩니다.
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
  <p style="color:#999;font-size:11px;">
    링크가 클릭되지 않는 경우 아래 URL을 브라우저에 붙여넣으세요:<br>
    <span style="color:#555;word-break:break-all;">{magic_link_url}</span>
  </p>
</div>
"""
    text_body = (
        f"Domo 로그인 링크\n\n"
        f"아래 링크를 클릭해 로그인하세요 (24시간 유효, 1회 사용):\n\n"
        f"{magic_link_url}\n\n"
        f"본인이 요청하지 않은 경우 이 이메일을 무시하세요."
    )

    provider = get_email_provider()
    try:
        message_id = await provider.send(
            EmailMessage(
                to=email,
                subject="[Domo] 로그인 링크",
                html=html_body,
                text=text_body,
                tags=["magic_link_auth"],
            )
        )
        log.info(
            "magic_link_auth_sent | to=%s provider=%s msg_id=%s",
            email,
            provider.name,
            message_id,
        )
        return {"sent": True, "provider": provider.name}
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "magic_link_auth_send_failed | to=%s error=%s",
            email,
            exc,
            exc_info=True,
        )
        return {"sent": False, "reason": str(exc)}
