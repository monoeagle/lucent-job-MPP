# Phase-Checkliste — Marketplace Portal (MPP)

Stand: 2026-03-26

---

## Backend-Phasen

### Phase B1: Identity & Access (Auth-Stub)
- [x] User-Domain-Modell und Role-Konstanten
- [x] Config-Modul mit Auth-Mode-Validierung
- [x] AuthService mit Stub-Login und JWT-Token-Generierung
- [x] Flask-App-Factory, Error-Handling, Request-ID-Middleware
- [x] JWT-Auth-Middleware (login_required, role_required)
- [x] Shared Test-Fixtures (conftest.py)
- **Audit:** bestanden

### Phase B2: Service Catalog
- [x] ServiceTemplate-Domain-Modelle (Template, ParameterDefinition, DependencyRule)
- [x] TemplateValidator (VAL-47..71)
- [x] ServiceTemplate-DB-Modell mit JSONB und Unique-Constraint
- [x] TemplateRepository mit CRUD, Filtering, Suche, Paginierung
- [x] CatalogService mit Parameter-Validierung und Dependency-Resolution
- [x] Catalog-API-Read-Endpoints mit DB-Session-Management
- [x] Admin-Catalog-Endpoints (Register, Status-Update)
- [x] Parameter-Validierung und dynamische Option-Resolution
- [x] Version-Diff-Endpoint
- **Audit:** bestanden

### Phase B3: Order Lifecycle
- [x] OrderStatus und ItemValidationState Domain-Modelle
- [x] Order- und OrderItem-DB-Modelle mit Cascade-Delete
- [x] OrderRepository mit CRUD, Item-Management, Status-Transitions
- [x] OrderService mit Validierung, Submission, Tofu-Export
- [x] Order-CRUD-API-Endpoints (Create, Get, List, Update, Delete)
- [x] Order-Item-Management-Endpoints (Add, Update, Remove, Reorder)
- [x] Order-Validierung mit Catalog-basierter Parameter-Pruefung
- [x] Order-Submit mit Status-Machine und Polling
- [x] OpenTofu-JSON-Export-Endpoints
- **Audit:** bestanden

### Phase B4: Context & CMDB
- [x] CMDB-Stub-Daten (Locations, Networks, Tenants, Security Zones)
- [x] CMDB-Stub-Client mit YAML-Daten und Filtering
- [x] CMDB-Stub-API-Endpoints
- [x] OrderContext-Domain-Modell und ContextService mit CMDB-Resolution
- [x] Context-Resolution-API-Endpoint mit CMDB-Validierung
- [x] AvailabilityRule, ContextRestriction, TenantAssignment DB-Modelle
- [x] Admin-APIs fuer Availability-Rules, Context-Restrictions, Tenant-Assignments
- [x] Context-Integration in Order-Erstellung
- **Audit:** bestanden

### Phase B5: Provisioning Engine
- [x] GitLab-Mock als separate Flask-App mit Pipeline-Simulation
- [x] ProvisioningStatus-Domain, DispatchLog-Modell, Provisioning-Spalten auf OrderItem
- [x] GitLab-API-Client fuer Pipeline-Triggering und Status-Polling
- [x] ProvisioningService mit Dispatch, Status-Sync und Webhook-Handling
- [x] Provisioning-API-Endpoints und Dispatch-Integration in Order-Submit
- **Audit:** bestanden

### Phase B6: Approval Workflow
- [x] ApprovalRule- und ApprovalRequest-DB-Modelle
- [x] ApprovalRepository und ApprovalService mit Rule-Evaluation und Decisions
- [x] Approval-API-Endpoints und Integration in Order-Submit-Flow
- **Audit:** bestanden

### Phase B7: Cross-Cutting Concerns
- [x] AuditLog-Modell, AuditService und Admin-API-Endpoint
- [x] Notification-Service mit Fire-and-Forget-E-Mail-Stubs
- [x] Secure Credential Delivery mit One-Time-Token-Links
- [x] Resource-Overview und Admin-Dashboard-API-Endpoints
- [x] Seed-Script mit Demo-Templates und Demo-Order
- **Audit:** bestanden

---

## Frontend-Phasen

### Phase F1: Projekt-Scaffold
- [x] Vite + React + TypeScript + TailwindCSS Scaffold
- [x] Common Types (User, ErrorResponse, ApiError)
- [x] API-Client mit Auth-Headers und Error-Handling
- [x] Auth-Store mit localStorage-Persistierung
- [x] Login-Seite
- **Audit:** bestanden

### Phase F2: Layout & Routing
- [x] AppLayout mit Sidebar, Header, ProtectedRoute, StatusBadge
- [x] Router mit Protected Routes und Sidebar-Layout
- **Audit:** bestanden

### Phase F3: Service Catalog
- [x] Catalog TypeScript-Types
- [x] Catalog-API-Modul mit Tests
- [x] Catalog tanstack-query Hooks
- [x] Reusable Drawer Slide-In-Komponente
- [x] Service-Catalog-Seite mit Template-Cards, Filtern und Detail-Drawer
- **Audit:** bestanden

### Phase F4: Order Management
- [x] Order TypeScript-Types
- [x] Orders-API-Modul
- [x] Order-Hooks mit Mutations und Status-Polling
- [x] Dynamisches ParameterForm mit Feld-Komponenten
- [x] Order-Hub-Seiten: OrderNew, OrderDetail, OrderList, OrderExport
- **Audit:** bestanden

### Phase F5: Context & CMDB
- [x] ContextSelector mit CMDB-Integration
- **Audit:** bestanden

### Phase F6: Approvals & Resources
- [x] Approvals-Seite
- [x] Resources-Seite
- **Audit:** bestanden

### Phase F7: Admin & Tests
- [x] Admin-Dashboard, Rules, AuditLog Seiten
- [x] Frontend-Tests (Approvals, Resources, Admin Dashboard)
- **Audit:** bestanden

---

## Integrations-Phase

### E2E-Tests
- [x] End-to-End-Integrationstests fuer kompletten Demo-Flow
- [x] Unified Dev Launcher (scripts/mpp.sh)
- **Audit:** bestanden

---

## Zusammenfassung

| Bereich   | Phasen | Status           |
|-----------|--------|------------------|
| Backend   | 7/7    | alle abgeschlossen |
| Frontend  | 7/7    | alle abgeschlossen |
| E2E       | 1/1    | abgeschlossen    |
| **Gesamt**| **15/15** | **komplett**   |
