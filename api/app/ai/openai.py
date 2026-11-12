"""OpenAI AI provider.

Real OpenAI integration using the Python OpenAI client. Requires
OPENAI_API_KEY environment variable. All outputs are validated against
Pydantic schemas before being returned.

If the API key is missing or the OpenAI call fails, the provider raises
AIProviderError — the backend routes are responsible for falling back to
deterministic rules.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

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
    ReminderTone,
    PriorityLevel,
)
from app.ai.rules import (
    analyze_invoice_for_attention,
    score_priority,
    generate_reminder_template,
    calculate_days_overdue,
)
from app.paypal.schemas import InvoiceSummary

logger = logging.getLogger(__name__)

# System prompt shared across all AI calls — constrains the model to
# safe, explainable behaviour with no invented data.
SYSTEM_PROMPT = """You are an AI assistant for an invoice collection dashboard.

Your job: help a business owner prioritize unpaid invoices, draft payment reminders,
and understand customer payment behaviour.

CRITICAL RULES:
1. NEVER invent customer history, payment dates, or financial data. If information
   is not provided, state that it is unavailable.
2. NEVER make legal threats, claim legal authority, or suggest illegal actions.
3. NEVER invent payment terms, interest rates, or late fees not explicitly stated.
4. NEVER present estimates or predictions as guaranteed outcomes.
5. Always be professional, polite, and concise.
6. Include only invoice details that are provided in the context (invoice number,
   amount, currency, due date, customer name/email).
7. Return ONLY valid JSON matching the requested schema — no markdown, no extra text.
8. Explain your reasoning in plain, transparent language."""

MAX_TOKENS = 1000
TEMPERATURE = 0.3  # Low temperature for consistent, explainable output
REQUEST_TIMEOUT = 30.0  # Seconds


class OpenAIProvider(AIProvider):
    """OpenAI-backed AI provider with graceful failure handling."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._client: Optional[AsyncOpenAI] = None
        if self.api_key:
            self._client = AsyncOpenAI(api_key=self.api_key)

    # ------------------------------------------------------------------
    # Health / configuration
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """True only when OPENAI_API_KEY is set."""
        return bool(self.api_key and self._client is not None)

    async def health(self) -> AIHealthResponse:
        return AIHealthResponse(
            ai_mode="openai",
            configured=self.is_configured(),
            provider="openai",
            available=self.is_configured(),
        )

    # ------------------------------------------------------------------
    # Internal helper: call OpenAI with structured output validation
    # ------------------------------------------------------------------

    async def _chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call OpenAI chat completion and return the raw content string.

        Raises AIProviderError on any failure (missing key, timeout,
        malformed response, API error).
        """
        if not self._client:
            raise AIProviderError(
                "OpenAI client not initialized. Set OPENAI_API_KEY environment variable."
            )

        try:
            completion = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                response_format=response_format,
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as exc:
            logger.warning(f"OpenAI API call failed: {exc}")
            raise AIProviderError(f"OpenAI provider unavailable: {exc}")

        if not completion.choices or not completion.choices[0].message:
            raise AIProviderError("OpenAI returned empty response.")

        content = completion.choices[0].message.content
        if not content or not content.strip():
            raise AIProviderError("OpenAI returned empty content.")

        return content.strip()

    def _parse_json_response(
        self,
        content: str,
        schema_name: str,
    ) -> Dict[str, Any]:
        """Parse and validate a JSON response from OpenAI.

        Strips markdown code fences if present. Raises AIProviderError
        if the response is not valid JSON or fails schema validation.
        """
        # Strip markdown fences if the model wrapped JSON in ```json ... ```
        cleaned = content.strip()
        if cleaned.startswith("```"):
            # Remove opening ```json or ```
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(f"OpenAI returned invalid JSON ({schema_name}): {exc}")
            raise AIProviderError(
                f"OpenAI returned malformed response for {schema_name}."
            )

        if not isinstance(data, dict):
            raise AIProviderError(
                f"OpenAI response for {schema_name} is not a JSON object."
            )

        return data

    # ------------------------------------------------------------------
    # Invoice Analysis
    # ------------------------------------------------------------------

    async def analyze_invoice(
        self,
        invoice: InvoiceSummary,
        customer_history: Optional[List[Dict[str, Any]]] = None,
    ) -> InvoiceAnalysisResponse:
        """Analyze a single invoice using OpenAI, with deterministic fallback."""
        try:
            return await self._analyze_invoice_openai(invoice, customer_history)
        except AIProviderError as exc:
            logger.warning(f"OpenAI analysis failed, using deterministic fallback: {exc}")
            return analyze_invoice_for_attention(invoice, customer_history)

    async def _analyze_invoice_openai(
        self,
        invoice: InvoiceSummary,
        customer_history: Optional[List[Dict[str, Any]]] = None,
    ) -> InvoiceAnalysisResponse:
        history_note = ""
        if customer_history:
            history_note = (
                f"Customer history ({len(customer_history)} records): "
                f"{customer_history}\n"
            )
        else:
            history_note = "No customer payment history provided.\n"

        user_prompt = f"""Analyze this invoice for collection attention:

