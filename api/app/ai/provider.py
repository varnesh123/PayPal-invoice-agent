"""Abstract AI provider base class.

Defines the interface that both the MockAIProvider and OpenAIProvider must
implement. Backend routes depend on this interface, not on a concrete
implementation, so AI_MODE can be switched without touching route logic.

Providers:
  - MockAIProvider:   deterministic, no API key, for testing/demo.
  - OpenAIProvider:   real OpenAI integration (env-configurable API key).
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.ai.schemas import (
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
    AIHealthResponse,
)
from app.paypal.schemas import InvoiceSummary


class AIProviderError(Exception):
    """Raised when an AI provider operation fails."""


class AIProvider(ABC):
    """Abstract AI integration provider."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the provider has the credentials/state it needs."""

    @abstractmethod
    async def health(self) -> AIHealthResponse:
        """Return AI service health status."""

    # ------------------------------------------------------------------
    # Invoice Analysis
    # ------------------------------------------------------------------

    @abstractmethod
    async def analyze_invoice(
        self,
        invoice: InvoiceSummary,
        customer_history: Optional[List[Dict[str, Any]]] = None,
    ) -> InvoiceAnalysisResponse:
        """Analyze a single invoice for collection attention."""

    @abstractmethod
    async def analyze_batch(
        self,
        invoices: List[InvoiceSummary],
    ) -> BatchAnalysisResponse:
        """Analyze multiple invoices for collection attention."""

    # ------------------------------------------------------------------
    # Priority Scoring
    # ------------------------------------------------------------------

    @abstractmethod
    async def score_priority(
        self,
        invoice: InvoiceSummary,
    ) -> PriorityScoreResponse:
        """Calculate priority score for a single invoice."""

    @abstractmethod
    async def score_batch_priority(
        self,
        invoices: List[InvoiceSummary],
    ) -> BatchPriorityResponse:
        """Calculate priority scores for multiple invoices."""

    # ------------------------------------------------------------------
    # Reminder Generation
    # ------------------------------------------------------------------

    @abstractmethod
    async def generate_reminder(
        self,
        request: ReminderDraftRequest,
        invoice: InvoiceSummary,
    ) -> ReminderDraftResponse:
        """Generate a personalized reminder draft (requires human approval)."""

    # ------------------------------------------------------------------
    # Payment Behaviour Insights
    # ------------------------------------------------------------------

    @abstractmethod
    async def generate_insights(
        self,
        invoices: List[InvoiceSummary],
        customer_email: Optional[str] = None,
    ) -> PaymentBehaviourResponse:
        """Generate payment behaviour insights from invoice history."""

    # ------------------------------------------------------------------
    # Approval Workflow
    # ------------------------------------------------------------------

    @abstractmethod
    async def process_approval(
        self,
        request: ApprovalRequest,
    ) -> ApprovalResponse:
        """Process an approve/reject/edit action on an AI recommendation."""

    @abstractmethod
    async def list_approvals(self) -> ApprovalsListResponse:
        """List approval records (history)."""


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

_providers: Dict[str, AIProvider] = {}


def get_provider() -> AIProvider:
    """Return the active AI provider based on AI_MODE env var.

    Defaults to ``mock`` when AI_MODE is unset — no API key required.
    """
    mode = os.environ.get("AI_MODE", "mock").lower()

    if mode not in _providers:
        if mode == "openai":
            from app.ai.openai import OpenAIProvider  # noqa: WPS433

            _providers[mode] = OpenAIProvider()
        else:
            from app.ai.mock import MockAIProvider  # noqa: WPS433

            _providers[mode] = MockAIProvider()

    return _providers[mode]


def get_provider_name() -> str:
    """Return the name of the active provider."""
    return os.environ.get("AI_MODE", "mock").lower()
