-- 0002_customer_payment_history.sql
-- Phase 4: Customer payment history tracking.
--
-- This table records ONLY genuine invoice payment events.
-- Reminder activity, AI analysis, approval actions, and other
-- application events are NOT recorded here. Customer payment
-- behavior is derived exclusively from this table.
--
-- Do NOT run automatically — apply manually via Supabase SQL Editor or psql.
-- Do NOT delete or modify existing data from 0001_initial.sql.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- customer_payment_history: genuine payment events only
-- ---------------------------------------------------------------------------
CREATE TABLE customer_payment_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    customer_email TEXT NOT NULL,
    customer_name TEXT,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    paypal_invoice_id TEXT,
    payment_amount_cents INTEGER NOT NULL,
    payment_currency TEXT NOT NULL DEFAULT 'USD',
    payment_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payment_method TEXT,  -- e.g., 'paypal', 'bank_transfer', 'check'
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX idx_customer_payment_history_customer_email ON customer_payment_history(customer_email);
CREATE INDEX idx_customer_payment_history_invoice_id ON customer_payment_history(invoice_id);
CREATE INDEX idx_customer_payment_history_paypal_invoice_id ON customer_payment_history(paypal_invoice_id);
CREATE INDEX idx_customer_payment_history_payment_date ON customer_payment_history(payment_date);
CREATE INDEX idx_customer_payment_history_user_id ON customer_payment_history(user_id);
