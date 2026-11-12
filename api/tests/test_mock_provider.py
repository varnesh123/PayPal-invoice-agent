"""Tests for the mock PayPal provider."""

import pytest

from app.paypal.mock import MockPayPalProvider, _make_invoice


@pytest.fixture
def provider() -> MockPayPalProvider:
    return MockPayPalProvider()


@pytest.mark.asyncio
async def test_mock_provider_is_configured(provider: MockPayPalProvider) -> None:
    """Mock provider is always configured (no credentials needed)."""
    assert provider.is_configured() is True


@pytest.mark.asyncio
async def test_mock_connect_never_claims_connected(
    provider: MockPayPalProvider,
) -> None:
    """connect() must never return connected=True in mock mode."""
    result = await provider.connect()
    assert result["connected"] is False
    assert "demo" in result["message"].lower() or "mock" in result["message"].lower()


@pytest.mark.asyncio
async def test_mock_list_invoices_returns_items(provider: MockPayPalProvider) -> None:
    """list_invoices returns a page of invoices with total count."""
    data = await provider.list_invoices(page=1, page_size=10)
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) <= 10
    assert data["total"] == 12  # 12 demo invoices


@pytest.mark.asyncio
async def test_mock_list_invoices_pagination(provider: MockPayPalProvider) -> None:
    """Pagination splits the 12 demo invoices correctly."""
    page1 = await provider.list_invoices(page=1, page_size=5)
    page2 = await provider.list_invoices(page=2, page_size=5)
    page3 = await provider.list_invoices(page=3, page_size=5)

    assert len(page1["items"]) == 5
    assert len(page2["items"]) == 5
    assert len(page3["items"]) == 2  # remaining 2

    # No overlap between pages
    ids_1 = {inv["id"] for inv in page1["items"]}
    ids_2 = {inv["id"] for inv in page2["items"]}
    ids_3 = {inv["id"] for inv in page3["items"]}
    assert ids_1.isdisjoint(ids_2)
    assert ids_1.isdisjoint(ids_3)
    assert ids_2.isdisjoint(ids_3)


@pytest.mark.asyncio
async def test_mock_get_invoice_found(provider: MockPayPalProvider) -> None:
    """get_invoice returns the matching invoice by PayPal ID."""
    all_invoices = await provider.list_invoices(page=1, page_size=100)
    first_id = all_invoices["items"][0]["id"]

    inv = await provider.get_invoice(first_id)
    assert inv is not None
    assert inv["id"] == first_id


@pytest.mark.asyncio
async def test_mock_get_invoice_not_found(provider: MockPayPalProvider) -> None:
    """get_invoice returns None for a non-existent ID."""
    inv = await provider.get_invoice("INV2-NONEXISTENT-0000")
    assert inv is None


@pytest.mark.asyncio
async def test_mock_send_reminder_accepted(provider: MockPayPalProvider) -> None:
    """send_reminder returns accepted=True without contacting PayPal."""
    all_invoices = await provider.list_invoices(page=1, page_size=100)
    inv_id = all_invoices["items"][0]["id"]

    result = await provider.send_reminder(inv_id)
    assert result["accepted"] is True
    assert result["demo_mode"] is True
    assert "paypal_request_id" in result


@pytest.mark.asyncio
async def test_mock_send_reminder_not_found(provider: MockPayPalProvider) -> None:
    """send_reminder raises for a non-existent invoice."""
    with pytest.raises(Exception):
        await provider.send_reminder("INV2-NONEXISTENT-0000")


def test_make_invoice_has_required_fields() -> None:
    """Each generated invoice has the fields PayPal API v2 returns."""
    inv = _make_invoice(0)
    assert "id" in inv
    assert "invoice_number" in inv
    assert "status" in inv
    assert "amount" in inv
    assert "balance_due" in inv
    assert "detail" in inv
    assert "due_date" in inv["detail"]
    assert "payer" in inv
    assert "email_address" in inv["payer"]


def test_invoice_statuses_are_valid() -> None:
    """Generated statuses are from the PayPal status enum."""
    valid = {"UNPAID", "PAID", "PARTIALLY_PAID", "SENT", "DRAFT", "CANCELLED"}
    all_invoices = [_make_invoice(i) for i in range(100)]
    for inv in all_invoices:
        assert inv["status"] in valid, f"Invalid status: {inv['status']}"


def test_invoices_have_varied_overdue_periods() -> None:
    """Demo data includes invoices with different due dates (overdue + future)."""
    all_invoices = [_make_invoice(i) for i in range(12)]
    due_dates = [inv["detail"]["due_date"] for inv in all_invoices]
    # Should not all be the same date
    assert len(set(due_dates)) > 1


def test_invoices_have_varied_amounts() -> None:
    """Demo data includes varied amounts."""
    all_invoices = [_make_invoice(i) for i in range(12)]
    amounts = [float(inv["amount"]["value"]) for inv in all_invoices]
    assert min(amounts) > 0
    assert max(amounts) < 20000
    assert len(set(amounts)) > 1  # not all identical
