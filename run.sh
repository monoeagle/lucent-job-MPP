#!/bin/bash
# PORT=3000
# HEALTHCHECK=/api/v1/health
# COLOR=#2196F3

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    wait 2>/dev/null
}
trap cleanup EXIT INT TERM

# ── Backend ────────────────────────────────────────────────
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "ERROR: venv not found at $VENV_DIR" >&2
    exit 1
fi

export AUTH_MODE=stub
export CMDB_MODE=stub
export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
export FLASK_APP=app

cd "$PROJECT_DIR"
flask run --port 5000 &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────────────────
set +e
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22 >/dev/null 2>&1
set -e

cd "$PROJECT_DIR/frontend"
[ -d node_modules ] || npm install -q 2>&1
npx vite --port 3000 &
FRONTEND_PID=$!

# Warten bis ein Prozess beendet wird
wait -n 2>/dev/null || wait
