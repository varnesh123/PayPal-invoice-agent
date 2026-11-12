# AI-Powered Invoice Collection Agent — Phase 4 (AI Intelligence)

Repo layout:
```
PAYPAL_PROJECT/
├── PROJECT_BLUEPRINT.md   # full specification (do not delete)
├── .env.example           # backend + shared env vars (copy to .env)
├── .gitignore
├── README.md              # this file
├── start.sh               # convenience script: starts backend + frontend
├── supabase/              # Supabase CLI project layout
│   ├── config.toml        # Supabase CLI configuration
│   └── migrations/
│       └── 0001_initial.sql   # SQL schema (moved from migrations/)
├── api/                   # FastAPI backend
│   ├── .venv/             # Python virtual environment
│   ├── requirements.txt
│   ├── tests/             # pytest suite (62 tests)
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_mock_provider.py
│   │   ├── test_api_routes.py
│   │   └── test_ai_intelligence.py
│   └── app/
│       ├── __init__.py
│       ├── main.py        # FastAPI app + all routes (incl. Phase 4 AI routes)
│       ├── db.py          # Supabase client + Settings + demo user + approval helpers
│       ├── schemas.py     # Pydantic schemas
│       ├── auth.py        # auth scaffold (no-op in Phase 1/2)
│       ├── paypal/        # PayPal integration layer
│       │   ├── __init__.py        # provider factory (PAYPAL_MODE)
│       │   ├── provider.py        # abstract base class
│       │   ├── mock.py            # mock/demo provider (PAYPAL_MODE=mock)
│       │   ├── sandbox_provider.py # real PayPal REST (PAYPAL_MODE=sandbox)
│       │   └── schemas.py         # PayPal request/response schemas
│       └── ai/              # AI Intelligence layer (Phase 4)
│           ├── __init__.py        # provider factory (AI_MODE)
│           ├── provider.py        # abstract AI base class + factory
│           ├── mock.py            # MockAIProvider (deterministic, no API key)
│           ├── openai.py          # OpenAIProvider (real OpenAI, env-configurable)
│           ├── schemas.py         # Pydantic schemas for AI requests/responses
│           └── rules.py           # Deterministic business rules (fallback)
└── web/                   # Next.js frontend (Tailwind, TypeScript)
    ├── .env.example       # copy to .env.local
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx           # dashboard (shows demo mode banner)
        │   ├── connect-paypal/
        │   │   └── page.tsx       # shows Demo Mode, never falsely connects
        │   ├── invoices/
        │   │   └── page.tsx       # listing + status filter + sync button
        │   ├── ai-insights/
        │   │   └── page.tsx       # AI Insights: priority, reminders, insights, approvals
        │   └── globals.css
        └── lib/
            └── api.ts             # typed fetch client (incl. Phase 4 AI client)
```

## Prerequisites

- Node.js (v20+) and npm
- Python 3.11+ (3.14 used here) with `venv`
- (Optional, for persistence) Supabase project
- (Optional, for real AI) OpenAI API key

## 1. One-time setup

```bash
cd /Users/varun/PAYPAL_PROJECT

# Create the Python virtual environment and install backend deps
python3 -m venv api/venv
./api/venv/bin/pip install --upgrade pip
./api/venv/bin/pip install -r api/requirements.txt

# Install frontend deps
cd web && npm install && cd ..

# Copy env templates (fill in real values for sandbox/OpenAI mode)
cp .env.example .env
cp web/.env.example web/.env.local
```

> `.env` and `.env.local` are gitignored — never commit real credentials.

## 2. Run locally (demo mode — no credentials needed)

By default `PAYPAL_MODE=mock` and `AI_MODE=mock`, so the app works immediately
with synthetic demo data and deterministic AI rules:

```bash
# One command starts both backend (port 8000) and frontend (port 3000)
./start.sh
```

Or manually in two terminals:

```bash
# Terminal 1 — Backend
cd /Users/varun/PAYPAL_PROJECT/api
source ./venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Frontend
cd /Users/varun/PAYPAL_PROJECT/web
npm run dev
```

Verify:
- Backend: `curl http://localhost:8000/health`
- AI health: `curl http://localhost:8000/ai/health`
- Frontend: `http://localhost:3000` (dashboard), `/invoices`, `/connect-paypal`, `/ai-insights`

## 3. Demo mode workflow (no PayPal or OpenAI credentials needed)

1. Open `http://localhost:3000/connect-paypal` — shows "Demo Mode Active", never claims PayPal is connected.
2. Open `http://localhost:3000/invoices` — click **"Sync Demo Data"** to load 12 synthetic invoices.
3. Open `http://localhost:3000/ai-insights` — view AI-powered:
   - **Collection Priority Overview** — invoices ranked by urgency (Low/Medium/High/Critical) with transparent factor breakdown
   - **AI Reminder Draft** — generate polite/friendly/firm reminder drafts (requires human approval before sending)
   - **Payment Behaviour Insights** — on-time rates, average days late, trend analysis (marked as estimates, not guarantees)
   - **Approval History** — track approve/reject/edit decisions on AI recommendations
