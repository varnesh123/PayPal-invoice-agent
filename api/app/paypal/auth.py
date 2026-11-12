"""PayPal OAuth 2.0 client-credentials token cache.

Single-tenant (app-level) authentication for ONE PayPal sandbox business account.

Endpoint: POST https://api-m.sandbox.paypal.com/v1/oauth2/token
Auth:    HTTP Basic (client_id:client_secret) + grant_type=client_credentials
Response: access_token, token_type: Bearer, expires_in (~28,800s / 8hrs), scope
No refresh_token is issued — re-request the token when it expires.
Cache with expires_at; refresh proactively ~60s before expiry; don't fetch per request.

Note: client-credentials is a direct merchant integration. It authenticates the app
itself, not an individual merchant. There is no per-user consent screen and no
per-user access token. Per-user merchant OAuth (Authorization Code grant) is out
of MVP scope and would be a post-hackathon change.
"""

import threading
import time
from typing import Optional

import httpx

from app.db import get_settings


class PayPalAuthError(Exception):
    """Raised when PayPal OAuth credentials are missing or a token request fails."""


class PayPalOAuthClient:
    """Client-credentials OAuth client with token caching and proactive refresh."""

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

    def _is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _fetch_token(self) -> str:
        """Request a fresh access token from PayPal."""
        if not self._is_configured():
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


# Module-level singleton (single-tenant: one app, one sandbox business account)
oauth_client = PayPalOAuthClient()


def get_access_token() -> str:
    """Public accessor: return a valid PayPal access token."""
    return oauth_client.get_access_token()