Invoice ID: {invoice.paypal_invoice_id}
Invoice Number: {invoice.invoice_number or 'Not provided'}
Customer Name: {invoice.customer_name or 'Not provided'}
Customer Email: {invoice.customer_email or 'Not provided'}
Amount: {invoice.amount} {invoice.currency}
Status: {invoice.status}
Due Date: {invoice.due_date or 'Not provided'}

{history_note}

Return JSON with these exact keys:
- "needs_attention": boolean
- "attention_reasons": array of {{"factor": str, "description": str, "severity": "low"|"medium"|"high"}}
- "summary": str (plain-language explanation, mention if history is unavailable)
- "days_overdue": integer (0 if not overdue)

Do not invent customer history. Do not make legal threats. Be concise."""

        content = await self._chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        data = self._parse_json_response(content, "invoice_analysis")

        # Validate and coerce fields with safe defaults
        needs_attention = bool(data.get("needs_attention", False))
        reasons_raw = data.get("attention_reasons", [])
        reasons = []
        if isinstance(reasons_raw, list):
            for r in reasons_raw:
                if isinstance(r, dict):
                    reasons.append({
                        "factor": str(r.get("factor", "unknown")),
                        "description": str(r.get("description", "")),
                        "severity": str(r.get("severity", "low")),
                    })

        days_overdue_raw = data.get("days_overdue")
        try:
            days_overdue = int(days_overdue_raw) if days_overdue_raw is not None else 0
        except (TypeError, ValueError):
            days_overdue = calculate_days_overdue(invoice.due_date)

        summary = str(data.get("summary", "")) or (
            f"Invoice {invoice.invoice_number or invoice.paypal_invoice_id} "
            f"analysis complete."
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
            days_overdue=max(0, days_overdue),
            needs_attention=needs_attention,
            attention_reasons=reasons,
            summary=summary,
        )

    async def analyze_batch(
        self,
        invoices: List[InvoiceSummary],
    ) -> BatchAnalysisResponse:
        """Analyze multiple invoices using OpenAI, one at a time."""
        results = []
        for inv in invoices:
            try:
                result = await self.analyze_invoice(inv)
            except AIProviderError:
                result = analyze_invoice_for_attention(inv)
            results.append(result)

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
        """Calculate priority score using OpenAI, with deterministic fallback."""
        try:
            return await self._score_priority_openai(invoice)
        except AIProviderError as exc:
            logger.warning(f"OpenAI priority failed, using deterministic fallback: {exc}")
            return score_priority(invoice)

    async def _score_priority_openai(
        self,
        invoice: InvoiceSummary,
    ) -> PriorityScoreResponse:
        user_prompt = f"""Assign a collection priority (low, medium, high, critical) and score (0-100) to this invoice:

Invoice ID: {invoice.paypal_invoice_id}
Invoice Number: {invoice.invoice_number or 'Not provided'}
Customer Name: {invoice.customer_name or 'Not provided'}
Amount: {invoice.amount} {invoice.currency}
Status: {invoice.status}
Due Date: {invoice.due_date or 'Not provided'}

Consider: days overdue, outstanding amount, and invoice status.

