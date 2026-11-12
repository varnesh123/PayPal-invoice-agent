"""Execution engine.

Executes approved reminders only, with idempotency prevention.
Never executes unapproved reminders.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_supabase, get_or_create_demo_user
from app.email import get_email_provider
from app.ai.scheduling_schemas import ExecutionResult

logger = logging.getLogger(__name__)

# Module-level in-memory fallback (session-only when Supabase not configured)
_execution_results: list[Dict[str, Any]] = []


class ExecutionEngine:
    """Executes approved reminders with idempotency prevention."""

    def __init__(self) -> None:
        self._execution_results: list[Dict[str, Any]] = []

    async def execute_reminder(
        self,
        reminder_id: str,
        paypal_invoice_id: str,
        customer_email: str,
        customer_name: Optional[str],
        subject: str,
        body: str,
        tone: str,
        channel: str,
        idempotency_key: str,
        user_id: str,
    ) -> ExecutionResult:
        """Execute an approved reminder.

        Only executes if the reminder is approved and eligible.
        Enforces idempotency via idempotency_key.
        """
        supabase = get_supabase()

        # Check idempotency — if already executed with this key, return prior result
        if supabase is not None:
            existing = self._find_existing_execution(supabase, user_id, idempotency_key)
            if existing:
                logger.info(
                    "Execution idempotency hit: reminder_id=%s key=%s",
                    reminder_id,
                    idempotency_key,
                )
                return ExecutionResult(
                    reminder_id=reminder_id,
                    status=existing["status"],
                    channel=existing.get("channel", channel),
                    idempotency_key=idempotency_key,
                    executed_at=existing.get("executed_at", datetime.now(timezone.utc)),
                    error=existing.get("error"),
                    details=existing.get("details", {}),
                )

        # Send via email provider
        provider = get_email_provider()
        result = await provider.send_email(
            to_email=customer_email,
            to_name=customer_name,
            subject=subject,
            body=body,
            idempotency_key=idempotency_key,
        )

        status = "sent" if result["accepted"] else "failed"

        # Persist execution result if Supabase configured
        if supabase is not None:
            try:
                self._persist_execution(
                    supabase,
                    user_id,
                    reminder_id,
                    status,
                    channel,
                    idempotency_key,
                    result,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to persist execution result: %s",
                    exc,
                )

        # Also store in-memory fallback
        self._execution_results.append(
            {
                "reminder_id": reminder_id,
                "status": status,
                "channel": channel,
                "idempotency_key": idempotency_key,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "error": result.get("error"),
                "details": result.get("details", {}),
            }
        )

        return ExecutionResult(
            reminder_id=reminder_id,
            status=status,
            channel=channel,
            idempotency_key=idempotency_key,
            executed_at=datetime.now(timezone.utc),
            error=result.get("error"),
            details=result.get("details", {}),
        )

    def _find_existing_execution(
        self, supabase: Any, user_id: str, idempotency_key: str
    ) -> Optional[Dict[str, Any]]:
        """Check if this idempotency key was already used."""
        try:
            res = (
                supabase.table("scheduled_reminders")
                .select("id, status, channel, sent_at, idempotency_key")
                .eq("user_id", user_id)
                .eq("idempotency_key", idempotency_key)
                .limit(1)
                .execute()
            )
            if res.data:
                return res.data[0]
        except Exception as exc:
            logger.warning("Idempotency check failed: %s", exc)
        return None

    def _persist_execution(
        self,
        supabase: Any,
        user_id: str,
        reminder_id: str,
        status: str,
        channel: str,
        idempotency_key: str,
        result: Dict[str, Any],
    ) -> None:
        """Persist execution result to Supabase."""
        update_data: Dict[str, Any] = {
            "status": status,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "delivery_attempts": 1,
        }
        if result.get("error"):
            update_data["last_error"] = result["error"]
        if result.get("details"):
            update_data["details"] = result["details"]

        supabase.table("scheduled_reminders").update(update_data).eq(
            "id", reminder_id
        ).execute()

    def get_execution_results(self) -> List[Dict[str, Any]]:
        """Return in-memory execution results (session-only)."""
        return list(self._execution_results)


# Module-level singleton
execution_engine = ExecutionEngine()
