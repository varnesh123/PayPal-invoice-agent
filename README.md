# AI-Powered Invoice Collection Agent

## Quick Start

### One-Command Start

```bash
cd /Users/varun/PAYPAL_PROJECT
./start.sh
```

This starts both services:

| Service | URL | What It Does |
|---------|-----|--------------|
| Backend | `http://localhost:8000` | FastAPI API + all Phase 1-5 endpoints |
| Frontend | `http://localhost:3000` | Next.js dashboard UI |

### Manual Start (Two Terminals)

**Terminal 1 — Backend:**
```bash
cd /Users/varun/PAYPAL_PROJECT/api
source ./venv/bin/activate   # or: . ./venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd /Users/varun/PAYPAL_PROJECT/web
npm run dev
```

### Stop Servers

```bash
pkill -f "uvicorn app.main:app"
pkill -f "next dev"
```

---

## Page-by-Page Guide

| Page | URL | Purpose |
|------|-----|---------|
| **Dashboard** | `http://localhost:3000` | Backend status, environment info, demo mode notice, next steps |
| **Invoices** | `http://localhost:3000/invoices` | Sync demo PayPal invoices, view/filter invoice list by status |
| **Connect PayPal** | `http://localhost:3000/connect-paypal` | Demo mode confirmation, PayPal sandbox connection info |
| **AI Insights** | `http://localhost:3000/ai-insights` | AI prioritization, reminder drafting, payment insights, approval center |
| **Automation** | `http://localhost:3000/automation` | Scheduler controls, scheduled reminders, audit log, integration controls |

---

## Demo Walkthrough (No Credentials Needed)

By default, the app runs in **mock/demo mode** — no PayPal Developer account, no OpenAI API key, no SMTP credentials required.

1. **Open** `http://localhost:3000` — verify backend is running (green status)
2. **Go to** `http://localhost:3000/invoices` — click **"Sync Demo Data"** to load 12 synthetic invoices
3. **Go to** `http://localhost:3000/ai-insights`:
   - View AI-prioritized invoice list (Critical/High/Medium/Low badges)
   - Click **"Draft Reminder"** on an invoice → generates personalized reminder text
   - Edit the reminder body/subject if desired
   - Click **"Approve Draft"** (requires Supabase for persistence; otherwise session-only)
4. **Go to** `http://localhost:3000/automation`:
   - Click **"Process Due Reminders"** — processes scheduled reminders with smart follow-up logic
   - Click **"Send Test Email"** — sends simulated email (no real email delivered)
   - View **Audit Log** — see all system events (reminder drafted, approved, sent, etc.)

---

## What Requires External Credentials (Optional)

| Feature | Environment Variables | Where to Set |
|---------|----------------------|--------------|
| Real PayPal Sandbox | `PAYPAL_MODE=sandbox`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` | `api/.env` |
| Real OpenAI AI | `AI_MODE=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` | `api/.env` |
| Real Email (SMTP) | `EMAIL_MODE=smtp`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` | `api/.env` |
| Database Persistence | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY` | `api/.env` |

**Demo mode works without any of these.** All data is synthetic, no emails are actually sent, and no PayPal API calls are made.

---

## Tests

```bash
cd /Users/varun/PAYPAL_PROJECT/api
source ./venv/bin/activate
./venv/bin/python -m pytest tests/ -v
```

**88 tests pass** covering PayPal mock, AI intelligence, scheduling, email providers, audit logging, approval workflows, and idempotency prevention.

---

## Repository Structure

```
PAYPAL_PROJECT/
├── .env.example              # Backend + shared env vars (copy to .env)
├── .gitignore
├── README.md                 # This file
├── start.sh                  # One-command start (backend + frontend)
├── supabase/
│   ├── config.toml           # Supabase CLI config
│   ├── migrations/
│   │   ├── 0001_initial.sql  # Phase 1: users, invoices, customers, approvals, etc.
│   │   ├── 0002_customer_payment_history.sql  # Phase 4: payment history
│   │   └── 0003_phase5_scheduling.sql  # Phase 5: scheduled reminders, audit log, scheduler jobs
├── api/                      # FastAPI backend
│   ├── .venv/
│   ├── requirements.txt
│   ├── tests/                # 88 tests
│   │   ├── test_mock_provider.py
│   │   ├── test_api_routes.py
│   │   ├── test_ai_intelligence.py
│   │   └── test_phase5_integration.py
│   └── app/
│       ├── __init__.py
│       ├── main.py           # FastAPI app + all routes (Phases 1-5)
│       ├── db.py             # Supabase client + settings + DB helpers
│       ├── schemas.py        # Phase 1 Pydantic schemas
│       ├── auth.py           # Auth scaffold
│       ├── paypal/           # PayPal integration (mock + sandbox)
│       │   ├── __init__.py
│       │   ├── provider.py
│       │   ├── mock.py
│       │   ├── sandbox_provider.py
│       │   └── schemas.py
│       ├── ai/               # AI Intelligence (Phase 4)
│       │   ├── __init__.py
│       │   ├── provider.py
│       │   ├── mock.py
│       │   ├── openai.py
│       │   ├── schemas.py
│       │   ├── rules.py
│       │   └── scheduling_schemas.py
│       ├── email/            # Email Integration (Phase 5)
│       │   ├── __init__.py
│       │   ├── provider.py
│       │   ├── mock_provider.py
│       │   └── smtp_provider.py
│       ├── execution/        # Execution Engine (Phase 5)
│       │   └── __init__.py
│       ├── scheduler/        # Scheduler Engine (Phase 5)
│       │   └── __init__.py
│       └── audit/            # Audit Logging (Phase 5)
│           └── __init__.py
└── web/                      # Next.js frontend
    ├── .env.example
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx              # Dashboard (/)
        │   ├── connect-paypal/       # /connect-paypal
        │   ├── invoices/             # /invoices
        │   ├── ai-insights/          # /ai-insights
        │   ├── automation/           # /automation
        │   └── globals.css
        └── lib/
            └── api.ts                # Typed fetch client (all phases)
```

---

## Architecture Decisions

- **Mock mode by default** — `PAYPAL_MODE=mock`, `AI_MODE=mock`, `EMAIL_MODE=mock`. No credentials needed.
- **Provider abstraction** — PayPal, AI, Email, and Execution all use provider patterns; routes depend on interfaces, not concrete implementations.
- **Human approval gate** — AI drafts reminders; humans must approve before any external action. Phase 4/5 never sends emails automatically.
- **Idempotency** — Reminder execution uses `idempotency_key` to prevent duplicate sends.
- **No credentials in frontend** — All API keys and secrets are backend-only (`api/.env`).
- **Session-only fallback** — When Supabase is not configured, approvals and scheduling live in memory (clearly labeled as "Session" storage).
- **No fabricated data** — Mock mode never claims real PayPal sync or email delivery occurred; all demo data is clearly labeled as synthetic.