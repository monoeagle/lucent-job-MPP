# Marketplace Portal (MPP)

Self-Service-Portal fuer automatisierte IT-Service-Provisionierung. Benutzer bestellen VMs aus einem Servicekatalog mit vollstaendigem Genehmigungs- und Provisioning-Workflow.

**Version:** 1.0.0 | **Tests:** 862 (756 Backend + 106 Frontend) | **Endpoints:** 96

## Tech Stack

| Layer | Technologie |
|-------|------------|
| Backend | Python 3.12, Flask 3.1, SQLAlchemy 2.0, PostgreSQL |
| Frontend | React 19, TypeScript, Vite 6, TailwindCSS 4, recharts |
| Auth | JWT (Stub + LDAP) |
| Provisioning | OpenTofu via GitLab Pipelines |

## Features

- **Service Catalog** — Template-basierter Servicekatalog mit Parametervalidierung
- **Shop Wizard** — Wizard (Step-by-Step) oder Formular-Ansicht, umschaltbar
- **Bestellungen** — Vollstaendiger Order-Lifecycle (Draft → Validated → Submitted → Done)
- **Gruppen + Quantity** — Cluster-Bestellungen mit Per-Instance-Parametern
- **Approval-Workflow** — Regelbasierte Genehmigungen mit Bulk-Aktionen
- **Subscriptions** — Lifecycle-Management (Change, Cancel) mit Approval
- **Notifications** — In-App mit read/unread, E-Mail-Stub, Event-Trigger
- **Dashboard** — Statistiken, Charts (recharts), globale Suche
- **DSGVO** — Backend-Middleware zur Anonymisierung personenbezogener Daten
- **Rollen** — requester, approver, admin, superadmin
- **Abhaengigkeitsmatrix** — 15 Cross-Field-Dependencies reduzieren ~11.6M auf ~45K Kombinationen
- **Offline-Installer** — Docker-basiertes Deployment (Mint + AlmaLinux)
- **Screenshot-Tool** — Playwright-basiert, WebP, pro Benutzerrolle

## Schnellstart

```bash
# Dev Launcher starten
bash scripts/mpp.sh

# Oder manuell:
source venv/bin/activate
export AUTH_MODE=stub CMDB_MODE=stub DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
flask run --port 5000        # Backend
cd frontend && npm run dev   # Frontend auf :3000
```

## Demo-Zugaenge (Stub-Modus)

| Benutzer | Rolle | Beschreibung |
|----------|-------|-------------|
| test-requester | requester | Besteller |
| test-approver | approver | Genehmiger |
| test-admin | admin | Administrator |
| test-multi | requester + approver + admin | Alle Standardrollen |
| test-superadmin | superadmin | System-Administration (Rules, Audit, DSGVO) |

Passwort: `stub-password` (oder leer im Stub-Modus)

## Projektstruktur

```
app/                    # Backend (Flask)
├── api/v1/            # 17 REST-Module, 96 Endpoints
├── core/              # Config, Auth, Errors, Middleware (DSGVO)
├── data/              # Models (15 Tabellen), Repositories, Clients
├── domain/            # Entities, Value Objects
└── services/          # 13 Business-Logic-Services

frontend/src/          # Frontend (React)
├── api/               # 10 API-Client-Module
├── components/        # UI-Komponenten (ParameterForm, Dashboard, Orders)
├── hooks/             # 7 tanstack-query Hook-Module
├── pages/             # 17 Seiten
├── store/             # zustand Auth-Store
└── types/             # TypeScript-Typen

scripts/               # Dev-Tools
├── mpp.sh             # Dev Launcher (Backend, Frontend, Tests, DB Reset)
├── seed.py            # Demo-Daten (2 Templates, 8 Orders, Notifications)
├── screenshot_tool.py # UI-Screenshots (Playwright, WebP)
├── build-bundle.sh    # Docker Offline-Bundle
└── install.sh         # Offline-Installation
```

## Tests

```bash
# Backend (pytest)
source venv/bin/activate
DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/ -q

# Frontend (vitest)
cd frontend && npx vitest run

# Oder ueber den Launcher: bash scripts/mpp.sh → [9]
```

## Lizenz

Tobias Philipp / Lucent Trails — Alle Rechte vorbehalten.
