# CLAUDE.md — Marketplace Portal (MPP)

## Was ist das?

**Marketplace Portal (MPP)** ist ein Self-Service-Portal fuer automatisierte IT-Service-Provisionierung. Benutzer bestellen VMs, Datenbanken und Container aus einem Servicekatalog. TDD-Projekt mit 641 Tests (594 Backend + 47 Frontend).

- **Backend:** Python 3.12, Flask 3.1, SQLAlchemy 2.0, PostgreSQL, Alembic
- **Frontend:** React 19, TypeScript, Vite 6, TailwindCSS 4, tanstack-query 5, zustand 5
- **Port 5000** (Backend), **Port 3000** (Frontend Dev)

Autor: Tobias Philipp / Lucent Trails.

---

## Prioritaeten (bei Konflikten)

1. Architektur-Regeln (Clean Architecture, Dependency Rules)
2. Sicherheit & Datenintegritaet
3. Korrektheit (keine Bugs)
4. Wartbarkeit & Lesbarkeit
5. Performance

---

## Verzeichnisstruktur

```
app/
├── api/v1/         # REST-Endpoints (12 Module, 76 Endpoints)
├── core/           # Config, Auth-Middleware, Errors
├── data/
│   ├── clients/    # CMDB-Stub, GitLab-Client
│   ├── db/models/  # SQLAlchemy-Modelle (8 Module)
│   └── repositories/
├── domain/         # Entities, Value Objects (auth, catalog, order, context, provisioning)
└── services/       # 10 Services (Business Logic)

frontend/src/
├── api/            # HTTP-Client + API-Module (7 Dateien)
├── components/     # UI-Komponenten (catalog, orders, ParameterForm, Layout)
├── hooks/          # tanstack-query Hooks (4 Dateien)
├── pages/          # 11 Seiten (inkl. admin/)
├── store/          # zustand Auth-Store
└── types/          # TypeScript-Typen
```

---

## Befehle

### Backend starten
```bash
source venv/bin/activate
export AUTH_MODE=stub CMDB_MODE=stub DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
alembic upgrade head
python scripts/seed.py
flask run --port 5000
```

### Frontend starten
```bash
cd frontend
npm install
npx vite --port 3000
```

### Interaktiver Launcher
```bash
bash scripts/mpp.sh
```

### Tests ausfuehren
```bash
# Backend
source venv/bin/activate
DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/ -q

# Frontend
cd frontend && npx vitest run
```

---

## Architektur (nicht verhandelbar)

### Backend
```
api/ → services/ → domain/ ← data/
```

### Frontend
```
pages/ → hooks/ → api/ ← types/
```

### Dependency-Regeln
- `api/` → `services/`, `core/` erlaubt
- `api/` → `data/` verboten
- `services/` → `domain/`, `data/repositories/` erlaubt
- `domain/` → nichts (keine Abhaengigkeiten)
- `data/` → `domain/` erlaubt

---

## Datenmodell

12 PostgreSQL-Tabellen: `service_templates`, `orders`, `order_items`, `approval_rules`, `approval_requests`, `availability_rules`, `context_restrictions`, `user_tenant_assignments`, `dispatch_logs`, `audit_logs`, `notifications`, `credential_links`

9 Alembic-Migrationen. JSONB fuer flexible Parameter, Constraints, Context.

---

## API-Endpoints (76 gesamt)

| Gruppe        | Anzahl | Auth            |
|---------------|--------|-----------------|
| Health        | 2      | —/admin         |
| Auth          | 3      | —/login         |
| Catalog       | 9      | login/admin     |
| Orders        | 14     | login           |
| Context/CMDB  | 19     | login/admin     |
| Approvals     | 10     | login/approver/admin |
| Provisioning  | 6      | —/admin         |
| Resources     | 2      | login           |
| Admin/Audit   | 3      | admin           |
| Notifications | 2      | login/admin     |

---

## Stubs und Mocks

- **Auth-Stub:** 4 Benutzer (test-requester, test-approver, test-admin, test-multi)
- **CMDB-Stub:** YAML-Daten in `stubs/cmdb/` (Locations, Networks, Tenants, Security Zones)
- **GitLab-Mock:** Pipeline-Simulation in `stubs/gitlab_mock.py`

---

## Verbote

- Keine destruktiven Commands ohne Nachfrage
- Keine Dependency-Aenderungen ohne Bestaetigng
- Kein DB-Schema-Upgrade ohne Freigabe
- Kein Architekturbruch
- Kein Stub-Modus in Produktion

---

## Vor jeder Aenderung pruefen

1. Architektur-Regeln eingehalten?
2. Backend + Frontend betroffen?
3. Konstanten statt Magic Numbers?
4. Test vorhanden?
5. Datei < 200 Zeilen?
6. API synchron?
