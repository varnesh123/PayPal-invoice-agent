"""Tests for API routes (mock mode)."""

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    """Health endpoint returns 200 with mock mode."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["paypal_mode"] == "mock"


def test_root(client: TestClient) -> None:
    """Root endpoint returns running status."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "running"
    assert data["paypal_mode"] == "mock"


def test_connect_paypal_mock_mode(client: TestClient) -> None:
    """Connect endpoint in mock mode never returns connected=True."""
    res = client.post("/paypal/connect")
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is False
    assert "demo" in data["message"].lower()


def test_list_invoices_mock(client: TestClient) -> None:
    """Invoices endpoint returns mock data with 12 invoices."""
    res = client.get("/invoices")
    assert res.status_code == 200
    data = res.json()
    assert len(data["invoices"]) == 12
    assert data["total"] == 12


def test_list_invoices_status_filter(client: TestClient) -> None:
    """Status filter returns only matching invoices."""
    # First, get all invoices to find a status that exists
    all_res = client.get("/invoices")
    all_data = all_res.json()
    assert len(all_data["invoices"]) > 0

    first_status = all_data["invoices"][0]["status"]
    filtered_res = client.get(f"/invoices?status={first_status}")
    assert filtered_res.status_code == 200
    filtered_data = filtered_res.json()
    assert len(filtered_data["invoices"]) > 0
    for inv in filtered_data["invoices"]:
        assert inv["status"] == first_status


def test_list_invoices_nonexistent_status(client: TestClient) -> None:
    """Filtering by a status that doesn't exist returns empty list."""
    res = client.get("/invoices?status=NONEXISTENT_STATUS")
    assert res.status_code == 200
    data = res.json()
    assert data["invoices"] == []
    assert data["total"] == 0


def test_get_invoice_mock_found(client: TestClient) -> None:
    """Get single invoice by ID returns the invoice."""
    list_res = client.get("/invoices")
    inv_id = list_res.json()["invoices"][0]["paypal_invoice_id"]

    res = client.get(f"/invoices/{inv_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["paypal_invoice_id"] == inv_id


def test_get_invoice_mock_not_found(client: TestClient) -> None:
    """Get non-existent invoice returns 404."""
    res = client.get("/invoices/INV2-NONEXISTENT-0000")
    assert res.status_code == 404


def test_mock_sync(client: TestClient) -> None:
    """Mock sync endpoint returns synced status without Supabase."""
    res = client.post("/paypal/mock-sync")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "synced"
    assert data["mode"] == "mock"
    assert data["demo_mode"] is True
    assert data["invoices_seen"] == 12


def test_webhooks_not_available_in_mock(client: TestClient) -> None:
    """Webhook endpoint returns 501 in mock mode."""
    res = client.post("/webhooks/paypal")
    assert res.status_code == 501
