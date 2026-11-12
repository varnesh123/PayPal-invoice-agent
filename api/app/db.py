"""Supabase / PostgreSQL database client.

Phase 1: wires the backend to Supabase using environment variables.
The client is created lazily so the health endpoint can respond without
a live database connection (important while Supabase is not yet provisioned).

Phase 2/3 additions:
- PayPal settings fields (incl. PAYPAL_MODE for mock/sandbox).
- Demo user helper so mock data can be associated with a user row.
- upsert_customers_and_invoices now includes user_id (fixes NOT NULL violation).
- get_invoices supports optional status filtering.
- All helpers degrade gracefully when Supabase is not configured.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from supabase import create_client, Client
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values are read from a `.env` file (not committed) or the shell
    environment. See `.env.example` for the full list of variables.
    """

    app_name: str = "invoice-collection-agent"
    app_env: str = "development"
    debug: bool = True

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    secret_key: str = "change-me-in-production"

    database_url: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_anon_key: Optional[str] = None

    # --- PayPal (single-tenant client-credentials or mock) ---------------
    paypal_mode: str = "mock"  # "mock" or "sandbox"
    paypal_client_id: Optional[str] = None
    paypal_client_secret: Optional[str] = None
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    paypal_webhook_id: Optional[str] = None

    # --- Demo user email (used when seeding mock data without auth) ------
    demo_user_email: str = "demo@invoice-collection-agent.example"

    # --- Scheduler settings (Phase 5) -------------------------------------
    scheduler_interval_seconds: int = 300  # 5 minutes default
    scheduler_job_type: str = "reminder_due_check"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def get_supabase() -> Optional[Client]:
    """Return a Supabase client, or None if credentials are not configured.

    Returning None (rather than raising) keeps the health endpoint and the
    rest of the app importable before Supabase has been provisioned.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_database_url() -> Optional[str]:
    return get_settings().database_url


# ---------------------------------------------------------------------------
# Demo user helper
# ---------------------------------------------------------------------------

def get_or_create_demo_user() -> Optional[Dict[str, Any]]:
    """Return a single demo user row, creating it if it does not exist.

    Used by mock mode so synthetic invoice data can be associated with a
    user row (all tables require user_id NOT NULL). Returns None if
    Supabase is not configured.
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    settings = get_settings()
    email = settings.demo_user_email

    # Try to find existing demo user
    res = (
        supabase.table("users")
        .select("*")
        .eq("email", email)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]

    # Create it
    res = (
        supabase.table("users")
        .insert({"email": email, "name": "Demo User"})
        .execute()
    )
    return res.data[0] if res.data else None


# ---------------------------------------------------------------------------
# PayPal connection helpers (single-tenant: one row in paypal_connections)
# ---------------------------------------------------------------------------

