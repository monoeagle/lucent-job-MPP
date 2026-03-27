# Projektkontext — Marketplace Portal (MPP)

## Was ist MPP?

Das **Marketplace Portal (MPP)** ist ein Self-Service-Portal fuer die automatisierte Bereitstellung von IT-Services. Endanwender (Requester) koennen aus einem Servicekatalog VMs, Datenbanken und Container bestellen. Die Bestellungen durchlaufen einen definierten Lifecycle mit optionaler Genehmigung (Approval) und werden automatisch via GitLab-Pipelines provisioniert.

**Autor:** Tobias Philipp / Lucent Trails
**Ansatz:** TDD (Test-Driven Development) mit 594 Backend-Tests und 47 Frontend-Tests (641 gesamt)

---

## Architektur

### Prinzip: Clean Architecture

Beide Seiten (Backend + Frontend) folgen Clean Architecture mit strikter Dependency-Richtung.

**Backend:**
```
api (Presentation) → services (Use Cases) → domain (Entities) ← data (Repositories/Clients)
```

**Frontend:**
```
pages (Presentation) → hooks (Use Cases) → api (Data) ← types (Domain)
```

### Dependency-Regeln

- `api/` → `services/` erlaubt
- `api/` → `data/` verboten (nur ueber services)
- `services/` → `domain/` erlaubt
- `services/` → `data/` erlaubt (Repositories)
- `domain/` → `data/` verboten
- `domain/` hat keine Abhaengigkeiten

---

## Tech-Stack

| Schicht      | Backend                        | Frontend                        |
|--------------|--------------------------------|---------------------------------|
| Sprache      | Python 3.12                    | TypeScript 5.7+                 |
| Framework    | Flask 3.1                      | React 19 + Vite 6              |
| ORM / State  | SQLAlchemy 2.0                 | tanstack-query 5 + zustand 5   |
| Datenbank    | PostgreSQL (psycopg2-binary)   | —                               |
| Migration    | Alembic 1.14                   | —                               |
| Auth         | PyJWT 2.10                     | Bearer-Token (localStorage)     |
| Styling      | —                              | TailwindCSS 4                   |
| Tests        | pytest                         | vitest + testing-library        |
| HTTP         | requests 2.32                  | fetch (nativer Client)          |
| Config       | python-dotenv, PyYAML          | Vite env                        |

---

## Hub-Integration

| Dienst    | Port  | Beschreibung                          |
|-----------|-------|---------------------------------------|
| Backend   | 5000  | Flask API Server                      |
| Frontend  | 3000  | Vite Dev Server                       |

Start ueber `scripts/mpp.sh` (interaktiver Dev-Launcher).

---

## Verzeichnisstruktur

```
lucent-app-mpp-TDD/
├── app/                          # Backend (Python/Flask)
│   ├── __init__.py               # Flask App Factory
│   ├── api/v1/                   # REST-Endpoints (12 Module)
│   ├── core/                     # Config, Auth-Middleware, Errors
│   ├── data/
│   │   ├── clients/              # CMDB-Stub, GitLab-Client
│   │   ├── db/
│   │   │   ├── models/           # SQLAlchemy-Modelle (8 Module)
│   │   │   └── session.py        # Engine, SessionFactory
│   │   └── repositories/         # Repository-Pattern
│   ├── domain/                   # Entities, Value Objects, Status
│   └── services/                 # Business Logic (10 Services)
├── frontend/                     # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── api/                  # API-Module (7 Dateien)
│   │   ├── components/           # UI-Komponenten
│   │   │   ├── catalog/          # Catalog-spezifisch
│   │   │   ├── Layout/           # AppLayout, Sidebar, Header
│   │   │   ├── orders/           # Order-spezifisch
│   │   │   └── ParameterForm/    # Dynamische Formular-Felder
│   │   ├── hooks/                # tanstack-query Hooks
│   │   ├── pages/                # 11 Seiten (inkl. admin/)
│   │   ├── store/                # zustand Auth-Store
│   │   └── types/                # TypeScript-Typen
│   └── tests/                    # Frontend-Tests (vitest)
├── migrations/versions/          # Alembic-Migrationen (9 Dateien)
├── stubs/
│   ├── cmdb/                     # YAML-Daten (4 Dateien)
│   └── gitlab_mock.py            # GitLab-Pipeline-Simulation
├── tests/                        # Backend-Tests
│   ├── unit/                     # Unit-Tests
│   ├── integration/              # Integrationstests
│   └── e2e/                      # End-to-End-Tests
├── scripts/
│   ├── mpp.sh                    # Interaktiver Dev-Launcher
│   └── seed.py                   # Demo-Daten laden
├── docs/specs/                   # 9 Feature-Spezifikationen
├── requirements.txt              # Python-Abhaengigkeiten
├── pytest.ini                    # pytest-Konfiguration
└── alembic.ini                   # Alembic-Konfiguration
```

---

## Externe Systeme (Stubs/Mocks in Entwicklung)

| System   | Produktiv         | Entwicklung              |
|----------|-------------------|--------------------------|
| Auth     | LDAP/AD           | Auth-Stub (4 Dummy-User) |
| CMDB     | Unternehmens-CMDB | CMDB-Stub (YAML-Daten)   |
| GitLab   | GitLab CI/CD      | GitLab-Mock (Simulation)  |
