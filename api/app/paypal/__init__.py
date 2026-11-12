"""PayPal package.

Exports :func:`get_provider` which returns the active PayPal provider based on
the ``PAYPAL_MODE`` environment variable:

  - ``PAYPAL_MODE=sandbox``  -> SandboxProvider (real PayPal OAuth + REST API)
  - ``PAYPAL_MODE=mock``     -> MockPayPalProvider  (demo data, no credentials)

Default is ``mock`` so the app is demonstrable without PayPal Developer
credentials. Real PayPal integration is isolated in
:mod:`app.paypal.sandbox_provider` for future activation.
"""

import os
from typing import Optional

from app.paypal.provider import PayPalProvider
from app.paypal.mock import mock_provider

_sandbox_provider: Optional[PayPalProvider] = None


def get_provider() -> PayPalProvider:
    """Return the active PayPal provider based on PAYPAL_MODE.

    Defaults to ``mock`` when PAYPAL_MODE is unset.
    """
    mode = os.environ.get("PAYPAL_MODE", "mock").lower()
    if mode == "sandbox":
        return _get_sandbox_provider()
    return mock_provider


def _get_sandbox_provider() -> PayPalProvider:
    """Lazy-import and return the real SandboxProvider."""
    global _sandbox_provider
    if _sandbox_provider is None:
        from app.paypal.sandbox_provider import SandboxProvider  # noqa: WPS433

        _sandbox_provider = SandboxProvider()
    return _sandbox_provider
