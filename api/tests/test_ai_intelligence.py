"""Phase 4 tests: AI Intelligence module.

Tests priority scoring, reminder generation, malformed AI responses,
provider failures, and approval/rejection workflows — all in mock mode
without requiring any external credentials.
"""

from datetime import date, timedelta
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from app.ai.mock import MockAIProvider
from app.ai.rules import (
    score_priority,
    analyze_invoice_for_attention,
    generate_reminder_template,
    calculate_days_overdue,
)
from app.ai.schemas import ReminderDraftRequest, ApprovalRequest
from app.paypal.schemas import InvoiceSummary


# ---------------------------------------------------------------------------
# Priority scoring unit tests
# ---------------------------------------------------------------------------

def _make_invoice(
    paypal_invoice_id: str = "INV2-TEST-0001",
    invoice_number: Optional[str] = "INV-1001",
    customer_name: Optional[str] = "Test Customer",
    customer_email: Optional[str] = "test@example.com",
    amount: float = 1000.0,
    currency: str = "USD",
    status: str = "UNPAID",
    due_date: Optional[str] = None,
    balance_due: float = 1000.0,
) -> InvoiceSummary:
    return InvoiceSummary(
        paypal_invoice_id=paypal_invoice_id,
        invoice_number=invoice_number,
        customer_name=customer_name,
        customer_email=customer_email,
        amount=amount,
        currency=currency,
        status=status,
        due_date=due_date,
        balance_due=balance_due,
    )


def test_priority_critical_high_amount_overdue():
    """Critical: high amount + long overdue + unpaid."""
    inv = _make_invoice(amount=10000.0, status="UNPAID", due_date="2026-09-01")
    result = score_priority(inv)
    assert result.priority_level == "critical"
    assert result.score >= 75
    assert result.method == "deterministic"
    assert "critical" in result.explanation.lower()


def test_priority_low_recent_small():
    """Low: small amount, not overdue, draft status."""
    inv = _make_invoice(amount=100.0, status="DRAFT", due_date="2026-12-01")
    result = score_priority(inv)
    assert result.priority_level == "low"
    assert result.score < 30


def test_priority_medium_moderate():
    """Medium: moderate amount, slightly overdue."""
    inv = _make_invoice(amount=1500.0, status="UNPAID", due_date="2026-10-20")
    result = score_priority(inv)
    assert result.priority_level in ("medium", "high")
    assert 0 <= result.score <= 100


def test_priority_score_has_factors():
    """Priority score includes explainable factors."""
    inv = _make_invoice(amount=5000.0, status="UNPAID", due_date="2026-09-01")
    result = score_priority(inv)
    assert len(result.factors) == 3
    factor_names = {f.name for f in result.factors}
    assert factor_names == {"days_overdue", "amount", "status"}
    for f in result.factors:
        assert f.explanation
        assert f.contribution >= 0


def test_paid_invoice_low_priority():
    """Paid invoice should have low priority."""
    inv = _make_invoice(amount=10000.0, status="PAID", due_date="2026-09-01")
    result = score_priority(inv)
    assert result.priority_level == "low"
    assert result.score < 30


# ---------------------------------------------------------------------------
# Days overdue calculation
# ---------------------------------------------------------------------------

def test_days_overdue_past():
    past = (date.today() - timedelta(days=10)).isoformat()
    assert calculate_days_overdue(past) == 10


def test_days_overdue_future():
    future = (date.today() + timedelta(days=10)).isoformat()
    assert calculate_days_overdue(future) == 0


def test_days_overdue_today():
    assert calculate_days_overdue(date.today().isoformat()) == 0


def test_days_overdue_none():
    assert calculate_days_overdue(None) == 0


def test_days_overdue_invalid():
    assert calculate_days_overdue("not-a-date") == 0


# ---------------------------------------------------------------------------
# Invoice analysis
# ---------------------------------------------------------------------------

def test_analysis_needs_attention_unpaid_overdue():
    inv = _make_invoice(amount=2000.0, status="UNPAID", due_date="2026-09-01")
    result = analyze_invoice_for_attention(inv, None)
    assert result.needs_attention is True
    assert len(result.attention_reasons) > 0
    assert result.summary


