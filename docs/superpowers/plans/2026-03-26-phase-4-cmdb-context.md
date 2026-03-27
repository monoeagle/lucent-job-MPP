# Phase 4: CMDB-Stub + Context-Dependent Ordering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the CMDB-Stub with static test data, the OrderContext model, context resolution/validation against CMDB, and context-dependent service availability + parameter restrictions.

**Architecture:** CMDB-Stub as an integrated Flask blueprint (activated by CMDB_MODE=stub). Static data from YAML files. Context resolution as a service layer. Availability and restriction rules stored in PostgreSQL. Admin endpoints for rule management.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, PyYAML, pytest

**Specs:**
- `docs/specs/development-testing.md` Feature 9.3 (CMDB-Stub)
- `docs/specs/context-dependent-ordering.md` Features 10.1-10.3

---

## File Structure (new/modified)

```
app/
├── domain/
│   └── context.py                      # OrderContext, ResolvedContext dataclasses
├── data/
│   ├── clients/
│   │   ├── __init__.py
│   │   └── cmdb_client.py              # CMDB client interface + stub implementation
│   ├── db/models/
│   │   ├── context_rule.py             # ContextRestriction, AvailabilityRule models
│   │   ├── tenant_assignment.py        # UserTenantAssignment model
│   │   └── __init__.py                 # updated
│   └── repositories/
│       ├── context_rule_repository.py  # CRUD for rules
│       └── tenant_repository.py        # User-Tenant assignments
├── services/
│   └── context_service.py              # Context resolution, validation, filtering
└── api/v1/
    ├── cmdb.py                         # CMDB-Stub endpoints
    └── context.py                      # Context resolution + admin endpoints

stubs/
└── cmdb/
    ├── locations.yaml
    ├── networks.yaml
    ├── tenants.yaml
    ├── security_zones.yaml
    └── config_options.yaml

tests/
├── unit/
│   ├── test_context_domain.py
│   ├── test_cmdb_client.py
│   └── test_context_service.py
└── integration/
    ├── test_cmdb_api.py
    ├── test_context_resolve_api.py
    ├── test_availability_rules_api.py
    └── test_context_restrictions_api.py
```

---

### Task 1: CMDB Static Data Files

**Files:**
- Create: `stubs/cmdb/locations.yaml`
- Create: `stubs/cmdb/networks.yaml`
- Create: `stubs/cmdb/tenants.yaml`
- Create: `stubs/cmdb/security_zones.yaml`

- [ ] **Step 1: Create YAML data files**

`stubs/cmdb/locations.yaml`:
```yaml
- id: loc-berlin
  name: Berlin HQ
  code: BER
  region: DE-NORTH
- id: loc-munich
  name: Munich DC
  code: MUC
  region: DE-SOUTH
- id: loc-hamburg
  name: Hamburg Edge
  code: HAM
  region: DE-NORTH
```

`stubs/cmdb/networks.yaml`:
```yaml
- id: net-ber-dmz
  name: Berlin DMZ
  cidr: "10.10.1.0/24"
  type: dmz
  location_id: loc-berlin
  security_zone_id: sz-medium
- id: net-ber-intern
  name: Berlin Internal
  cidr: "10.10.10.0/24"
  type: internal
  location_id: loc-berlin
  security_zone_id: sz-low
- id: net-ber-mgmt
  name: Berlin Mgmt
  cidr: "10.10.100.0/24"
  type: mgmt
  location_id: loc-berlin
  security_zone_id: sz-high
- id: net-muc-dmz
  name: Munich DMZ
  cidr: "10.20.1.0/24"
  type: dmz
  location_id: loc-munich
  security_zone_id: sz-medium
- id: net-muc-intern
  name: Munich Internal
  cidr: "10.20.10.0/24"
  type: internal
  location_id: loc-munich
  security_zone_id: sz-low
- id: net-ham-intern
  name: Hamburg Internal
  cidr: "10.30.10.0/24"
  type: internal
  location_id: loc-hamburg
  security_zone_id: sz-low
- id: net-ham-dmz
  name: Hamburg DMZ
  cidr: "10.30.1.0/24"
  type: dmz
  location_id: loc-hamburg
  security_zone_id: sz-medium
```

`stubs/cmdb/tenants.yaml`:
```yaml
- id: ten-corp
  name: Corporate IT
  code: CORP
- id: ten-dev
  name: Development
  code: DEV
```

`stubs/cmdb/security_zones.yaml`:
```yaml
- id: sz-low
  name: LOW
  level: 1
  description: Interne Systeme, kein Internetzugang
- id: sz-medium
  name: MEDIUM
  level: 2
  description: DMZ, kontrollierter Zugang
- id: sz-high
  name: HIGH
  level: 3
  description: Management-Netz, eingeschränkter Zugang
```

- [ ] **Step 2: Install PyYAML**

Add `pyyaml==6.0.2` to requirements.txt, run `pip install pyyaml`

- [ ] **Step 3: Commit**

