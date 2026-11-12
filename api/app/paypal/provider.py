"""PayPal provider abstraction.

Defines the interface that both the real Sandbox provider and the Mock/Demo
provider must implement. The backend routes depend on this interface, not on
a concrete implementation, so PAYPAL_MODE can be switched without touching
route logic.

Providers:
  - SandboxProvider: real PayPal REST API (client-credentials OAuth).
  - MockProvider:   realistic synthetic invoices for demo/testing (no PayPal
                    credentials required, no OAuth tokens minted).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PayPalProviderError(Exception):
    """Raised when a PayPal provider operation fails."""


class PayPalProvider(ABC):
    """Abstract PayPal integration provider."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the provider has the credentials/state it needs."""

    @abstractmethod
    async def connect(self) -> Dict[str, Any]:
        """Validate connection. Returns {connected, message, ...}."""

    @abstractmethod
    async def list_invoices(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """List invoices. Returns PayPal-shaped {items, total}."""

    @abstractmethod
    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get a single invoice by PayPal ID."""

    @abstractmethod
    async def send_reminder(
        self,
        invoice_id: str,
        send_to_recipient: bool = True,
        send_to_invoicer: bool = False,
        additional_recipients: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send a reminder for an invoice."""
