"""Resend email provider (placeholder — Phase 4 M5).

Ready to use when EMAIL_PROVIDER=resend + RESEND_API_KEY are set.
Uses the Resend HTTP API directly via httpx (no SDK needed).
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.email.base import EmailMessage, EmailProvider


class ResendEmailProvider(EmailProvider):
    name = "resend"

    def __init__(self):
        settings = get_settings()
        self.api_key = getattr(settings, "resend_api_key", "")
        self.from_address = getattr(
            settings, "email_from", "noreply@domo.tuzigroup.com"
        )
        if not self.api_key:
            raise RuntimeError(
                "ResendEmailProvider requires RESEND_API_KEY. "
                "Set EMAIL_PROVIDER=mock for development."
            )

    async def send(self, message: EmailMessage) -> str:
        payload = {
            "from": self.from_address,
            "to": [message.to],
            "subject": message.subject,
            "html": message.html,
        }
        if message.text:
            payload["text"] = message.text
        if message.tags:
            payload["tags"] = [{"name": t, "value": t} for t in message.tags]

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if r.status_code >= 400:
            raise RuntimeError(f"Resend API error {r.status_code}: {r.text}")
        data = r.json()
        return data.get("id", "unknown")
