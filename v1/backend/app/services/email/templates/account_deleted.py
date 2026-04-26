"""Account deletion confirmation email template.

Sent after a user requests account deletion (POST /me/delete).
"""
from __future__ import annotations

from app.services.email.base import EmailMessage


def render(
    *,
    user_email: str,
    user_name: str,
    deletion_scheduled_for: str,
) -> EmailMessage:
    subject = "[Domo] 계정 삭제 요청이 접수되었습니다"
    html = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>계정 삭제 요청 확인</h2>
  <p>안녕하세요, <strong>{user_name}</strong>님.</p>
  <p>계정 삭제 요청이 접수되었습니다.</p>
  <p>
    계정 및 관련 데이터는 <strong>{deletion_scheduled_for}</strong>에
    영구 삭제됩니다.
  </p>
  <p>삭제 전까지는 아래 링크에서 취소하실 수 있습니다.</p>
  <p>
    <a href="https://domo.art/me/account" style="display:inline-block; padding:12px 24px;
    background:#A8D76E; color:#1A1410; text-decoration:none;
    border-radius:999px; font-weight:bold;">삭제 취소하기</a>
  </p>
  <p style="color:#888; font-size:12px;">
    본인이 요청하지 않은 경우 즉시 비밀번호를 변경하고 고객지원에 문의해주세요.
  </p>
</div>
""".strip()
    text = (
        f"계정 삭제 요청 확인\n\n"
        f"삭제 예정일: {deletion_scheduled_for}\n"
        f"취소하려면: https://domo.art/me/account\n"
    )
    return EmailMessage(
        to=user_email,
        subject=subject,
        html=html,
        text=text,
        tags=["account_deleted"],
    )
