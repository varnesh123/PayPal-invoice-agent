"""Pydantic schemas for AI Intelligence module.

All AI request/response bodies use structured schemas so that AI responses
can be validated before being returned to the frontend. No AI output is
ever passed through unvalidated.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, conint, constr


# ---------------------------------------------------------------------------
# Invoice Analysis
# ---------------------------------------------------------------------------

class InvoiceAnalysisRequest(BaseModel):
    """Request to analyze a single invoice for collection attention."""
    invoice_id: str


class AttentionReason(BaseModel):
    """A single reason why an invoice needs attention."""
    factor: str = Field(..., description="e.g. 'days_overdue', 'amount', 'status'")
    description: str = Field(..., description="Human-readable explanation")
    severity: str = Field(..., description="low | medium | high")


class InvoiceAnalysisResponse(BaseModel):
    """Result of analyzing one invoice."""
    invoice_id: str
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float
    currency: str = "USD"
    status: str
    due_date: Optional[str] = None
    days_overdue: int = 0
    needs_attention: bool = False
    attention_reasons: List[AttentionReason] = []
    summary: str = Field(..., description="Plain-language summary of why this invoice does/doesn't need attention")


class BatchAnalysisResponse(BaseModel):
    """Result of analyzing multiple invoices."""
    invoices: List[InvoiceAnalysisResponse]
    total_analyzed: int
    needs_attention_count: int


# ---------------------------------------------------------------------------
# Priority Scoring
# ---------------------------------------------------------------------------

class PriorityLevel(str):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriorityFactor(BaseModel):
    """A single factor contributing to the priority score."""
    name: str
    weight: float
    contribution: float
    explanation: str


class PriorityScoreResponse(BaseModel):
    """Priority score for a single invoice."""
    invoice_id: str
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float
    currency: str = "USD"
    status: str
    due_date: Optional[str] = None
    days_overdue: int = 0
    priority_level: str = Field(..., description="low | medium | high | critical")
    score: float = Field(..., ge=0, le=100, description="0-100 priority score")
    factors: List[PriorityFactor] = []
    explanation: str = Field(..., description="Plain-language explanation of the priority")
    method: str = Field(..., description="'ai' | 'deterministic' | 'fallback'")


class BatchPriorityResponse(BaseModel):
    """Priority scores for multiple invoices, sorted by priority."""
    invoices: List[PriorityScoreResponse]
    total_count: int


# ---------------------------------------------------------------------------
# Reminder Generation
# ---------------------------------------------------------------------------

class ReminderTone(str):
    POLITE = "polite"
    FRIENDLY = "friendly"
    FIRM = "firm"


class ReminderDraftRequest(BaseModel):
    """Request to generate a reminder draft."""
    invoice_id: str
    tone: str = Field(default="polite", description="polite | friendly | firm")
    custom_context: Optional[str] = Field(
        default=None,
        description="Optional user-provided context to include in the reminder",
    )


class ReminderDraftResponse(BaseModel):
    """AI-generated reminder draft (requires human approval before sending)."""
    invoice_id: str
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float
    currency: str = "USD"
    due_date: Optional[str] = None
    tone: str
    subject: str
    body: str
    method: str = Field(..., description="'ai' | 'template' | 'fallback'")
    requires_approval: bool = True


# ---------------------------------------------------------------------------
# Payment Behaviour Insights
# ---------------------------------------------------------------------------

class InsightTrend(str):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class PaymentBehaviourInsight(BaseModel):
    """A single insight about customer payment behaviour."""
    category: str = Field(..., description="e.g. 'late_payment_pattern', 'average_days_late'")
    label: str
    value: Any
    confidence: str = Field(..., description="low | medium | high")
    description: str
    is_estimate: bool = False


class PaymentBehaviourResponse(BaseModel):
    """Payment behaviour analysis for a customer or across all invoices."""
    customer_email: Optional[str] = None
    total_invoices: int
    paid_invoices: int
    unpaid_invoices: int
    average_days_late: Optional[float] = None
    on_time_rate: Optional[float] = None
    trends: List[PaymentBehaviourInsight] = []
    summary: str
    is_estimate: bool = False


# ---------------------------------------------------------------------------
# Approval Workflow
# ---------------------------------------------------------------------------

class ApprovalAction(str):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"


class ApprovalRequest(BaseModel):
    """Request to approve, reject, or edit an AI recommendation."""
    recommendation_id: str
    action: str = Field(..., description="approve | reject | edit")
    edited_content: Optional[Dict[str, Any]] = None
    editor_note: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Result of an approval action."""
    recommendation_id: str
    action: str
    status: str  # "approved" | "rejected" | "edited"
    decided_at: datetime
    editor_note: Optional[str] = None


class ApprovalRecordSummary(BaseModel):
    """Summary of an approval record for history listing."""
    id: str
    recommendation_id: str
    action: str
    status: str
    decided_at: Optional[datetime] = None
    editor_note: Optional[str] = None


class ApprovalsListResponse(BaseModel):
    """List of approval records."""
    records: List[ApprovalRecordSummary]
    total: int


# ---------------------------------------------------------------------------
# AI Configuration / Health
# ---------------------------------------------------------------------------

class AIHealthResponse(BaseModel):
    """AI service health status."""
    ai_mode: str
    configured: bool
    provider: str
    available: bool
