"""Mock email provider — logs to stdout + in-memory inbox for tests."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from app.services.email.base import EmailMessage, EmailProvider

log = logging.getLogger(__name__)

# In-memory inbox for testing — keyed by recipient email
_MOCK_INBOX: dict[str, list[dict]] = {}


class MockEmailProvider(EmailProvider):
    name = "mock"

    async def send(self, message: EmailMessage) -> str:
        message_id = f"mock_{secrets.token_hex(12)}"
        log.info(
            "MockEmailProvider: to=%s subject=%s tags=%s",
            message.to,
            message.subject,
            message.tags,
        )
        # Print to stdout so the Docker log shows full content for demos
        print(
            f"\n=== MOCK EMAIL ===\n"
            f"to: {message.to}\n"
            f"subject: {message.subject}\n"
            f"tags: {message.tags}\n"
            f"--- text ---\n{message.text or '(no text)'}\n"
            f"--- html ---\n{message.html[:300]}...\n"
            f"==================\n",
            flush=True,
        )
        _MOCK_INBOX.setdefault(message.to, []).append(
            {
                "id": message_id,
                "to": message.to,
                "subject": message.subject,
                "html": message.html,
                "text": message.text,
                "tags": message.tags,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return message_id


def get_mock_inbox(email: str) -> list[dict]:
    return _MOCK_INBOX.get(email, [])
