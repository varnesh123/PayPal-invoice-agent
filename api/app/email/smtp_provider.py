"""SMTP email provider.

Real SMTP integration using Python's smtplib. Requires SMTP_HOST, SMTP_PORT,
SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL environment variables.

If SMTP credentials are not configured, raises EmailProviderError — the
backend routes are responsible for falling back to mock mode or surfacing
the error to the user.
"""

import hashlib
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

from app.email.provider import EmailProvider, EmailProviderError

logger = logging.getLogger(__name__)


class SmtpEmailProvider(EmailProvider):
    """Real SMTP email provider."""

    def __init__(self) -> None:
        self.smtp_host = os.environ.get("SMTP_HOST")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_username = os.environ.get("SMTP_USERNAME")
        self.smtp_password = os.environ.get("SMTP_PASSWORD")
        self.smtp_from_email = os.environ.get("SMTP_FROM_EMAIL")
        self.smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    def is_configured(self) -> bool:
        """True only when SMTP credentials are configured."""
        return bool(
            self.smtp_host
            and self.smtp_username
            and self.smtp_password
            and self.smtp_from_email
        )

    async def health(self) -> Dict[str, Any]:
        return {
            "email_mode": "smtp",
            "configured": self.is_configured(),
            "provider": "smtp",
            "available": self.is_configured(),
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
        }

    async def send_email(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Send a real email via SMTP."""
        if not self.is_configured():
            raise EmailProviderError(
                "SMTP credentials not configured. Set SMTP_HOST, SMTP_USERNAME, "
                "SMTP_PASSWORD, SMTP_FROM_EMAIL environment variables."
            )

        msg = EmailMessage()
        msg["From"] = self.smtp_from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                if self.smtp_use_tls:
                    server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(
                "SMTP email sent: to=%s subject=%s message_id=%s",
                to_email,
                subject,
                idempotency_key,
            )

            return {
                "accepted": True,
                "message_id": idempotency_key,
                "error": None,
                "provider": "smtp",
                "details": {
                    "simulated": False,
                    "to_email": to_email,
                    "subject": subject,
                    "smtp_host": self.smtp_host,
                },
            }
        except Exception as exc:
            logger.warning("SMTP email failed: to=%s error=%s", to_email, exc)
            return {
                "accepted": False,
                "message_id": None,
                "error": str(exc),
                "provider": "smtp",
                "details": {
                    "simulated": False,
                    "to_email": to_email,
                    "subject": subject,
                    "smtp_host": self.smtp_host,
                },
            }

    async def send_test_email(self, to_email: str) -> Dict[str, Any]:
        """Send a test email via SMTP."""
        return await self.send_email(
            to_email=to_email,
            to_name=None,
            subject="Test Email — Invoice Collection Agent",
            body="This is a test email from the Invoice Collection Agent "
            "sent via SMTP.",
            idempotency_key=f"smtp-test-{to_email}-{hashlib.sha256(to_email.encode()).hexdigest()[:8]}",
        )
