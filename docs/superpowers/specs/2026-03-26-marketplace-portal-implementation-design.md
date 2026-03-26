# Marketplace Portal — Implementation Design

> **Erstellt:** 2026-03-26
> **Status:** Approved
> **Tech-Stack:** Python/Flask + PostgreSQL + TDD
> **Scope:** Backend/API only (kein Frontend)

---

## Kontext

Ein Marketplace Portal für automatisierte IT-Services (VMs, Datenbanken, Container). User bestellen Services, das System generiert JSON und übergibt an GitLab + OpenTofu für die Provisionierung.

9 Feature-Specs liegen unter `docs/specs/` vor (~420 KB, ~240 Requirements, ~86 Endpoints).

---

## Tech-Stack

| Komponente | Technologie |
|------------|-------------|
| Backend Framework | Flask |
| Datenbank | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Testing | pytest |
| Auth (Dev) | Auth-Stub mit JWT |
| Auth (Prod) | LDAP/SSO gegen Active Directory |
| API-Format | REST + SSE, JSON |
| Task Queue | (später: Celery oder äquivalent) |

---

## Projekt-Struktur

```
lucent-app-mpp-TDD/
├── app/
│   ├── __init__.py          # Flask App Factory
│   ├── core/                # Config, Error-Handling, Constants, Middleware
│   │   ├── config.py
│   │   ├── errors.py        # Standard Error-Response-Format
│   │   ├── auth.py          # Auth-Middleware (JWT-Validierung)
│   │   └── circuit_breaker.py
│   ├── domain/              # Models, Entities, Interfaces (keine DB-Abhängigkeit)
│   │   ├── models/          # Dataclasses / Pydantic Models
│   │   └── interfaces/      # Repository-Interfaces (ABC)
│   ├── data/                # Repositories, DB-Access, externe Clients
│   │   ├── repositories/    # SQLAlchemy Repository-Implementierungen
│   │   ├── db/              # SQLAlchemy Models, Session Management
│   │   └── clients/         # CMDB-Client, GitLab-Client
│   ├── services/            # Business Logic, UseCases
│   │   ├── catalog_service.py
│   │   ├── order_service.py
│   │   ├── provisioning_service.py
│   │   ├── approval_service.py
│   │   └── notification_service.py
│   └── api/                 # Flask Blueprints, Routes, Serialization
│       ├── v1/
│       │   ├── catalog.py
│       │   ├── orders.py
│       │   ├── approvals.py
│       │   ├── admin.py
│       │   ├── resources.py
│       │   └── auth.py
│       └── middleware/       # Request-ID, Logging, Rate-Limiting
├── tests/
│   ├── conftest.py          # Shared Fixtures, Test-DB-Setup
│   ├── unit/                # Service-Layer Tests (gemockte Repos)
│   ├── integration/         # API-Tests (echte DB, Auth-Stub)
│   └── fixtures/            # JSON Test-Fixtures
├── stubs/
│   ├── auth_stub.py         # Dummy-User ohne AD
│   ├── gitlab_mock.py       # GitLab Pipeline-Mock (separater Prozess)
│   └── cmdb_stub.py         # CMDB-Stub (Standorte, Netze, etc.)
├── migrations/              # Alembic
├── docs/
│   ├── specs/               # Feature-Spezifikationen (vorhanden)
│   └── superpowers/specs/   # Design-Docs
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Dependency Rules (Clean Architecture)

```
api/ → services/ → domain/ ✓
api/ → data/ ✗ (niemals direkt)
domain/ → data/ ✗ (niemals)
data/ → domain/ ✓ (implementiert Interfaces)
core/ → überall ✓
```

---

## Implementierungsphasen

### Phase 0+1: Scaffold + Auth-Stub + Error-Patterns

**Specs:** `development-testing.md` (9.1, 9.4), `cross-cutting-concerns.md`

**Ergebnis:**
- Flask App Factory mit Blueprint-Registrierung
- PostgreSQL-Verbindung + Alembic-Setup
- Standard Error-Response-Format (error_code, message, details, request_id)
- Auth-Middleware mit JWT-Validierung
- Auth-Stub: 4 Dummy-User (requester, approver, admin, multi-role)
- ENV-Switch AUTH_MODE=stub mit Produktions-Safeguard
- pytest-Setup mit Test-DB, Fixtures-Mechanismus
- Health-Endpoint

**~5 Endpoints**

---

### Phase 2: Service Catalog

**Spec:** `service-catalog.md`

**Ergebnis:**
- ServiceTemplate-Model mit SemVer-Versionierung
- ParameterDefinition mit 8 Parametertypen und Constraints
- DependencyRules und cross_parameter_rules
- Template-Lifecycle (active/deprecated/disabled)
- CRUD + Validierung + dynamische Optionsauflösung

**~8 Endpoints**

---

### Phase 3: Order Lifecycle + JSON Export

**Spec:** `order-lifecycle.md`

**Ergebnis:**
- Order-Model mit Multi-Service OrderItems
- Persistente Drafts, volles CRUD im Draft-Status
- Statusmaschine: draft → validated → submitted → provisioning → done/failed
- Validierung gegen Service Catalog Templates
- JSON-Export für OpenTofu (TF_VAR_-Mapping)
- SSE für Status-Updates

**~15 Endpoints**

---

### Phase 4: CMDB-Stub + Kontextabhängige Bestellung

**Specs:** `context-dependent-ordering.md`, `development-testing.md` (9.3)

**Ergebnis:**
- CMDB-Stub mit Standorten, Netzen, Mandanten, Sicherheitsbereichen
- Bestellkontext-Modell (Schritt 0 vor Service-Auswahl)
- ContextRestrictions und AvailabilityRules
- Asynchrone Draft-Revalidierung bei Regeländerungen
- CMDB-Ausfall blockiert Bestellprozess

**~21 Endpoints**

---

### Phase 5: GitLab-Mock + Provisioning

**Specs:** `provisioning-engine.md`, `development-testing.md` (9.2)

**Ergebnis:**
- GitLab-Mock als separater Prozess
- Job-Dispatcher (Dual-Trigger: submitted + approved)
- Status-Sync (Polling + Webhook)
- Fehlerbehandlung + Rollback
- Idempotenz-Schutz pro OrderItem

**~19 Endpoints**

---

### Phase 6: Approval Workflow

**Spec:** `approval-workflow.md`

**Ergebnis:**
- Approval-Regeln (cost_threshold, service_type, always)
- 1-stufiger Approval-Workflow mit Race-Condition-Schutz
- Self-Approval-Prävention
- Timeout-Cron mit automatischer Ablehnung
- Frist-Verlängerung durch Admin

**~10 Endpoints**

---

### Phase 7: Notifications + Ressourcen + Admin

**Spec:** `resources-notifications-admin.md`

**Ergebnis:**
- E-Mail-Benachrichtigungen (Template-basiert, Fire-and-Forget)
- Secure-Link für Zugangsdaten (einmalig, 48h TTL)
- Ressourcen-Übersicht pro User
- Admin-Dashboard (Orders, Ressourcen, Health)
- Audit-Log (unveränderlich, durchsuchbar, Export)

**~16 Endpoints**

---

## TDD-Workflow pro Phase

```
1. Spec lesen
2. qa-test-writer Agent schreibt Tests (API + Service-Layer)
3. python-flask-dev Agent implementiert bis Tests grün
4. code-reviewer Agent reviewed gegen Spec + Clean Architecture
5. Commit + nächste Phase
```

---

## Entscheidungen

| Entscheidung | Wert | Begründung |
|-------------|------|------------|
| Tech-Stack | Python/Flask | Passt zu vorhandenen Agenten |
| Datenbank | PostgreSQL | Robustheit, ACID, JSON-Support |
| TDD | Ja | Im Projektnamen verankert |
| Frontend | Nein (nur API) | Entkopplung, API-First |
| Auth im Dev | Stub mit JWT | Kein AD nötig zum Entwickeln |
| CMDB-Ausfall | Blockiert Bestellprozess | Sicherheit > Resilienz |
| Draft-Revalidierung | Asynchron bei Regeländerung | Konsistenz > Convenience |
| Phasen 0+1 | Zusammengelegt | Scaffold + Auth gehören zusammen |
