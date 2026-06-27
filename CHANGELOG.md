# Changelog — Marketplace Portal (MPP)

Alle relevanten Aenderungen in chronologischer Reihenfolge, gruppiert nach Phasen.

---

## v1.1.0 — Delivery & Doku-Paritaet (2026-06-27)

Angleichung an den Stand des Django-Schwesterprojekts (Delivery + Doku-Site).

- `32747e1` feat: Offline-Release-Workflow (`run.sh release` + `tools/build_release.py`, prebuilt SPA + Wheels) + Produktions-Installer `deploy/install.sh` (AlmaLinux 9: gunicorn-Factory, alembic, nginx-SPA + self-signed TLS, systemd; **kein** Celery/Redis) + `docs/deployment/vm-installation-offline.md`
- `32747e1` feat(docs): Oberflaechen-Galerie, gh-pages-Deploy (`mpp-docs/deploy_ghpages.sh`), Architektur-Header-Badge (`index-1.svg`), Heatmap-Klick-Toggle, `.adb-shot-compare`-CSS; Versions-Bump v1.1.0
- `20ad905` fix(docs): Galerie-Bestellformular links leer / rechts ausgefuellt (12 echte Playwright-Screenshots)
- chore: Repo **public** + GitHub Pages live (<https://monoeagle.github.io/lucent-job-MPP/>); Roadmap/Gantt + `todos.md` nachgezogen
- Tests (Stand 2026-06-27): **771 Backend (739 gruen / 32 pre-existing rot)** + 106 Frontend

## Phase B1: Identity & Access

- `1fb48da` initial: Project Specs, Design Docs und Agent-Definitionen
- `079c1ce` chore: Projekt-Abhaengigkeiten und pytest-Konfiguration
- `8f1cda1` feat: Config-Modul mit Auth-Mode-Validierung
- `0cd0179` feat: User-Domain-Modell und Role-Konstanten
- `9f2e8c9` feat: AuthService mit Stub-Login und JWT-Token-Generierung
- `bd9d9f3` feat: Flask-App-Factory, Error-Handling, Request-ID-Middleware, Health/Login/Stub-Users
- `3bcb3a5` feat: JWT-Auth-Middleware (login_required, role_required)
- `d0922bf` refactor: Shared Test-Fixtures in conftest.py extrahiert
- `3b295ac` chore: .gitignore und __pycache__-Bereinigung
- `cf64b23` chore: __pycache__ aus Tracking entfernt

## Phase B2: Service Catalog

- `fa143b3` feat: Service-Catalog-Domain-Modelle (ServiceTemplate, ParameterDefinition, DependencyRule)
- `02a72df` feat: TemplateValidator fuer Registrierungs-Validierung (VAL-47..71)
- `a0e53c1` feat: ServiceTemplate-DB-Modell mit JSONB-Parameters und Unique-Constraint
- `6c64c6c` feat: TemplateRepository mit CRUD, Filtering, Suche, Paginierung
- `e698da4` feat: CatalogService mit Parameter-Validierung und Dependency-Resolution
- `d06f5d6` feat: Catalog-API-Read-Endpoints mit DB-Session-Management
- `43fe6db` feat: Admin-Catalog-Endpoints (Register, Status-Update)
- `af2522d` feat: Parameter-Validierung und dynamische Option-Resolution
- `00f2ceb` feat: Version-Diff-Endpoint

## Phase B3: Order Lifecycle

- `69fe25c` feat: OrderStatus und ItemValidationState Domain-Modelle
- `961d0a5` feat: Order- und OrderItem-DB-Modelle mit Cascade-Delete
- `aefb908` feat: OrderRepository mit CRUD, Items, Status-Transitions
- `635a3a8` feat: OrderService mit Validierung, Submission, Tofu-Export
- `4aaae9c` feat: Order-CRUD-API-Endpoints
- `db3f728` feat: Order-Item-Management-Endpoints (Add, Update, Remove, Reorder)
- `8c8c6cb` feat: Order-Validierung mit Catalog-basierter Parameter-Pruefung
- `3680125` feat: Order-Submit mit Status-Machine und Polling
- `074e08e` feat: OpenTofu-JSON-Export-Endpoints

## Phase B4: Context & CMDB

- `a5812e7` feat: CMDB-Stub-Daten (Locations, Networks, Tenants, Security Zones)
- `197fa0e` feat: CMDB-Stub-Client mit YAML-Daten und Filtering
- `8df3a85` feat: CMDB-Stub-API-Endpoints
- `ac001f2` feat: OrderContext-Domain und ContextService mit CMDB-Resolution
- `df7d30c` feat: Context-Resolution-API-Endpoint mit CMDB-Validierung
- `6034387` feat: AvailabilityRule, ContextRestriction, TenantAssignment DB-Modelle
- `2647b27` feat: Admin-APIs fuer Availability-Rules, Restrictions, Tenant-Assignments
- `2f8eb46` feat: OrderContext-Integration in Order-Erstellung

## Phase B5: Provisioning Engine

- `81312f4` feat: GitLab-Mock als separate Flask-App mit Pipeline-Simulation
- `2035147` feat: ProvisioningStatus-Domain, DispatchLog-Modell, Provisioning-Spalten
- `db2d57c` feat: GitLab-API-Client fuer Pipeline-Triggering und Status-Polling
- `e1ef4c7` feat: ProvisioningService mit Dispatch, Status-Sync, Webhooks
- `30639a2` feat: Provisioning-API-Endpoints, Dispatch in Order-Submit integriert

## Phase B6: Approval Workflow

- `d161afb` feat: ApprovalRule- und ApprovalRequest-DB-Modelle
- `30a444f` feat: ApprovalRepository und ApprovalService mit Rule-Evaluation
- `90b8dcd` feat: Approval-API-Endpoints, Integration in Order-Submit

## Phase B7: Cross-Cutting Concerns

- `613ef07` feat: Audit-Log-Modell, Service und Admin-API-Endpoint
- `b7d9a87` feat: Notification-Service mit Fire-and-Forget-E-Mail-Stubs
- `c4116e1` feat: Secure Credential Delivery mit One-Time-Token-Links
- `10d2171` feat: Resource-Overview und Admin-Dashboard-API-Endpoints

---

## Phase F1: Frontend Scaffold

- `5d9543a` docs: Frontend-Design-Spec (React + TypeScript)
- `9fb2e30` feat(frontend): Vite + React + TypeScript + TailwindCSS Scaffold
- `2b0801d` feat(frontend): Common Types (User, ErrorResponse, ApiError)
- `b2ac0f3` feat(frontend): API-Client mit Auth-Headers und Error-Handling
- `d939e84` feat(frontend): Auth-Store mit localStorage-Persistierung
- `eb49583` feat(frontend): Login-Seite

## Phase F2: Layout & Routing

- `c55c90f` feat(frontend): AppLayout mit Sidebar, Header, ProtectedRoute, StatusBadge
- `0b89be1` feat(frontend): Router mit Protected Routes und Sidebar-Layout
- `596931d` fix(frontend): Unused Imports entfernt
- `463718d` chore: .gitignore aktualisiert (venv/, dist/ entfernt)

## Phase F3: Service Catalog

- `87e008e` feat(frontend): Catalog TypeScript-Types
- `b72b34d` feat(frontend): Catalog-API-Modul mit Tests
- `84b13b2` feat(frontend): Catalog tanstack-query Hooks
- `e85f7b5` feat(frontend): Reusable Drawer Slide-In-Komponente
- `19bfb46` feat(frontend): Service-Catalog-Seite mit Template-Cards, Filtern, Detail-Drawer

## Phase F4: Order Management

- `09758c0` feat(frontend): Order TypeScript-Types
- `3db0ef2` feat(frontend): Orders-API-Modul
- `2e0e374` feat(frontend): Order-Hooks mit Mutations und Status-Polling
- `26f4fd0` feat(frontend): Dynamisches ParameterForm mit Feld-Komponenten
- `09f9902` feat(frontend): Order-Hub-Seiten (OrderNew, OrderDetail, OrderList, OrderExport)

## Phase F5: Context & CMDB

- `6ae8ec6` feat(frontend): ContextSelector mit CMDB-Integration

## Phase F6: Approvals & Resources

- `185845e` feat(frontend): Approvals- und Resources-Seiten

## Phase F7: Admin & Tests

- `888975b` feat(frontend): Admin-Seiten (Dashboard, Rules, AuditLog)
- `f001e78` test(frontend): Tests fuer Approvals, Resources, Admin Dashboard

---

## Integrations-Phase

- `f366bfe` feat: Seed-Script mit Demo-Templates und run_dev.sh
- `3066b76` test: End-to-End-Integrationstests fuer kompletten Demo-Flow
- `39cb93c` feat: run_frontend.sh Dev-Helper-Script
- `e58ae0a` feat: Unified Dev Launcher (scripts/mpp.sh)

---

## Statistik

- **77 Commits** insgesamt
- **594 Backend-Tests**, **47 Frontend-Tests** = **641 Tests**
- **76 API-Endpoints**
- **12 Datenbanktabellen**, **9 Alembic-Migrationen**
- **11 Frontend-Seiten**
- **9 Feature-Spezifikationen**
