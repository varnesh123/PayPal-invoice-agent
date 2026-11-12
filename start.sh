#!/usr/bin/env bash
# Convenience script: start backend + frontend for Phase 1.
# Run from the repo root: ./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$ROOT/api"
WEB_DIR="$ROOT/web"

echo "==> Stopping any previously running servers..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

if [ ! -d "$API_DIR/venv" ]; then
  echo "==> Creating Python venv and installing backend deps..."
  python3 -m venv "$API_DIR/venv"
  "$API_DIR/venv/bin/pip" install --quiet --upgrade pip
  "$API_DIR/venv/bin/pip" install --quiet -r "$API_DIR/requirements.txt"
fi

echo "==> Starting backend on http://localhost:8000 ..."
cd "$API_DIR"
source ./venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/invoice_backend.log 2>&1 &
BACKEND_PID=$!
echo "    backend PID: $BACKEND_PID"

echo "==> Installing frontend deps (if needed) and starting frontend on http://localhost:3000 ..."
cd "$WEB_DIR"
if [ ! -d node_modules ]; then
  npm install --quiet
fi
nohup npm run dev > /tmp/invoice_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "    frontend PID: $FRONTEND_PID"

sleep 4
echo ""
echo "==> Services started."
echo "    Backend:  http://localhost:8000/health"
echo "    Frontend: http://localhost:3000"
echo ""
echo "Logs: tail -f /tmp/invoice_backend.log   tail -f /tmp/invoice_frontend.log"
echo "Stop: pkill -f 'uvicorn app.main:app' && pkill -f 'next dev'"
