"""Auction won email template.

Sent to the winner after auction settlement.
"""
from __future__ import annotations

from app.services.email.base import EmailMessage


def render(
    *,
    winner_email: str,
    winner_name: str,
    auction_id: str,
    artwork_title: str,
    artist_name: str,
    winning_amount: str,
    currency: str,
    payment_deadline: str,
) -> EmailMessage:
    subject = f"[Domo] 경매 낙찰 축하드립니다 — {artwork_title}"
    html = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>경매 낙찰 축하드립니다!</h2>
  <p>안녕하세요, <strong>{winner_name}</strong>님.</p>
  <p>아래 경매에서 최종 낙찰되셨습니다.</p>
  <table style="width:100%; border-collapse:collapse;">
    <tr><td style="padding:8px; border-bottom:1px solid #eee;"><strong>작품</strong></td>
        <td style="padding:8px; border-bottom:1px solid #eee;">{artwork_title}</td></tr>
    <tr><td style="padding:8px; border-bottom:1px solid #eee;"><strong>작가</strong></td>
        <td style="padding:8px; border-bottom:1px solid #eee;">{artist_name}</td></tr>
    <tr><td style="padding:8px; border-bottom:1px solid #eee;"><strong>낙찰가</strong></td>
        <td style="padding:8px; border-bottom:1px solid #eee;">{winning_amount} {currency}</td></tr>
    <tr><td style="padding:8px;"><strong>결제 마감</strong></td>
        <td style="padding:8px;">{payment_deadline}</td></tr>
  </table>
  <p style="margin-top:24px;">
    <a href="https://domo.art/orders" style="display:inline-block; padding:12px 24px;
    background:#A8D76E; color:#1A1410; text-decoration:none;
    border-radius:999px; font-weight:bold;">결제하러 가기</a>
  </p>
  <p style="color:#888; font-size:12px;">
    마감 기한 내 결제하지 않으면 낙찰이 취소될 수 있습니다.
  </p>
</div>
""".strip()
    text = (
        f"경매 낙찰 안내\n\n"
        f"작품: {artwork_title} (by {artist_name})\n"
        f"낙찰가: {winning_amount} {currency}\n"
        f"결제 마감: {payment_deadline}\n"
        f"결제 링크: https://domo.art/orders\n"
    )
    return EmailMessage(
        to=winner_email,
        subject=subject,
        html=html,
        text=text,
        tags=["auction_won"],
    )
