"""Deterministic business rules for AI fallback.

These rules are used when the AI provider is unavailable or as a fallback
to validate/sanity-check AI outputs. They are fully transparent and
explainable — no "black box" behaviour.

All scoring is deterministic: same inputs always produce same outputs.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from app.ai.schemas import (
    PriorityFactor,
    PriorityScoreResponse,
    AttentionReason,
    InvoiceAnalysisResponse,
)
from app.paypal.schemas import InvoiceSummary


# ---------------------------------------------------------------------------
# Priority scoring weights (deterministic, transparent)
# ---------------------------------------------------------------------------

# Days overdue thresholds and points
DAYS_OVERDUE_CRITICAL = 45
DAYS_OVERDUE_HIGH = 21
DAYS_OVERDUE_MEDIUM = 7

# Amount thresholds (in dollars)
AMOUNT_CRITICAL = 5000
AMOUNT_HIGH = 2000
AMOUNT_MEDIUM = 500

# Status-based points
STATUS_POINTS: Dict[str, int] = {
    "UNPAID": 25,
    "PARTIALLY_PAID": 20,
    "SENT": 15,
    "DRAFT": 5,
    "PAID": 0,
    "CANCELLED": 0,
}


def calculate_days_overdue(due_date_str: Optional[str]) -> int:
    """Calculate days overdue from a due date string (YYYY-MM-DD).

    Returns 0 if the date is in the future or today, or if parsing fails.
    Never invents a date.
    """
    if not due_date_str:
        return 0
    try:
        due_date = date.fromisoformat(due_date_str)
    except (ValueError, TypeError):
        return 0
    today = date.today()
    delta = (today - due_date).days
    return max(0, delta)


def score_priority(invoice: InvoiceSummary) -> PriorityScoreResponse:
    """Deterministic priority score for an invoice (0-100).

    Factors:
      - Days overdue (up to 40 points)
      - Outstanding amount (up to 35 points)
      - Invoice status (up to 25 points)

    Falls back to transparent rules — no AI required.
    """
    days_overdue = calculate_days_overdue(invoice.due_date)
    amount = invoice.amount
    status = invoice.status.upper()

    # --- Days overdue factor (0-40 points) ---
    if days_overdue >= DAYS_OVERDUE_CRITICAL:
        overdue_points = 40
        overdue_explanation = f"{days_overdue} days overdue (critical)"
    elif days_overdue >= DAYS_OVERDUE_HIGH:
        overdue_points = 30
        overdue_explanation = f"{days_overdue} days overdue (high)"
    elif days_overdue >= DAYS_OVERDUE_MEDIUM:
        overdue_points = 20
        overdue_explanation = f"{days_overdue} days overdue (medium)"
    elif days_overdue > 0:
        overdue_points = 10
        overdue_explanation = f"{days_overdue} day(s) overdue"
    else:
        overdue_points = 0
        overdue_explanation = "Not yet overdue"

    # --- Amount factor (0-35 points) ---
    if amount >= AMOUNT_CRITICAL:
        amount_points = 35
        amount_explanation = f"${amount:,.2f} (critical amount)"
    elif amount >= AMOUNT_HIGH:
        amount_points = 25
        amount_explanation = f"${amount:,.2f} (high amount)"
    elif amount >= AMOUNT_MEDIUM:
        amount_points = 15
        amount_explanation = f"${amount:,.2f} (medium amount)"
    else:
        amount_points = 5
        amount_explanation = f"${amount:,.2f} (lower amount)"

    # --- Status factor (0-25 points) ---
    status_points = STATUS_POINTS.get(status, 10)
    status_explanation = f"Status: {invoice.status}"

    total_score = overdue_points + amount_points + status_points
    total_score = min(100, max(0, total_score))

    # --- Determine priority level ---
    # PAID or CANCELLED invoices are always low priority regardless of amount
    if status in ("PAID", "CANCELLED"):
        priority_level = "low"
        total_score = min(total_score, 25)  # Cap at 25 for paid/cancelled
    elif total_score >= 75:
        priority_level = "critical"
    elif total_score >= 55:
        priority_level = "high"
    elif total_score >= 30:
        priority_level = "medium"
    else:
        priority_level = "low"

    factors = [
        PriorityFactor(
            name="days_overdue",
            weight=40.0,
            contribution=float(overdue_points),
            explanation=overdue_explanation,
        ),
        PriorityFactor(
            name="amount",
            weight=35.0,
            contribution=float(amount_points),
            explanation=amount_explanation,
        ),
        PriorityFactor(
            name="status",
            weight=25.0,
            contribution=float(status_points),
            explanation=status_explanation,
        ),
    ]

    explanation = (
        f"Priority {priority_level.upper()}: score {total_score}/100. "
        f"{overdue_explanation}; {amount_explanation}; {status_explanation}."
    )

    return PriorityScoreResponse(
        invoice_id=invoice.paypal_invoice_id,
        invoice_number=invoice.invoice_number,
        customer_name=invoice.customer_name,
        customer_email=invoice.customer_email,
        amount=invoice.amount,
        currency=invoice.currency,
        status=invoice.status,
        due_date=invoice.due_date,
        days_overdue=days_overdue,
        priority_level=priority_level,
        score=float(total_score),
        factors=factors,
        explanation=explanation,
        method="deterministic",
    )


def analyze_invoice_for_attention(
    invoice: InvoiceSummary,
    customer_history: Optional[List[Dict[str, Any]]] = None,
) -> InvoiceAnalysisResponse:
    """Analyze a single invoice and determine if it needs collection attention.

    Never invents customer history. If history is not provided, the analysis
    states that no history is available rather than fabricating data.
    """
    days_overdue = calculate_days_overdue(invoice.due_date)
    amount = invoice.amount
    status = invoice.status.upper()

    reasons: List[AttentionReason] = []

    # Status-based reasons
    if status == "UNPAID":
        reasons.append(
            AttentionReason(
                factor="status",
                description="Invoice is unpaid and requires follow-up.",
                severity="high",
            )
        )
    elif status == "PARTIALLY_PAID":
        reasons.append(
            AttentionReason(
                factor="status",
                description="Invoice is partially paid; balance remains outstanding.",
                severity="medium",
            )
        )
    elif status == "SENT":
        reasons.append(
            AttentionReason(
                factor="status",
                description="Invoice has been sent but not yet paid.",
                severity="medium",
            )
        )
    elif status == "DRAFT":
        reasons.append(
            AttentionReason(
                factor="status",
                description="Invoice is still in draft and has not been sent.",
                severity="low",
            )
        )
    elif status == "PAID":
        reasons.append(
            AttentionReason(
                factor="status",
                description="Invoice is marked as paid. No attention needed.",
                severity="low",
            )
        )
    elif status == "CANCELLED":
        reasons.append(
            AttentionReason(
                factor="status",
                description="Invoice is cancelled. No attention needed.",
                severity="low",
            )
        )

    # Overdue-based reasons
    if days_overdue >= DAYS_OVERDUE_CRITICAL:
        reasons.append(
            AttentionReason(
                factor="days_overdue",
                description=f"Severely overdue: {days_overdue} days past due date.",
                severity="high",
            )
        )
    elif days_overdue >= DAYS_OVERDUE_HIGH:
        reasons.append(
            AttentionReason(
                factor="days_overdue",
                description=f"Overdue: {days_overdue} days past due date.",
                severity="high",
            )
        )
    elif days_overdue >= DAYS_OVERDUE_MEDIUM:
        reasons.append(
            AttentionReason(
                factor="days_overdue",
                description=f"Overdue: {days_overdue} days past due date.",
                severity="medium",
            )
        )
    elif days_overdue > 0:
        reasons.append(
            AttentionReason(
                factor="days_overdue",
                description=f"Slightly overdue: {days_overdue} day(s) past due date.",
                severity="low",
            )
        )

    # Amount-based reasons
    if amount >= AMOUNT_CRITICAL:
        reasons.append(
            AttentionReason(
                factor="amount",
                description=f"High-value invoice: ${amount:,.2f} outstanding.",
                severity="high",
            )
        )
    elif amount >= AMOUNT_HIGH:
        reasons.append(
            AttentionReason(
                factor="amount",
                description=f"Significant amount: ${amount:,.2f} outstanding.",
                severity="medium",
            )
        )

    # Customer history — never invent
    history_note = ""
    if customer_history:
        history_note = f" Based on {len(customer_history)} prior interaction(s) on record."
    else:
        history_note = " No prior payment history available for this customer."

    # Determine if attention is needed
    needs_attention = status in ("UNPAID", "PARTIALLY_PAID", "SENT") and (
        days_overdue > 0 or amount >= AMOUNT_MEDIUM or len(reasons) >= 2
    )

    if needs_attention:
        summary = (
            f"Invoice {invoice.invoice_number or invoice.paypal_invoice_id} "
            f"(${amount:,.2f} {invoice.currency}) needs attention: "
            f"{len(reasons)} factor(s) identified.{history_note}"
        )
    else:
        summary = (
            f"Invoice {invoice.invoice_number or invoice.paypal_invoice_id} "
            f"does not currently require collection attention.{history_note}"
        )

    return InvoiceAnalysisResponse(
        invoice_id=invoice.paypal_invoice_id,
        invoice_number=invoice.invoice_number,
        customer_name=invoice.customer_name,
        customer_email=invoice.customer_email,
        amount=invoice.amount,
        currency=invoice.currency,
        status=invoice.status,
        due_date=invoice.due_date,
        days_overdue=days_overdue,
        needs_attention=needs_attention,
        attention_reasons=reasons,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Reminder template fallback (when AI unavailable)
# ---------------------------------------------------------------------------

REMINDER_TEMPLATES: Dict[str, Dict[str, str]] = {
    "polite": {
        "subject": "Friendly reminder: Invoice {invoice_number} is due",
        "body": "Dear {customer_name},\n\nI hope you're well. This is a friendly reminder that invoice {invoice_number} for {amount} is due on {due_date}.\n\nIf you've already sent the payment, please disregard this message. Otherwise, we'd appreciate it if you could arrange payment at your earliest convenience.\n\nThank you,\n{business_name}",
    },
    "friendly": {
        "subject": "Quick check-in on invoice {invoice_number}",
        "body": "Hi {customer_name},\n\nJust checking in on invoice {invoice_number} for {amount}, which was due on {due_date}.\n\nPlease let us know if there are any questions or if you need anything from our side to process the payment.\n\nBest regards,\n{business_name}",
    },
    "firm": {
        "subject": "Payment overdue: Invoice {invoice_number}",
        "body": "Dear {customer_name},\n\nOur records show that invoice {invoice_number} for {amount} was due on {due_date} and remains unpaid.\n\nPlease remit payment immediately or contact us to discuss payment arrangements. If you have already sent payment, please provide the transaction details so we can update our records.\n\nRegards,\n{business_name}",
    },
}


def generate_reminder_template(
    invoice: InvoiceSummary,
    tone: str = "polite",
    custom_context: Optional[str] = None,
) -> Dict[str, str]:
    """Generate a reminder draft from a template (no AI required).

    Never invents payment terms or makes legal threats. The tone options
    are limited to polite, friendly, and firm.
    """
    tone_key = tone.lower() if tone.lower() in REMINDER_TEMPLATES else "polite"
    template = REMINDER_TEMPLATES[tone_key]

    customer_name = invoice.customer_name or "Valued Customer"
    amount_str = f"{invoice.amount:,.2f} {invoice.currency}"
    due_date = invoice.due_date or "not specified"
    invoice_number = invoice.invoice_number or invoice.paypal_invoice_id

    subject = template["subject"].format(
        invoice_number=invoice_number,
        customer_name=customer_name,
    )
    body = template["body"].format(
        invoice_number=invoice_number,
        customer_name=customer_name,
        amount=amount_str,
        due_date=due_date,
        business_name="Your Business",
    )

    if custom_context:
        body += f"\n\nAdditional note: {custom_context}"

    return {"subject": subject, "body": body}