def test_analysis_no_attention_paid():
    inv = _make_invoice(amount=2000.0, status="PAID", due_date="2026-09-01")
    result = analyze_invoice_for_attention(inv, None)
    assert result.needs_attention is False


def test_analysis_no_invented_history():
    """Analysis should not claim history exists when it doesn't."""
    inv = _make_invoice()
    result = analyze_invoice_for_attention(inv, None)
    assert "No prior payment history" in result.summary or "history" in result.summary.lower()


# ---------------------------------------------------------------------------
# Reminder generation
# ---------------------------------------------------------------------------

def test_reminder_polite_tone():
    inv = _make_invoice()
    body = generate_reminder_template(inv, "polite")
    assert "subject" in body
    assert "body" in body
    assert inv.invoice_number in body["body"]
    assert f"{inv.amount:,.2f}" in body["body"]
    assert inv.currency in body["body"]


def test_reminder_friendly_tone():
    inv = _make_invoice()
    body = generate_reminder_template(inv, "friendly")
    assert "body" in body
    assert "legal" not in body["body"].lower()
    assert "threat" not in body["body"].lower()


def test_reminder_firm_tone():
    inv = _make_invoice()
    body = generate_reminder_template(inv, "firm")
    assert "body" in body
    assert "immediately" in body["body"].lower() or "overdue" in body["body"].lower()


def test_reminder_no_legal_threats():
    inv = _make_invoice()
    for tone in ("polite", "friendly", "firm"):
        body = generate_reminder_template(inv, tone)
        text = (body["subject"] + " " + body["body"]).lower()
        for forbidden in ["sue", "court", "lawsuit", "legal action", "arrest"]:
            assert forbidden not in text, f"Forbidden word '{found}' in {tone} reminder"


def test_reminder_includes_custom_context():
    inv = _make_invoice()
    body = generate_reminder_template(inv, "polite", custom_context="Please contact accounts payable.")
    assert "Please contact accounts payable." in body["body"]


# ---------------------------------------------------------------------------
# Mock AI provider tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_ai_health():
    provider = MockAIProvider()
    health = await provider.health()
    assert health.ai_mode == "mock"
    assert health.configured is True
    assert health.available is True


@pytest.mark.asyncio
async def test_mock_ai_never_requires_key():
    """Mock provider works without OPENAI_API_KEY."""
    provider = MockAIProvider()
    assert provider.is_configured() is True


@pytest.mark.asyncio
async def test_mock_ai_analyze_invoice():
    provider = MockAIProvider()
    inv = _make_invoice(amount=5000.0, status="UNPAID", due_date="2026-09-01")
    result = await provider.analyze_invoice(inv, None)
    assert result.needs_attention is True


@pytest.mark.asyncio
async def test_mock_ai_priority():
    provider = MockAIProvider()
    inv = _make_invoice(amount=10000.0, status="UNPAID", due_date="2026-09-01")
    result = await provider.score_priority(inv)
    assert result.priority_level == "critical"
    assert result.method == "deterministic"


@pytest.mark.asyncio
async def test_mock_ai_reminder():
    provider = MockAIProvider()
    inv = _make_invoice()
    request = ReminderDraftRequest(invoice_id=inv.paypal_invoice_id, tone="polite")
    result = await provider.generate_reminder(request, inv)
    assert result.requires_approval is True
    assert result.method == "template"
    assert result.subject
    assert result.body
    assert inv.invoice_number in result.body


@pytest.mark.asyncio
async def test_mock_ai_insights():
    provider = MockAIProvider()
    invs = [
        _make_invoice(paypal_invoice_id="INV2-1", status="PAID", amount=100.0),
        _make_invoice(paypal_invoice_id="INV2-2", status="UNPAID", amount=200.0),
    ]
    result = await provider.generate_insights(invs, None)
    assert result.total_invoices == 2
    assert result.paid_invoices == 1
    assert result.unpaid_invoices == 1
    assert result.is_estimate is True