Return JSON with these exact keys:
- "priority_level": "low" | "medium" | "high" | "critical"
- "score": number (0-100)
- "factors": array of {{"name": str, "weight": number, "contribution": number, "explanation": str}}
- "explanation": str (plain-language, transparent reasoning)

Be concise and do not invent data."""

        content = await self._chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        data = self._parse_json_response(content, "priority_score")

        priority_level = str(data.get("priority_level", "medium")).lower()
        if priority_level not in ("low", "medium", "high", "critical"):
            priority_level = "medium"

        try:
            score = float(data.get("score", 50))
        except (TypeError, ValueError):
            score = 50.0
        score = min(100.0, max(0.0, score))

        factors_raw = data.get("factors", [])
        factors = []
        if isinstance(factors_raw, list):
            for f in factors_raw:
                if isinstance(f, dict):
                    factors.append({
                        "name": str(f.get("name", "unknown")),
                        "weight": float(f.get("weight", 0)),
                        "contribution": float(f.get("contribution", 0)),
                        "explanation": str(f.get("explanation", "")),
                    })

        explanation = str(data.get("explanation", "")) or (
            f"Priority {priority_level}: score {score:.0f}/100."
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
            days_overdue=calculate_days_overdue(invoice.due_date),
            priority_level=priority_level,
            score=score,
            factors=factors,
            explanation=explanation,
            method="ai",
        )

    async def score_batch_priority(
        self,
        invoices: List[InvoiceSummary],
    ) -> BatchPriorityResponse:
        """Calculate priority scores for multiple invoices."""
        scored = []
        for inv in invoices:
            try:
                result = await self.score_priority(inv)
            except AIProviderError:
                result = score_priority(inv)
            scored.append(result)

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
        """Generate a reminder draft using OpenAI, with template fallback."""
        try:
            return await self._generate_reminder_openai(request, invoice)
        except AIProviderError as exc:
            logger.warning(f"OpenAI reminder failed, using template fallback: {exc}")
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

    async def _generate_reminder_openai(
        self,
        request: ReminderDraftRequest,
        invoice: InvoiceSummary,
    ) -> ReminderDraftResponse:
        tone = request.tone if request.tone in ("polite", "friendly", "firm") else "polite"
        custom_context = f"\nAdditional context to incorporate: {request.custom_context}" if request.custom_context else ""

        user_prompt = f"""Write a personalized payment reminder email for this invoice:

Invoice ID: {invoice.paypal_invoice_id}
Invoice Number: {invoice.invoice_number or 'Not provided'}
Customer Name: {invoice.customer_name or 'Not provided'}
Customer Email: {invoice.customer_email or 'Not provided'}
Amount: {invoice.amount} {invoice.currency}
Status: {invoice.status}
Due Date: {invoice.due_date or 'Not provided'}
Tone: {tone}{custom_context}

Requirements:
- Include the invoice number, amount, and due date.
- Do NOT invent payment terms, interest rates, or late fees.
- Do NOT make legal threats or claim legal authority.
- Be professional and concise.
- Do not claim payment has been received.

Return JSON with these exact keys:
- "subject": str (email subject line)
- "body": str (email body, plain text)"""

        content = await self._chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        data = self._parse_json_response(content, "reminder_draft")

        subject = str(data.get("subject", "")) or f"Reminder: Invoice {invoice.invoice_number or invoice.paypal_invoice_id}"
        body = str(data.get("body", "")) or ""

        if not body:
            # Fallback to template if body is empty
            template = generate_reminder_template(invoice, tone, request.custom_context)
            subject = template["subject"]
            body = template["body"]
            method = "template"
        else:
            method = "ai"

        return ReminderDraftResponse(
            invoice_id=invoice.paypal_invoice_id,
            invoice_number=invoice.invoice_number,
            customer_name=invoice.customer_name,
            customer_email=invoice.customer_email,
            amount=invoice.amount,
            currency=invoice.currency,
            due_date=invoice.due_date,
            tone=tone,
            subject=subject,
            body=body,
            method=method,
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
        """Generate payment behaviour insights using OpenAI, with deterministic fallback."""
        try:
            return await self._generate_insights_openai(invoices, customer_email)
        except AIProviderError as exc:
            logger.warning(f"OpenAI insights failed, using deterministic fallback: {exc}")
            # Use mock provider's deterministic logic inline
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
            return PaymentBehaviourResponse(
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
                        description="Deterministic fallback — OpenAI unavailable.",
                        is_estimate=True,
                    )
                ],
                summary=(
                    f"Analyzed {total} invoice(s) using fallback rules. "
                    "OpenAI unavailable — insights are indicative only."
                ),
                is_estimate=True,
            )

    async def _generate_insights_openai(
        self,
        invoices: List[InvoiceSummary],
        customer_email: Optional[str] = None,
    ) -> PaymentBehaviourResponse:
        # Build a compact summary of invoices for the prompt (avoid sending too much data)
        invoice_summaries = []
        for inv in invoices:
            invoice_summaries.append({
                "id": inv.paypal_invoice_id,
                "number": inv.invoice_number,
                "customer_email": inv.customer_email,
                "amount": inv.amount,
                "currency": inv.currency,
                "status": inv.status,
                "due_date": inv.due_date,
            })

        context_note = f"Focus on customer: {customer_email}" if customer_email else "Analyze all customers."

        user_prompt = f"""Analyze payment behaviour from these invoices:

