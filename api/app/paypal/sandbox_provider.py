"""PayPal Sandbox provider — real PayPal REST integration.

Implements :class:`app.paypal.provider.PayPalProvider` using the existing
client-credentials OAuth flow and Invoicing API v2 endpoints. Isolated here so
that PAYPAL_MODE=sandbox can be activated without touching route logic.

Never used when PAYPAL_MODE=mock (the default for demos).
"""

import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from app.db import get_settings
from app.paypal.provider import PayPalProvider, PayPalProviderError


class PayPalAuthError(Exception):
    """Raised when PayPal OAuth credentials are missing or a token request fails."""


class SandboxProvider(PayPalProvider):
    """Real PayPal Sandbox integration via OAuth 2.0 client-credentials."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client_id = settings.paypal_client_id
        self.client_secret = settings.paypal_client_secret
        self.base_url = (
            settings.paypal_base_url or "https://api-m.sandbox.paypal.com"
        ).rstrip("/")
        self.token_url = f"{self.base_url}/v1/oauth2/token"

        self._token: Optional[str] = None
        self._expires_at: float = 0.0  # epoch seconds
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """True only when real PayPal client credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def _fetch_token(self) -> str:
        """Request a fresh access token from PayPal."""
        if not self.is_configured():
            raise PayPalAuthError(
                "PayPal client credentials not configured. "
                "Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env."
            )

        data = {"grant_type": "client_credentials"}

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                self.token_url,
                data=data,
                auth=(self.client_id, self.client_secret),
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "en_US",
                },
            )

        if resp.status_code != 200:
            raise PayPalAuthError(
                f"PayPal token request failed: HTTP {resp.status_code} {resp.text}"
            )

        payload = resp.json()
        access_token = payload.get("access_token")
        expires_in = float(payload.get("expires_in", 28800))
        if not access_token:
            raise PayPalAuthError(
                f"PayPal token response missing access_token: {payload}"
            )

        # Cache with proactive refresh ~60s before expiry
        self._token = access_token
        self._expires_at = time.time() + expires_in - 60
        return access_token

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if missing or near expiry."""
        with self._lock:
            if self._token is None or time.time() >= self._expires_at:
                return self._fetch_token()
            return self._token

    def clear_token(self) -> None:
        """Clear the cached token so the next call fetches a fresh one."""
        with self._lock:
            self._token = None
            self._expires_at = 0.0

    # ------------------------------------------------------------------
    # PayPalProvider interface
    # ------------------------------------------------------------------

    async def connect(self) -> Dict[str, Any]:
        """Validate PayPal client-credentials by requesting a token."""
        try:
            self.get_access_token()
        except PayPalAuthError as exc:
            return {"connected": False, "message": str(exc)}
        return {
            "connected": True,
            "message": "PayPal OAuth credentials validated.",
        }

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        token = self.get_access_token()
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
            raise PayPalProviderError(
                f"PayPal API error: HTTP {resp.status_code} {resp.text}"
            )

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def list_invoices(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """GET /v2/invoicing/invoices — list invoices."""
        params: Dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "total_required": "true",
        }
        return self._request("GET", "/v2/invoicing/invoices", params=params)

    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """GET /v2/invoicing/invoices/{invoice_id} — get invoice details."""
        return self._request("GET", f"/v2/invoicing/invoices/{invoice_id}")

    async def send_reminder(
        self,
        invoice_id: str,
        send_to_recipient: bool = True,
        send_to_invoicer: bool = False,
        additional_recipients: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """POST /v2/invoicing/invoices/{invoice_id}/remind — send reminder.

        IMPORTANT: PayPal ignores user-provided subject/note fields — it always
        sends a system-generated reminder email. Rate limit: 2 reminders/day.
        """
        import uuid

        body: Dict[str, Any] = {
            "send_to_recipient": send_to_recipient,
            "send_to_invoicer": send_to_invoicer,
        }
        if additional_recipients:
            body["additional_recipients"] = additional_recipients

        idempotency_key = str(uuid.uuid4())
        headers = {"PayPal-Request-Id": idempotency_key}
        return self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/remind",
            json=body,
            headers=headers,
        )


# Module-level singleton (instantiated lazily via get_provider in __init__.py)
sandbox_provider = SandboxProvider()
