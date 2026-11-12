"""AI Intelligence package.

Exports :func:`get_provider` which returns the active AI provider based on
the ``AI_MODE`` environment variable:

  - ``AI_MODE=openai``  -> OpenAIProvider (real OpenAI API, requires OPENAI_API_KEY)
  - ``AI_MODE=mock``    -> MockAIProvider  (deterministic, no credentials)

Default is ``mock`` so the app is demonstrable without paid API credentials.
Real OpenAI integration is isolated in :mod:`app.ai.openai` for future activation.
"""

from app.ai.provider import AIProvider, AIProviderError, get_provider, get_provider_name
from app.ai.schemas import (
    AIHealthResponse,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalsListResponse,
    ApprovalRecordSummary,
    BatchAnalysisResponse,
    BatchPriorityResponse,
    InvoiceAnalysisResponse,
    PaymentBehaviourResponse,
    PriorityScoreResponse,
    ReminderDraftRequest,
    ReminderDraftResponse,
)

__all__ = [
    "AIProvider",
    "AIProviderError",
    "get_provider",
    "get_provider_name",
    "AIHealthResponse",
    "ApprovalRequest",
    "ApprovalResponse",
    "ApprovalsListResponse",
    "ApprovalRecordSummary",
    "BatchAnalysisResponse",
    "BatchPriorityResponse",
    "InvoiceAnalysisResponse",
    "PaymentBehaviourResponse",
    "PriorityScoreResponse",
    "ReminderDraftRequest",
    "ReminderDraftResponse",
]
