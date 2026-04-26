"""Payment receipt email template.

Sent to buyer after payment_intent.succeeded webhook.
"""
from __future__ import annotations

from app.services.email.base import EmailMessage


def render(
    *,
    buyer_email: str,
    buyer_name: str,
    order_id: str,
    amount: str,
    currency: str,
    artist_name: str,
    artwork_title: str,
    paid_at: str,
) -> EmailMessage:
    subject = f"[Domo] 결제 완료 — {artwork_title}"
    html = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>결제가 완료되었습니다</h2>
  <p>안녕하세요, <strong>{buyer_name}</strong>님.</p>
  <p>다음 주문의 결제가 완료되었습니다.</p>
  <table style="width:100%; border-collapse:collapse;">
    <tr><td style="padding:8px; border-bottom:1px solid #eee;"><strong>주문 번호</strong></td>
        <td style="padding:8px; border-bottom:1px solid #eee;">{order_id}</td></tr>
    <tr><td style="padding:8px; border-bottom:1px solid #eee;"><strong>작품</strong></td>
        <td style="padding:8px; border-bottom:1px solid #eee;">{artwork_title}</td></tr>
    <tr><td style="padding:8px; border-bottom:1px solid #eee;"><strong>작가</strong></td>
        <td style="padding:8px; border-bottom:1px solid #eee;">{artist_name}</td></tr>
    <tr><td style="padding:8px; border-bottom:1px solid #eee;"><strong>금액</strong></td>
        <td style="padding:8px; border-bottom:1px solid #eee;">{amount} {currency}</td></tr>
    <tr><td style="padding:8px;"><strong>결제 시각</strong></td>
        <td style="padding:8px;">{paid_at}</td></tr>
  </table>
  <p style="margin-top:24px;">작품이 발송되면 별도로 안내해 드립니다.</p>
  <p style="color:#888; font-size:12px;">Domo 고객지원: support@domo.art</p>
</div>
""".strip()
    text = (
        f"결제 완료\n\n"
        f"주문번호: {order_id}\n"
        f"작품: {artwork_title} (by {artist_name})\n"
        f"금액: {amount} {currency}\n"
        f"결제 시각: {paid_at}\n"
    )
    return EmailMessage(
        to=buyer_email,
        subject=subject,
        html=html,
        text=text,
        tags=["payment_receipt"],
    )
