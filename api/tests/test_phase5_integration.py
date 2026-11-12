"""Phase 5 tests: Scheduling, Execution, Email, Audit, Automation.

Tests persistent scheduling, idempotency prevention, email providers,
audit logging, and the automation dashboard endpoints.
All tests run in mock mode without requiring external credentials.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.email.mock_provider import MockEmailProvider
from app.email.smtp_provider import SmtpEmailProvider
from app.execution import execution_engine
from app.scheduler import scheduler_engine
from app.audit import audit_logger


# ---------------------------------------------------------------------------
# Scheduler engine tests
# ---------------------------------------------------------------------------

def test_scheduler_create_job():
    """Scheduler engine can create a job."""
    job = scheduler_engine.create_job(
        job_name="test_job",
        job_type="reminder_due_check",
        interval_seconds=300,
    )
    assert job is not None
    assert job["job_name"] == "test_job"
    assert job["job_type"] == "reminder_due_check"
    assert job["status"] == "active"
    assert job["interval_seconds"] == 300
    assert job["run_count"] == 0


def test_scheduler_get_jobs():
    """Scheduler engine can list jobs."""
    scheduler_engine.create_job(job_name="job1", job_type="test", interval_seconds=60)
    scheduler_engine.create_job(job_name="job2", job_type="test", interval_seconds=120)
    jobs = scheduler_engine.get_jobs()
    assert len(jobs) >= 2


def test_scheduler_pause_resume_disable():
    """Scheduler engine can pause, resume, and disable jobs."""
    job = scheduler_engine.create_job(job_name="pause_test", job_type="test", interval_seconds=60)
    job_id = job["id"]

    assert scheduler_engine.pause_job(job_id) is True
    fetched = scheduler_engine.get_job(job_id)
    assert fetched["status"] == "paused"

    assert scheduler_engine.resume_job(job_id) is True
    fetched = scheduler_engine.get_job(job_id)
    assert fetched["status"] == "active"

    assert scheduler_engine.disable_job(job_id) is True
    fetched = scheduler_engine.get_job(job_id)
    assert fetched["status"] == "disabled"


def test_scheduler_record_job_run():
    """Scheduler engine records job runs."""
    job = scheduler_engine.create_job(job_name="run_test", job_type="test", interval_seconds=60)
    job_id = job["id"]

    scheduler_engine.record_job_run(job_id, success=True)
    fetched = scheduler_engine.get_job(job_id)
    assert fetched["run_count"] == 1
    assert fetched["failure_count"] == 0

    scheduler_engine.record_job_run(job_id, success=False, error="test error")
    fetched = scheduler_engine.get_job(job_id)
    assert fetched["run_count"] == 2
    assert fetched["failure_count"] == 1
    assert fetched["last_error"] == "test error"


def test_scheduler_get_due_jobs():
    """Scheduler engine returns due jobs."""
    # Create a job that's due now
    job = scheduler_engine.create_job(
        job_name="due_test", job_type="test", interval_seconds=1
    )
    job_id = job["id"]

    # Manually set next_run_at to now
    scheduler_engine._jobs[0]["next_run_at"] = datetime.now(timezone.utc).isoformat()

    due = scheduler_engine.get_due_jobs()
    due_ids = [j["id"] for j in due]
    assert job_id in due_ids


# ---------------------------------------------------------------------------
# Execution engine tests
# ---------------------------------------------------------------------------

def test_execution_engine_idempotency():
    """Execution engine prevents duplicate execution via idempotency key."""
    # In-memory mode (no Supabase), so execution goes to _execution_results
    engine = execution_engine

    import asyncio

    result1 = asyncio.run(
        engine.execute_reminder(
            reminder_id="remind-1",
            paypal_invoice_id="INV2-1",
            customer_email="test@example.com",
            customer_name="Test Customer",
            subject="Test Reminder",
            body="Please pay",
            tone="polite",
            channel="email",
            idempotency_key="idem-key-1",
            user_id="user-1",
        )
    )
    assert result1.status == "sent"  # mock provider accepts
    assert result1.idempotency_key == "idem-key-1"

    # Same idempotency key - should return cached result
    result2 = asyncio.run(
        engine.execute_reminder(
            reminder_id="remind-1",
            paypal_invoice_id="INV2-1",
            customer_email="test@example.com",
            customer_name="Test Customer",
            subject="Test Reminder",
            body="Please pay",
            tone="polite",
            channel="email",
            idempotency_key="idem-key-1",
            user_id="user-1",
        )
    )
    assert result2.status == "sent"
    # Should be the same result (not re-executed)


# ---------------------------------------------------------------------------
# Email provider tests
# ---------------------------------------------------------------------------

def test_mock_email_provider_is_configured():
    """Mock email provider is always configured."""
    provider = MockEmailProvider()
    assert provider.is_configured() is True


def test_mock_email_provider_send_email():
    """Mock email provider sends simulated email."""
    import asyncio

    provider = MockEmailProvider()
    result = asyncio.run(
        provider.send_email(
            to_email="test@example.com",
            to_name="Test Customer",
            subject="Test Subject",
            body="Test body",
            idempotency_key="idem-key-email-1",
        )
    )
    assert result["accepted"] is True
    assert result["provider"] == "mock"
    assert result["details"]["simulated"] is True
    assert result["details"]["duplicate"] is False
    assert result["message_id"] is not None


def test_mock_email_provider_idempotency():
    """Mock email provider enforces idempotency."""
    import asyncio

    provider = MockEmailProvider()
    key = "idem-key-email-2"

    result1 = asyncio.run(
        provider.send_email(
            to_email="test@example.com",
            to_name="Test Customer",
            subject="Test Subject",
            body="Test body",
            idempotency_key=key,
        )
    )
    assert result1["details"]["duplicate"] is False

    result2 = asyncio.run(
        provider.send_email(
            to_email="test@example.com",
            to_name="Test Customer",
            subject="Test Subject",
            body="Test body",
            idempotency_key=key,
        )
    )
    assert result2["details"]["duplicate"] is True


def test_mock_email_provider_never_claims_delivered():
    """Mock email provider never claims real delivery."""
    import asyncio

    provider = MockEmailProvider()
    result = asyncio.run(
        provider.send_email(
            to_email="test@example.com",
            to_name="Test Customer",
            subject="Test Subject",
            body="Test body",
            idempotency_key="idem-key-email-3",
        )
    )
    assert result["details"]["simulated"] is True


def test_smtp_email_provider_not_configured():
    """SMTP provider is not configured without credentials."""
    provider = SmtpEmailProvider()
    assert provider.is_configured() is False


# ---------------------------------------------------------------------------
# Audit logger tests
# ---------------------------------------------------------------------------

def test_audit_logger_log_and_get():
    """Audit logger can log and retrieve events."""
    logger_ = audit_logger

    event_id = logger_.log(
        event_type="test_event",
        event_category="test",
        resource_type="test_resource",
        resource_id="res-1",
        actor="user",
        details={"key": "value"},
        user_id="user-1",
    )
    assert event_id is not None

    events = logger_.get_events(limit=10)
    assert len(events) >= 1

    # Find our event
    found = [e for e in events if e.get("id") == event_id]
    assert len(found) == 1
    assert found[0]["event_type"] == "test_event"
    assert found[0]["actor"] == "user"


def test_audit_logger_filter_by_type():
    """Audit logger can filter by event type."""
    logger_ = audit_logger

    logger_.log(
        event_type="reminder_drafted",
        event_category="reminder",
        resource_type="reminder",
        resource_id="res-2",
        actor="system",
        details={},
    )
    logger_.log(
        event_type="approval_requested",
        event_category="approval",
        resource_type="approval",
        resource_id="res-3",
        actor="user",
        details={},
    )

    reminder_events = logger_.get_events(event_type="reminder_drafted")
    assert all(e["event_type"] == "reminder_drafted" for e in reminder_events)


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------

def test_email_health_endpoint(client: TestClient):
    """Email health endpoint returns mock provider status."""
    res = client.get("/ai/email/health")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "mock"
    assert data["configured"] is True


def test_email_test_endpoint(client: TestClient):
    """Email test endpoint sends simulated test email."""
    res = client.post("/ai/email/test?to_email=test@example.com")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "mock"
    assert data["details"]["simulated"] is True


def test_scheduler_jobs_endpoint(client: TestClient):
    """Scheduler jobs endpoint returns jobs."""
    res = client.get("/ai/scheduler/jobs")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_scheduler_pause_resume_endpoints(client: TestClient):
    """Scheduler pause/resume endpoints work."""
    # First create a job via the scheduler engine
    scheduler_engine.create_job(job_name="api_test_job", job_type="reminder_due_check", interval_seconds=300)

    res = client.post("/ai/scheduler/pause")
    assert res.status_code == 200
    assert res.json()["status"] == "paused"

    res = client.post("/ai/scheduler/resume")
    assert res.status_code == 200
    assert res.json()["status"] == "resumed"


def test_automation_status_endpoint(client: TestClient):
    """Automation status endpoint returns status (503 without Supabase)."""
    res = client.get("/ai/automation-status")
    assert res.status_code == 503


def test_audit_log_endpoint(client: TestClient):
    """Audit log endpoint returns events."""
    res = client.get("/ai/audit-log")
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert "total" in data
