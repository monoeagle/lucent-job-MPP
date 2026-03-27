# Offline-Installer — Design Spec

**Ziel:** Docker-basiertes Offline-Bundle fuer Air-Gap-Installation auf Linux Mint (Debian-basiert) und AlmaLinux 10 (RHEL-basiert). Ein Bundle fuer beide Distros, einzige Prereq ist Docker.

---

## Architektur

3 Docker-Images + docker-compose:
- `mpp-backend` — Python 3.12 + Flask + Alembic + Seed-Daten
- `mpp-frontend` — Node Build → nginx Static Serving
- `postgres:16` — PostgreSQL Datenbank

Alle Images werden auf dem Entwicklungsrechner gebaut, via `docker save` als `.tar` exportiert, und auf dem Zielrechner via `docker load` importiert.

## Bundle-Struktur

```
mpp-offline-bundle/
├── images/
│   └── mpp-images.tar              # docker save: alle 3 Images
├── docker-compose.yml               # Production-Compose mit allen Services
├── .env.example                     # Konfigurierbare Variablen
├── docker-packages/
│   ├── mint/                        # .deb-Pakete fuer Docker CE + compose
│   └── alma/                        # .rpm-Pakete fuer Docker CE + compose
├── install-docker.sh                # Auto-Detect Distro, installiert Docker offline
├── install.sh                       # Hauptskript: Docker pruefen, Images laden, starten
├── uninstall.sh                     # Aufraeum-Skript
└── README.md                        # Installationsanleitung
```

## Dockerfiles

### Backend (mpp-backend)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY stubs/ stubs/
COPY scripts/seed.py scripts/seed.py
COPY alembic/ alembic/
COPY alembic.ini .
ENV FLASK_APP=app AUTH_MODE=stub CMDB_MODE=stub
EXPOSE 5000
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed.py && flask run --host=0.0.0.0 --port=5000"]
```

### Frontend (mpp-frontend)

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Nginx-Config leitet `/api/` Requests an Backend weiter (Reverse Proxy).

### PostgreSQL

Standard `postgres:16` Image, kein Custom-Build noetig.

## docker-compose.yml

```yaml
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
      retries: 5

  backend:
    image: mpp-backend:latest
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://mpp:${DB_PASSWORD:-mpp}@db:5432/mpp
      AUTH_MODE: stub
      CMDB_MODE: stub
      JWT_SECRET: ${JWT_SECRET:-change-me-in-production}
    ports:
      - "${BACKEND_PORT:-5000}:5000"

  frontend:
    image: mpp-frontend:latest
    depends_on:
      - backend
    ports:
      - "${FRONTEND_PORT:-80}:80"

volumes:
  mpp-data:
```

## Skripte

### install.sh (Hauptskript)

1. Pruefen ob Docker laeuft, falls nicht → Hinweis auf install-docker.sh
2. `docker load -i images/mpp-images.tar`
3. `.env` aus `.env.example` kopieren falls nicht vorhanden
4. `docker compose up -d`
5. Warten bis Backend healthy
6. URL anzeigen: "MPP laeuft unter http://localhost"

### install-docker.sh (Docker offline installieren)

1. Distro erkennen (Mint/Ubuntu vs AlmaLinux/RHEL)
2. Passende Pakete aus `docker-packages/{mint,alma}/` installieren
3. Docker-Service starten + enablen
4. Aktuellen User zur docker-Gruppe hinzufuegen

### build-bundle.sh (auf Entwicklungsrechner)

1. `docker build -t mpp-backend .`
2. `docker build -t mpp-frontend -f Dockerfile.frontend .`
3. `docker pull postgres:16`
4. `docker save mpp-backend mpp-frontend postgres:16 -o images/mpp-images.tar`
5. Docker-Pakete fuer beide Distros herunterladen (apt/dnf download)
6. Alles in `mpp-offline-bundle/` zusammenpacken
7. `tar czf mpp-offline-bundle.tar.gz mpp-offline-bundle/`

### uninstall.sh

1. `docker compose down -v` (stoppt + loescht Volumes)
2. `docker rmi mpp-backend mpp-frontend postgres:16`

## Prereq-Collector (build-bundle.sh)

Das Skript sammelt alle Prereqs automatisch:

**Docker-Pakete (Mint/Ubuntu):**
```bash
apt-get download docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin
```

**Docker-Pakete (AlmaLinux):**
```bash
dnf download --resolve docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin
```

Diese werden in `docker-packages/{mint,alma}/` abgelegt.

## nginx.conf

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Konfiguration (.env.example)

```
DB_PASSWORD=mpp
JWT_SECRET=change-me-in-production
BACKEND_PORT=5000
FRONTEND_PORT=80
AUTH_MODE=stub
CMDB_MODE=stub
```

## Betroffene Dateien

### Neu erstellen
- `Dockerfile` — Backend
- `Dockerfile.frontend` — Frontend (Multi-Stage)
- `nginx.conf` — Reverse Proxy Config
- `docker-compose.yml` — Production Compose
- `.env.example` — Konfiguration
- `scripts/build-bundle.sh` — Bundle bauen + Prereqs sammeln
- `scripts/install.sh` — Offline-Installation
- `scripts/install-docker.sh` — Docker offline installieren
- `scripts/uninstall.sh` — Aufraeumen
- `.dockerignore` — Build-Context einschraenken

### Nicht aendern
- Anwendungscode (Backend + Frontend)
- Bestehende Skripte (mpp.sh bleibt fuer Dev)
- Tests

## Abgrenzung

- Kein Kubernetes
- Kein automatisches Update-Mechanismus
- Kein TLS/HTTPS (kann spaeter per Reverse Proxy davor)
- Kein Multi-Node Deployment
- Docker-Pakete werden auf dem Entwicklungsrechner heruntergeladen (braucht Internet)
- Getestet fuer Linux Mint 21+ und AlmaLinux 10
