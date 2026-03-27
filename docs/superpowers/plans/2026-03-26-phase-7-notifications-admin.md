# Phase 7: Notifications + Resources + Admin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement email notifications (template-based, fire-and-forget), secure credential delivery links, resource overview for users, admin dashboard aggregation, and an immutable audit log.

**Architecture:** NotificationService for email dispatch. AuditService for logging. Resources read from orders/provisioning data. Admin dashboard aggregates from existing models. All are relatively lightweight — reading/writing from existing data.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, pytest

**Spec:** `docs/specs/resources-notifications-admin.md` — Features 5.1, 6.1-6.2, 7.1-7.2

---

### Task 1: Audit Log — Model + Service + API

**Files:**
- Create: `app/data/db/models/audit_log.py` (AuditLogModel)
- Create: `app/data/repositories/audit_log_repository.py`
- Create: `app/services/audit_service.py`
- Create: `app/api/v1/admin.py` (admin blueprint for dashboard + audit)
- Test: `tests/integration/test_audit_log_api.py`

Audit log: id, timestamp, actor_id, actor_type (user/system), action, entity_type, entity_id, details (JSONB), request_id.

Endpoints:
- GET /api/v1/admin/audit-log — list with filters (actor_id, action, entity_type, date range), pagination (admin only)
- GET /api/v1/admin/audit-log/export — export as JSON (admin only)

TDD: tests first, implement, commit.

```bash
git commit -m "feat: add audit log model, service, and admin API endpoint"
```

---

### Task 2: Notification Service — Fire-and-Forget Email Stubs

**Files:**
- Create: `app/data/db/models/notification.py` (NotificationModel)
- Create: `app/services/notification_service.py`
- Test: `tests/unit/test_notification_service.py`

NotificationModel: id, event_type, recipient_email, recipient_id, subject, body, status (pending/sent/failed), attempts, created_at, sent_at, error_message.

NotificationService:
- send_notification(event_type, recipient_email, recipient_id, subject, body)
- Creates DB record with status "pending"
- In dev mode: marks as "sent" immediately (no actual email)
- list_notifications(recipient_id=None, status=None)

Event types: order_submitted, order_approved, order_rejected, provisioning_done, provisioning_failed, approval_requested, credentials_ready.

TDD: tests first, implement, commit.

```bash
git commit -m "feat: add notification service with fire-and-forget email stubs"
```

---

### Task 3: Secure Credential Links

**Files:**
- Create: `app/data/db/models/credential_link.py` (CredentialLinkModel)
- Create: `app/services/credential_service.py`
- Modify: `app/api/v1/provisioning.py` (add credential endpoints)
- Test: `tests/integration/test_credential_api.py`

CredentialLinkModel: id, order_item_id, token_hash (SHA-256), credentials (JSONB encrypted or plain for MVP), expires_at, accessed_at, is_consumed.

Endpoints:
- POST /api/v1/admin/orders/{order_id}/items/{item_id}/credentials — create secure link (admin, returns one-time URL)
- GET /api/v1/credentials/{token} — retrieve credentials (no auth, token-based, one-time, 48h TTL)

TDD: tests first, implement, commit.

```bash
git commit -m "feat: add secure credential delivery with one-time token links"
```

---

### Task 4: Resource Overview API

**Files:**
- Create: `app/api/v1/resources.py`
- Modify: `app/__init__.py`
- Test: `tests/integration/test_resources_api.py`

Endpoints:
- GET /api/v1/resources — list provisioned resources for current user (from orders with status done, items with provisioning_status done). Shows: hostname, IP, service type, status, order date, order reference.
- GET /api/v1/resources/{item_id} — resource detail

This reads from existing OrderItem + Order data. No new DB models needed.

TDD: tests first, implement, commit.

```bash
git commit -m "feat: add resource overview API for provisioned services"
```

---

### Task 5: Admin Dashboard API

**Files:**
- Modify: `app/api/v1/admin.py` (add dashboard endpoint)
- Test: `tests/integration/test_admin_dashboard_api.py`

Endpoint:
- GET /api/v1/admin/dashboard — aggregated view (admin only):
  - order_counts: {draft: N, submitted: N, provisioning: N, done: N, failed: N}
  - pending_approvals: N
  - recent_orders: last 10
  - service_account_health: from CMDB/GitLab health
  - provisioning_active: count of items in provisioning

This aggregates from existing models.

TDD: tests first, implement, commit.

```bash
git commit -m "feat: add admin dashboard API with aggregated system overview"
```

---

### Task 6: Final Verification

- [ ] Run complete test suite
- [ ] Verify all endpoints
- [ ] Final commit

```bash
git commit -m "chore: phase 7 complete — Notifications, Resources, Admin Dashboard, Audit Log"
```
