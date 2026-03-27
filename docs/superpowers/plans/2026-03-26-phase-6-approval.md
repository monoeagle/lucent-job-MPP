# Phase 6: Approval Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement approval rules, a 1-step approval workflow with approve/reject, and automatic timeout rejection. Wire into the order submit flow so that orders requiring approval go through pending_approval before provisioning.

**Architecture:** ApprovalRule and ApprovalRequest as DB models. ApprovalService handles rule evaluation, decision processing, and timeout. The submit flow checks rules after setting "submitted" and routes to either provisioning or pending_approval.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, pytest

**Spec:** `docs/specs/approval-workflow.md` — Features 8.1-8.3

---

## File Structure (new/modified)

```
app/
├── data/db/models/
│   ├── approval.py                  # ApprovalRuleModel, ApprovalRequestModel
│   └── __init__.py                  # updated
├── data/repositories/
│   └── approval_repository.py       # CRUD for rules + requests
├── services/
│   └── approval_service.py          # Rule evaluation, decisions, timeout
└── api/v1/
    └── approvals.py                 # Blueprint: approval endpoints

tests/
├── unit/
│   └── test_approval_service.py
└── integration/
    ├── test_approval_rules_api.py
    ├── test_approval_workflow_api.py
    └── test_approval_submit_integration.py
```

---

### Task 1: Approval DB Models + Migration

**Files:**
- Create: `app/data/db/models/approval.py`
- Modify: `app/data/db/models/__init__.py`
- Test: `tests/integration/test_approval_db.py`

- [ ] **Step 1: Write failing tests**

Test ApprovalRuleModel and ApprovalRequestModel CRUD. ApprovalRule has: id, name, rule_type (cost_threshold/service_type/always), threshold_eur, service_type_slug, is_active, created_at, updated_at. ApprovalRequest has: id, order_id, status (pending/approved/rejected), approval_rule_ids (JSONB array), requested_at, deadline_at, decided_by, decided_at, decision_reason.

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement models, create Alembic migration**
- [ ] **Step 4: Run tests — verify PASS, run ALL, commit**

```bash
git commit -m "feat: add ApprovalRule and ApprovalRequest database models"
```

---

### Task 2: Approval Repository

**Files:**
- Create: `app/data/repositories/approval_repository.py`
- Test: `tests/integration/test_approval_repository.py`

- [ ] **Step 1: Write failing tests**

Repository methods:
- create_rule(name, rule_type, threshold_eur, service_type_slug, is_active)
- list_rules(is_active=None)
- get_rule(id)
- update_rule(id, **fields)
- delete_rule(id) — checks no pending requests reference it
- create_request(order_id, approval_rule_ids, deadline_hours)
- get_request(id)
- get_request_for_order(order_id)
- list_pending_requests()
- list_expired_requests(now)
- decide_request(id, decision, decided_by, decision_reason) — atomic CAS WHERE status='pending'

- [ ] **Step 2-6: Standard TDD cycle, commit**

```bash
git commit -m "feat: add ApprovalRepository with rule CRUD and request management"
```

---

### Task 3: Approval Service — Rule Evaluation + Decisions

**Files:**
- Create: `app/services/approval_service.py`
- Test: `tests/unit/test_approval_service.py`

- [ ] **Step 1: Write failing tests** with mocked repos:

- evaluate_rules(order) — no rules → no approval needed
- evaluate_rules — cost_threshold exceeded → approval needed
- evaluate_rules — service_type matches → approval needed
- evaluate_rules — always rule → approval needed
- evaluate_rules — template has approval_always_required=true → approval needed
- evaluate_rules — inactive rule → ignored
- approve_request(request_id, approver_id, reason) — success
- approve_request — self-approval blocked (allow_self_approval=false)
- approve_request — already decided → ConflictError
- reject_request(request_id, approver_id, reason) — success
- reject_request — missing reason → ValidationError
- process_timeouts() — expires overdue requests

- [ ] **Step 2-6: Standard TDD cycle, commit**

```bash
git commit -m "feat: add ApprovalService with rule evaluation, decisions, and timeout processing"
```

---

### Task 4: Approval API — Rules Admin + Workflow Endpoints

**Files:**
- Create: `app/api/v1/approvals.py`
- Modify: `app/__init__.py`
- Test: `tests/integration/test_approval_rules_api.py`
- Test: `tests/integration/test_approval_workflow_api.py`

- [ ] **Step 1: Write failing tests**

**Rules Admin (admin only):**
- POST /api/v1/admin/approval-rules → create (201)
- GET /api/v1/admin/approval-rules → list (200)
- PATCH /api/v1/admin/approval-rules/{id} → update (200)
- DELETE /api/v1/admin/approval-rules/{id} → delete (204)
- GET /api/v1/admin/approval-settings → get timeout config (200)
- PUT /api/v1/admin/approval-settings → update timeout (200)

**Workflow (approver/admin):**
- GET /api/v1/approvals → list pending requests (200)
- GET /api/v1/approvals/{id} → request detail with order info (200)
- POST /api/v1/approvals/{id}/approve → approve (200)
- POST /api/v1/approvals/{id}/reject → reject with reason (200)
- POST /api/v1/approvals/{id}/reject without reason → 400

- [ ] **Step 2-6: Standard TDD cycle, commit**

```bash
git commit -m "feat: add approval rules admin and workflow API endpoints"
```

---

### Task 5: Integration — Submit Routes Through Approval

**Files:**
- Modify: `app/services/order_service.py`
- Modify: `app/api/v1/orders.py`
- Test: `tests/integration/test_approval_submit_integration.py`

- [ ] **Step 1: Write failing tests**

End-to-end:
1. Create approval rule (cost_threshold > 50 EUR)
2. Create template with estimated_cost=100 EUR
3. Create order → add item → validate → submit
4. Verify order status is "pending_approval" (not "provisioning")
5. Approve the request
6. Verify order status transitions through "approved" to "provisioning"

Also test:
- Submit without matching rule → goes directly to provisioning
- Template with approval_always_required=true → always pending_approval

- [ ] **Step 2: Wire approval into submit flow**

In OrderService.submit_order(), after setting status to "submitted":
1. Call ApprovalService.evaluate_rules(order)
2. If approval needed: create ApprovalRequest, set order to pending_approval
3. If no approval: dispatch provisioning (existing flow)

In the approve handler: after setting request to approved, trigger provisioning dispatch.

- [ ] **Step 3-6: Standard TDD cycle, commit**

```bash
git commit -m "feat: wire approval workflow into order submit flow"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run complete test suite**
- [ ] **Step 2: Verify endpoints**

Expected new endpoints (~10):
- Admin: approval-rules CRUD (4), approval-settings GET/PUT (2)
- Workflow: list pending, detail, approve, reject (4)

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: phase 6 complete — Approval Workflow"
```