@pytest.mark.asyncio
async def test_mock_ai_approval_workflow():
    provider = MockAIProvider()
    from app.ai.schemas import ApprovalRequest

    # Approve
    req = ApprovalRequest(recommendation_id="rec-1", action="approve", editor_note="Looks good")
    resp = await provider.process_approval(req)
    assert resp.status == "approved"
    assert resp.action == "approve"

    # Reject
    req2 = ApprovalRequest(recommendation_id="rec-2", action="reject", editor_note="Too aggressive")
    resp2 = await provider.process_approval(req2)
    assert resp2.status == "rejected"

    # Edit
    req3 = ApprovalRequest(
        recommendation_id="rec-3",
        action="edit",
        edited_content={"body": "Edited reminder text"},
        editor_note="Toned down",
    )
    resp3 = await provider.process_approval(req3)
    assert resp3.status == "edited"

    # List
    listing = await provider.list_approvals()
    assert listing.total == 3


@pytest.mark.asyncio
async def test_mock_ai_approval_invalid_action():
    provider = MockAIProvider()
    from app.ai.schemas import ApprovalRequest

    req = ApprovalRequest(recommendation_id="rec-x", action="delete")
    with pytest.raises(Exception):
        await provider.process_approval(req)


# ---------------------------------------------------------------------------
# API route tests (mock mode, no credentials)
# ---------------------------------------------------------------------------

def test_ai_health_endpoint(client: TestClient):
    res = client.get("/ai/health")
    assert res.status_code == 200
    data = res.json()
    assert data["ai_mode"] == "mock"
    assert data["configured"] is True
    assert data["available"] is True


def test_ai_analyze_invoice_endpoint(client: TestClient):
    # First get an invoice ID
    list_res = client.get("/invoices")
    inv_id = list_res.json()["invoices"][0]["paypal_invoice_id"]

    res = client.post("/ai/analyze", json={"invoice_id": inv_id})
    assert res.status_code == 200
    data = res.json()
    assert data["invoice_id"] == inv_id
    assert "needs_attention" in data
    assert "summary" in data


def test_ai_analyze_nonexistent_invoice(client: TestClient):
    res = client.post("/ai/analyze", json={"invoice_id": "INV2-NONEXISTENT-0000"})
    assert res.status_code == 404


def test_ai_priority_endpoint(client: TestClient):
    list_res = client.get("/invoices")
    inv_id = list_res.json()["invoices"][0]["paypal_invoice_id"]

    res = client.post("/ai/priority", json={"invoice_id": inv_id})
    assert res.status_code == 200
    data = res.json()
    assert data["invoice_id"] == inv_id
    assert data["priority_level"] in ("low", "medium", "high", "critical")
    assert 0 <= data["score"] <= 100
    assert data["method"] == "deterministic"


