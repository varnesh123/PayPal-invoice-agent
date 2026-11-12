"""Email provider package marker."""

from typing import Optional

from app.email.mock_provider import MockEmailProvider
from app.email.smtp_provider import SmtpEmailProvider
from app.email.provider import EmailProvider

_providers: dict = {}
_email_provider: Optional[EmailProvider] = None


def get_provider() -> EmailProvider:
    """Return the active email provider based on EMAIL_MODE env var.

    Defaults to ``mock`` when EMAIL_MODE is unset — no SMTP credentials
    required, no real emails sent.
    """
    import os

    mode = os.environ.get("EMAIL_MODE", "mock").lower()

    if mode not in _providers:
        if mode == "smtp":
            _providers[mode] = SmtpEmailProvider()
        else:
            _providers[mode] = MockEmailProvider()

    return _providers[mode]


def get_provider_name() -> str:
    """Return the name of the active provider."""
    import os

    return os.environ.get("EMAIL_MODE", "mock").lower()


def get_email_provider() -> EmailProvider:
    """Return a cached email provider instance."""
    global _email_provider
    if _email_provider is None:
        _email_provider = get_provider()
    return _email_provider