def upsert_paypal_connection(
    sandbox_business_email: Optional[str] = None,
    webhook_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Insert or update the single PayPal connection row.

    Returns the row dict, or None if Supabase is not configured.
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    settings = get_settings()
    payload: Dict[str, Any] = {
        "sandbox_business_email": sandbox_business_email,
        "webhook_id": webhook_id,
    }
    if settings.paypal_client_id:
        payload["paypal_access_token_encrypted"] = "cached-in-memory"  # token lives in memory

    existing = (
        supabase.table("paypal_connections")
        .select("id")
        .limit(1)
        .execute()
    )
    if existing.data:
        row_id = existing.data[0]["id"]
        res = (
            supabase.table("paypal_connections")
            .update(payload)
            .eq("id", row_id)
            .execute()
        )
    else:
        res = supabase.table("paypal_connections").insert(payload).execute()

    return res.data[0] if res.data else None


def get_paypal_connection() -> Optional[Dict[str, Any]]:
    """Return the stored PayPal connection row, or None."""
    supabase = get_supabase()
    if supabase is None:
        return None
    res = supabase.table("paypal_connections").select("*").limit(1).execute()
    return res.data[0] if res.data else None


# ---------------------------------------------------------------------------
# Customer + invoice helpers (synced from PayPal Invoicing API v2)
# ---------------------------------------------------------------------------

def upsert_customers_and_invoices(
    invoices_raw: List[Dict[str, Any]],
    user_id: Optional[str] = None,
) -> Dict[str, int]:
    """Upsert customers and invoices from a raw PayPal invoice list.

    Returns counts: {"customers": N, "invoices": M}.
    Degrades gracefully (returns zeros) if Supabase is not configured.

    Requires user_id (invoices.user_id and customers.user_id are NOT NULL).
    If user_id is None, attempts to use the demo user.
    """
    supabase = get_supabase()
    if supabase is None:
        return {"customers": 0, "invoices": 0}

    if user_id is None:
        demo_user = get_or_create_demo_user()
        if demo_user is None:
            return {"customers": 0, "invoices": 0}
        user_id = demo_user["id"]

    # Build customers and invoices rows from PayPal's invoice objects
    customer_rows: List[Dict[str, Any]] = []
    invoice_rows: List[Dict[str, Any]] = []

    for inv in invoices_raw:
        payer = inv.get("payer") or {}
        recipient_email = (
            payer.get("email_address")
            or (inv.get("recipient") or {}).get("email_address")
        )
        customer_name = (
            payer.get("name") or (inv.get("recipient") or {}).get("name")
        )

        if recipient_email:
            customer_rows.append(
                {
                    "user_id": user_id,
                    "email": recipient_email,
                    "name": customer_name or recipient_email,
                }
            )

        amount_detail = inv.get("amount") or {}
        currency = amount_detail.get("currency_code", "USD")
        value = amount_detail.get("value", "0")
        try:
            amount_cents = int(float(value) * 100)
        except (TypeError, ValueError):
            amount_cents = 0

        detail = inv.get("detail") or {}
        due_date = detail.get("due_date")

        balance_detail = inv.get("balance_due") or {}
        try:
            balance_due_cents = int(float(balance_detail.get("value", value)) * 100)
        except (TypeError, ValueError):
            balance_due_cents = amount_cents

        invoice_rows.append(
            {
                "user_id": user_id,
                "paypal_invoice_id": inv.get("id"),
                "invoice_number": inv.get("invoice_number"),
                "amount_cents": amount_cents,
                "currency": currency,
                "status": inv.get("status"),
                "due_date": due_date,
                "balance_due_cents": balance_due_cents,
            }
        )

    customers_inserted = 0
    invoices_inserted = 0

    if customer_rows:
        # Upsert by (user_id, email) — Supabase needs a unique constraint on (user_id, email)
        res = supabase.table("customers").upsert(
            customer_rows, on_conflict="user_id,email"
        ).execute()
        customers_inserted = len(res.data) if res.data else 0

    if invoice_rows:
        res = supabase.table("invoices").upsert(
            invoice_rows, on_conflict="paypal_invoice_id"
        ).execute()
        invoices_inserted = len(res.data) if res.data else 0

    return {"customers": customers_inserted, "invoices": invoices_inserted}


def get_invoices(
    limit: int = 100, status: Optional[str] = None, user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return invoices from the local DB (most recent first).

    Args:
        limit: max rows to return.
        status: optional PayPal status filter (e.g. "UNPAID").
        user_id: optional user filter; defaults to demo user if Supabase configured.

    Returns an empty list if Supabase is not configured or no rows exist.
    """
    supabase = get_supabase()
    if supabase is None:
        return []

    if user_id is None:
        demo_user = get_or_create_demo_user()
        if demo_user is None:
            return []
        user_id = demo_user["id"]

    query = supabase.table("invoices").select("*").eq("user_id", user_id)

    if status:
        query = query.eq("status", status)

    res = query.order("created_at", desc=True).limit(limit).execute()
    return res.data or []


def get_invoice_by_paypal_id(paypal_invoice_id: str) -> Optional[Dict[str, Any]]:
    """Return a single invoice by PayPal invoice ID, or None."""
    supabase = get_supabase()
    if supabase is None:
        return None

    demo_user = get_or_create_demo_user()
    if demo_user is None:
        return None

    res = (
        supabase.table("invoices")
        .select("*")
        .eq("user_id", demo_user["id"])
        .eq("paypal_invoice_id", paypal_invoice_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


# ---------------------------------------------------------------------------
# AI recommendation + approval helpers (Phase 4)
# ---------------------------------------------------------------------------

def create_ai_recommendation(
    recommendation_type: str,
    content: Dict[str, Any],
    invoice_id: Optional[str] = None,
    customer_message_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create a pending AI recommendation row in Supabase.

    Returns the created row, or None if Supabase is not configured.
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    demo_user = get_or_create_demo_user()
    if demo_user is None:
        return None

    res = (
        supabase.table("ai_recommendations")
        .insert(
            {
                "user_id": demo_user["id"],
                "type": recommendation_type,
                "content": content,
                "status": "pending",
                "invoice_id": invoice_id,
                "customer_message_id": customer_message_id,
            }
        )
        .execute()
    )
    return res.data[0] if res.data else None


def create_approval_record(
    ai_recommendation_id: Optional[str],
    action: str,
    approved: bool,
    editor_note: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create an approval record in Supabase.

    Returns the created row, or None if Supabase is not configured.
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    demo_user = get_or_create_demo_user()
    if demo_user is None:
        return None

    from datetime import datetime

    res = (
        supabase.table("approval_records")
        .insert(
            {
                "user_id": demo_user["id"],
                "ai_recommendation_id": ai_recommendation_id,
                "action": action,
                "approved": approved,
                "decided_at": datetime.utcnow().isoformat(),
                "editor_note": editor_note,
            }
        )
        .execute()
    )
    return res.data[0] if res.data else None


def get_approval_records(limit: int = 50) -> Optional[List[Dict[str, Any]]]:
    """Return approval records from Supabase (most recent first).

    Returns None if Supabase is not configured (so callers can fall back
    to in-memory provider store).
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    demo_user = get_or_create_demo_user()
    if demo_user is None:
        return []

    res = (
        supabase.table("approval_records")
        .select("*")
        .eq("user_id", demo_user["id"])
        .order("decided_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


# ---------------------------------------------------------------------------
# Customer payment history helpers (Phase 4)
# Only genuine invoice payment events are recorded here.
# Reminder activity, AI analysis, approval actions, and other
# application events are NOT recorded here.

def record_payment_event(
    customer_email: str,
    payment_amount_cents: int,
    payment_currency: str = "USD",
    invoice_id: Optional[str] = None,
    paypal_invoice_id: Optional[str] = None,
    payment_date: Optional[str] = None,
    payment_method: Optional[str] = None,
    notes: Optional[str] = None,
    customer_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Record a genuine customer payment event.

    Only payment events (invoice marked PAID) should be recorded here.
    Reminder activity, AI analysis, and approval actions are NOT payment
    events and must not be recorded in this table.

    Returns the created row, or None if Supabase is not configured.
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    demo_user = get_or_create_demo_user()
    if demo_user is None:
        return None

    from datetime import datetime, timezone

    res = (
        supabase.table("customer_payment_history")
        .insert(
            {
                "user_id": demo_user["id"],
                "customer_email": customer_email,
                "customer_name": customer_name,
                "invoice_id": invoice_id,
                "paypal_invoice_id": paypal_invoice_id,
                "payment_amount_cents": payment_amount_cents,
                "payment_currency": payment_currency,
                "payment_date": payment_date or datetime.now(timezone.utc).isoformat(),
                "payment_method": payment_method,
                "notes": notes,
            }
        )
        .execute()
    )
    return res.data[0] if res.data else None


def get_customer_payment_history(
    customer_email: str, limit: int = 50
) -> Optional[List[Dict[str, Any]]]:
    """Return payment history for a customer (most recent first).

    Only genuine payment events are returned. Returns None if Supabase
    is not configured.
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    demo_user = get_or_create_demo_user()
    if demo_user is None:
        return []

    res = (
        supabase.table("customer_payment_history")
        .select("*")
        .eq("user_id", demo_user["id"])
        .eq("customer_email", customer_email)
        .order("payment_date", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def get_payment_events_for_invoice(
    invoice_id: str,
) -> Optional[List[Dict[str, Any]]]:
    """Return all payment events for a specific invoice.

    Returns None if Supabase is not configured.
    """
    supabase = get_supabase()
    if supabase is None:
        return None

    demo_user = get_or_create_demo_user()
    if demo_user is None:
        return []

    res = (
        supabase.table("customer_payment_history")
        .select("*")
        .eq("user_id", demo_user["id"])
        .eq("invoice_id", invoice_id)
        .order("payment_date", desc=True)
        .execute()
    )
    return res.data or []

