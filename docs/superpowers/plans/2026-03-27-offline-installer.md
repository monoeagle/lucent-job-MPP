# Offline-Installer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Docker-based offline bundle for air-gap installation of MPP on Linux Mint and AlmaLinux 10, with automated Docker package collection and one-command install.

**Architecture:** 3 Docker images (backend, frontend/nginx, postgres). Multi-stage frontend build. Nginx reverse proxy for `/api/` → backend. Bundle script collects images + Docker packages for both distros. Install script loads images + starts compose.

**Tech Stack:** Docker, docker-compose, nginx, bash

**Spec:** `docs/superpowers/specs/2026-03-27-offline-installer-design.md`

---

## File Structure

```
(project root)
├── Dockerfile                  # NEW: Backend image
├── Dockerfile.frontend         # NEW: Frontend multi-stage build
├── nginx.conf                  # NEW: Reverse proxy config
├── docker-compose.yml          # NEW: Production compose
├── docker-compose.dev.yml      # NEW: Dev compose (optional, uses host DB)
├── .dockerignore               # NEW: Build context filter
├── .env.example                # NEW: Configuration template
└── scripts/
    ├── build-bundle.sh         # NEW: Build images + collect packages + create archive
    ├── install.sh              # NEW: Offline install (load images, start compose)
    ├── install-docker.sh       # NEW: Offline Docker install (detect distro, install packages)
    └── uninstall.sh            # NEW: Cleanup (stop, remove images + volumes)
```

---

### Task 1: Dockerfiles + nginx Config

**Files:**
- Create: `Dockerfile`
- Create: `Dockerfile.frontend`
- Create: `nginx.conf`
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore**

```
# .dockerignore
.git
.claude
__pycache__
*.pyc
venv/
.venv/
node_modules/
frontend/node_modules/
frontend/dist/
mpp-docs/
docs/
tests/
*.md
*.zip
.env
```

- [ ] **Step 2: Create Backend Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY stubs/ stubs/
COPY scripts/seed.py scripts/seed.py
COPY alembic.ini .
COPY migrations/ migrations/

ENV FLASK_APP=app
ENV AUTH_MODE=stub
ENV CMDB_MODE=stub
ENV CMDB_STUB_DATA_PATH=./stubs/cmdb/

EXPOSE 5000

