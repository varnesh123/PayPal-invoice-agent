"""Phase 5 scheduling schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScheduledReminderBase(BaseModel):
    """Base model for scheduled reminders."""
    ai_recommendation_id: Optional[str] = None
    invoice_id: Optional[str] = None
    paypal_invoice_id: str
    customer_email: str
    customer_name: Optional[str] = None
    subject: str
    body: str
    tone: str = Field(default="polite", description="polite | friendly | firm")
    channel: str = Field(default="email", description="email | paypal_remind")
    scheduled_for: datetime
    max_attempts: int = Field(default=3, ge=1, le=10)


class ScheduledReminderCreate(ScheduledReminderBase):
    """Request to schedule a reminder."""
    pass


class ScheduledReminderResponse(BaseModel):
    """Response for a scheduled reminder."""
    id: str
    user_id: str
    ai_recommendation_id: Optional[str] = None
    invoice_id: Optional[str] = None
    paypal_invoice_id: str
    customer_email: str
    customer_name: Optional[str] = None
    subject: str
    body: str
    tone: str
    channel: str
    status: str  # scheduled | sent | failed | cancelled | skipped
    scheduled_for: datetime
    sent_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    idempotency_key: str
    delivery_attempts: int
    max_attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ScheduledRemindersListResponse(BaseModel):
    """List of scheduled reminders."""
    reminders: List[ScheduledReminderResponse]
    total: int


class ScheduleReminderRequest(BaseModel):
    """Request to schedule a reminder from an approved draft."""
    recommendation_id: str
    scheduled_for: datetime
    tone: str = Field(default="polite", description="polite | friendly | firm")
    channel: str = Field(default="email", description="email | paypal_remind")


class CancelReminderRequest(BaseModel):
    """Request to cancel a scheduled reminder."""
    reminder_id: str
    reason: Optional[str] = None


class SchedulerJobBase(BaseModel):
    """Base model for scheduler jobs."""
    job_name: str
    job_type: str
    interval_seconds: int = Field(default=300, ge=60, le=86400)


class SchedulerJobResponse(BaseModel):
    """Response for a scheduler job."""
    id: str
    job_name: str
    job_type: str
    status: str  # active | paused | disabled
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    interval_seconds: int
    run_count: int
    failure_count: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExecutionResult(BaseModel):
    """Result of executing a scheduled reminder."""
    reminder_id: str
    status: str  # sent | failed | skipped
    channel: str
    idempotency_key: str
    executed_at: datetime
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AutomationStatus(BaseModel):
    """Overall automation system status."""
    scheduler_running: bool
    total_scheduled_reminders: int
    pending_reminders: int
    sent_reminders: int
    failed_reminders: int
    cancelled_reminders: int
    next_job_run: Optional[datetime] = None
    storage_backend: str  # database | session