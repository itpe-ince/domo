"""AWS SES email service — C-5 newsletter-digest.

Supports Mock mode when aws_ses_access_key_id is not configured (dev/CI).
Uses aioboto3 for async SES calls (aioboto3>=13.2 is already in pyproject.toml).

Usage:
    from app.services.email_ses import ses_client
    result = await ses_client.send_email(to, subject, html_body)
"""
from __future__ import annotations

import logging
import uuid

log = logging.getLogger(__name__)

# Lazy import aioboto3 — avoids hard failure when the library is present
# but AWS credentials are not configured (Mock mode).
try:
    import aioboto3  # type: ignore[import]
    _AIOBOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover
    _AIOBOTO3_AVAILABLE = False
    log.warning("aioboto3 not installed — SES email will use Mock mode")


class SESClient:
    """Thin async wrapper around AWS SES send_email.

    Mock mode: When aws_ses_access_key_id is empty (or aioboto3 unavailable),
    emails are logged and a mock message_id is returned.  No AWS calls made.
    """

    def __init__(self) -> None:
        self._settings_loaded = False
        self._region: str = "us-east-1"
        self._from_address: str = "noreply@domo.art"
        self._access_key_id: str | None = None
        self._secret_access_key: str | None = None

    def _load_settings(self) -> None:
        if self._settings_loaded:
            return
        from app.core.config import get_settings
        s = get_settings()
        self._region = s.aws_ses_region
        self._from_address = s.aws_ses_from_address
        self._access_key_id = s.aws_ses_access_key_id or None
        self._secret_access_key = s.aws_ses_secret_access_key or None
        self._settings_loaded = True

    @property
    def is_mock(self) -> bool:
        self._load_settings()
        return not self._access_key_id or not _AIOBOTO3_AVAILABLE

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> dict:
        """Send a single email.  Returns dict with message_id and status."""
        self._load_settings()

        if self.is_mock:
            return self._mock_send(to, subject)

        message: dict = {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        }
        if text_body:
            message["Body"]["Text"] = {"Data": text_body, "Charset": "UTF-8"}

        session = aioboto3.Session()
        async with session.client(
            "ses",
            region_name=self._region,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
        ) as client:
            response = await client.send_email(
                Source=self._from_address,
                Destination={"ToAddresses": [to]},
                Message=message,
            )
        return {"message_id": response["MessageId"], "status": "sent"}

    def _mock_send(self, to: str, subject: str) -> dict:
        mock_id = f"mock-{uuid.uuid4().hex[:12]}"
        log.info("SES MOCK send | to=%s subject=%s message_id=%s", to, subject, mock_id)
        return {"message_id": mock_id, "status": "mock"}


# Module-level singleton — lazy settings load on first use
ses_client = SESClient()