```bash
git add stubs/ requirements.txt
git commit -m "feat: add CMDB static test data files (locations, networks, tenants, security zones)"
```

---

### Task 2: CMDB Client — Stub Implementation

**Files:**
- Create: `app/data/clients/__init__.py`
- Create: `app/data/clients/cmdb_client.py`
- Test: `tests/unit/test_cmdb_client.py`

- [ ] **Step 1: Write failing tests**

Test the CmdbStubClient:
- `get_locations()` → returns 3 locations
- `get_location(id)` → returns location or None
- `get_networks(location_id=None, security_zone_id=None)` → filtered list
- `get_network(id)` → returns network or None
- `get_tenants()` → returns 2 tenants
- `get_tenant(id)` → returns tenant or None
- `get_security_zones()` → returns 3 zones
- `get_security_zone(id)` → returns zone or None
- `get_networks_for_context(location_id, security_zone_id)` → filtered by both
- `health()` → returns True if data loaded

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement CmdbStubClient**

Loads YAML files from configurable path. All data in memory. Filter methods for networks.

```python
class CmdbClient:
    """Interface for CMDB access."""
    def get_locations(self): raise NotImplementedError
    def get_location(self, id): raise NotImplementedError
    # ... etc

class CmdbStubClient(CmdbClient):
    def __init__(self, data_path="./stubs/cmdb/"):
        self._locations = self._load("locations", data_path)
        self._networks = self._load("networks", data_path)
        # ...
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/data/clients/ tests/unit/test_cmdb_client.py
git commit -m "feat: add CMDB stub client with YAML data loading and filtering"
```

---

### Task 3: CMDB API Blueprint

**Files:**
- Create: `app/api/v1/cmdb.py`
- Modify: `app/__init__.py` (register blueprint, CMDB_MODE config)
- Test: `tests/integration/test_cmdb_api.py`

- [ ] **Step 1: Write failing tests**

Test CMDB endpoints (only available when CMDB_MODE=stub):
- `GET /api/v1/cmdb/locations` → 200, 3 locations
- `GET /api/v1/cmdb/locations/loc-berlin` → 200
- `GET /api/v1/cmdb/locations/nonexistent` → 404
- `GET /api/v1/cmdb/networks?location_id=loc-berlin` → filtered
- `GET /api/v1/cmdb/networks?location_id=loc-berlin&security_zone_id=sz-medium` → 1 result
- `GET /api/v1/cmdb/tenants` → 200, 2 tenants
- `GET /api/v1/cmdb/security-zones` → 200, 3 zones
- `GET /api/v1/cmdb/health` → 200

All endpoints require @login_required.

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement CMDB blueprint + register**

Add CMDB_MODE to config. Register blueprint in app factory. Create CmdbStubClient on app init when CMDB_MODE=stub.

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/cmdb.py app/__init__.py app/core/config.py tests/integration/test_cmdb_api.py
git commit -m "feat: add CMDB stub API endpoints (locations, networks, tenants, security zones)"
```

---

### Task 4: Context Domain + Resolution Service

**Files:**
- Create: `app/domain/context.py`
- Create: `app/services/context_service.py`
- Test: `tests/unit/test_context_domain.py`
- Test: `tests/unit/test_context_service.py`

- [ ] **Step 1: Write failing tests for domain**

Test OrderContext dataclass, validation (required fields), ResolvedContext.

- [ ] **Step 2: Write failing tests for service**

Test ContextService with mocked CmdbClient:
- `resolve_context(location_id, tenant_id, security_zone_id, network_id)` → returns ResolvedContext
- Validation: location not found, tenant not found, zone not found, zone not at location, network not at location
- `get_allowed_tenants(user_id)` → returns filtered tenants based on assignments
- CMDB unavailable → raises CmdbUnavailableError

- [ ] **Step 3: Run tests — verify FAIL**
- [ ] **Step 4: Implement domain + service**
- [ ] **Step 5: Run tests — verify PASS**
- [ ] **Step 6: Run ALL tests, commit**

```bash
git add app/domain/context.py app/services/context_service.py tests/unit/test_context_domain.py tests/unit/test_context_service.py
git commit -m "feat: add OrderContext domain model and ContextService with CMDB resolution"
```

---

### Task 5: Context Resolution API Endpoint

**Files:**
- Create: `app/api/v1/context.py`
- Modify: `app/__init__.py` (register blueprint)
- Test: `tests/integration/test_context_resolve_api.py`

- [ ] **Step 1: Write failing tests**

- `POST /api/v1/context/resolve` with valid context → 200 with ResolvedContext
- Missing location_id → 400
- Unknown location → 400 with CMDB error
- Zone not at location → 400
- `GET /api/v1/context/locations` → proxy to CMDB
- `GET /api/v1/context/tenants` → filtered by user permissions

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement context blueprint**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/context.py app/__init__.py tests/integration/test_context_resolve_api.py
git commit -m "feat: add context resolution endpoint with CMDB validation"
```

---

### Task 6: DB Models — AvailabilityRule + ContextRestriction + TenantAssignment

