# CLAUDE.md — Marketplace Portal (MPP)

## Was ist das?

**Marketplace Portal (MPP)** ist ein Self-Service-Portal fuer automatisierte IT-Service-Provisionierung. Benutzer bestellen VMs, Datenbanken und Container aus einem Servicekatalog. TDD-Projekt mit 862 Tests (756 Backend + 106 Frontend).

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
├── api/v1/         # REST-Endpoints (17 Module, 96 Endpoints)
│   │               # admin, approvals, auth, catalog, cmdb, context,
│   │               # dashboard, health, notifications, order_actions,
│   │               # order_groups, order_items, orders, provisioning,
│   │               # resources, search, subscriptions
├── core/           # Config, Auth-Middleware, DSGVO-Anonymisierung, Errors
├── data/
│   ├── clients/    # CMDB-Stub, GitLab-Client
│   ├── db/models/  # SQLAlchemy-Modelle (15 Klassen, 10 Module)
│   │               # order, order_group, approval, context_rule,
│   │               # subscription, notification, dispatch_log,
│   │               # audit_log, credential_link, service_template
│   └── repositories/
├── domain/         # Entities, Value Objects (auth, catalog, order, context, provisioning)
└── services/       # 13 Services (Business Logic)
                    # approval, audit, auth, catalog, context, credential,
                    # dashboard, notification, order, provisioning,
                    # resource, search, subscription

frontend/src/
├── api/            # HTTP-Client + API-Module (10 Dateien)
│   │               # client, admin, approvals, catalog, context,
│   │               # dashboard, notifications, orders, resources, subscriptions
├── components/     # UI-Komponenten (catalog, dashboard, orders, subscriptions,
│   │               # ParameterForm, Layout, Drawer, StatusBadge, ProtectedRoute)
├── hooks/          # tanstack-query Hooks (7 Dateien)
│   │               # useAuth, useCatalog, useDashboard, useNotifications,
│   │               # useOrderStatus, useOrders, useSubscriptions
├── pages/          # 17 Seiten (inkl. admin/)
│   │               # Dashboard, Catalog, Workspace (Alle/Meine Bestellungen),
│   │               # OrderNew/Detail/List/Export, ServiceRequest, MyRequests,
│   │               # MyServices, Subscriptions/Detail, Notifications,
│   │               # Resources, Login + admin/ (Dashboard, Rules, AuditLog)
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

15 PostgreSQL-Tabellen: `service_templates`, `orders`, `order_items`, `order_item_groups`, `approval_rules`, `approval_requests`, `availability_rules`, `context_restrictions`, `user_tenant_assignments`, `dispatch_logs`, `audit_logs`, `notifications`, `credential_links`, `subscriptions`, `group_subscriptions`

11 Alembic-Migrationen. JSONB fuer flexible Parameter, Constraints, Context.

---

## API-Endpoints (96 gesamt)

| Gruppe              | Anzahl | Auth                  |
|---------------------|--------|-----------------------|
| Health              | 1      | —                     |
| Auth                | 4      | —/login               |
| Catalog             | 10     | login/admin           |
| Orders              | 5      | login                 |
| Order Items         | 4      | login                 |
| Order Actions       | 5      | login                 |
| Order Groups        | 4      | login                 |
| Context/CMDB        | 26     | login/admin           |
| Approvals           | 10     | login/approver/admin  |
| Provisioning        | 6      | —/admin               |
| Resources           | 2      | login                 |
| Admin/Audit         | 5      | admin/superadmin      |
| Notifications       | 5      | login/admin           |
| Subscriptions       | 7      | login                 |
| Dashboard           | 1      | login/admin           |
| Search              | 1      | login                 |

---

## Rollen

| Rolle       | Beschreibung                                      |
|-------------|---------------------------------------------------|
| requester   | Standardbenutzer, kann Bestellungen aufgeben      |
| approver    | Kann Approval-Requests genehmigen/ablehnen        |
| admin       | Vollzugriff auf Katalog, Regeln, Audit            |
| superadmin  | Systemweite Verwaltung, DSGVO-Anonymisierung      |

---

## Stubs und Mocks

- **Auth-Stub:** 5 Benutzer (test-requester, test-approver, test-admin, test-multi, test-superadmin)
- **CMDB-Stub:** YAML-Daten in `stubs/cmdb/` (Locations, Networks, Tenants, Security Zones)
- **GitLab-Mock:** Pipeline-Simulation in `stubs/gitlab_mock.py`

---

## Features (Ueberblick)

- **Servicekatalog:** Templates mit T-Shirt-Sizes, Dependency-Matrix, Shop-Wizard (Wizard/Form-Toggle)
- **Bestellworkflow:** Order Groups, Quantity-Scaling, Per-Instance Parameters
- **Subscriptions:** Lifecycle-Management, Aenderungen, Kuendigungen
- **Notifications:** Read/Unread, Event-Trigger, E-Mail-Stub
- **Dashboard:** Stats, Suche (GlobalSearch), Charts (Recharts)
- **DSGVO:** Anonymisierungs-Middleware fuer personenbezogene Daten
- **Offline-Installer:** Docker-basiertes Setup
- **Screenshot-Tool:** Playwright + WebP

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
