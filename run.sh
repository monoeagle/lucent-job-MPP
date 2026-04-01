#!/bin/bash
# PORT=5000
# HEALTHCHECK=/health
# COLOR=#2196F3

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# Activate venv
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
exec flask run --port 5000
