# Changelog

Alle relevanten Aenderungen in chronologischer Reihenfolge, gruppiert nach Phasen.

---

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

## Phase B8: Order Groups, Quantity, Per-Instance Parameters

- `76dbfdbb` feat: add OrderItemGroup model and extend OrderItem with group_id, quantity, instance_parameters
- `e8a71ca5` feat: add per_instance field to ParameterDefinition (false/true/auto)
- `e5130a80` feat: add group CRUD API endpoints for orders (16 Tests)
- `f6282644` feat: add quantity and instance_parameters support to order items API (5 Tests)
- `fec79e33` feat: add per-instance parameter support to catalog and order validation (8 Tests)
- `d870799c` test: add E2E test for groups + quantity + per-instance parameters
- `a475f839` feat(frontend): extend order types and API for groups + quantity
- `4654725a` feat(frontend): add group sections, quantity selector, and per-instance UI

## Sidebar Navigation Redesign

- `902a3bd4` feat(frontend): add Notifications placeholder page
- `feed9b83` feat(frontend): rewrite Sidebar with collapsible layout, new menu structure, role-based sections (11 Tests)
- `9e0490b7` feat(frontend): update AppLayout for collapsible sidebar, simplify Header

## Phase 9: Shop Wizard

- `feat(frontend)` add StepIndicator, RequestSummary, WizardView, FormView components
- `feat(frontend)` add ServiceRequest page with wizard/form toggle
- `feat(frontend)` add /shop/:slug/request route and Bestellen button
- `feat(frontend)` add copy-shortcut — Aehnlichen Service hinzufuegen

## Dashboard Redesign

- `feat` add dashboard stats API endpoint (5 Tests)
- `feat` add global search API endpoint (5 Tests)
- `feat(frontend)` add recharts, StatCard, GlobalSearch, OrderStatusChart, OrderTimelineChart
- `feat(frontend)` add RecentOrders, PopularServices, PendingApprovals widgets
- `feat(frontend)` rewrite Dashboard with stat cards, charts, search, role-based widgets

## Notifications System

- `feat` add read/unread notification endpoints with read_at field (8 Tests)
- `feat` add EmailSender interface and StubEmailSender (2 Tests)
- `feat` add create_event_notification with templates and email sender (4 Tests)
- `feat` trigger order_submitted notification on order submit
- `feat(frontend)` add notifications API client, hooks with polling
- `feat(frontend)` rewrite Notifications page with read/unread, sidebar badge

## Subscriptions System

- `feat` add SubscriptionModel and GroupSubscriptionModel
- `feat` add SubscriptionRepository with CRUD, status, changes, groups (22 Tests)
- `feat` add SubscriptionService with change/cancel/create lifecycle (30 Tests)
- `feat` add subscription REST API endpoints (7 Tests)
- `feat` create subscriptions automatically on order submit
- `feat(frontend)` add subscription types, API, hooks, pages, components

## Security Audit + Fixes

- `docs` add consolidated 3-way audit report (Security + Architecture + Quality)
- `security` fix critical findings — webhook auth, credential auth, exception logging
- `docs` add security-engineer, auditor, devops-engineer agents

## Architektur-Audit Fixes

- `fix` add pagination cap (max 200) to all paginated endpoints
- `fix` use consistent AppError classes in catalog and context API
- `refactor` split orders.py (679 lines) into 4 focused modules
- `refactor` move post-submit orchestration to OrderService
- `refactor` extract DashboardService, SearchService, ResourceService

## UI Consolidation

- `feat(frontend)` consolidate into Workspace page (Bestellungen tabs)
- `feat(frontend)` move page titles to Header bar with dynamic routes
- `fix(frontend)` sidebar stays fixed, only content area scrolls
- `feat(frontend)` split layout in FormView — form left, sticky summary right

## VM Templates + Abhaengigkeitsmatrix

- `feat` comprehensive Windows + Linux VM templates (30 params, 9 groups each)
- `feat` T-Shirt Size auto-fill + metadata-based option filtering
- `feat` comprehensive dependency matrix — 15 cross-field dependencies (~45K valid combos)
- `feat(frontend)` red border on required empty/invalid fields, submit gate

## Rollen + DSGVO

- `feat` introduce superadmin role — Rules, Audit Log, DSGVO restricted
- `feat` DSGVO anonymization middleware + admin toggle
- `fix` approvals API supports all statuses (pending/approved/rejected)
- `feat` show order details in review requests, Besteller column

## DevOps + Tools

- `feat` add Dockerfiles, docker-compose, nginx, offline installer scripts
- `feat` add Screenshot-Tool (Playwright, WebP, per user role)
- `feat` show demo credentials in launcher, version v1.0.0 on login
- `feat` add DB Reset + Reseed option to dev launcher
- `feat` 8 demo orders + notifications + approval requests in seed

## Dokumentation

- `docs` add comprehensive README.md
- `docs` update CLAUDE.md to reflect current project state
- `docs` comprehensive update of mpp-docs (11 files)
- `docs` add design specs + implementation plans for all features

---

## Session 2026-06-19: Produktionsreife + VM-Install-Guide

- `0ed38136` docs: App-Look + TDD-Gate + Ein-Befehl-Release (Vorsession-Arbeit committet)
- `e70b6f76` feat(appimage): App-AppRun mit Random-Ports + isolierter Chromium-Instanz
- `5217bfc5` docs: Insights/Handoffs in Nav + run_mpp_docs.sh gehaertet + TDD-Regel R-ERKENNTNISSE
- `117c5883` docs: VM-Installationsanleitung (Flask/React, Produktions-Ziel, 19 Abschnitte)
- `9168f693` feat: Produktionsreife-Fixes (gunicorn, ProxyFix, Readiness `/ready`, alembic-DATABASE_URL)

> **Test-Stand:** +7 Backend-Tests via TDD. Ein voller Lauf deckte **23 pre-existing Failures** auf
> (Stub-User-Count / Auth-403 / DSGVO / Audit-Log) — per `git stash` als Nicht-Regression bewiesen;
> Triage offen. Offener Prod-Blocker: LDAP-Auth (`auth_service.py` → `NotImplementedError`).

---

## Statistik

- **204 Commits** insgesamt (77 Phase 1 + 122 Phase 2 + 5 Session 2026-06-19)
- **763 Backend-Tests**, **106 Frontend-Tests** = **869 Tests** (davon 23 Backend aktuell rot, pre-existing — s. o.)
- **96 API-Endpoints** in **17 Modulen**
- **15 Datenbanktabellen**
- **13 Backend-Services**
- **17 Frontend-Seiten**
- **5 Rollen** (requester, approver, admin, superadmin + multi)
- **15 Design-Specs**, **12 Implementation Plans**
- **Docker Offline-Installer** (Backend + Frontend + PostgreSQL)
- **Screenshot-Tool** (Playwright, WebP, 5 Benutzerrollen)
