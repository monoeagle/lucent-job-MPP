#!/bin/bash
# Start the marketplace portal frontend in development mode
set -e

echo "=== Marketplace Portal - Frontend Dev ==="

cd "$(dirname "$0")/.."

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22 2>/dev/null || {
    echo "Error: Node 22 not available. Run: nvm install 22"
    exit 1
}

cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo ""
echo "Starting Vite dev server on http://localhost:3000"
echo "Backend proxy: /api → http://localhost:5000"
echo ""
echo "Login: test-requester (kein Passwort)"
echo ""

npm run dev
