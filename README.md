# AI-Powered Invoice Collection Agent — Phase 1 (Foundation)

Repo layout:
```
PAYPAL_PROJECT/
├── PROJECT_BLUEPRINT.md   # full specification (do not delete)
├── .env.example           # backend + shared env vars (copy to .env)
├── .gitignore
├── README.md              # this file
├── migrations/
│   └── 0001_initial.sql   # Supabase/PostgreSQL schema (Phase 1)
├── api/                   # FastAPI backend
│   ├── .venv/             # Python virtual environment
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py        # FastAPI app + /health endpoint
│       ├── db.py          # Supabase client + Settings (.env loader)
│       ├── schemas.py     # Pydantic schemas
│       └── auth.py        # auth scaffold (no-op in Phase 1)
└── web/                   # Next.js frontend (Tailwind, TypeScript)
    ├── .env.example       # copy to .env.local
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx   # calls backend /health and shows status
        │   └── globals.css
        └── lib/
            └── api.ts     # typed fetch client (getHealth)
```

## Prerequisites

- Node.js (v20+) and npm
- Python 3.11+ (3.14 used here) with `venv`
- (Phase 2+) Supabase project, PayPal Developer account, OpenAI API key

## 1. One-time setup

```bash
cd /Users/varun/PAYPAL_PROJECT

# Create the Python virtual environment and install backend deps
python3 -m venv api/venv
./api/venv/bin/pip install --upgrade pip
./api/venv/bin/pip install -r api/requirements.txt

# Install frontend deps (already done via create-next-app)
cd web && npm install && cd ..

# Copy env templates (fill in real values before Phase 2)
cp .env.example .env
cp web/.env.example web/.env.local
```

> `.env` and `.env.local` are gitignored — never commit real credentials.

## 2. Run locally

You need two terminals.

### Terminal 1 — Backend (FastAPI)

**Important:** run from the `api/` directory so the `app` package is importable, and use the venv Python.

```bash
cd /Users/varun/PAYPAL_PROJECT/api
source ./venv/bin/activate   # or: . ./venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend is now at `http://localhost:8000`.

Verify:
```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"invoice-collection-agent",...,"database_configured":false}
```

### Terminal 2 — Frontend (Next.js)

```bash
cd /Users/varun/PAYPAL_PROJECT/web
npm run dev
```

The frontend is now at `http://localhost:3000`. It calls `GET /health` on the backend and displays the status.

## 3. Database (Supabase) — needed before Phase 2

Phase 1 runs without Supabase (`database_configured: false` is expected). When you're ready:

1. Create a Supabase project and note the connection string.
2. Set `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY` in `api/.env`.
3. Apply the schema:
   ```bash
   # via the Supabase SQL Editor, or with psql:
   psql "$DATABASE_URL" -f migrations/0001_initial.sql
   ```

## 4. Stop the servers

Press `Ctrl+C` in each terminal, or:
```bash
pkill -f "uvicorn app.main:app"
pkill -f "next dev"
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'fastapi'` (or uvicorn, supabase) | Python venv not activated / deps not installed | Activate `api/venv` and run `pip install -r api/requirements.txt` |
| `ModuleNotFoundError: No module named 'app'` | Running uvicorn from repo root instead of `api/` | `cd api` first, then `uvicorn app.main:app ...` |
| Frontend "page not found" / blank | Dev server not running or wrong port | `cd web && npm run dev`, then open `http://localhost:3000` |
| `address already in use` | A previous server is still running | `pkill -f "uvicorn app.main:app"` and/or `pkill -f "next dev"`, then retry |
