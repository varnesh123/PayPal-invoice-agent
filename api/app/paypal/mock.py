"""Mock / Demo PayPal provider.

Generates realistic synthetic PayPal invoices for demonstration and testing
without requiring PayPal Developer credentials, OAuth tokens, or network
calls to api-m.sandbox.paypal.com.

IMPORTANT: This provider never mints OAuth tokens, never claims PayPal
authentication succeeded, and never contacts PayPal. It is purely a local
demo data source. Real PayPal integration lives in SandboxProvider.
"""

import random
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.db import get_settings
from app.paypal.provider import PayPalProvider, PayPalProviderError


# Deterministic seed so the demo data is stable across restarts
_random = random.Random(20261112)

# Sample customer pool for realistic demo data
_CUSTOMERS: List[Dict[str, str]] = [
    {"name": "Acme Design Studio", "email": "billing@acmedesign.example"},
    {"name": "Brightside Consulting", "email": "ap@brightside.example"},
    {"name": "Cobalt Technologies", "email": "accounts.payable@cobalt.example"},
    {"name": "Dune & Co.", "email": "finance@dune.example"},
    {"name": "Echo Retail Group", "email": "payables@echo.example"},
    {"name": "Falcon Logistics", "email": "accounting@falcon.example"},
    {"name": "Glimmer Marketing", "email": "billing@glimmer.example"},
    {"name": "Horizon Ventures", "email": "ap@horizon.example"},
]

_STATUS_WEIGHTS: List[tuple[str, int]] = [
    ("UNPAID", 4),
    ("PAID", 3),
    ("PARTIALLY_PAID", 2),
    ("SENT", 2),
    ("DRAFT", 1),
    ("CANCELLED", 1),
]

_CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]

_INVOICE_PREFIXES = ["INV", "INV-2026", "INV-2025"]


def _random_status() -> str:
    total = sum(w for _, w in _STATUS_WEIGHTS)
    pick = _random.randint(1, total)
    running = 0
    for status, weight in _STATUS_WEIGHTS:
        running += weight
        if pick <= running:
            return status
    return "UNPAID"


def _make_invoice(index: int) -> Dict[str, Any]:
    """Build one realistic synthetic PayPal invoice object."""
    customer = _CUSTOMERS[index % len(_CUSTOMERS)]
    status = _random_status()

    # Amount between $50 and $15,000
    amount = round(_random.uniform(50.0, 15000.0), 2)
    currency = _random.choice(_CURRENCIES)

    # Due date: 30% overdue, 30% due soon, 40% future
    days_offset = _random.choice(
        [-45, -30, -21, -14, -7, -3, 0, 3, 7, 14, 30, 60, 90]
    )
    due_date = (date.today() + timedelta(days=days_offset)).isoformat()

    # Balance due: full for UNPAID/SENT, partial for PARTIALLY_PAID, 0 for PAID
    if status == "PAID":
        balance_due = 0.0
    elif status == "PARTIALLY_PAID":
        balance_due = round(amount * _random.uniform(0.1, 0.6), 2)
    else:
        balance_due = amount

    invoice_number = f"{_random.choice(_INVOICE_PREFIXES)}-{1000 + index}"

    return {
        "id": f"INV2-{_random.randint(10000000, 99999999)}-{index:04d}",
        "invoice_number": invoice_number,
        "status": status,
        "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
        "balance_due": {"currency_code": currency, "value": f"{balance_due:.2f}"},
        "detail": {"due_date": due_date},
        "payer": {
            "email_address": customer["email"],
            "name": customer["name"],
        },
        "recipient": {
            "email_address": customer["email"],
            "name": customer["name"],
        },
    }


class MockPayPalProvider(PayPalProvider):
    """In-memory mock provider that generates deterministic demo invoices."""

    def __init__(self) -> None:
        # Generate a stable set of demo invoices once at init
        self._invoices: List[Dict[str, Any]] = [
            _make_invoice(i) for i in range(12)
        ]
        self._sync_count = 0

    def is_configured(self) -> bool:
        """Mock provider is always 'configured' — no credentials needed."""
        return True

    async def connect(self) -> Dict[str, Any]:
        """Demo mode: reports that PayPal is NOT connected (real auth skipped).

        Never returns connected=True — that would falsely claim PayPal OAuth
        succeeded. Instead it reports that the app is running in demo mode.
        """
        return {
            "connected": False,
            "message": "Demo mode: PayPal OAuth not required. Using mock invoice data.",
            "demo_mode": True,
        }

    async def list_invoices(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """Return a page of mock invoices in PayPal-shaped format."""
        start = (page - 1) * page_size
        end = start + page_size
        page_items = self._invoices[start:end]
        return {
            "items": page_items,
            "total": len(self._invoices),
            "page": page,
            "page_size": page_size,
            "demo_mode": True,
        }

    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Return a single mock invoice by PayPal ID, or None."""
        for inv in self._invoices:
            if inv["id"] == invoice_id:
                return inv
        return None

    async def send_reminder(
        self,
        invoice_id: str,
        send_to_recipient: bool = True,
        send_to_invoicer: bool = False,
        additional_recipients: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Mock send_reminder — always accepted, never contacts PayPal."""
        inv = await self.get_invoice(invoice_id)
        if inv is None:
            raise PayPalProviderError(f"Invoice {invoice_id} not found")
        return {
            "accepted": True,
            "message": f"Demo reminder queued for invoice {invoice_id} (no email actually sent).",
            "demo_mode": True,
            "paypal_request_id": f"demo-{_random.randint(100000, 999999)}",
        }

    @property
    def sync_count(self) -> int:
        return self._sync_count

    def increment_sync(self) -> None:
        self._sync_count += 1


# Module-level singleton
mock_provider = MockPayPalProvider()