# Run migrations, seed, then start Flask
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed.py && flask run --host=0.0.0.0 --port=5000"]
```

- [ ] **Step 3: Create Frontend Dockerfile**

```dockerfile
# Dockerfile.frontend
FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 4: Create nginx.conf**

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # API reverse proxy
    location /api/ {
        proxy_pass http://backend:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

- [ ] **Step 5: Verify builds work**

Run:
```bash
docker build -t mpp-backend .
docker build -t mpp-frontend -f Dockerfile.frontend .
```

- [ ] **Step 6: Commit**

```bash
git add Dockerfile Dockerfile.frontend nginx.conf .dockerignore
git commit -m "feat: add Dockerfiles for backend and frontend, nginx reverse proxy config"
```

---

### Task 2: docker-compose + .env

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: mpp
      POSTGRES_PASSWORD: ${DB_PASSWORD:-mpp}
      POSTGRES_DB: mpp
    volumes:
      - mpp-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mpp"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  backend:
    image: mpp-backend:latest
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://mpp:${DB_PASSWORD:-mpp}@db:5432/mpp
      AUTH_MODE: ${AUTH_MODE:-stub}
      CMDB_MODE: ${CMDB_MODE:-stub}
      CMDB_STUB_DATA_PATH: ./stubs/cmdb/
      JWT_SECRET: ${JWT_SECRET:-change-me-in-production}
      GITLAB_WEBHOOK_SECRET: ${GITLAB_WEBHOOK_SECRET:-}
    restart: unless-stopped

  frontend:
    image: mpp-frontend:latest
    depends_on:
      - backend
    ports:
      - "${MPP_PORT:-80}:80"
    restart: unless-stopped

volumes:
  mpp-data:
```

- [ ] **Step 2: Create .env.example**

```bash
# MPP Offline Installation — Configuration
# Copy to .env and adjust values

# Database
DB_PASSWORD=mpp

# Auth (stub for demo, ldap for production)
AUTH_MODE=stub

# CMDB
CMDB_MODE=stub

# Security
JWT_SECRET=change-me-in-production
GITLAB_WEBHOOK_SECRET=

# Port (frontend served here)
MPP_PORT=80
```

- [ ] **Step 3: Test compose**

```bash
cp .env.example .env
docker compose up -d
# Wait for healthy
docker compose ps
# Check health
curl -s http://localhost/api/v1/health | python3 -m json.tool
# Cleanup
docker compose down
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add docker-compose.yml and .env.example for production deployment"
```

---

### Task 3: Install + Uninstall Scripts

**Files:**
- Create: `scripts/install.sh`
- Create: `scripts/uninstall.sh`

- [ ] **Step 1: Create install.sh**

```bash
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
    echo -e "Fuehre zuerst aus: ${YELLOW}bash scripts/install-docker.sh${NC}"
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
for i in $(seq 1 30); do
    if curl -sf http://localhost:$(grep MPP_PORT .env 2>/dev/null | cut -d= -f2 || echo 80)/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Backend ist bereit"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Backend nicht erreichbar nach 30 Sekunden${NC}"
        echo -e "Pruefe Logs: ${YELLOW}docker compose logs backend${NC}"
        exit 1
    fi
    sleep 1
done

# Done
PORT=$(grep MPP_PORT .env 2>/dev/null | cut -d= -f2 || echo 80)
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  MPP laeuft!                             ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  URL: http://localhost:${PORT}              ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  Login: test-admin / stub-password       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
```

- [ ] **Step 2: Create uninstall.sh**

```bash
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
```

- [ ] **Step 3: Make executable**

```bash
chmod +x scripts/install.sh scripts/uninstall.sh
```

- [ ] **Step 4: Commit**

```bash
git add scripts/install.sh scripts/uninstall.sh
git commit -m "feat: add install.sh and uninstall.sh for offline deployment"
```

---

### Task 4: Docker Installer + Bundle Builder

**Files:**
- Create: `scripts/install-docker.sh`
- Create: `scripts/build-bundle.sh`

- [ ] **Step 1: Create install-docker.sh**

```bash
#!/bin/bash
# Offline Docker Installer — Detects distro and installs Docker from local packages
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG_DIR="$BUNDLE_DIR/docker-packages"

echo -e "${YELLOW}MPP — Offline Docker Installation${NC}"
echo ""

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="$ID"
    DISTRO_LIKE="$ID_LIKE"
else
    echo -e "${RED}Kann Betriebssystem nicht erkennen.${NC}"
    exit 1
fi

echo "Erkannt: $PRETTY_NAME"

install_deb() {
    local dir="$PKG_DIR/mint"
    if [ ! -d "$dir" ] || [ -z "$(ls -A "$dir"/*.deb 2>/dev/null)" ]; then
        echo -e "${RED}Keine .deb-Pakete gefunden in $dir${NC}"
        echo -e "Baue das Bundle neu mit: ${YELLOW}bash scripts/build-bundle.sh${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Installiere Docker aus .deb-Paketen...${NC}"
    sudo dpkg -i "$dir"/*.deb || sudo apt-get install -f -y
    echo -e "${GREEN}✓${NC} Docker installiert"
}

install_rpm() {
    local dir="$PKG_DIR/alma"
    if [ ! -d "$dir" ] || [ -z "$(ls -A "$dir"/*.rpm 2>/dev/null)" ]; then
        echo -e "${RED}Keine .rpm-Pakete gefunden in $dir${NC}"
        echo -e "Baue das Bundle neu mit: ${YELLOW}bash scripts/build-bundle.sh${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Installiere Docker aus .rpm-Paketen...${NC}"
    sudo rpm -ivh "$dir"/*.rpm --nodeps 2>/dev/null || sudo dnf localinstall -y "$dir"/*.rpm
    echo -e "${GREEN}✓${NC} Docker installiert"
}

case "$DISTRO_ID" in
    linuxmint|ubuntu|debian)
        install_deb
        ;;
    almalinux|rocky|rhel|centos|fedora)
        install_rpm
        ;;
    *)
        if echo "$DISTRO_LIKE" | grep -q "debian\|ubuntu"; then
            install_deb
        elif echo "$DISTRO_LIKE" | grep -q "rhel\|fedora"; then
            install_rpm
        else
            echo -e "${RED}Nicht unterstuetzte Distribution: $DISTRO_ID${NC}"
            echo "Unterstuetzt: Linux Mint, Ubuntu, Debian, AlmaLinux, Rocky, RHEL"
            exit 1
        fi
        ;;
esac

# Start Docker
echo ""
echo -e "${YELLOW}Starte Docker-Service...${NC}"
sudo systemctl enable docker
sudo systemctl start docker

# Add current user to docker group
if ! groups | grep -q docker; then
    sudo usermod -aG docker "$USER"
    echo -e "${YELLOW}User '$USER' zur docker-Gruppe hinzugefuegt.${NC}"
    echo -e "${YELLOW}Bitte abmelden und neu anmelden, damit die Aenderung wirkt.${NC}"
fi

echo ""
echo -e "${GREEN}✓ Docker ist bereit: $(docker --version)${NC}"
```

- [ ] **Step 2: Create build-bundle.sh**

```bash
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

# Mint/Ubuntu/Debian packages
if command -v apt-get &> /dev/null; then
    echo "  Sammle .deb-Pakete..."
    cd "$BUNDLE_DIR/docker-packages/mint"
    apt-get download docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin 2>/dev/null || \
        echo -e "  ${YELLOW}Warnung: .deb-Download fehlgeschlagen (nicht auf Debian-System?)${NC}"
    cd "$PROJECT_DIR"
fi

# AlmaLinux/RHEL packages
if command -v dnf &> /dev/null; then
    echo "  Sammle .rpm-Pakete..."
    cd "$BUNDLE_DIR/docker-packages/alma"
    dnf download --resolve docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin 2>/dev/null || \
        echo -e "  ${YELLOW}Warnung: .rpm-Download fehlgeschlagen (nicht auf RHEL-System?)${NC}"
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
echo -e "${GREEN}║  Archiv: ${BUNDLE_NAME}.tar.gz${NC}"
echo -e "${GREEN}║  Groesse: ${ARCHIVE_SIZE}${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  Auf Zielrechner:                        ║${NC}"
echo -e "${GREEN}║  tar xzf ${BUNDLE_NAME}.tar.gz${NC}"
echo -e "${GREEN}║  cd ${BUNDLE_NAME}${NC}"
echo -e "${GREEN}║  bash scripts/install.sh                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
```

- [ ] **Step 3: Make executable**

```bash
chmod +x scripts/install-docker.sh scripts/build-bundle.sh
```

- [ ] **Step 4: Commit**

```bash
git add scripts/install-docker.sh scripts/build-bundle.sh
git commit -m "feat: add install-docker.sh (offline Docker install) and build-bundle.sh (archive builder)"
```

---

### Task 5: Test the Full Flow

- [ ] **Step 1: Build images**

```bash
docker build -t mpp-backend .
docker build -t mpp-frontend -f Dockerfile.frontend .
```

- [ ] **Step 2: Run compose**

```bash
cp .env.example .env
docker compose up -d
```

- [ ] **Step 3: Verify health**

```bash
# Wait for services
sleep 10
# Check backend health
curl -s http://localhost/api/v1/health
# Check frontend serves HTML
curl -s http://localhost/ | head -5
# Check login works
curl -s -X POST http://localhost/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"test-admin"}'
```

- [ ] **Step 4: Cleanup**

```bash
docker compose down -v
```

- [ ] **Step 5: Final commit**

```bash
git commit -m "chore: offline installer complete — Dockerfiles, compose, bundle builder, install scripts"
```
