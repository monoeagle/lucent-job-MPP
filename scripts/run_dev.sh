#!/bin/bash
# Start the marketplace portal in development mode
set -e

echo "=== Marketplace Portal - Dev Mode ==="

export AUTH_MODE=stub
export CMDB_MODE=stub
export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
export FLASK_APP=app

echo "Running database migrations..."
cd "$(dirname "$0")/.."
source venv/bin/activate
alembic upgrade head

echo "Seeding demo data..."
python scripts/seed.py

echo ""
echo "Starting Flask backend on port 5000..."
flask run --port 5000