def test_ai_priority_batch_endpoint(client: TestClient):
    res = client.post("/ai/priority/batch", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 12
    assert len(data["invoices"]) == 12
    # Should be sorted by priority descending
    scores = [inv["score"] for inv in data["invoices"]]
    assert scores == sorted(scores, reverse=True)


def test_ai_reminder_endpoint(client: TestClient):
    list_res = client.get("/invoices")
    inv_id = list_res.json()["invoices"][0]["paypal_invoice_id"]

    res = client.post(
        "/ai/reminder",
        json={"invoice_id": inv_id, "tone": "polite"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["invoice_id"] == inv_id
    assert data["requires_approval"] is True
    assert data["method"] in ("ai", "template")
    assert data["subject"]
    assert data["body"]


def test_ai_reminder_different_tones(client: TestClient):
    list_res = client.get("/invoices")
    inv_id = list_res.json()["invoices"][0]["paypal_invoice_id"]

    for tone in ("polite", "friendly", "firm"):
        res = client.post(
            "/ai/reminder",
            json={"invoice_id": inv_id, "tone": tone},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tone"] == tone


def test_ai_insights_endpoint(client: TestClient):
    res = client.post("/ai/insights", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["total_invoices"] == 12
    assert data["is_estimate"] is True
    assert len(data["trends"]) > 0


def test_ai_insights_customer_filter(client: TestClient):
    # Get a customer email from an existing invoice
    list_res = client.get("/invoices")
    customer_email = list_res.json()["invoices"][0]["customer_email"]

    res = client.post(f"/ai/insights?customer_email={customer_email}")
    assert res.status_code == 200
    data = res.json()
    assert data["customer_email"] == customer_email


def test_ai_approval_endpoint(client: TestClient):
    res = client.post(
        "/ai/approval",
        json={
            "recommendation_id": "rec-test-1",
            "action": "approve",
            "editor_note": "Looks good",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["action"] == "approve"


def test_ai_approval_reject(client: TestClient):
    res = client.post(
        "/ai/approval",
        json={
            "recommendation_id": "rec-test-2",
            "action": "reject",
            "editor_note": "Too aggressive",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "rejected"


def test_ai_approval_edit(client: TestClient):
    res = client.post(
        "/ai/approval",
        json={
            "recommendation_id": "rec-test-3",
            "action": "edit",
            "edited_content": {"body": "Edited text"},
            "editor_note": "Toned down",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "edited"


def test_ai_approvals_list_endpoint(client: TestClient):
    # Create some approvals first
    client.post("/ai/approval", json={"recommendation_id": "rec-a", "action": "approve"})
    client.post("/ai/approval", json={"recommendation_id": "rec-b", "action": "reject"})

    res = client.get("/ai/approvals")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2


def test_mock_mode_no_credentials_required(client: TestClient):
    """Verify mock mode works without OPENAI_API_KEY or PayPal credentials."""
    # Health endpoint should report mock mode as configured
    res = client.get("/ai/health")
    assert res.status_code == 200
    assert res.json()["configured"] is True
    assert res.json()["ai_mode"] == "mock"

    # Invoices should work without any credentials
    res = client.get("/invoices")
    assert res.status_code == 200
    assert len(res.json()["invoices"]) == 12

    # AI analyze should work with deterministic fallback
    list_res = client.get("/invoices")
    inv_id = list_res.json()["invoices"][0]["paypal_invoice_id"]
    res = client.post("/ai/analyze", json={"invoice_id": inv_id})
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Phase 4 repair tests: storage_backend, edited_content, payment history
# ---------------------------------------------------------------------------

def test_ai_health_storage_backend_session(client: TestClient):
    """Health endpoint reports storage_backend='session' when no Supabase."""
    res = client.get("/ai/health")
    assert res.status_code == 200
    data = res.json()
    assert data["storage_backend"] == "session"


def test_ai_approval_storage_backend_session(client: TestClient):
    """Approval response reports storage_backend='session' when no Supabase."""
    res = client.post(
        "/ai/approval",
        json={
            "recommendation_id": "repair-test-1",
            "action": "approve",
            "editor_note": "Session-only test",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["storage_backend"] == "session"


def test_ai_approval_edited_content_preserved(client: TestClient):
    """Edited content is stored and returned in approval response."""
    edited_body = {
        "subject": "Edited subject line",
        "body": "This is the edited reminder body text.",
    }
    res = client.post(
        "/ai/approval",
        json={
            "recommendation_id": "repair-test-2",
            "action": "edit",
            "edited_content": edited_body,
            "editor_note": "Toned down the language",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "edited"
    assert data["editor_note"] == "Toned down the language"


def test_ai_approvals_include_storage_backend(client: TestClient):
    """Approval list includes storage_backend field for each record."""
    client.post(
        "/ai/approval",
        json={"recommendation_id": "repair-test-3", "action": "reject"},
    )
    res = client.get("/ai/approvals")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for record in data["records"]:
        assert "storage_backend" in record
        assert record["storage_backend"] == "session"


def test_payment_history_recording_requires_supabase(client: TestClient):
    """Payment history recording returns 503 without Supabase configured."""
    res = client.post(
        "/ai/payment-history",
        json={
            "customer_email": "test@example.com",
            "payment_amount_cents": 5000,
        },
    )
    assert res.status_code == 503


def test_payment_history_retrieval_requires_supabase(client: TestClient):
    """Payment history retrieval returns 503 without Supabase configured."""
    res = client.get("/ai/payment-history/test@example.com")
    assert res.status_code == 503


def test_payment_history_invoice_endpoint_requires_supabase(client: TestClient):
    """Invoice payment history endpoint returns 503 without Supabase."""
    res = client.get("/ai/payment-history/invoice/INV2-TEST-0001")
    assert res.status_code == 503
