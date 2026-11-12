"""FastAPI application entry point.

Phase 1 (Foundation): health-check endpoint.
Phase 2 (PayPal Integration): OAuth client-credentials, invoice sync,
invoices list/details endpoints, and webhook listener with signature
verification + idempotency.
Phase 3 (Mock/Demo Mode): PAYPAL_MODE=mock|sandbox provider selection,
mock sync endpoint, demo user seeding.

Endpoints:
    GET  /health                          — backend health check
    POST /paypal/connect                  — validate PayPal / demo connection
    POST /paypal/mock-sync                — sync mock invoices into Supabase (mock mode)
    GET  /invoices                        — list synced invoices (supports ?status=)
    GET  /invoices/{invoice_id}           — get invoice details
    POST /webhooks/paypal                 — PayPal webhook listener (sandbox mode)
"""

import base64
import logging
import time
import zlib
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.db import (
    get_settings,
    get_supabase,
    get_or_create_demo_user,
    upsert_paypal_connection,
    upsert_customers_and_invoices,
    get_invoices,
    get_invoice_by_paypal_id,
    create_ai_recommendation,
    create_approval_record,
    get_approval_records,
)
from app.schemas import HealthResponse
from app.paypal import get_provider as get_paypal_provider
from app.paypal.provider import PayPalProviderError
from app.paypal.schemas import (
    PayPalConnectResponse,
    InvoiceSummary,
    InvoiceDetail,
    InvoicesListResponse,
    RemindRequest,
    RemindResponse,
)
from app.ai import get_provider as get_ai_provider
from app.ai.schemas import (
    AIHealthResponse,
    InvoiceAnalysisRequest,
    InvoiceAnalysisResponse,
    BatchAnalysisResponse,
    PriorityScoreResponse,
    BatchPriorityResponse,
    ReminderDraftRequest,
    ReminderDraftResponse,
    PaymentBehaviourResponse,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalsListResponse,
)
from app.ai.provider import AIProviderError as AIProviderError
from app.ai.rules import (
    analyze_invoice_for_attention,
    score_priority,
    generate_reminder_template,
    calculate_days_overdue,
)
from app.ai.schemas import PaymentBehaviourInsight

logger = logging.getLogger(__name__)

# Cert cache for webhook verification (avoid re-downloading on every event)
_cert_cache: Dict[str, bytes] = {}


def _download_cert(cert_url: str) -> bytes:
    """Download and cache a PayPal public certificate from cert_url."""
    host = cert_url.split("//")[-1].split("/")[0]
    if host != "paypal.com" and not host.endswith(".paypal.com"):
        raise ValueError(f"Cert URL host is not paypal.com: {host}")
    if cert_url in _cert_cache:
        return _cert_cache[cert_url]
    resp = httpx.get(cert_url, timeout=10.0)
    resp.raise_for_status()
    _cert_cache[cert_url] = resp.content
    return resp.content


