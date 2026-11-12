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

---

## How PayPal Is Used

### PayPal Invoicing API v2 Integration

The project integrates with PayPal's Invoicing API v2 to retrieve and manage invoices. The integration is abstracted behind a provider interface so the same code works in both mock and sandbox modes.

**PayPal Mock Mode (Default — No Credentials Needed):**
- Generates 12 synthetic invoices with realistic customer names, email addresses, amounts ($50–$15,000), currencies (USD/EUR/GBP/CAD/AUD), and statuses (UNPAID, PAID, PARTIALLY_PAID, SENT, DRAFT, CANCELLED).
- Due dates range from 45 days overdue to 90 days in the future.
- No OAuth tokens are minted, no network calls are made to PayPal, and no real PayPal account is contacted.
- Clearly labeled as "Demo Mode" in the UI.

**PayPal Sandbox Mode (Requires Credentials):**
- Uses OAuth 2.0 Client Credentials grant to obtain an access token from `https://api-m.sandbox.paypal.com/v1/oauth2/token`.
- Calls `GET /v2/invoicing/invoices` to list invoices and `GET /v2/invoicing/invoices/{id}` for details.
- Supports `POST /v2/invoicing/invoices/{id}/remind` to send PayPal-generated reminder emails.
- Webhook support for `INVOICING.INVOICE.PAID` events with RSA-SHA256 signature verification.

### PayPal Authentication Model

The project uses **single-tenant client-credentials OAuth** — the app authenticates as itself against PayPal, not on behalf of individual merchants. Per-user merchant OAuth (Authorization Code grant) is out of MVP scope.

---

## How AI Is Used

### AI Intelligence Module (Phase 4)

The project includes a modular AI agent that analyzes invoices, prioritizes collection efforts, and drafts personalized reminders.

**Mock AI Mode (Default — No API Key Needed):**
- Uses deterministic business rules for all AI functions.
- No OpenAI API key required, no network calls to OpenAI.
- All outputs are transparent and explainable — no black-box behavior.

**OpenAI Mode (Requires `OPENAI_API_KEY`):**
- Uses OpenAI's GPT-4o-mini model via the OpenAI Python SDK.
- All AI outputs are validated against Pydantic schemas before being returned.
- Falls back to deterministic rules if the OpenAI API is unavailable.

### AI Capabilities

1. **Invoice Analysis** — Analyzes each invoice for collection attention based on amount, due date, days overdue, and status. Never invents customer payment history.
2. **Priority Scoring** — Assigns Low/Medium/High/Critical priority using a transparent weighted formula (days overdue 40%, amount 35%, status 25%).
3. **Reminder Generation** — Drafts personalized payment reminders in polite, friendly, or firm tones. Includes invoice number, amount, and due date. Never invents payment terms or legal threats.
4. **Payment Behaviour Insights** — Analyzes payment patterns, on-time rates, and average days late. All estimates are clearly labeled as not guaranteed.
5. **Human Approval Gate** — All AI-generated reminders require human approval before sending. No auto-send.

### AI Safety Rules (System Prompt)

The AI system prompt enforces these rules:
1. Never invent customer history, payment dates, or financial data.
2. Never make legal threats or claim legal authority.
3. Never invent payment terms, interest rates, or late fees.
4. Never present estimates as guaranteed outcomes.
5. Always be professional, polite, and concise.
6. Include only invoice details that are provided in context.
7. Return only valid JSON — no markdown or extra text.

---

## Technologies & Integrations

### Backend (Python/FastAPI)

| Technology | Purpose |
|------------|---------|
| FastAPI 0.162.5 | Web framework + API routing |
| Uvicorn 0.35.0 | ASGI server |
| Pydantic 2.x | Data validation & schemas |
| Pydantic-Settings 2.x | Environment variable management |
| httpx | HTTP client for PayPal API calls |
| Supabase 2.34.1 | PostgreSQL database client |
| cryptography 49.0.0 | X.509 certificate verification for PayPal webhooks |
| OpenAI 1.x | Optional AI integration (gpt-4o-mini) |
| Python 3.14 | Runtime |

### Frontend (Next.js/React)

| Technology | Purpose |
|------------|---------|
| Next.js 16.4.6 | React framework with App Router |
| React 19.3.0 | UI library |
| Tailwind CSS 4.x | Styling |
| TypeScript | Type safety |

### Database

| Technology | Purpose |
|------------|---------|
| Supabase PostgreSQL | Persistent storage for invoices, customers, approvals, scheduled reminders, audit logs |
| Supabase SQL Editor | Migration application interface |

### Testing

| Technology | Purpose |
|------------|---------|
| pytest 8.3.4 | Backend test runner |
| pytest-asyncio 0.26.0 | Async test support |
| httpx 0.28.1 | HTTP test client |

### Sponsor & Third-Party Integrations

| Service | Purpose | Integration Type |
|---------|---------|-----------------|
| **PayPal Developer** | Invoicing API v2, OAuth 2.0, webhooks | Direct REST API (sandbox or mock) |
| **OpenAI** | GPT-4o-mini for AI agent reasoning | Optional API integration (mock by default) |
| **Supabase** | PostgreSQL database, auth | Optional (session-only fallback available) |
| **SMTP (optional)** | Email delivery for reminders | Optional (mock by default) |

### No Sponsor Integrations

This project does **not** integrate with APIMatic, Postman, Astro, Render, or any other sponsor platforms. All integrations listed above are direct API integrations or open-source libraries. If you wish to add sponsored integrations, they can be added as additional provider implementations following the existing provider pattern.

---

## License

MIT License — see [LICENSE](LICENSE) file.