**Files:**
- Create: `app/data/db/models/context_rule.py`
- Create: `app/data/db/models/tenant_assignment.py`
- Modify: `app/data/db/models/__init__.py`
- Test: `tests/integration/test_context_rule_db.py`

- [ ] **Step 1: Write failing tests**

Test CRUD for AvailabilityRule, ContextRestriction, UserTenantAssignment models.

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement models**

AvailabilityRule: id, name, template_slug, rule_type (allow/deny), conditions (JSONB), priority, is_active, timestamps
ContextRestriction: id, name, template_slug (optional), parameter_key, restriction_type, conditions (JSONB), effect (JSONB), priority, is_active, timestamps
UserTenantAssignment: id, user_id, tenant_id, timestamps

- [ ] **Step 4: Create Alembic migration**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/data/db/models/ migrations/ tests/integration/test_context_rule_db.py
git commit -m "feat: add AvailabilityRule, ContextRestriction, and TenantAssignment DB models"
```

---

### Task 7: Availability Rules — Repository + Admin API

**Files:**
- Create: `app/data/repositories/context_rule_repository.py`
- Modify: `app/api/v1/context.py` (add admin endpoints)
- Test: `tests/integration/test_availability_rules_api.py`

- [ ] **Step 1: Write failing tests**

Admin CRUD for availability rules:
- `POST /api/v1/admin/context/availability-rules` → create rule (201)
- `GET /api/v1/admin/context/availability-rules` → list rules (200)
- `PATCH /api/v1/admin/context/availability-rules/{id}` → update (200)
- `DELETE /api/v1/admin/context/availability-rules/{id}` → delete (204)
- `POST /api/v1/context/check-availability` → check template availability in context (200)
- Admin-only (403 for requester)

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement repository + endpoints**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/data/repositories/context_rule_repository.py app/api/v1/context.py tests/integration/test_availability_rules_api.py
git commit -m "feat: add availability rules CRUD and context-based service filtering"
```

---

### Task 8: Context Restrictions — Admin API + Parameter Filtering

**Files:**
- Modify: `app/data/repositories/context_rule_repository.py`
- Modify: `app/services/context_service.py`
- Modify: `app/api/v1/context.py`
- Test: `tests/integration/test_context_restrictions_api.py`

- [ ] **Step 1: Write failing tests**

Admin CRUD for context restrictions:
- `POST /api/v1/admin/context/restrictions` → create restriction (201)
- `GET /api/v1/admin/context/restrictions` → list (200)
- `POST /api/v1/context/resolve-parameters` → resolve parameter constraints for a template in a given context (200)
- Example: In security_zone=sz-medium, cpu_cores max is 8 instead of 64

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/ tests/integration/test_context_restrictions_api.py
git commit -m "feat: add context restrictions for parameter-level filtering based on order context"
```

---

### Task 9: Tenant Assignment — Admin API

**Files:**
- Create: `app/data/repositories/tenant_repository.py`
- Modify: `app/api/v1/context.py`
- Test: `tests/integration/test_tenant_assignment_api.py`

- [ ] **Step 1: Write failing tests**

- `POST /api/v1/admin/context/tenant-assignments` → assign tenant to user (201)
- `GET /api/v1/admin/context/tenant-assignments?user_id=X` → list assignments (200)
- `DELETE /api/v1/admin/context/tenant-assignments/{id}` → remove (204)
- Context resolution respects tenant assignments (user can only resolve allowed tenants)

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/data/repositories/tenant_repository.py app/api/v1/context.py tests/integration/test_tenant_assignment_api.py
git commit -m "feat: add tenant assignment management for user-level ordering permissions"
```

---

### Task 10: Integrate Context with Order Creation

**Files:**
- Modify: `app/data/db/models/order.py` (add context fields)
- Modify: `app/services/order_service.py` (require context on create)
- Modify: `app/api/v1/orders.py` (accept context in create)
- Test: `tests/integration/test_order_context_integration.py`

- [ ] **Step 1: Write failing tests**

- Create order with context → 201, context stored
- Create order without context → 400
- Get order → context fields in response
- Context validation against CMDB on create
- Context immutable after submit

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

Add JSONB `context` column to OrderModel. Alembic migration. OrderService validates context via ContextService before creating order.

- [ ] **Step 4: Create Alembic migration**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/ migrations/ tests/integration/test_order_context_integration.py
git commit -m "feat: integrate OrderContext with order creation and CMDB validation"
```

---

### Task 11: Final Verification

- [ ] **Step 1: Run complete test suite**

Run: `pytest tests/ -v --tb=short`

- [ ] **Step 2: Verify endpoint count**

Expected new endpoints (~20):
- CMDB: locations, location detail, networks, tenants, security-zones, health (6)
- Context: resolve, locations proxy, tenants proxy, check-availability, resolve-parameters (5)
- Admin: availability-rules CRUD (4), restrictions CRUD (3), tenant-assignments CRUD (3)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: phase 4 complete — CMDB-Stub + context-dependent ordering"
```
