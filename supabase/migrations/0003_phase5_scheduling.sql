-- 0003_phase5_scheduling.sql
-- Phase 5: Automated reminder scheduling, execution engine, audit logs.
--
-- These tables support:
--   - scheduled_reminders: reminders approved for future execution
--   - audit_log: comprehensive activity and audit trail
--   - scheduler_jobs: persistent scheduler job records (survive restarts)
--
-- Do NOT run automatically — apply manually via Supabase SQL Editor or psql.
-- Do NOT delete or modify existing data from 0001_initial.sql or 0002_customer_payment_history.sql.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- scheduled_reminders: reminders approved for future execution
-- ---------------------------------------------------------------------------
CREATE TABLE scheduled_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ai_recommendation_id UUID REFERENCES ai_recommendations(id) ON DELETE SET NULL,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    paypal_invoice_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_name TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    tone TEXT NOT NULL DEFAULT 'polite',
    channel TEXT NOT NULL DEFAULT 'email',  -- email, paypal_remind
    status TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled, sent, failed, cancelled, skipped
    scheduled_for TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    idempotency_key TEXT UNIQUE NOT NULL,  -- PayPal-Request-Id or email Message-ID
    delivery_attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- audit_log: comprehensive activity and audit trail
-- ---------------------------------------------------------------------------
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,  -- invoice_analyzed, recommendation_generated, reminder_drafted, approval_requested, approved, rejected, reminder_scheduled, reminder_sent, reminder_failed, delivery_failed, invoice_status_changed, automation_paused, automation_resumed
    event_category TEXT NOT NULL,  -- invoice, recommendation, reminder, approval, delivery, automation, system
    resource_type TEXT,  -- invoice, reminder, approval, email, scheduler_job
    resource_id TEXT,
    actor TEXT NOT NULL DEFAULT 'system',  -- system, user, scheduler
    details JSONB,  -- flexible event payload
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- scheduler_jobs: persistent scheduler job records (survive restarts)
-- ---------------------------------------------------------------------------
CREATE TABLE scheduler_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name TEXT NOT NULL,
    job_type TEXT NOT NULL,  -- reminder_due_check, invoice_sync, webhook_processing
    status TEXT NOT NULL DEFAULT 'active',  -- active, paused, disabled
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    interval_seconds INTEGER NOT NULL DEFAULT 300,  -- default 5 minutes
    run_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX idx_scheduled_reminders_user_id ON scheduled_reminders(user_id);
CREATE INDEX idx_scheduled_reminders_status ON scheduled_reminders(status);
CREATE INDEX idx_scheduled_reminders_scheduled_for ON scheduled_reminders(scheduled_for);
CREATE INDEX idx_scheduled_reminders_paypal_invoice_id ON scheduled_reminders(paypal_invoice_id);
CREATE INDEX idx_scheduled_reminders_idempotency_key ON scheduled_reminders(idempotency_key);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_event_category ON audit_log(event_category);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

CREATE INDEX idx_scheduler_jobs_status ON scheduler_jobs(status);
CREATE INDEX idx_scheduler_jobs_next_run_at ON scheduler_jobs(next_run_at);
