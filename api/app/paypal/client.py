"""PayPal Invoicing API v2 client — direct REST integration via httpx.

Per blueprint §8D, the PayPal Agentic Toolkit is NOT used. Direct REST gives
full control over approval gates, idempotency (PayPal-Request-Id), and debugging.

Essential operations (MVP):
  GET /v2/invoicing/invoices          — list invoices
  GET /v2/invoicing/invoices/{id}     — get invoice details
  POST /v2/invoicing/invoices/{id}/remind — send reminder (Phase 5)

Scopes required:
  read:  https://uri.paypal.com/services/invoicing/invoices/read
  write: https://uri.paypal.com/services/invoicing/invoices/readwrite  (for /remind)
"""

import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.db import get_settings
from app.paypal.auth import PayPalAuthError, get_access_token


class PayPalClientError(Exception):
    """Raised when a PayPal API call returns an error status."""


class PayPalClient:
    """Thin wrapper around PayPal Invoicing API v2."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = (
            settings.paypal_base_url or "https://api-m.sandbox.paypal.com"
        ).rstrip("/")

    def _headers(
        self, extra: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        # Raises PayPalAuthError if credentials are not configured
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._headers(kwargs.pop("headers", None))

        with httpx.Client(timeout=30.0) as client:
            resp = client.request(method, url, headers=headers, **kwargs)

        if resp.status_code >= 400:
            raise PayPalClientError(
                f"PayPal API error: HTTP {resp.status_code} {resp.text}"
            )

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ------------------------------------------------------------------
    # Invoicing API v2 operations
    # ------------------------------------------------------------------

    def list_invoices(
        self,
        page: int = 1,
        page_size: int = 20,
        total_required: bool = True,
    ) -> Dict[str, Any]:
        """GET /v2/invoicing/invoices — list invoices."""
        params: Dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "total_required": "true" if total_required else "false",
        }
        return self._request("GET", "/v2/invoicing/invoices", params=params)

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """GET /v2/invoicing/invoices/{invoice_id} — get invoice details."""
        return self._request("GET", f"/v2/invoicing/invoices/{invoice_id}")

    def send_reminder(
        self,
        invoice_id: str,
        send_to_recipient: bool = True,
        send_to_invoicer: bool = False,
        additional_recipients: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """POST /v2/invoicing/invoices/{invoice_id}/remind — send reminder.

        IMPORTANT: PayPal ignores user-provided subject/note fields — it always
        sends a system-generated reminder email. The AI-composed reminder text can
        only be logged for manual send (see blueprint §8C issue).
        Rate limit: 2 reminders per day per caller.
        """
        body: Dict[str, Any] = {
            "send_to_recipient": send_to_recipient,
            "send_to_invoicer": send_to_invoicer,
        }
        if additional_recipients:
            body["additional_recipients"] = additional_recipients

        # Idempotency header required on POSTs; reuse same UUID on retry
        idempotency_key = str(uuid.uuid4())
        headers = {"PayPal-Request-Id": idempotency_key}
        return self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/remind",
            json=body,
            headers=headers,
        )


# Module-level singleton
paypal_client = PayPalClient()
