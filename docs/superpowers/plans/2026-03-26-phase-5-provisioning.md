# Phase 5: GitLab-Mock + Provisioning Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the GitLab-Mock as a separate Flask process, the Job-Dispatcher that triggers pipelines after order submit, Status-Sync via polling/webhook, and basic error handling with rollback markers. AD/IPAM integration deferred as interfaces.

**Architecture:** GitLab-Mock runs as a separate Flask app (stubs/gitlab_mock.py). The portal's ProvisioningService dispatches jobs per OrderItem via GitLab API. Status-Sync polls the mock (or receives webhooks). OrderItem gets provisioning_status + job_id columns.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, requests (HTTP client), pytest

**Specs:**
- `docs/specs/development-testing.md` Feature 9.2 (GitLab-Mock)
- `docs/specs/provisioning-engine.md` Features 4.1-4.2, 4.6-4.7

**Scope for this phase (MVP):**
- GitLab-Mock (Feature 9.2) — full implementation
- Job-Dispatcher (Feature 4.1) — GitLab method only
- Status-Sync (Feature 4.2) — polling + webhook
- Error handling (Feature 4.6) — basic: mark failed, log rollback needs
- Idempotenz (Feature 4.7) — DB-based CAS
- AD/IPAM (Features 4.3-4.5) — interfaces only, no implementation

---

## File Structure (new/modified)

```
stubs/
└── gitlab_mock.py                      # Separate Flask app for GitLab mock

app/
├── domain/
│   └── provisioning.py                 # ProvisioningStatus, DispatchEvent
├── data/
│   ├── clients/
│   │   └── gitlab_client.py            # GitLab API client
│   ├── db/models/
│   │   ├── dispatch_log.py             # DispatchLogModel
│   │   └── order.py                    # Add provisioning_status, job_id to OrderItemModel
│   └── repositories/
│       └── dispatch_log_repository.py
├── services/
│   └── provisioning_service.py         # Dispatch, status sync, error handling
└── api/v1/
    ├── provisioning.py                 # Webhook receiver, admin dispatch endpoints
    └── orders.py                       # Update status endpoint to include provisioning data

tests/
├── unit/
│   ├── test_provisioning_domain.py
│   ├── test_gitlab_client.py
│   └── test_provisioning_service.py
└── integration/
    ├── test_gitlab_mock.py
    ├── test_dispatch_api.py
    └── test_provisioning_webhook_api.py
```

---

### Task 1: GitLab-Mock — Separate Flask App

**Files:**
- Create: `stubs/gitlab_mock.py`
- Test: `tests/integration/test_gitlab_mock.py`

- [ ] **Step 1: Write failing tests**

Tests use a test client for the GitLab mock app:
- POST trigger pipeline → 201 with pipeline_id
- POST trigger without token → 401
- GET pipeline status → 200 with current status
- GET unknown pipeline → 404
- GET /dev/gitlab-mock/pipelines → inspect all pipelines
- DELETE /dev/gitlab-mock/pipelines → reset

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement gitlab_mock.py**

Separate Flask app with:
- `POST /api/v4/projects/<project_id>/trigger/pipeline` — accepts token, ref, variables. Creates pipeline with auto-incrementing ID, status "pending". Stores variables.
- `GET /api/v4/projects/<project_id>/pipelines/<pipeline_id>` — returns current status
- `GET /dev/gitlab-mock/pipelines` — inspect all pipelines with status history
- `DELETE /dev/gitlab-mock/pipelines` — reset all
- In-memory storage (dict of pipelines)
- Status transitions happen immediately for test simplicity (no async delays in test mode)
- Configurable result via `GITLAB_MOCK_PIPELINE_RESULT` env var

Add `requests==2.32.3` to requirements.txt.

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add stubs/gitlab_mock.py tests/integration/test_gitlab_mock.py requirements.txt
git commit -m "feat: add GitLab mock as separate Flask app with pipeline simulation"
```

---

### Task 2: Provisioning Domain + DB Changes

**Files:**
- Create: `app/domain/provisioning.py`
- Create: `app/data/db/models/dispatch_log.py`
- Modify: `app/data/db/models/order.py` (add provisioning_status, job_id to OrderItemModel)
- Modify: `app/data/db/models/__init__.py`
- Test: `tests/unit/test_provisioning_domain.py`

- [ ] **Step 1: Write failing tests for domain**

```python
from app.domain.provisioning import ProvisioningStatus

class TestProvisioningStatus:
    def test_values(self):
        assert ProvisioningStatus.NOT_STARTED == "not_started"
        assert ProvisioningStatus.PENDING == "pending"
        assert ProvisioningStatus.PROVISIONING == "provisioning"
        assert ProvisioningStatus.DONE == "done"
        assert ProvisioningStatus.FAILED == "failed"

    def test_transitions(self):
        assert ProvisioningStatus.can_transition("not_started", "pending") is True
        assert ProvisioningStatus.can_transition("pending", "provisioning") is True
        assert ProvisioningStatus.can_transition("provisioning", "done") is True
        assert ProvisioningStatus.can_transition("provisioning", "failed") is True
        assert ProvisioningStatus.can_transition("done", "failed") is False
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement domain + DB changes**

`app/domain/provisioning.py`:
```python
class ProvisioningStatus:
    NOT_STARTED = "not_started"
    PENDING = "pending"
    PROVISIONING = "provisioning"
    DONE = "done"
    FAILED = "failed"

    _TRANSITIONS = {
        "not_started": {"pending"},
        "pending": {"provisioning", "failed"},
        "provisioning": {"done", "failed"},
        "done": set(),
        "failed": set(),
    }

    @classmethod
    def can_transition(cls, from_s, to_s):
        return to_s in cls._TRANSITIONS.get(from_s, set())
```

