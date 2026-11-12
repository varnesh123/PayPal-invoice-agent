"""Email provider base classes.

Defines the abstract interface that both MockEmailProvider and SmtpEmailProvider
must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EmailProviderError(Exception):
    """Raised when an email provider operation fails."""


class EmailProvider(ABC):
    """Abstract email integration provider."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the provider has the credentials/state it needs."""

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Return email service health status."""

    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Send an email.

        Returns a dict with keys:
          - accepted: bool
          - message_id: str | None
          - error: str | None
          - provider: str  # "mock" | "smtp"
          - details: dict
        """

    @abstractmethod
    async def send_test_email(self, to_email: str) -> Dict[str, Any]:
        """Send a test email to verify configuration."""
