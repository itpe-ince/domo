"""Admin login from new device alert.

Sent when an admin successfully logs in from a (user_agent, IP)
combination not seen on any of their previous active sessions.
"""
from __future__ import annotations

from datetime import datetime

from app.services.email.base import EmailMessage


def render(
    *,
    admin_email: str,
    admin_name: str,
    user_agent: str | None,
    ip_address: str | None,
    when: datetime,
    auth_method: str = "totp",
    sessions_url: str = "https://admin.domo.art/settings/sessions",
) -> EmailMessage:
    subject = "[Domo Admin] 새 디바이스에서 관리자 로그인이 감지되었습니다"
    method_label = "복구 코드" if auth_method == "recovery_code" else "Authenticator (TOTP)"
    safe_ua = (user_agent or "(알 수 없음)").replace("<", "&lt;").replace(">", "&gt;")
    safe_ip = ip_address or "(알 수 없음)"
    when_str = when.strftime("%Y-%m-%d %H:%M:%S UTC")
    html = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <div style="background:#0B1220; padding:20px; border-radius:8px;">
    <h2 style="color:#6366F1; margin:0 0 8px 0;">🛡️ 새 디바이스 로그인</h2>
    <p style="color:#E5EDF7; margin:0;">관리자 콘솔에 새 위치에서 로그인이 감지되었습니다.</p>
  </div>

  <table style="width:100%; margin-top:16px; border-collapse:collapse;">
    <tr>
      <td style="padding:8px; color:#6B7A95; width:120px;">계정</td>
      <td style="padding:8px; color:#1f2937;"><strong>{admin_name}</strong> &lt;{admin_email}&gt;</td>
    </tr>
    <tr>
      <td style="padding:8px; color:#6B7A95;">시각 (UTC)</td>
      <td style="padding:8px; color:#1f2937; font-family:monospace;">{when_str}</td>
    </tr>
    <tr>
      <td style="padding:8px; color:#6B7A95;">IP</td>
      <td style="padding:8px; color:#1f2937; font-family:monospace;">{safe_ip}</td>
    </tr>
    <tr>
      <td style="padding:8px; color:#6B7A95;">디바이스 / 브라우저</td>
      <td style="padding:8px; color:#1f2937; font-size:12px; word-break:break-all;">{safe_ua}</td>
    </tr>
    <tr>
      <td style="padding:8px; color:#6B7A95;">2차 인증 방식</td>
      <td style="padding:8px; color:#1f2937;">{method_label}</td>
    </tr>
  </table>

  <div style="margin-top:24px; padding:16px; background:#FEF3C7; border-left:4px solid #F59E0B; border-radius:4px;">
    <strong>본인이 한 로그인이 아니라면</strong> 즉시:
    <ol style="margin:8px 0 0 0; padding-left:20px;">
      <li>비밀번호를 변경하세요.</li>
      <li>모든 활성 세션을 종료하세요. (
        <a href="{sessions_url}" style="color:#6366F1;">세션 관리</a>
      )</li>
      <li>TOTP를 재설정하세요.</li>
    </ol>
  </div>

  <p style="color:#888; font-size:12px; margin-top:24px;">
    이 알림은 알려진 (디바이스, IP) 조합이 아닐 때마다 자동 발송됩니다.<br/>
    Domo 운영팀
  </p>
</div>
""".strip()
    text = (
        f"새 디바이스에서 관리자 로그인\n\n"
        f"계정: {admin_name} <{admin_email}>\n"
        f"시각: {when_str}\n"
        f"IP: {safe_ip}\n"
        f"디바이스: {user_agent or '(알 수 없음)'}\n"
        f"2차 인증: {method_label}\n\n"
        f"본인이 아니라면 즉시 비밀번호 변경 + 세션 종료 + TOTP 재설정:\n"
        f"{sessions_url}\n"
    )
    return EmailMessage(
        to=admin_email,
        subject=subject,
        html=html,
        text=text,
        tags=["admin_login_alert"],
    )
