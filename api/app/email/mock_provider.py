"""Mock / Demo email provider.

Deterministic email replacement that requires no SMTP credentials, makes no
external network calls, and never sends real emails. Used for demo and testing.

IMPORTANT: This provider never actually delivers emails. It simulates delivery
and always reports clearly that the email was simulated, never claimed as real.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.email.provider import EmailProvider, EmailProviderError

logger = logging.getLogger(__name__)


class MockEmailProvider(EmailProvider):
    """In-memory mock email provider — no credentials, no network calls."""

    def __init__(self) -> None:
        self._sent_emails: list[Dict[str, Any]] = []

    def is_configured(self) -> bool:
        """Mock provider is always configured — no credentials needed."""
        return True

    async def health(self) -> Dict[str, Any]:
        return {
            "email_mode": "mock",
            "configured": True,
            "provider": "mock",
            "available": True,
        }

    async def send_email(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Simulate sending an email. Never actually sends an email."""
        # Check for idempotency — if this key was already used, return the
        # previous result instead of "sending" again.
        for sent in self._sent_emails:
            if sent["idempotency_key"] == idempotency_key:
                logger.info(
                    "Mock email idempotency hit: key=%s to=%s",
                    idempotency_key,
                    to_email,
                )
                return {
                    "accepted": True,
                    "message_id": sent["message_id"],
                    "error": None,
                    "provider": "mock",
                    "details": {
                        "simulated": True,
                        "duplicate": True,
                        "to_email": to_email,
                        "subject": subject,
                    },
                }

        message_id = f"mock-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:12]}"

        record = {
            "idempotency_key": idempotency_key,
            "message_id": message_id,
            "to_email": to_email,
            "to_name": to_name,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now().isoformat(),
            "simulated": True,
        }
        self._sent_emails.append(record)

        logger.info(
            "Mock email simulated: key=%s to=%s subject=%s",
            idempotency_key,
            to_email,
            subject,
        )

        return {
            "accepted": True,
            "message_id": message_id,
            "error": None,
            "provider": "mock",
            "details": {
                "simulated": True,
                "duplicate": False,
                "to_email": to_email,
                "subject": subject,
            },
        }

    async def send_test_email(self, to_email: str) -> Dict[str, Any]:
        """Simulate sending a test email."""
        return await self.send_email(
            to_email=to_email,
            to_name=None,
            subject="Test Email — Invoice Collection Agent",
            body="This is a test email from the Invoice Collection Agent. "
            "No real email was sent — this is mock/demo mode.",
            idempotency_key=f"test-{to_email}-{hashlib.sha256(to_email.encode()).hexdigest()[:8]}",
        )