4. Use status filter chips on the Invoices page to view UNPAID, PAID, SENT, etc.

## 4. Switching to real integrations

### Real PayPal Sandbox (`PAYPAL_MODE=sandbox`)

1. Create a PayPal Developer sandbox app at https://developer.paypal.com/dashboard/
2. Set in `api/.env`:
   ```
   PAYPAL_MODE=sandbox
   PAYPAL_CLIENT_ID=your-sandbox-client-id
   PAYPAL_CLIENT_SECRET=your-sandbox-client-secret
   PAYPAL_WEBHOOK_ID=your-sandbox-webhook-id
   ```
3. Register `https://<your-backend>/webhooks/paypal` in the PayPal Developer Portal.

### Real OpenAI (`AI_MODE=openai`)

1. Get an API key from https://platform.openai.com/
2. Set in `api/.env`:
   ```
   AI_MODE=openai
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL=gpt-4o-mini
   ```
3. Restart the backend. AI routes will use OpenAI with deterministic fallback if the API is unavailable.

**Important:** Mock mode never mints OAuth tokens, never contacts PayPal, and never calls OpenAI. All AI outputs in mock mode come from transparent, explainable business rules.

## 5. Database (Supabase) — migration workflow

The Supabase schema lives at `supabase/migrations/0001_initial.sql`. This is the standard Supabase CLI layout.

### Migration workflow

1. **Provision a Supabase project** at https://supabase.com/
2. **Set env vars** in `api/.env`:
   ```
   DATABASE_URL=postgresql://postgres:<password>@db..supabase.co:5432/postgres
   SUPABASE_URL=https://.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
   SUPABASE_ANON_KEY=<anon-key>
   ```
3. **Apply the migration manually** (do NOT apply automatically):
   ```bash
   # Option A: via Supabase SQL Editor (web UI)
   # Copy the contents of supabase/migrations/0001_initial.sql and run it.

   # Option B: via psql
   psql "$DATABASE_URL" -f supabase/migrations/0001_initial.sql
   ```

4. **Verify** the tables exist:
   ```bash
   psql "$DATABASE_URL" -c "\dt"
   ```

> Migrations are NOT applied automatically. Do not delete existing database data.

## 6. Run tests

```bash
cd /Users/varun/PAYPAL_PROJECT/api
source ./venv/bin/activate
./venv/bin/python -m pytest tests/ -v
```

62 tests cover: PayPal mock provider, API routes, AI priority scoring, reminder generation,
insights, approval workflows, malformed response handling, and the "no credentials needed"
guarantee.

## 7. Stop the servers

```bash
pkill -f "uvicorn app.main:app"
pkill -f "next dev"
```

## 8. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'fastapi'` | venv not activated / deps missing | Activate `api/venv` and `pip install -r api/requirements.txt` |
| `ModuleNotFoundError: No module named 'app'` | Running uvicorn from repo root | `cd api` first, then `uvicorn app.main:app ...` |
| Frontend blank / 404 | Dev server not running | `cd web && npm run dev`, open `http://localhost:3000` |
| `address already in use` | Previous server still running | `pkill -f "uvicorn app.main:app" && pkill -f "next dev"` |
| Sync shows 0 invoices upserted | Supabase not configured | `database_configured: false` is expected without Supabase; mock data still displays from the provider |
| `PAYPAL_MODE=sandbox` fails with 401 | Missing/invalid sandbox credentials | Set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` in `api/.env` |
| `AI_MODE=openai` fails | Missing OpenAI API key | Set `OPENAI_API_KEY` in `api/.env`; fallback to deterministic rules if unavailable |

## 9. Key design decisions

- **PAYPAL_MODE=mock (default):** Synthetic invoice data, no PayPal credentials, no OAuth tokens. Fully demonstrable offline.
- **PAYPAL_MODE=sandbox:** Real PayPal client-credentials OAuth + Invoicing API v2. Isolated in `app/paypal/sandbox_provider.py`.
- **AI_MODE=mock (default):** Deterministic AI replacement, no API key, no network calls. Outputs come from transparent business rules.
- **AI_MODE=openai:** Real OpenAI integration with graceful fallback to deterministic rules if the API is unavailable.
- **Provider abstraction:** Both PayPal and AI use provider patterns — routes depend on interfaces, not concrete implementations.
- **Never fake auth:** Mock modes never return `connected: true` and never mint tokens. They explicitly report demo mode.
- **No AI keys in frontend:** All AI calls go through the backend; `OPENAI_API_KEY` is never exposed to the browser.
- **Human approval gate:** AI reminder drafts require explicit approval before any external action. Phase 4 does not send emails.
