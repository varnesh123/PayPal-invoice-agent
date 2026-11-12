-- 0001_initial.sql
-- Phase 1 (Foundation): initial database structure for the
-- AI-Powered Invoice Collection Agent.
--
-- Schema follows PROJECT_BLUEPRINT.md §12 (Database Schema).
-- Apply this migration to a provisioned Supabase PostgreSQL database.
--
-- NOTE: Do NOT apply until a Supabase project exists and DATABASE_URL is set.
-- See .env.example for required variables.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- users: business owner dashboard account
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- paypal_connections: one per user (PayPal OAuth link; Phase 2+)
-- ---------------------------------------------------------------------------
CREATE TABLE paypal_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paypal_access_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    sandbox_business_email TEXT,
    webhook_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- customers: invoice recipients
-- ---------------------------------------------------------------------------
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- invoices: synced from PayPal Invoicing API v2
-- ---------------------------------------------------------------------------
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paypal_invoice_id TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    invoice_number TEXT,
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL,
    due_date DATE,
    balance_due_cents INTEGER,
    paid_at TIMESTAMPTZ,
    collection_stopped BOOLEAN NOT NULL DEFAULT FALSE,
    next_follow_up DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- invoice_activity: audit trail of status changes
-- ---------------------------------------------------------------------------
CREATE TABLE invoice_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- reminder_history: record of each sent reminder
-- ---------------------------------------------------------------------------
CREATE TABLE reminder_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    approval_id UUID REFERENCES approval_records(id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_preview TEXT,
    paypal_request_id TEXT
);

-- ---------------------------------------------------------------------------
-- customer_messages: logged inbound/outbound customer replies
-- ---------------------------------------------------------------------------
CREATE TABLE customer_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    message_text TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    intent_category TEXT,
    intent_confidence REAL
);

-- ---------------------------------------------------------------------------
-- ai_recommendations: agent draft recommendations
-- ---------------------------------------------------------------------------
CREATE TABLE ai_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    customer_message_id UUID REFERENCES customer_messages(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    content JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- webhook_events: idempotency log for PayPal webhooks
-- ---------------------------------------------------------------------------
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paypal_event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed BOOLEAN NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------------
-- approval_records: human approval gate
-- ---------------------------------------------------------------------------
CREATE TABLE approval_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ai_recommendation_id UUID REFERENCES ai_recommendations(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    decided_at TIMESTAMPTZ,
    editor_note TEXT
);

-- ---------------------------------------------------------------------------
-- Indexes (from blueprint §12 "Important indexes")
-- ---------------------------------------------------------------------------
CREATE INDEX idx_invoices_user_status ON invoices(user_id, status);
CREATE INDEX idx_invoices_paypal_id ON invoices(paypal_invoice_id);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_reminder_history_invoice_sent ON reminder_history(invoice_id, sent_at);
CREATE INDEX idx_webhook_events_paypal_event_id ON webhook_events(paypal_event_id);
CREATE INDEX idx_customer_messages_customer_received ON customer_messages(customer_id, received_at);

-- ---------------------------------------------------------------------------
-- Row-level security (optional, enabled per table when auth is enforced)
-- ---------------------------------------------------------------------------
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
