"""Mock / Demo AI provider.

Deterministic AI replacement that requires no API key, makes no external
network calls, and never mints tokens. Used for demo and testing.

All outputs are generated from transparent business rules in
:mod:`app.ai.rules`. The provider never invents customer history or
payment information — it states when data is unavailable.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ai.provider import AIProvider, AIProviderError
from app.ai.schemas import (
    InvoiceAnalysisResponse,
    BatchAnalysisResponse,
    PriorityScoreResponse,
    BatchPriorityResponse,
    ReminderDraftRequest,
    ReminderDraftResponse,
    PaymentBehaviourResponse,
    PaymentBehaviourInsight,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalRecordSummary,
    ApprovalsListResponse,
    AIHealthResponse,
)
from app.ai.rules import (
    analyze_invoice_for_attention,
    score_priority,
    generate_reminder_template,
    calculate_days_overdue,
)
from app.paypal.schemas import InvoiceSummary


class MockAIProvider(AIProvider):
    """Deterministic mock AI provider — no credentials, no network calls."""

    def __init__(self) -> None:
        # In-memory approval store (resets on restart; Supabase persistence
        # is handled by the backend routes via db.py helpers)
        self._approvals: Dict[str, Dict[str, Any]] = {}
        self._recommendation_counter = 0

    # ------------------------------------------------------------------
    # Health / configuration
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Mock provider is always configured — no credentials needed."""
        return True

    async def health(self) -> AIHealthResponse:
        return AIHealthResponse(
            ai_mode="mock",
            configured=True,
            provider="mock",
            available=True,
            storage_backend="session",
        )

    # ------------------------------------------------------------------
    # Invoice Analysis
    # ------------------------------------------------------------------

    async def analyze_invoice(
        self,
        invoice: InvoiceSummary,
        customer_history: Optional[List[Dict[str, Any]]] = None,
    ) -> InvoiceAnalysisResponse:
        """Analyze a single invoice using deterministic rules."""
        return analyze_invoice_for_attention(invoice, customer_history)

    async def analyze_batch(
        self,
        invoices: List[InvoiceSummary],
    ) -> BatchAnalysisResponse:
        """Analyze multiple invoices using deterministic rules."""
        results = [
            analyze_invoice_for_attention(inv) for inv in invoices
        ]
        needs_attention = sum(1 for r in results if r.needs_attention)
        return BatchAnalysisResponse(
            invoices=results,
            total_analyzed=len(results),
            needs_attention_count=needs_attention,
        )

    # ------------------------------------------------------------------
    # Priority Scoring
    # ------------------------------------------------------------------

    async def score_priority(
        self,
        invoice: InvoiceSummary,
    ) -> PriorityScoreResponse:
        """Calculate priority score using deterministic rules."""
        return score_priority(invoice)

    async def score_batch_priority(
        self,
        invoices: List[InvoiceSummary],
    ) -> BatchPriorityResponse:
        """Calculate priority scores for multiple invoices, sorted by score."""
        scored = [score_priority(inv) for inv in invoices]
        scored.sort(key=lambda x: x.score, reverse=True)
        return BatchPriorityResponse(
            invoices=scored,
            total_count=len(scored),
        )

    # ------------------------------------------------------------------
    # Reminder Generation
    # ------------------------------------------------------------------

    async def generate_reminder(
        self,
        request: ReminderDraftRequest,
        invoice: InvoiceSummary,
    ) -> ReminderDraftResponse:
        """Generate a reminder draft from a template (no AI).

        Supports polite, friendly, and firm tones. Never invents payment
        terms or legal threats. Always requires human approval.
        """
        tone = request.tone if request.tone in ("polite", "friendly", "firm") else "polite"
        template = generate_reminder_template(invoice, tone, request.custom_context)

        return ReminderDraftResponse(
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

    # ------------------------------------------------------------------
    # Payment Behaviour Insights
    # ------------------------------------------------------------------

    async def generate_insights(
        self,
        invoices: List[InvoiceSummary],
        customer_email: Optional[str] = None,
    ) -> PaymentBehaviourResponse:
        """Generate payment behaviour insights from available invoice data.

        Never invents historical data. Provides estimates with clear
        uncertainty labels. Does not present predictions as guaranteed.
        """
        total = len(invoices)
        paid = [inv for inv in invoices if inv.status.upper() == "PAID"]
        unpaid = [inv for inv in invoices if inv.status.upper() in ("UNPAID", "PARTIALLY_PAID", "SENT")]

        on_time_rate = (len(paid) / total * 100) if total > 0 else None

        # Average days late — only for invoices with due dates
        overdue_with_dates = [
            inv for inv in invoices
            if inv.due_date and inv.status.upper() != "PAID"
        ]
        avg_days_late = None
        if overdue_with_dates:
            total_days = sum(calculate_days_overdue(inv.due_date) for inv in overdue_with_dates)
            avg_days_late = round(total_days / len(overdue_with_dates), 1)

        trends: List[PaymentBehaviourInsight] = []

        if total > 0:
            trends.append(
                PaymentBehaviourInsight(
                    category="invoice_volume",
                    label="Total invoices tracked",
                    value=total,
                    confidence="high",
                    description=f"{total} invoice(s) are currently being tracked.",
                )
            )

        if on_time_rate is not None:
            trends.append(
                PaymentBehaviourInsight(
                    category="on_time_rate",
                    label="On-time payment rate",
                    value=f"{on_time_rate:.0f}%",
                    confidence="medium",
                    description=(
                        f"{len(paid)} of {total} invoice(s) are marked as paid. "
                        "This is based on current status only, not payment timing history."
                    ),
                    is_estimate=True,
                )
            )

        if avg_days_late is not None:
            trend_label = (
                "improving" if avg_days_late < 7 else
                "stable" if avg_days_late < 30 else
                "declining"
            )
            trends.append(
                PaymentBehaviourInsight(
                    category="average_days_late",
                    label="Average days late (unpaid invoices)",
                    value=f"{avg_days_late} days",
                    confidence="medium",
                    description=(
                        f"Unpaid invoices are an average of {avg_days_late} days "
                        "past their due date. Trend appears {trend_label} based on "
                        "current snapshot — not a prediction of future behaviour."
                    ),
                    is_estimate=True,
                )
            )

        # Customer-specific note — never invent history
        if customer_email:
            customer_invoices = [inv for inv in invoices if inv.customer_email == customer_email]
            trends.append(
                PaymentBehaviourInsight(
                    category="customer_focus",
                    label=f"Invoices for {customer_email}",
                    value=len(customer_invoices),
                    confidence="high",
                    description=(
                        f"{len(customer_invoices)} invoice(s) found for this customer. "
                        "No prior payment behaviour history is available beyond current statuses."
                    ),
                )
            )

        summary = (
            f"Analyzed {total} invoice(s): {len(paid)} paid, {len(unpaid)} outstanding. "
            "Insights are based on current invoice statuses only — no external "
            "payment history is available. Treat estimates as indicative, not guaranteed."
        )

        return PaymentBehaviourResponse(
            customer_email=customer_email,
            total_invoices=total,
            paid_invoices=len(paid),
            unpaid_invoices=len(unpaid),
            average_days_late=avg_days_late,
            on_time_rate=on_time_rate,
            trends=trends,
            summary=summary,
            is_estimate=True,
        )

    # ------------------------------------------------------------------
    # Approval Workflow
    # ------------------------------------------------------------------

    async def process_approval(
        self,
        request: ApprovalRequest,
    ) -> ApprovalResponse:
        """Process an approve/reject/edit action on an AI recommendation.

        Records the decision in-memory (session-only storage). In production
        with Supabase configured, the backend route also persists to the
        database via create_approval_record().
        """
        self._recommendation_counter += 1
        rec_id = request.recommendation_id or f"rec-{self._recommendation_counter:06d}"

        if request.action == "approve":
            status = "approved"
        elif request.action == "reject":
            status = "rejected"
        elif request.action == "edit":
            status = "edited"
        else:
            raise AIProviderError(f"Unknown approval action: {request.action}")

        record = {
            "id": rec_id,
            "recommendation_id": rec_id,
            "action": request.action,
            "status": status,
            "decided_at": datetime.now(timezone.utc),
            "editor_note": request.editor_note,
            "edited_content": request.edited_content,
            "storage_backend": "session",
        }
        self._approvals[rec_id] = record

        return ApprovalResponse(
            recommendation_id=rec_id,
            action=request.action,
            status=status,
            decided_at=record["decided_at"],
            editor_note=request.editor_note,
            storage_backend="session",
        )

    async def list_approvals(self) -> ApprovalsListResponse:
        """List all approval records (most recent first).

        These are session-only (in-memory) records. When Supabase is
        configured, the backend route reads from the database instead.
        """
        records = sorted(
            self._approvals.values(),
            key=lambda r: r.get("decided_at") or datetime.min,
            reverse=True,
        )
        summaries = [
            ApprovalRecordSummary(
                id=r["id"],
                recommendation_id=r["recommendation_id"],
                action=r["action"],
                status=r["status"],
                decided_at=r.get("decided_at"),
                editor_note=r.get("editor_note"),
                storage_backend=r.get("storage_backend", "session"),
            )
            for r in records
        ]
        return ApprovalsListResponse(records=summaries, total=len(summaries))
