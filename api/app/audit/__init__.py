"""Audit logging module.

Records all system events for compliance and debugging:
- Invoice analysed
- Recommendation generated
- Reminder drafted
- Approval requested / approved / rejected
- Reminder scheduled / sent / failed
- Delivery failed
- Invoice status changed
- Automation paused / resumed
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_supabase, get_or_create_demo_user

logger = logging.getLogger(__name__)

# Module-level in-memory fallback (session-only when Supabase not configured)
_audit_events: list[Dict[str, Any]] = []


class AuditLogger:
    """Logs system events to Supabase audit_log table (or in-memory fallback)."""

    def __init__(self) -> None:
        self._events: list[Dict[str, Any]] = []

    def log(
        self,
        event_type: str,
        event_category: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """Log an event.

        Returns the event ID if persisted, or None if Supabase not configured
        (event is stored in-memory only).
        """
        event_id = f"audit-{hashlib.sha256(f'{event_type}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:12]}"

        record = {
            "id": event_id,
            "user_id": user_id,
            "event_type": event_type,
            "event_category": event_category,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "actor": actor,
            "details": details or {},
            "ip_address": ip_address,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase = get_supabase()
        if supabase is not None:
            try:
                # Need demo_user for user_id if not provided
                if user_id is None:
                    demo_user = get_or_create_demo_user()
                    if demo_user:
                        user_id = demo_user["id"]
                        record["user_id"] = user_id

                supabase.table("audit_log").insert(record).execute()
                logger.debug("Audit event persisted: %s %s", event_type, event_id)
            except Exception as exc:
                logger.warning("Failed to persist audit event: %s", exc)

        # Always store in-memory fallback
        self._events.append(record)
        return event_id

    def get_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return audit events (most recent first).

        Falls back to in-memory if Supabase not configured.
        """
        supabase = get_supabase()
        if supabase is not None:
            try:
                if user_id is None:
                    demo_user = get_or_create_demo_user()
                    if demo_user:
                        user_id = demo_user["id"]

                query = supabase.table("audit_log").select("*")
                if user_id:
                    query = query.eq("user_id", user_id)
                if event_type:
                    query = query.eq("event_type", event_type)
                if event_category:
                    query = query.eq("event_category", event_category)

                res = query.order("created_at", desc=True).limit(limit).execute()
                return res.data or []
            except Exception as exc:
                logger.warning("Failed to fetch audit events: %s", exc)

        # In-memory fallback
        events = list(self._events)
        if user_id:
            events = [e for e in events if e.get("user_id") == user_id]
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        if event_category:
            events = [e for e in events if e.get("event_category") == event_category]
        events.sort(key=lambda e: e.get("created_at", ""), reverse=True)
        return events[:limit]


# Module-level singleton
audit_logger = AuditLogger()