{json.dumps(invoice_summaries, indent=2)}

{context_note}

Return JSON with these exact keys:
- "total_invoices": integer
- "paid_invoices": integer
- "unpaid_invoices": integer
- "average_days_late": number or null
- "on_time_rate": number or null (percentage 0-100)
- "trends": array of {{"category": str, "label": str, "value": any, "confidence": "low"|"medium"|"high", "description": str, "is_estimate": boolean}}
- "summary": str (plain-language, mark estimates as not guaranteed)

Do not invent historical data. Mark all estimates with is_estimate: true. Do not present predictions as guaranteed outcomes."""

        content = await self._chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        data = self._parse_json_response(content, "payment_insights")

        total = int(data.get("total_invoices", len(invoices)))
        paid = int(data.get("paid_invoices", 0))
        unpaid = int(data.get("unpaid_invoices", 0))

        avg_days_late_raw = data.get("average_days_late")
        avg_days_late = float(avg_days_late_raw) if avg_days_late_raw is not None else None

        on_time_rate_raw = data.get("on_time_rate")
        on_time_rate = float(on_time_rate_raw) if on_time_rate_raw is not None else None

        trends_raw = data.get("trends", [])
        trends = []
        if isinstance(trends_raw, list):
            for t in trends_raw:
                if isinstance(t, dict):
                    trends.append(PaymentBehaviourInsight(
                        category=str(t.get("category", "general")),
                        label=str(t.get("label", "Insight")),
                        value=t.get("value"),
                        confidence=str(t.get("confidence", "low")),
                        description=str(t.get("description", "")),
                        is_estimate=bool(t.get("is_estimate", True)),
                    ))

        summary = str(data.get("summary", "")) or (
            f"Analyzed {total} invoice(s) using AI. Insights are indicative, not guaranteed."
        )

        return PaymentBehaviourResponse(
            customer_email=customer_email,
            total_invoices=total,
            paid_invoices=paid,
            unpaid_invoices=unpaid,
            average_days_late=avg_days_late,
            on_time_rate=on_time_rate,
            trends=trends,
            summary=summary,
            is_estimate=True,
        )

    # ------------------------------------------------------------------
    # Approval Workflow (OpenAI doesn't generate these; they're deterministic)
    # ------------------------------------------------------------------

    async def process_approval(
        self,
        request: ApprovalRequest,
    ) -> ApprovalResponse:
        """Process an approval action (deterministic — no AI needed)."""
        from datetime import datetime

        if request.action == "approve":
            status = "approved"
        elif request.action == "reject":
            status = "rejected"
        elif request.action == "edit":
            status = "edited"
        else:
            raise AIProviderError(f"Unknown approval action: {request.action}")

        return ApprovalResponse(
            recommendation_id=request.recommendation_id,
            action=request.action,
            status=status,
            decided_at=datetime.utcnow(),
            editor_note=request.editor_note,
        )

    async def list_approvals(self) -> ApprovalsListResponse:
        """List approvals — OpenAI provider doesn't store them; returns empty."""
        return ApprovalsListResponse(records=[], total=0)
