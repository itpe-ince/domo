"""Generic SMTP email provider — works with Gmail / Workspace / SES SMTP / Mailgun SMTP.

Configuration via env (read by app.core.config.Settings):
    SMTP_HOST           # e.g. smtp.gmail.com
    SMTP_PORT           # e.g. 587 (STARTTLS) or 465 (SMTPS)
    SMTP_USER           # e.g. no-reply@tuzigroup.com
    SMTP_PASSWORD       # App Password (Gmail) or SMTP credential
    SMTP_USE_TLS        # 'true' (default) → STARTTLS on 587
    SMTP_USE_SSL        # 'true' → implicit SSL on 465 (mutually exclusive with TLS)
    EMAIL_FROM_ADDRESS  # falls back to SMTP_USER if not set
    EMAIL_FROM_NAME     # display name (e.g. "Domo")

For Google Workspace / Gmail:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=no-reply@tuzigroup.com
    SMTP_PASSWORD=<16-char App Password — myaccount.google.com/apppasswords>
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
import uuid
from email.message import EmailMessage as MimeMessage

from app.core.config import get_settings
from app.services.email.base import EmailMessage, EmailProvider

log = logging.getLogger(__name__)


class SmtpEmailProvider(EmailProvider):
    name = "smtp"

    def __init__(self):
        settings = get_settings()
        self.host = getattr(settings, "smtp_host", "") or "smtp.gmail.com"
        self.port = int(getattr(settings, "smtp_port", 0) or 587)
        self.user = getattr(settings, "smtp_user", "") or ""
        self.password = getattr(settings, "smtp_password", "") or ""
        self.use_ssl = bool(getattr(settings, "smtp_use_ssl", False))
        self.use_tls = bool(getattr(settings, "smtp_use_tls", True))
        self.from_address = (
            getattr(settings, "email_from_address", "") or self.user
        )
        self.from_name = getattr(settings, "email_from_name", "") or "Domo"

        if not self.host or not self.user or not self.password:
            raise RuntimeError(
                "SMTP not configured. Set SMTP_HOST / SMTP_USER / SMTP_PASSWORD."
            )

    def _build_mime(self, message: EmailMessage) -> MimeMessage:
        msg = MimeMessage()
        msg["From"] = f"{self.from_name} <{self.from_address}>"
        msg["To"] = message.to
        msg["Subject"] = message.subject
        # Tags as custom header (some MTAs preserve, others ignore)
        if message.tags:
            msg["X-Domo-Tags"] = ",".join(message.tags)
        # Plain text fallback first, then HTML
        plain = message.text or _strip_html(message.html)
        msg.set_content(plain)
        msg.add_alternative(message.html, subtype="html")
        return msg

    def _send_sync(self, mime: MimeMessage) -> None:
        """Blocking SMTP send — wrapped in asyncio.to_thread by send()."""
        context = ssl.create_default_context()
        if self.use_ssl:
            with smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=30) as s:
                s.login(self.user, self.password)
                s.send_message(mime)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=30) as s:
                s.ehlo()
                if self.use_tls:
                    s.starttls(context=context)
                    s.ehlo()
                s.login(self.user, self.password)
                s.send_message(mime)

    async def send(self, message: EmailMessage) -> str:
        mime = self._build_mime(message)
        try:
            await asyncio.to_thread(self._send_sync, mime)
        except smtplib.SMTPException as e:
            log.error("SMTP send failed to=%s subject=%s err=%s", message.to, message.subject, e)
            raise
        # SMTP doesn't return a provider message id — synthesize one for logging
        return f"smtp:{uuid.uuid4().hex[:12]}"


def _strip_html(html: str) -> str:
    """Very rough HTML→text fallback when message.text is missing."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()
