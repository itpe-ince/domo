"""Warning issued email template.

Sent to a user when an admin issues a formal warning.
"""
from __future__ import annotations

from app.services.email.base import EmailMessage


def render(
    *,
    user_email: str,
    user_name: str,
    reason: str,
    warning_count: int,
    suspension_threshold: int = 3,
) -> EmailMessage:
    subject = "[Domo] 커뮤니티 규칙 위반 경고 안내"
    remaining = max(0, suspension_threshold - warning_count)
    html = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color:#d94a4a;">커뮤니티 규칙 위반 경고</h2>
  <p>안녕하세요, <strong>{user_name}</strong>님.</p>
  <p>아래 사유로 공식 경고가 발송되었습니다.</p>
  <blockquote style="border-left:4px solid #d94a4a; padding:8px 16px; margin:16px 0; color:#555;">
    {reason}
  </blockquote>
  <p>현재 경고 횟수: <strong>{warning_count}회</strong></p>
  <p>경고 {remaining}회 추가 시 계정이 정지됩니다.</p>
  <p>이의가 있으시면 아래 링크에서 이의를 제기하실 수 있습니다.</p>
  <p>
    <a href="https://domo.art/warnings" style="display:inline-block; padding:12px 24px;
    background:#A8D76E; color:#1A1410; text-decoration:none;
    border-radius:999px; font-weight:bold;">이의 제기하기</a>
  </p>
  <p style="color:#888; font-size:12px;">Domo 운영팀</p>
</div>
""".strip()
    text = (
        f"커뮤니티 규칙 위반 경고\n\n"
        f"사유: {reason}\n"
        f"경고 횟수: {warning_count}회\n"
        f"이의 제기: https://domo.art/warnings\n"
    )
    return EmailMessage(
        to=user_email,
        subject=subject,
        html=html,
        text=text,
        tags=["warning_issued"],
    )