def _verify_webhook_signature(
    headers: Dict[str, str],
    raw_body: bytes,
    webhook_id: str,
) -> bool:
    """Self-verify a PayPal webhook signature (RSA-SHA256 / PKCS1v15).

    Signed message format (per PayPal docs):
        transmissionId|transmissionTime|webhookId|crc32(rawBody)
    where crc32 is the unsigned decimal CRC-32 of the raw HTTP body.
    """
    transmission_id = headers.get("paypal-transmission-id")
    transmission_time = headers.get("paypal-transmission-time")
    cert_url = headers.get("paypal-cert-url")
    transmission_sig = headers.get("paypal-transmission-sig")

    if not all([transmission_id, transmission_time, cert_url, transmission_sig]):
        logger.warning("Missing PayPal webhook headers")
        return False

    # Replay protection: timestamp within 5 minutes
    msg_time: Optional[float] = None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            msg_time = time.mktime(time.strptime(transmission_time, fmt))
            break
        except (ValueError, TypeError):
            continue
    if msg_time is None:
        logger.warning("Invalid transmission_time format")
        return False
    if abs(time.time() - msg_time) > 300:
        logger.warning("Webhook timestamp outside 5-minute window")
        return False

    # Build signed message
    crc = zlib.crc32(raw_body) & 0xFFFFFFFF
    message = f"{transmission_id}|{transmission_time}|{webhook_id}|{crc}".encode("utf-8")

    # Download cert and verify RSA-SHA256 / PKCS1v15
    try:
        cert_pem = _download_cert(cert_url)
        cert = x509.load_pem_x509_certificate(cert_pem)
        public_key = cert.public_key()
        public_key.verify(
            base64.b64decode(transmission_sig),
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception as exc:
        logger.warning(f"Webhook signature verification failed: {exc}")
        return False

    return True


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Invoice Collection Agent — backend (FastAPI)",
        version="0.3.0",
        debug=settings.debug,
    )

    # --- CORS ---------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Helper: map raw PayPal invoice dict to InvoiceSummary
    # ------------------------------------------------------------------
    def _map_raw_to_invoice_summary(inv: Dict[str, Any]) -> InvoiceSummary:
        amount_detail = inv.get("amount") or {}
        currency = amount_detail.get("currency_code", "USD")
        value = amount_detail.get("value", "0")
        try:
            amount = float(value)
        except (TypeError, ValueError):
            amount = 0.0

        detail = inv.get("detail") or {}
        balance_detail = inv.get("balance_due") or {}
        try:
            balance_due = float(balance_detail.get("value", value))
        except (TypeError, ValueError):
            balance_due = amount

        payer = inv.get("payer") or {}
        recipient = inv.get("recipient") or {}
        customer_email = (
            payer.get("email_address") or recipient.get("email_address")
        )
        customer_name = payer.get("name") or recipient.get("name")

        return InvoiceSummary(
            paypal_invoice_id=inv.get("id", ""),
            invoice_number=inv.get("invoice_number"),
            customer_name=customer_name,
            customer_email=customer_email,
            amount=amount,
            currency=currency,
            status=inv.get("status", "UNKNOWN"),
            due_date=detail.get("due_date"),
            balance_due=balance_due,
        )


    # ========================================================================
    # HEALTH
    # ========================================================================
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health():
        supabase = get_supabase()
        return HealthResponse(
            environment=settings.app_env,
            database_configured=supabase is not None,
            paypal_mode=settings.paypal_mode,
        )

    @app.get("/", tags=["root"])
    async def root():
        return {
            "service": settings.app_name,
            "status": "running",
            "paypal_mode": settings.paypal_mode,
            "docs": "/docs",
            "health": "/health",
        }

    # ========================================================================
    # PAYPAL CONNECT
    # ========================================================================
    @app.post(
        "/paypal/connect",
        response_model=PayPalConnectResponse,
        tags=["paypal"],
    )
    async def connect_paypal():
        """Validate PayPal connection (sandbox) or report demo mode (mock).

        In mock mode, never returns connected=True — that would falsely claim
        PayPal OAuth succeeded. Instead it reports demo_mode=True.
        """
        provider = get_paypal_provider()
        result = await provider.connect()

        if settings.paypal_mode == "mock":
            return PayPalConnectResponse(
                connected=False,
                sandbox_business_email=None,
                message=result.get(
                    "message", "Demo mode: PayPal OAuth not required."
                ),
            )

        # Sandbox mode: store connection if successful
        if result.get("connected"):
            upsert_paypal_connection(
                sandbox_business_email=None,
                webhook_id=settings.paypal_webhook_id,
            )
        return PayPalConnectResponse(
            connected=bool(result.get("connected")),
            sandbox_business_email=None,
            message=result.get("message", ""),
        )

    # ========================================================================
    # MOCK SYNC (demo mode only)
    # ========================================================================
    @app.post("/paypal/mock-sync", tags=["paypal"])
    async def mock_sync():
        """Sync mock/demo invoices into Supabase (mock mode only).

        Generates demo invoice data via the mock provider and upserts it
        into the local DB using the existing schema. Requires Supabase to
        be configured; returns a no-op message otherwise.
        """
        if settings.paypal_mode != "mock":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mock sync is only available in PAYPAL_MODE=mock",
            )

        provider = get_paypal_provider()
        data = await provider.list_invoices(page=1, page_size=100)
        raw_invoices: List[Dict[str, Any]] = data.get("items", []) or []

        # Persist to local DB using the existing schema (demo user)
        counts = upsert_customers_and_invoices(raw_invoices)

        provider.increment_sync()  # type: ignore[attr-defined]

        return {
            "status": "synced",
            "mode": "mock",
            "invoices_seen": len(raw_invoices),
            "customers_upserted": counts.get("customers", 0),
            "invoices_upserted": counts.get("invoices", 0),
            "demo_mode": True,
        }

    # ========================================================================
    # INVOICES
    # ========================================================================
    def _map_paypal_invoice_to_summary(inv: Dict[str, Any]) -> InvoiceSummary:
        amount_detail = inv.get("amount") or {}
        currency = amount_detail.get("currency_code", "USD")
        value = amount_detail.get("value", "0")
        try:
            amount = float(value)
        except (TypeError, ValueError):
            amount = 0.0

        detail = inv.get("detail") or {}
        balance_detail = inv.get("balance_due") or {}
        try:
            balance_due = float(balance_detail.get("value", value))
        except (TypeError, ValueError):
            balance_due = amount

        payer = inv.get("payer") or {}
        recipient = inv.get("recipient") or {}
        customer_email = (
            payer.get("email_address") or recipient.get("email_address")
        )
        customer_name = payer.get("name") or recipient.get("name")

        return InvoiceSummary(
            paypal_invoice_id=inv.get("id", ""),
            invoice_number=inv.get("invoice_number"),
            customer_name=customer_name,
            customer_email=customer_email,
            amount=amount,
            currency=currency,
            status=inv.get("status", "UNKNOWN"),
            due_date=detail.get("due_date"),
            balance_due=balance_due,
        )

    def _map_paypal_invoice_to_detail(inv: Dict[str, Any]) -> InvoiceDetail:
        summary = _map_paypal_invoice_to_summary(inv)
        return InvoiceDetail(
            paypal_invoice_id=summary.paypal_invoice_id,
            status=summary.status,
            amount=summary.amount,
            currency=summary.currency,
            due_date=summary.due_date,
            customer_email=summary.customer_email,
            customer_name=summary.customer_name,
            balance_due=summary.balance_due,
            invoice_number=summary.invoice_number,
        )

    @app.get(
        "/invoices",
        response_model=InvoicesListResponse,
        tags=["invoices"],
    )
    async def list_invoices(
        page: int = 1, page_size: int = 20, status: Optional[str] = None
    ):
        """List invoices.

        In mock mode: returns mock invoices from the provider.
        In sandbox mode: fetches from PayPal and optionally persists to Supabase.

        Query params:
            page: page number (default 1)
            page_size: items per page (default 20)
            status: optional PayPal status filter (e.g. "UNPAID", "PAID")
        """
        provider = get_paypal_provider()

        if settings.paypal_mode == "mock":
            data = await provider.list_invoices(page=1, page_size=1000)
            raw_invoices: List[Dict[str, Any]] = data.get("items", []) or []
            summaries = [_map_paypal_invoice_to_summary(inv) for inv in raw_invoices]

            # Apply status filter client-side for mock data
            if status:
                summaries = [s for s in summaries if s.status == status]

            return InvoicesListResponse(
                invoices=summaries,
                total=len(summaries),
            )

        # Sandbox mode: fetch from PayPal
        try:
            data = await provider.list_invoices(page=page, page_size=page_size)
        except PayPalAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )

        raw_invoices: List[Dict[str, Any]] = data.get("items", []) or []
        summaries = [_map_paypal_invoice_to_summary(inv) for inv in raw_invoices]

        # Persist to local DB if configured (demo user)
        if get_supabase() is not None:
            demo_user = get_or_create_demo_user()
            if demo_user:
                upsert_customers_and_invoices(raw_invoices, user_id=demo_user["id"])

        total = data.get("total")
        try:
            total = int(total) if total is not None else None
        except (TypeError, ValueError):
            total = None

        return InvoicesListResponse(invoices=summaries, total=total)

    @app.get(
        "/invoices/{invoice_id}",
        response_model=InvoiceDetail,
        tags=["invoices"],
    )
    async def get_invoice(invoice_id: str):
        """Get a single invoice's details.

        In mock mode: looks up in the mock provider.
        In sandbox mode: fetches from PayPal.
        """
        provider = get_paypal_provider()

        if settings.paypal_mode == "mock":
            inv = await provider.get_invoice(invoice_id)
            if not inv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invoice not found",
                )
            return _map_paypal_invoice_to_detail(inv)

        try:
            inv = await provider.get_invoice(invoice_id)
        except PayPalAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )
        return _map_paypal_invoice_to_detail(inv)

    # ========================================================================
    # PAYPAL WEBHOOKS (sandbox mode only)
    # ========================================================================
    @app.post("/webhooks/paypal", tags=["webhooks"])
    async def paypal_webhook(request: Request):
        """PayPal webhook listener.

        Verifies the RSA-SHA256 signature, enforces idempotency, and (stub)
        logs the event. Invoice status updates happen in Phase 5.
        Only meaningful in sandbox mode; in mock mode it returns 501.
        """
        if settings.paypal_mode == "mock":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Webhooks are not used in mock mode",
            )

        webhook_id = settings.paypal_webhook_id
        if not webhook_id:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="PAYPAL_WEBHOOK_ID not configured",
            )

        # Read raw body — do not parse then re-serialize (signature is over raw bytes)
        raw_body = await request.body()

        # Headers are case-insensitive; normalize to lowercase for lookup
        headers = {k.lower(): v for k, v in request.headers.items()}

        # Verify signature
        if not _verify_webhook_signature(headers, raw_body, webhook_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )

        # Parse event for idempotency / logging
        try:
            event = await request.json()
        except Exception:
            event = {}

        paypal_event_id = (
            event.get("id")
            or (event.get("webhook_event") or {}).get("id")
            or headers.get("paypal-transmission-id")
        )
        event_type = (
            event.get("event_type")
            or (event.get("webhook_event") or {}).get("event_type")
            or "unknown"
        )

        # Idempotency: skip if already processed
        supabase = get_supabase()
        if supabase is not None and paypal_event_id:
            existing = (
                supabase.table("webhook_events")
                .select("id")
                .eq("paypal_event_id", paypal_event_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                return {"status": "duplicate", "event_id": paypal_event_id}

            supabase.table("webhook_events").insert(
                {
                    "paypal_event_id": paypal_event_id,
                    "event_type": event_type,
                    "processed": False,
                }
            ).execute()

        logger.info(
            "PayPal webhook received: event_id=%s type=%s",
            paypal_event_id,
            event_type,
        )

        # Phase 2/3 stub: log only. Invoice status updates happen in Phase 5.
        return {
            "status": "received",
            "event_id": paypal_event_id,
            "event_type": event_type,
        }

    # ========================================================================
    # AI INTELLIGENCE (Phase 4)
    # ========================================================================
    @app.post(
        "/ai/analyze",
        response_model=InvoiceAnalysisResponse,
        tags=["ai"],
    )
    async def analyze_invoice(request: InvoiceAnalysisRequest):
        """Analyze a single invoice for collection attention.

        Uses the active AI provider (mock or OpenAI). Falls back to
        deterministic rules if the provider is unavailable.
        """
        provider = get_ai_provider()

        # Fetch invoice details from PayPal provider
        paypal = get_paypal_provider()
        try:
            raw_inv = await paypal.get_invoice(request.invoice_id)
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )
        if not raw_inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )

        invoice = _map_raw_to_invoice_summary(raw_inv)

        # Customer history — not available in current schema, pass None
        # (provider will state "no history available" rather than inventing)
        try:
            result = await provider.analyze_invoice(invoice, None)
        except AIProviderError:
            result = analyze_invoice_for_attention(invoice, None)

        return result

    @app.post(
        "/ai/analyze/batch",
        response_model=BatchAnalysisResponse,
        tags=["ai"],
    )
    async def analyze_batch_invoices():
        """Analyze all current invoices for collection attention."""
        provider = get_ai_provider()
        paypal = get_paypal_provider()

        try:
            data = await paypal.list_invoices(page=1, page_size=1000)
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )

        raw_invoices: List[Dict[str, Any]] = data.get("items", []) or []
        invoices = [_map_raw_to_invoice_summary(inv) for inv in raw_invoices]

        try:
            result = await provider.analyze_batch(invoices)
        except AIProviderError:
            results = [
                analyze_invoice_for_attention(inv) for inv in invoices
            ]
            needs_attention = sum(1 for r in results if r.needs_attention)
            result = BatchAnalysisResponse(
                invoices=results,
                total_analyzed=len(results),
                needs_attention_count=needs_attention,
            )

        return result

    @app.post(
        "/ai/priority",
        response_model=PriorityScoreResponse,
        tags=["ai"],
    )
    async def score_invoice_priority(request: InvoiceAnalysisRequest):
        """Calculate priority score for a single invoice."""
        provider = get_ai_provider()
        paypal = get_paypal_provider()

        try:
            raw_inv = await paypal.get_invoice(request.invoice_id)
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )
        if not raw_inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )

        invoice = _map_raw_to_invoice_summary(raw_inv)

        try:
            result = await provider.score_priority(invoice)
        except AIProviderError:
            result = score_priority(invoice)

        return result

    @app.post(
        "/ai/priority/batch",
        response_model=BatchPriorityResponse,
        tags=["ai"],
    )
    async def score_batch_priority():
        """Calculate priority scores for all invoices, sorted by priority."""
        provider = get_ai_provider()
        paypal = get_paypal_provider()

        try:
            data = await paypal.list_invoices(page=1, page_size=1000)
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )

        raw_invoices: List[Dict[str, Any]] = data.get("items", []) or []
        invoices = [_map_raw_to_invoice_summary(inv) for inv in raw_invoices]

        try:
            result = await provider.score_batch_priority(invoices)
        except AIProviderError:
            scored = [score_priority(inv) for inv in invoices]
            scored.sort(key=lambda x: x.score, reverse=True)
            result = BatchPriorityResponse(
                invoices=scored,
                total_count=len(scored),
            )

        return result

    @app.post(
        "/ai/reminder",
        response_model=ReminderDraftResponse,
        tags=["ai"],
    )
    async def generate_reminder(request: ReminderDraftRequest):
        """Generate a personalized reminder draft (requires human approval).

        Never sends emails — returns a draft only. The draft must be
        approved via /ai/approval before any external action.
        """
        provider = get_ai_provider()
        paypal = get_paypal_provider()

        try:
            raw_inv = await paypal.get_invoice(request.invoice_id)
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )
        if not raw_inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )

        invoice = _map_raw_to_invoice_summary(raw_inv)

        try:
            result = await provider.generate_reminder(request, invoice)
        except AIProviderError:
            tone = request.tone if request.tone in ("polite", "friendly", "firm") else "polite"
            template = generate_reminder_template(invoice, tone, request.custom_context)
            result = ReminderDraftResponse(
                invoice_id=invoice.paypal_invoice_id,
                invoice_number=invoice.invoice_number,
                customer_name=invoice.customer_name,
                customer_email=invoice.customer_email,
                amount=invoice.amount,
                currency=invoice.currency,
                due_date=invoice.due_date,
                tone=tone,
                subject=template["subject"],
                body=template["body"],
                method="template",
                requires_approval=True,
            )

        # Create a pending AI recommendation row if Supabase is configured
        rec_row = create_ai_recommendation(
            recommendation_type="reminder_draft",
            content={
                "subject": result.subject,
                "body": result.body,
                "tone": result.tone,
                "method": result.method,
            },
            invoice_id=request.invoice_id,
        )
        if rec_row:
            # Attach the recommendation ID to the response
            result_dict = result.model_dump()
            result_dict["recommendation_id"] = rec_row["id"]
            result = ReminderDraftResponse(**result_dict)

        return result

    @app.post(
        "/ai/insights",
        response_model=PaymentBehaviourResponse,
        tags=["ai"],
    )
    async def generate_insights(customer_email: Optional[str] = None):
        """Generate payment behaviour insights from invoice data."""
        provider = get_ai_provider()
        paypal = get_paypal_provider()

        try:
            data = await paypal.list_invoices(page=1, page_size=1000)
        except PayPalProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            )

        raw_invoices: List[Dict[str, Any]] = data.get("items", []) or []
        invoices = [_map_raw_to_invoice_summary(inv) for inv in raw_invoices]

        try:
            result = await provider.generate_insights(invoices, customer_email)
        except AIProviderError:
            # Deterministic fallback
            total = len(invoices)
            paid = [inv for inv in invoices if inv.status.upper() == "PAID"]
            unpaid = [inv for inv in invoices if inv.status.upper() in ("UNPAID", "PARTIALLY_PAID", "SENT")]
            on_time_rate = (len(paid) / total * 100) if total > 0 else None
            overdue_with_dates = [
                inv for inv in invoices
                if inv.due_date and inv.status.upper() != "PAID"
            ]
            avg_days_late = None
            if overdue_with_dates:
                total_days = sum(calculate_days_overdue(inv.due_date) for inv in overdue_with_dates)
                avg_days_late = round(total_days / len(overdue_with_dates), 1)
            result = PaymentBehaviourResponse(
                customer_email=customer_email,
                total_invoices=total,
                paid_invoices=len(paid),
                unpaid_invoices=len(unpaid),
                average_days_late=avg_days_late,
                on_time_rate=on_time_rate,
                trends=[
                    PaymentBehaviourInsight(
                        category="summary",
                        label="Analysis summary",
                        value=f"{len(paid)} paid, {len(unpaid)} outstanding of {total}",
                        confidence="medium",
                        description="Deterministic fallback — AI unavailable.",
                        is_estimate=True,
                    )
                ],
                summary=(
                    f"Analyzed {total} invoice(s) using fallback rules. "
                    "AI unavailable — insights are indicative only."
                ),
                is_estimate=True,
            )

        return result

    @app.post(
        "/ai/approval",
        response_model=ApprovalResponse,
        tags=["ai"],
    )
    async def process_approval(request: ApprovalRequest):
        """Approve, reject, or edit an AI recommendation.

        Human approval gate — no external actions are taken automatically.
        """
        provider = get_ai_provider()

        try:
            result = await provider.process_approval(request)
        except AIProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

        # Persist to Supabase if configured
        if get_supabase() is not None:
            approved = result.status in ("approved", "edited")
            create_approval_record(
                ai_recommendation_id=request.recommendation_id,
                action=request.action,
                approved=approved,
                editor_note=request.editor_note,
            )

        return result

    @app.get(
        "/ai/approvals",
        response_model=ApprovalsListResponse,
        tags=["ai"],
    )
    async def list_approvals():
        """List approval history (most recent first)."""
        provider = get_ai_provider()

        # Try Supabase first
        records = get_approval_records()
        if records is not None:
            summaries = [
                ApprovalRecordSummary(
                    id=r["id"],
                    recommendation_id=r.get("ai_recommendation_id", ""),
                    action=r.get("action", ""),
                    status="approved" if r.get("approved") else "rejected",
                    decided_at=r.get("decided_at"),
                    editor_note=r.get("editor_note"),
                )
                for r in records
            ]
            return ApprovalsListResponse(records=summaries, total=len(summaries))

        # Fall back to in-memory provider store
        return await provider.list_approvals()

    @app.get(
        "/ai/health",
        response_model=AIHealthResponse,
        tags=["ai"],
    )
    async def ai_health():
        """AI service health status."""
        provider = get_ai_provider()
        return await provider.health()

    return app


app = create_app()
