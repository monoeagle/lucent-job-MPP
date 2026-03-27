# Projektstruktur

Vollstaendige Verzeichnisstruktur des MPP-Projekts.

---

## Uebersicht

```
lucent-app-mpp-TDD/
├── app/                          # Backend (Python/Flask)
│   ├── __init__.py               # Flask App Factory
│   ├── api/v1/                   # REST-Endpoints (17 Module)
│   ├── core/                     # Config, Auth-Middleware, Errors
│   ├── data/
│   │   ├── clients/              # CMDB-Stub, GitLab-Client
│   │   ├── db/
│   │   │   ├── models/           # SQLAlchemy-Modelle (15 Tabellen)
│   │   │   └── session.py        # Engine, SessionFactory
│   │   └── repositories/         # Repository-Pattern
│   ├── domain/                   # Entities, Value Objects, Status
│   └── services/                 # Business Logic (13 Services)
├── frontend/                     # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── api/                  # API-Module (10 Dateien)
│   │   ├── components/           # UI-Komponenten
│   │   │   ├── catalog/          # Catalog-spezifisch
│   │   │   ├── Layout/           # AppLayout, Sidebar, Header
│   │   │   ├── orders/           # Order-spezifisch
│   │   │   └── ParameterForm/    # Dynamische Formular-Felder
│   │   ├── hooks/                # tanstack-query Hooks
│   │   ├── pages/                # 17 Seiten (inkl. admin/)
│   │   ├── store/                # zustand Auth-Store
│   │   └── types/                # TypeScript-Typen
│   └── tests/                    # Frontend-Tests (vitest)
├── migrations/versions/          # Alembic-Migrationen
├── stubs/
│   ├── cmdb/                     # YAML-Daten (4 Dateien)
│   └── gitlab_mock.py            # GitLab-Pipeline-Simulation
├── tests/                        # Backend-Tests (756)
│   ├── unit/                     # Unit-Tests
│   ├── integration/              # Integrationstests
│   └── e2e/                      # End-to-End-Tests
├── scripts/
│   ├── mpp.sh                    # Interaktiver Dev-Launcher
│   ├── seed.py                   # Demo-Daten laden
│   ├── screenshot.py             # Playwright Screenshot-Tool (WebP)
│   └── bundle-builder.sh         # Offline-Bundle erstellen
├── docs/specs/                   # Feature-Spezifikationen
├── mpp-docs/                     # Zensical-Dokumentationsseite
├── Dockerfile                    # Multi-Stage Docker-Build
├── docker-compose.yml            # Docker-Orchestrierung
├── requirements.txt              # Python-Abhaengigkeiten
├── pytest.ini                    # pytest-Konfiguration
├── alembic.ini                   # Alembic-Konfiguration
└── CHANGELOG.md                  # Versionshistorie
```

---

## Backend (`app/`)

### `app/api/v1/` — REST-Endpoints

Flask-Blueprints, ein Modul pro Feature-Bereich. Kein direkter Datenbankzugriff — alles ueber Services.

### `app/core/` — Querschnittsfunktionen

- `config.py` — Konfiguration aus Environment-Variablen, Auth-Mode-Validierung
- `auth.py` — JWT-Middleware (`login_required`, `role_required`)
- `errors.py` — Fehlerklassen (ValidationError, NotFoundError, ForbiddenError, ...)

### `app/data/` — Datenzugriff

- `db/models/` — SQLAlchemy-Modelle (15 Tabellen)
- `db/session.py` — Engine und SessionFactory
- `repositories/` — Repository-Pattern fuer Datenbankzugriff
- `clients/` — Externe API-Clients (CMDB, GitLab)

### `app/domain/` — Domaenenmodell

Reine Datenklassen ohne Framework-Abhaengigkeiten. Status-Enums, Value Objects, Entity-Definitionen.

### `app/services/` — Business-Logik

13 Services mit klar abgegrenzten Verantwortlichkeiten. Orchestrieren Repositories, Clients und Domain-Logik.

---

## Frontend (`frontend/`)

### `src/api/` — HTTP-Client

10 Module fuer die Kommunikation mit dem Backend. Basis-Client mit automatischem Auth-Header.

### `src/components/` — UI-Komponenten

- `Layout/` — AppLayout, Fixed Sidebar, Header mit dynamischen Titeln, ProtectedRoute
- `ParameterForm/` — Dynamische Formular-Felder (5 Feldtypen)
- `catalog/` — Catalog-spezifische Komponenten
- `orders/` — ContextSelector, OrderItemCard, WizardView, FormView, RequestSummary
- `GlobalSearch.tsx` — Globale Suche im Header
- `StatCard.tsx` — Dashboard-Statistikkarte
- `StepIndicator.tsx` — Wizard-Fortschrittsanzeige

### `src/hooks/` — tanstack-query Hooks

Custom Hooks fuer Server-State-Management. Queries, Mutations und Polling.

### `src/pages/` — Seiten

17 Seiten inklusive Admin-Bereich, Dashboard, Workspace, Subscriptions und DSGVO. Jede Seite in einer eigenen Datei.

### `src/types/` — TypeScript-Typen

Zentrale Typdefinitionen fuer alle Domaen-Objekte.

---

## Tests

### `tests/` — Backend-Tests (756)

- `unit/` — Isolierte Tests pro Service und Repository
- `integration/` — Tests mit Datenbank-Interaktion
- `e2e/` — End-to-End-Tests fuer komplette Flows

### `frontend/tests/` — Frontend-Tests (106)

Komponenten-Tests mit vitest und @testing-library/react.

---

## Stubs & Mocks (`stubs/`)

- `cmdb/` — YAML-Dateien mit Testdaten (Locations, Networks, Tenants, Security Zones)
- `gitlab_mock.py` — Separate Flask-App zur Pipeline-Simulation
