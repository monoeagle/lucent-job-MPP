#!/bin/bash
# MPP Uninstaller — Stops services and removes images/volumes
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}MPP Uninstaller${NC}"
echo ""

cd "$BUNDLE_DIR"

echo -e "${YELLOW}Stoppe Services...${NC}"
docker compose down -v 2>/dev/null || true
echo -e "${GREEN}✓${NC} Services gestoppt, Volumes entfernt"

echo ""
read -p "Docker-Images entfernen? (j/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[jJyY]$ ]]; then
    docker rmi mpp-backend:latest mpp-frontend:latest 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Images entfernt"
else
    echo "Images beibehalten."
fi

echo ""
echo -e "${GREEN}MPP wurde deinstalliert.${NC}"
