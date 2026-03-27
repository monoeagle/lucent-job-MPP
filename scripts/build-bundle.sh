#!/bin/bash
# MPP Bundle Builder — Builds Docker images, collects packages, creates offline archive
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE_DIR="$PROJECT_DIR/mpp-offline-bundle"
BUNDLE_NAME="mpp-offline-bundle"

echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  MPP Bundle Builder                      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# Clean previous bundle
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR/images" "$BUNDLE_DIR/docker-packages/mint" "$BUNDLE_DIR/docker-packages/alma" "$BUNDLE_DIR/scripts"

# 1. Build Docker images
echo -e "${YELLOW}[1/5] Baue Backend-Image...${NC}"
docker build -t mpp-backend:latest "$PROJECT_DIR"
echo -e "${GREEN}✓${NC} mpp-backend:latest"

echo -e "${YELLOW}[2/5] Baue Frontend-Image...${NC}"
docker build -t mpp-frontend:latest -f "$PROJECT_DIR/Dockerfile.frontend" "$PROJECT_DIR"
echo -e "${GREEN}✓${NC} mpp-frontend:latest"

echo -e "${YELLOW}[3/5] Lade PostgreSQL-Image...${NC}"
docker pull postgres:16
echo -e "${GREEN}✓${NC} postgres:16"

# 2. Save images
echo -e "${YELLOW}[4/5] Exportiere Images...${NC}"
docker save mpp-backend:latest mpp-frontend:latest postgres:16 -o "$BUNDLE_DIR/images/mpp-images.tar"
IMAGE_SIZE=$(du -sh "$BUNDLE_DIR/images/mpp-images.tar" | cut -f1)
echo -e "${GREEN}✓${NC} Images exportiert ($IMAGE_SIZE)"

# 3. Copy compose + config + scripts
cp "$PROJECT_DIR/docker-compose.yml" "$BUNDLE_DIR/"
cp "$PROJECT_DIR/.env.example" "$BUNDLE_DIR/"
cp "$PROJECT_DIR/scripts/install.sh" "$BUNDLE_DIR/scripts/"
cp "$PROJECT_DIR/scripts/uninstall.sh" "$BUNDLE_DIR/scripts/"
cp "$PROJECT_DIR/scripts/install-docker.sh" "$BUNDLE_DIR/scripts/"
chmod +x "$BUNDLE_DIR/scripts/"*.sh

# 4. Collect Docker packages (requires internet)
echo -e "${YELLOW}[5/5] Sammle Docker-Pakete...${NC}"

if command -v apt-get &> /dev/null; then
    echo "  Sammle .deb-Pakete..."
    cd "$BUNDLE_DIR/docker-packages/mint"
    apt-get download docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin 2>/dev/null || \
        echo -e "  ${YELLOW}Hinweis: .deb-Download uebersprungen (Docker-Repo nicht konfiguriert oder nicht auf Debian-System)${NC}"
    cd "$PROJECT_DIR"
fi

if command -v dnf &> /dev/null; then
    echo "  Sammle .rpm-Pakete..."
    cd "$BUNDLE_DIR/docker-packages/alma"
    dnf download --resolve docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin 2>/dev/null || \
        echo -e "  ${YELLOW}Hinweis: .rpm-Download uebersprungen (Docker-Repo nicht konfiguriert oder nicht auf RHEL-System)${NC}"
    cd "$PROJECT_DIR"
fi

echo -e "${GREEN}✓${NC} Pakete gesammelt"

# 5. Create README
cat > "$BUNDLE_DIR/README.md" << 'READMEEOF'
# MPP Offline Installation

## Voraussetzungen
- Linux (Mint, Ubuntu, Debian, AlmaLinux, Rocky, RHEL)
- Docker (wird mitgeliefert falls nicht installiert)

## Installation

### 1. Docker installieren (falls nicht vorhanden)
```bash
sudo bash scripts/install-docker.sh
# Danach abmelden + neu anmelden
```

### 2. MPP starten
```bash
bash scripts/install.sh
```

### 3. Zugriff
- URL: http://localhost (oder konfigurierter Port)
- Login: test-admin / stub-password

## Konfiguration
Bearbeite `.env` fuer Anpassungen (Port, Passwort, etc.)

## Deinstallation
```bash
bash scripts/uninstall.sh
```
READMEEOF

# 6. Create archive
echo ""
echo -e "${YELLOW}Erstelle Archiv...${NC}"
cd "$PROJECT_DIR"
tar czf "${BUNDLE_NAME}.tar.gz" -C "$PROJECT_DIR" "mpp-offline-bundle"
ARCHIVE_SIZE=$(du -sh "${BUNDLE_NAME}.tar.gz" | cut -f1)

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Bundle erstellt!                        ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  Archiv: ${BUNDLE_NAME}.tar.gz           ${NC}"
echo -e "${GREEN}║  Groesse: ${ARCHIVE_SIZE}                ${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  Auf Zielrechner:                        ║${NC}"
echo -e "${GREEN}║  tar xzf ${BUNDLE_NAME}.tar.gz           ${NC}"
echo -e "${GREEN}║  cd ${BUNDLE_NAME}                       ${NC}"
echo -e "${GREEN}║  bash scripts/install.sh                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
