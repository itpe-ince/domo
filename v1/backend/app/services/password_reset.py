"""비밀번호 재설정 이메일 서비스 — Phase 12 C-1.

email_verification.py 패턴 재활용.

- send_password_reset_email(): 재설정 링크를 포함한 이메일 발송
- 토큰 만료: 1시간 (이메일 인증 24시간보다 짧게 — 고위험 작업)
- 5 locale 본문 지원 (ko/en/ja/zh/es)
- 발송 실패 시 graceful (log only, sent=False 반환)
"""
from __future__ import annotations

import logging

from app.services.email.base import EmailMessage
from app.services.email.factory import get_email_provider

log = logging.getLogger(__name__)

# 프론트엔드 기본 URL
_FRONTEND_BASE = "https://domo.art"

# ─── locale별 이메일 본문 ────────────────────────────────────────────────────

_SUBJECTS: dict[str, str] = {
    "ko": "[Domo] 비밀번호를 재설정해주세요",
    "en": "[Domo] Reset your password",
    "ja": "[Domo] パスワードをリセットしてください",
    "zh": "[Domo] 請重設您的密碼",
    "es": "[Domo] Restablece tu contraseña",
}

_HTML_BODIES: dict[str, str] = {
    "ko": """\
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
  <h2 style="color:#1a1a1a;">Domo 비밀번호 재설정</h2>
  <p>안녕하세요, <strong>{display_name}</strong>님!</p>
  <p>비밀번호 재설정을 요청하셨습니다. 아래 버튼을 클릭하여 새 비밀번호를 설정해주세요.</p>
  <p>
    <a href="{reset_url}"
       style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
              border-radius:6px;text-decoration:none;font-weight:bold;">
      비밀번호 재설정하기
    </a>
  </p>
  <p style="color:#666;font-size:12px;">
    이 링크는 <strong>1시간</strong> 동안 유효합니다.<br>
    본인이 요청하지 않은 경우 이 이메일을 무시하셔도 됩니다.
  </p>
</div>""",
    "en": """\
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
  <h2 style="color:#1a1a1a;">Domo Password Reset</h2>
  <p>Hi <strong>{display_name}</strong>,</p>
  <p>You requested to reset your password. Click the button below to set a new password.</p>
  <p>
    <a href="{reset_url}"
       style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
              border-radius:6px;text-decoration:none;font-weight:bold;">
      Reset Password
    </a>
  </p>
  <p style="color:#666;font-size:12px;">
    This link is valid for <strong>1 hour</strong>.<br>
    If you did not request this, please ignore this email.
  </p>
</div>""",
    "ja": """\
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
  <h2 style="color:#1a1a1a;">Domo パスワードリセット</h2>
  <p><strong>{display_name}</strong>さん、こんにちは。</p>
  <p>パスワードのリセットをリクエストしました。以下のボタンをクリックして新しいパスワードを設定してください。</p>
  <p>
    <a href="{reset_url}"
       style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
              border-radius:6px;text-decoration:none;font-weight:bold;">
      パスワードをリセット
    </a>
  </p>
  <p style="color:#666;font-size:12px;">
    このリンクは<strong>1時間</strong>有効です。<br>
    身に覚えがない場合は、このメールを無視してください。
  </p>
</div>""",
    "zh": """\
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
  <h2 style="color:#1a1a1a;">Domo 密碼重設</h2>
  <p>您好，<strong>{display_name}</strong>！</p>
  <p>您申請了重設密碼。請點擊下方按鈕設定新密碼。</p>
  <p>
    <a href="{reset_url}"
       style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
              border-radius:6px;text-decoration:none;font-weight:bold;">
      重設密碼
    </a>
  </p>
  <p style="color:#666;font-size:12px;">
    此連結有效期限為<strong>1小時</strong>。<br>
    若非本人操作，請忽略此郵件。
  </p>
</div>""",
    "es": """\
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
  <h2 style="color:#1a1a1a;">Restablecimiento de contraseña de Domo</h2>
  <p>Hola, <strong>{display_name}</strong>.</p>
  <p>Solicitaste restablecer tu contraseña. Haz clic en el botón para establecer una nueva.</p>
  <p>
    <a href="{reset_url}"
       style="display:inline-block;padding:12px 24px;background:#1a1a1a;color:#fff;
              border-radius:6px;text-decoration:none;font-weight:bold;">
      Restablecer contraseña
    </a>
  </p>
  <p style="color:#666;font-size:12px;">
    Este enlace es válido por <strong>1 hora</strong>.<br>
    Si no lo solicitaste, ignora este correo.
  </p>
</div>""",
}

_TEXT_BODIES: dict[str, str] = {
    "ko": (
        "Domo 비밀번호 재설정\n\n"
        "안녕하세요, {display_name}님!\n\n"
        "다음 링크를 클릭하여 비밀번호를 재설정하세요 (1시간 유효):\n\n"
        "{reset_url}\n\n"
        "본인이 요청하지 않은 경우 이 이메일을 무시하셔도 됩니다."
    ),
    "en": (
        "Domo Password Reset\n\n"
        "Hi {display_name},\n\n"
        "Click the link below to reset your password (valid for 1 hour):\n\n"
        "{reset_url}\n\n"
        "If you did not request this, please ignore this email."
    ),
    "ja": (
        "Domo パスワードリセット\n\n"
        "{display_name}さん、\n\n"
        "以下のリンクをクリックしてパスワードをリセットしてください（1時間有効）:\n\n"
        "{reset_url}\n\n"
        "身に覚えがない場合は無視してください。"
    ),
    "zh": (
        "Domo 密碼重設\n\n"
        "{display_name}，您好！\n\n"
        "請點擊以下連結重設密碼（有效期1小時）:\n\n"
        "{reset_url}\n\n"
        "若非本人操作，請忽略此郵件。"
    ),
    "es": (
        "Restablecimiento de contraseña de Domo\n\n"
        "Hola {display_name},\n\n"
        "Haz clic en el enlace para restablecer tu contraseña (válido 1 hora):\n\n"
        "{reset_url}\n\n"
        "Si no lo solicitaste, ignora este correo."
    ),
}


async def send_password_reset_email(
    *,
    email: str,
    display_name: str,
    token: str,
    language: str = "ko",
    frontend_base_url: str = _FRONTEND_BASE,
) -> dict:
    """비밀번호 재설정 이메일 발송.

    이메일 제공자 미설정(mock) 또는 발송 실패 시 graceful.
    5 locale 지원 (ko/en/ja/zh/es), 미지원 locale은 ko 기본 적용.

    Returns:
        {"sent": True, "provider": "mock"|"resend"|"smtp"}
        {"sent": False, "reason": "..."}
    """
    lang = language if language in _SUBJECTS else "ko"
    reset_url = f"{frontend_base_url}/auth/password-reset/{token}"

    html_body = _HTML_BODIES[lang].format(
        display_name=display_name,
        reset_url=reset_url,
    )
    text_body = _TEXT_BODIES[lang].format(
        display_name=display_name,
        reset_url=reset_url,
    )

    provider = get_email_provider()
    try:
        message_id = await provider.send(
            EmailMessage(
                to=email,
                subject=_SUBJECTS[lang],
                html=html_body,
                text=text_body,
                tags=["password_reset"],
            )
        )
        log.info(
            "password_reset_email_sent | to=%s provider=%s msg_id=%s lang=%s",
            email,
            provider.name,
            message_id,
            lang,
        )
        return {"sent": True, "provider": provider.name}
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "password_reset_email_send_failed | to=%s error=%s",
            email,
            exc,
            exc_info=True,
        )
        return {"sent": False, "reason": str(exc)}
