#!/bin/bash
# MPP Offline Installer — Loads Docker images and starts the application
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  MPP Offline Installer                   ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker ist nicht installiert.${NC}"
    echo -e "Fuehre zuerst aus: ${YELLOW}sudo bash scripts/install-docker.sh${NC}"
    exit 1
fi

if ! docker info &> /dev/null 2>&1; then
    echo -e "${RED}Docker-Daemon laeuft nicht.${NC}"
    echo -e "Starte Docker: ${YELLOW}sudo systemctl start docker${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker gefunden: $(docker --version)"

# Load images
IMAGES_TAR="$BUNDLE_DIR/images/mpp-images.tar"
if [ -f "$IMAGES_TAR" ]; then
    echo ""
    echo -e "${YELLOW}Lade Docker-Images...${NC}"
    docker load -i "$IMAGES_TAR"
    echo -e "${GREEN}✓${NC} Images geladen"
else
    echo -e "${YELLOW}Kein Image-Archiv gefunden — verwende lokale Images${NC}"
fi

# Create .env if not exists
if [ ! -f "$BUNDLE_DIR/.env" ]; then
    cp "$BUNDLE_DIR/.env.example" "$BUNDLE_DIR/.env"
    echo -e "${GREEN}✓${NC} .env erstellt (aus .env.example)"
fi

# Start services
echo ""
echo -e "${YELLOW}Starte Services...${NC}"
cd "$BUNDLE_DIR"
docker compose up -d

# Wait for backend health
echo ""
echo -e "${YELLOW}Warte auf Backend...${NC}"
PORT=$(grep MPP_PORT .env 2>/dev/null | cut -d= -f2 || echo 80)
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${PORT}/api/v1/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Backend ist bereit"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}Backend nicht erreichbar nach 30 Sekunden${NC}"
        echo -e "Pruefe Logs: ${YELLOW}docker compose logs backend${NC}"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  MPP laeuft!                             ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  URL: http://localhost:${PORT}${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  Login: test-admin / stub-password       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
