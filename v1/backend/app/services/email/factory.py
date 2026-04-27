"""Email provider factory.

EMAIL_PROVIDER env var:
- 'mock' (default) → MockEmailProvider (logs + in-memory)
- 'resend' → ResendEmailProvider (requires RESEND_API_KEY)
- 'smtp'   → SmtpEmailProvider (Gmail / Google Workspace / SES SMTP / Mailgun SMTP)
             requires SMTP_HOST / SMTP_USER / SMTP_PASSWORD
"""
from functools import lru_cache

from app.core.config import get_settings
from app.services.email.base import EmailProvider
from app.services.email.mock import MockEmailProvider


@lru_cache
def get_email_provider() -> EmailProvider:
    settings = get_settings()
    provider = getattr(settings, "email_provider", "mock")

    if provider == "resend":
        from app.services.email.resend import ResendEmailProvider

        return ResendEmailProvider()

    if provider == "smtp":
        from app.services.email.smtp import SmtpEmailProvider

        return SmtpEmailProvider()

    return MockEmailProvider()
