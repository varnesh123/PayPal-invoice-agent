"""Persistent scheduler engine.

Manages scheduler job records that survive backend restarts.
Jobs are stored in Supabase scheduler_jobs table (or in-memory fallback).
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.db import get_supabase, get_or_create_demo_user
from app.audit import audit_logger
from app.execution import execution_engine

logger = logging.getLogger(__name__)

# Module-level in-memory fallback
_scheduler_jobs: list[Dict[str, Any]] = []


class SchedulerEngine:
    """Manages persistent scheduler job records."""

    def __init__(self) -> None:
        self._jobs: list[Dict[str, Any]] = []

    def create_job(
        self,
        job_name: str,
        job_type: str,
        interval_seconds: int = 300,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a scheduler job record."""
        supabase = get_supabase()
        if supabase is None:
            # In-memory fallback
            job_id = f"sched-{hashlib.sha256(f'{job_name}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:12]}"
            job = {
                "id": job_id,
                "user_id": user_id,
                "job_name": job_name,
                "job_type": job_type,
                "status": "active",
                "interval_seconds": interval_seconds,
                "run_count": 0,
                "failure_count": 0,
                "next_run_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._jobs.append(job)
            return job

        try:
            if user_id is None:
                demo_user = get_or_create_demo_user()
                if demo_user:
                    user_id = demo_user["id"]

            res = (
                supabase.table("scheduler_jobs")
                .insert(
                    {
                        "user_id": user_id,
                        "job_name": job_name,
                        "job_type": job_type,
                        "status": "active",
                        "interval_seconds": interval_seconds,
                        "run_count": 0,
                        "failure_count": 0,
                        "next_run_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as exc:
            logger.warning("Failed to create scheduler job: %s", exc)
            return None

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Return all scheduler jobs."""
        supabase = get_supabase()
        if supabase is not None:
            try:
                demo_user = get_or_create_demo_user()
                user_id = demo_user["id"] if demo_user else None
                query = supabase.table("scheduler_jobs").select("*")
                if user_id:
                    query = query.eq("user_id", user_id)
                res = query.order("created_at", desc=True).execute()
                return res.data or []
            except Exception as exc:
                logger.warning("Failed to fetch scheduler jobs: %s", exc)
        return list(self._jobs)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return a single scheduler job."""
        supabase = get_supabase()
        if supabase is not None:
            try:
                res = (
                    supabase.table("scheduler_jobs")
                    .select("*")
                    .eq("id", job_id)
                    .limit(1)
                    .execute()
                )
                return res.data[0] if res.data else None
            except Exception as exc:
                logger.warning("Failed to fetch scheduler job: %s", exc)
        for job in self._jobs:
            if job["id"] == job_id:
                return job
        return None

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduler job."""
        return self._update_job_status(job_id, "paused")

    def resume_job(self, job_id: str) -> bool:
        """Resume a scheduler job."""
        return self._update_job_status(job_id, "active")

    def disable_job(self, job_id: str) -> bool:
        """Disable a scheduler job."""
        return self._update_job_status(job_id, "disabled")

    def _update_job_status(self, job_id: str, status: str) -> bool:
        supabase = get_supabase()
        if supabase is not None:
            try:
                supabase.table("scheduler_jobs").update(
                    {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", job_id).execute()
                return True
            except Exception as exc:
                logger.warning("Failed to update job status: %s", exc)
        for job in self._jobs:
            if job["id"] == job_id:
                job["status"] = status
                job["updated_at"] = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def record_job_run(
        self,
        job_id: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record that a job ran (success or failure)."""
        supabase = get_supabase()
        if supabase is not None:
            try:
                job = self.get_job(job_id)
                if job:
                    new_run_count = (job.get("run_count") or 0) + 1
                    new_failure_count = (job.get("failure_count") or 0)
                    if not success:
                        new_failure_count += 1

                    next_run = datetime.now(timezone.utc) + timedelta(
                        seconds=job.get("interval_seconds", 300)
                    )

                    supabase.table("scheduler_jobs").update(
                        {
                            "last_run_at": datetime.now(timezone.utc).isoformat(),
                            "next_run_at": next_run.isoformat(),
                            "run_count": new_run_count,
                            "failure_count": new_failure_count,
                            "last_error": error,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("id", job_id).execute()
            except Exception as exc:
                logger.warning("Failed to record job run: %s", exc)
        else:
            for job in self._jobs:
                if job["id"] == job_id:
                    job["run_count"] = (job.get("run_count") or 0) + 1
                    if not success:
                        job["failure_count"] = (job.get("failure_count") or 0) + 1
                    job["last_error"] = error
                    job["last_run_at"] = datetime.now(timezone.utc).isoformat()
                    job["next_run_at"] = (
                        datetime.now(timezone.utc)
                        + timedelta(seconds=job.get("interval_seconds", 300))
                    ).isoformat()
                    job["updated_at"] = datetime.now(timezone.utc).isoformat()
                    break

    def get_due_jobs(self) -> List[Dict[str, Any]]:
        """Return jobs that are due to run (next_run_at <= now)."""
        supabase = get_supabase()
        if supabase is not None:
            try:
                demo_user = get_or_create_demo_user()
                user_id = demo_user["id"] if demo_user else None
                query = (
                    supabase.table("scheduler_jobs")
                    .select("*")
                    .eq("status", "active")
                    .lte("next_run_at", datetime.now(timezone.utc).isoformat())
                )
                if user_id:
                    query = query.eq("user_id", user_id)
                res = query.execute()
                return res.data or []
            except Exception as exc:
                logger.warning("Failed to fetch due jobs: %s", exc)
        now = datetime.now(timezone.utc)
        return [
            job
            for job in self._jobs
            if job["status"] == "active"
            and job.get("next_run_at")
            and datetime.fromisoformat(job["next_run_at"]) <= now
        ]

    # ------------------------------------------------------------------
    # Smart follow-up logic: process due reminders
    # ---------------------------------------------------------------------------

    def process_due_reminders(self) -> Dict[str, Any]:
        """Process all due scheduled reminders with smart follow-up logic.

        Checks each scheduled reminder for eligibility before execution:
        - Invoice must not be PAID or CANCELLED (stop follow-up on payment)
        - Reminder must not exceed max_attempts (avoid duplicate reminders)
        - Reminder must be in 'scheduled' status (approved but not yet sent)
        - Idempotency is enforced by execution_engine

        Returns a summary of processed reminders.
        """
        if get_supabase() is None:
            logger.warning("Scheduler cannot process reminders without Supabase")
            return {
                "processed": 0,
                "sent": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "Supabase not configured",
            }

        demo_user = get_or_create_demo_user()
        if demo_user is None:
            return {
                "processed": 0,
                "sent": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "Cannot create demo user",
            }

        user_id = demo_user["id"]
        now = datetime.now(timezone.utc)

        # Get all scheduled reminders that are due
        res = (
            supabase.table("scheduled_reminders")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "scheduled")
            .lte("scheduled_for", now.isoformat())
            .execute()
        )
        reminders = res.data or []

        processed = 0
        sent = 0
        failed = 0
        skipped = 0
        details: list[Dict[str, Any]] = []

        for reminder in reminders:
            reminder_id = reminder["id"]
            paypal_invoice_id = reminder.get("paypal_invoice_id", "")
            customer_email = reminder.get("customer_email", "")

            # Check 1: Is the invoice still eligible?
            # If invoice is PAID or CANCELLED, stop follow-up
            invoice_eligible = True
            skip_reason = ""
            if reminder.get("invoice_id"):
                inv_res = (
                    supabase.table("invoices")
                    .select("status, paypal_invoice_id")
                    .eq("id", reminder["invoice_id"])
                    .limit(1)
                    .execute()
                )
                if inv_res.data:
                    inv_status = inv_res.data[0].get("status", "")
                    if inv_status in ("PAID", "CANCELLED"):
                        invoice_eligible = False
                        skip_reason = f"Invoice {inv_status}"

            # Check 2: Has the reminder exceeded max attempts?
            attempts = reminder.get("delivery_attempts", 0)
            max_attempts = reminder.get("max_attempts", 3)
            if attempts >= max_attempts:
                invoice_eligible = False
                skip_reason = f"Max attempts ({max_attempts}) reached"

            # Check 3: Is there already a sent record for this idempotency key?
            # (Handled by execution_engine, but we can pre-check)
            if reminder.get("status") != "scheduled":
                invoice_eligible = False
                skip_reason = f"Already {reminder.get('status')}"

            if not invoice_eligible:
                # Skip - mark as skipped
                supabase.table("scheduled_reminders").update(
                    {
                        "status": "skipped",
                        "updated_at": now.isoformat(),
                        "last_error": skip_reason,
                    }
                ).eq("id", reminder_id).execute()

                audit_logger.log(
                    event_type="reminder_skipped",
                    event_category="reminder",
                    resource_type="scheduled_reminder",
                    resource_id=reminder_id,
                    actor="scheduler",
                    details={"reason": skip_reason, "invoice_id": reminder.get("invoice_id")},
                    user_id=user_id,
                )
                skipped += 1
                details.append(
                    {
                        "reminder_id": reminder_id,
                        "action": "skipped",
                        "reason": skip_reason,
                    }
                )
                continue

            # Check 4: Execute the reminder via execution engine
            try:
                result = execution_engine.execute_reminder(
                    reminder_id=reminder_id,
                    paypal_invoice_id=paypal_invoice_id,
                    customer_email=customer_email,
                    customer_name=reminder.get("customer_name"),
                    subject=reminder["subject"],
                    body=reminder["body"],
                    tone=reminder["tone"],
                    channel=reminder["channel"],
                    idempotency_key=reminder["idempotency_key"],
                    user_id=user_id,
                )

                processed += 1

                if result.status == "sent":
                    sent += 1
                    details.append(
                        {
                            "reminder_id": reminder_id,
                            "action": "sent",
                            "message_id": result.idempotency_key,
                        }
                    )
                else:
                    failed += 1
                    details.append(
                        {
                            "reminder_id": reminder_id,
                            "action": "failed",
                            "error": result.error,
                        }
                    )

                audit_logger.log(
                    event_type="reminder_sent" if result.status == "sent" else "reminder_failed",
                    event_category="reminder",
                    resource_type="scheduled_reminder",
                    resource_id=reminder_id,
                    actor="scheduler",
                    details={
                        "status": result.status,
                        "channel": result.channel,
                        "idempotency_key": result.idempotency_key,
                        "error": result.error,
                    },
                    user_id=user_id,
                )

            except Exception as exc:
                failed += 1
                logger.warning("Failed to execute reminder %s: %s", reminder_id, exc)
                details.append(
                    {
                        "reminder_id": reminder_id,
                        "action": "failed",
                        "error": str(exc),
                    }
                )

        return {
            "processed": processed,
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "details": details,
        }


# Module-level singleton
scheduler_engine = SchedulerEngine()