Add to OrderItemModel: `provisioning_status` (String, default "not_started"), `job_id` (String, nullable).

DispatchLogModel: id, order_id, order_item_id, job_id, dispatch_method, dispatched_at, attempt_count, status, error_message.

Create Alembic migration.

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/domain/provisioning.py app/data/db/models/ migrations/ tests/unit/test_provisioning_domain.py
git commit -m "feat: add ProvisioningStatus domain, dispatch_log model, and provisioning columns on OrderItem"
```

---

### Task 3: GitLab Client

**Files:**
- Create: `app/data/clients/gitlab_client.py`
- Test: `tests/unit/test_gitlab_client.py`

- [ ] **Step 1: Write failing tests**

Test GitLabClient with mocked requests:
- trigger_pipeline(project_id, token, ref, variables) → returns pipeline dict
- get_pipeline_status(project_id, pipeline_id) → returns status
- Handle connection error → raises GitLabUnavailableError
- Handle 401 → raises GitLabAuthError

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement GitLabClient**

Uses `requests` library to call GitLab API. Base URL configurable.

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/data/clients/gitlab_client.py tests/unit/test_gitlab_client.py
git commit -m "feat: add GitLab API client for pipeline triggering and status polling"
```

---

### Task 4: Provisioning Service — Dispatch + Status Sync

**Files:**
- Create: `app/services/provisioning_service.py`
- Create: `app/data/repositories/dispatch_log_repository.py`
- Test: `tests/unit/test_provisioning_service.py`

- [ ] **Step 1: Write failing tests**

With mocked repos and GitLab client:
- dispatch_order(order) → dispatches each item, sets provisioning_status=pending, stores job_id
- dispatch_order with already provisioning item → skips (idempotenz)
- dispatch_item(order_id, item) → triggers pipeline, stores log
- sync_item_status(item) → polls GitLab, updates provisioning_status
- sync_item_status: running → provisioning
- sync_item_status: success → done
- sync_item_status: failed → failed
- handle_webhook(payload) → updates item status from webhook data
- check_all_items_done(order) → True if all done, transitions order to done
- check_any_item_failed(order) → True if any failed, transitions order to failed

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement ProvisioningService**

Key logic:
- `dispatch_order(order_id)`: loads order, for each item with provisioning_status="not_started", calls dispatch_item
- `dispatch_item(order_id, item_id)`: atomic CAS (UPDATE WHERE provisioning_status='not_started' AND job_id IS NULL), triggers GitLab, stores job_id
- `sync_status(order_id)`: for each item in provisioning, polls GitLab, maps status, updates
- `handle_webhook(pipeline_id, status)`: finds item by job_id, updates status
- `update_order_aggregate_status(order_id)`: checks all items, transitions order to done/failed

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/services/provisioning_service.py app/data/repositories/dispatch_log_repository.py tests/unit/test_provisioning_service.py
git commit -m "feat: add ProvisioningService with dispatch, status sync, and webhook handling"
```

---

### Task 5: Provisioning API — Webhook + Admin Endpoints

**Files:**
- Create: `app/api/v1/provisioning.py`
- Modify: `app/__init__.py`
- Test: `tests/integration/test_provisioning_webhook_api.py`
- Test: `tests/integration/test_dispatch_api.py`

- [ ] **Step 1: Write failing tests**

Webhook endpoint:
- `POST /api/v1/webhooks/gitlab` — receives GitLab webhook payload, updates item status
- No auth required (webhook from external system, validated by payload structure)

Admin endpoints:
- `GET /api/v1/admin/dispatcher/config` → current dispatcher config (admin only)
- `GET /api/v1/admin/orders/{order_id}/dispatch-log` → dispatch log for order (admin only)
- `POST /api/v1/admin/orders/{order_id}/items/{item_id}/dispatch` → manual dispatch (admin only)

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement endpoints**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/provisioning.py app/__init__.py tests/integration/
git commit -m "feat: add provisioning webhook receiver and admin dispatch endpoints"
```

---

### Task 6: Integration — Submit Triggers Dispatch

**Files:**
- Modify: `app/services/order_service.py` (trigger dispatch after submit)
- Modify: `app/api/v1/orders.py` (wire provisioning service)
- Test: `tests/integration/test_submit_dispatch_integration.py`

- [ ] **Step 1: Write failing tests**

End-to-end: create order → add item → validate → submit → verify dispatch was triggered → verify item has job_id and provisioning_status

Uses the GitLab mock as test fixture.

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Wire provisioning into submit flow**

After successful submit in OrderService, call ProvisioningService.dispatch_order(order_id).

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/services/order_service.py app/api/v1/orders.py tests/integration/test_submit_dispatch_integration.py
git commit -m "feat: trigger provisioning dispatch on order submit"
```

---

### Task 7: Final Verification

- [ ] **Step 1: Run complete test suite**

Run: `pytest tests/ -v --tb=short`

- [ ] **Step 2: Verify new endpoints**

Expected:
1. GitLab Mock: trigger, status, inspect, reset (4 — separate app)
2. `POST /api/v1/webhooks/gitlab` (webhook receiver)
3. `GET /api/v1/admin/dispatcher/config`
4. `GET /api/v1/admin/orders/{order_id}/dispatch-log`
5. `POST /api/v1/admin/orders/{order_id}/items/{item_id}/dispatch`

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: phase 5 complete — GitLab-Mock + Provisioning Engine"
```
