# Notifications System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In-app notifications with read/unread status, automatic event-triggered creation, email stub with protocol, sidebar badge, and full notifications page.

**Architecture:** Extend existing NotificationModel with `read_at` field. Add read/unread endpoints. Create EmailSender stub. Wire notification triggers into OrderService and ApprovalService. Frontend: real notifications page with filter/read, sidebar badge with polling, API client and hooks.

**Tech Stack:** Python/Flask, SQLAlchemy, Alembic (backend). React 19, TypeScript, TailwindCSS 4, tanstack-query (frontend).

**Spec:** `docs/superpowers/specs/2026-03-27-notifications-design.md`

---

## File Structure

### Backend
```
app/
├── data/
│   ├── db/models/notification.py      # MODIFY: add read_at
│   └── clients/email_sender.py        # NEW: EmailSender interface + stub
├── services/
│   ├── notification_service.py        # MODIFY: mark_read, mark_all_read, unread_count, create_event_notification
│   ├── order_service.py               # MODIFY: trigger notification on submit
│   └── approval_service.py            # MODIFY: trigger notification on approve/reject/create
└── api/v1/
    └── notifications.py               # MODIFY: 3 new endpoints + read_at in serialization

tests/
├── integration/test_notification_read_api.py   # NEW
└── unit/test_notification_events.py            # NEW
```

### Frontend
```
frontend/src/
├── api/notifications.ts                        # NEW
├── hooks/useNotifications.ts                   # NEW
├── pages/Notifications.tsx                     # REWRITE
└── components/Layout/Sidebar.tsx               # MODIFY: badge

frontend/tests/
└── pages/Notifications.test.tsx                # REWRITE
```

---

### Task 1: Backend — read_at Field + Read Endpoints

**Files:**
- Modify: `app/data/db/models/notification.py`
- Modify: `app/services/notification_service.py`
- Modify: `app/api/v1/notifications.py`
- Create: `tests/integration/test_notification_read_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_notification_read_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.services.notification_service import NotificationService


@pytest.fixture
def db_session(app):
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seed_notifications(db_session):
    service = NotificationService(db_session)
    n1 = service.send("order_submitted", "user@test.local", "test-requester",
                       "Order Submitted", "Your order ORD-1 has been submitted.")
    n2 = service.send("approval_requested", "user@test.local", "test-requester",
                       "Approval Needed", "Order ORD-2 needs approval.")
    return [n1, n2]


class TestMarkRead:
    def test_mark_read_returns_200(self, client, db_session, seed_notifications, requester_headers):
        nid = seed_notifications[0].id
        resp = client.patch(f"/api/v1/notifications/{nid}/read", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["read_at"] is not None

    def test_mark_read_not_found_returns_404(self, client, db_session, requester_headers):
        resp = client.patch("/api/v1/notifications/nonexistent/read", headers=requester_headers)
        assert resp.status_code == 404

    def test_mark_read_other_user_returns_403(self, client, db_session, seed_notifications, approver_headers):
        nid = seed_notifications[0].id
        resp = client.patch(f"/api/v1/notifications/{nid}/read", headers=approver_headers)
        assert resp.status_code == 403


class TestMarkAllRead:
    def test_mark_all_read_returns_200(self, client, db_session, seed_notifications, requester_headers):
        resp = client.patch("/api/v1/notifications/read-all", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["marked_count"] == 2

    def test_mark_all_read_only_own(self, client, db_session, seed_notifications, approver_headers):
        resp = client.patch("/api/v1/notifications/read-all", headers=approver_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["marked_count"] == 0


class TestUnreadCount:
    def test_unread_count_returns_count(self, client, db_session, seed_notifications, requester_headers):
        resp = client.get("/api/v1/notifications/unread-count", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 2

    def test_unread_count_after_mark_read(self, client, db_session, seed_notifications, requester_headers):
        nid = seed_notifications[0].id
        client.patch(f"/api/v1/notifications/{nid}/read", headers=requester_headers)
        resp = client.get("/api/v1/notifications/unread-count", headers=requester_headers)
        data = resp.get_json()
        assert data["count"] == 1


class TestListIncludesReadAt:
    def test_list_includes_read_at_field(self, client, db_session, seed_notifications, requester_headers):
        resp = client.get("/api/v1/notifications", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "read_at" in data["items"][0]
        assert data["items"][0]["read_at"] is None
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `source venv/bin/activate && DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/integration/test_notification_read_api.py -v --tb=short`

- [ ] **Step 3: Add read_at to model**

In `app/data/db/models/notification.py`, add after `error_message`:
```python
    read_at = Column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Add service methods**

In `app/services/notification_service.py`, add these methods to NotificationService:

```python
    def mark_read(self, notification_id: str, user_id: str) -> NotificationModel | None:
        notif = self.get_notification(notification_id)
        if notif is None:
            return None
        if notif.recipient_id != user_id:
            raise PermissionError("Not your notification.")
        if notif.read_at is None:
            notif.read_at = datetime.now(timezone.utc)
            self.session.commit()
        return notif

    def mark_all_read(self, user_id: str) -> int:
        from sqlalchemy import update
        result = self.session.execute(
            update(NotificationModel)
            .where(NotificationModel.recipient_id == user_id)
            .where(NotificationModel.read_at.is_(None))
            .values(read_at=datetime.now(timezone.utc))
        )
        self.session.commit()
        return result.rowcount

    def unread_count(self, user_id: str) -> int:
        return self.session.query(NotificationModel).filter(
            NotificationModel.recipient_id == user_id,
            NotificationModel.read_at.is_(None),
        ).count()
```

- [ ] **Step 5: Add endpoints + update serialization**

In `app/api/v1/notifications.py`:

Add `read_at` to `_serialize`:
```python
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
```

Add new endpoints:
```python
from app.core.errors import NotFoundError, ForbiddenError


@bp.route("/notifications/<notification_id>/read", methods=["PATCH"])
@login_required
def mark_read(notification_id):
    service = _get_service()
    try:
        notif = service.mark_read(notification_id, g.current_user.username)
    except PermissionError:
        raise ForbiddenError("Keine Berechtigung.")
    if notif is None:
        raise NotFoundError("Notification not found.")
    return jsonify(_serialize(notif)), 200


@bp.route("/notifications/read-all", methods=["PATCH"])
@login_required
def mark_all_read():
    service = _get_service()
    count = service.mark_all_read(g.current_user.username)
    return jsonify({"marked_count": count}), 200


@bp.route("/notifications/unread-count", methods=["GET"])
@login_required
def unread_count():
    service = _get_service()
    count = service.unread_count(g.current_user.username)
    return jsonify({"count": count}), 200
```

**Important:** The `read-all` route must be registered BEFORE the `<notification_id>/read` route to avoid Flask matching `read-all` as a notification_id. Reorder routes so `read-all` comes first.

- [ ] **Step 6: Run tests — verify PASS**
- [ ] **Step 7: Run full backend tests**

Run: `pytest tests/ -q --tb=short`

- [ ] **Step 8: Commit**

```bash
git add app/data/db/models/notification.py app/services/notification_service.py app/api/v1/notifications.py tests/integration/test_notification_read_api.py
git commit -m "feat: add read/unread notification endpoints with read_at field"
```

---

### Task 2: Backend — Email Sender Stub

**Files:**
- Create: `app/data/clients/email_sender.py`
- Create: `tests/unit/test_email_sender.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_email_sender.py
import logging
from app.data.clients.email_sender import StubEmailSender


class TestStubEmailSender:
    def test_send_logs_email(self, caplog):
        sender = StubEmailSender()
        with caplog.at_level(logging.INFO):
            sender.send("user@test.local", "Test Subject", "Test Body")
        assert "user@test.local" in caplog.text
        assert "Test Subject" in caplog.text

    def test_send_returns_true(self):
        sender = StubEmailSender()
        result = sender.send("user@test.local", "Subject", "Body")
        assert result is True
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement**

```python
# app/data/clients/email_sender.py
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmailSender(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, body: str) -> bool:
        pass


class StubEmailSender(EmailSender):
    def send(self, to_email: str, subject: str, body: str) -> bool:
        logger.info(
            "EMAIL STUB — To: %s | Subject: %s | Body: %s",
            to_email, subject, body[:200],
        )
        return True
```

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add app/data/clients/email_sender.py tests/unit/test_email_sender.py
git commit -m "feat: add EmailSender interface and StubEmailSender"
```

---

### Task 3: Backend — Event Notification Creation

**Files:**
- Modify: `app/services/notification_service.py`
- Create: `tests/unit/test_notification_events.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_notification_events.py
import pytest
from unittest.mock import MagicMock
from app.services.notification_service import NotificationService
from app.data.clients.email_sender import StubEmailSender


class TestCreateEventNotification:
    def setup_method(self):
        self.session = MagicMock()
        self.email_sender = StubEmailSender()
        self.service = NotificationService(self.session, email_sender=self.email_sender)

    def test_creates_order_submitted_notification(self):
        result = self.service.create_event_notification(
            event_type="order_submitted",
            recipient_id="user-1",
            recipient_email="user@test.local",
            context={"order_number": "ORD-2026-00001", "title": "My Order"},
        )
        assert result.event_type == "order_submitted"
        assert result.recipient_id == "user-1"
        assert "ORD-2026-00001" in result.subject
        self.session.add.assert_called_once()

    def test_creates_approval_requested_notification(self):
        result = self.service.create_event_notification(
            event_type="approval_requested",
            recipient_id="approver-1",
            recipient_email="approver@test.local",
            context={"order_number": "ORD-2026-00002", "requester": "user-1"},
        )
        assert result.event_type == "approval_requested"
        assert "Genehmigung" in result.subject

    def test_calls_email_sender(self):
        sender = MagicMock()
        service = NotificationService(self.session, email_sender=sender)
        service.create_event_notification(
            event_type="order_submitted",
            recipient_id="user-1",
            recipient_email="user@test.local",
            context={"order_number": "ORD-1", "title": "Test"},
        )
        sender.send.assert_called_once()

    def test_works_without_email_sender(self):
        service = NotificationService(self.session)
        result = service.create_event_notification(
            event_type="order_submitted",
            recipient_id="user-1",
            recipient_email="user@test.local",
            context={"order_number": "ORD-1", "title": "Test"},
        )
        assert result is not None
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

Update `NotificationService.__init__` to accept optional `email_sender`:

```python
class NotificationService:
    def __init__(self, session: Session, email_sender=None):
        self.session = session
        self.email_sender = email_sender
```

Add `create_event_notification` method and subject/body templates:

```python
    EVENT_TEMPLATES = {
        "order_submitted": {
            "subject": "Bestellung {order_number} eingereicht",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde erfolgreich eingereicht.",
        },
        "order_approved": {
            "subject": "Bestellung {order_number} genehmigt",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde genehmigt.",
        },
        "order_rejected": {
            "subject": "Bestellung {order_number} abgelehnt",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde abgelehnt. Grund: {reason}",
        },
        "order_provisioned": {
            "subject": "Bestellung {order_number} bereitgestellt",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde erfolgreich bereitgestellt.",
        },
        "order_failed": {
            "subject": "Bestellung {order_number} fehlgeschlagen",
            "body": "Bei der Bereitstellung von '{title}' ({order_number}) ist ein Fehler aufgetreten.",
        },
        "approval_requested": {
            "subject": "Genehmigung erforderlich: {order_number}",
            "body": "Bestellung {order_number} von {requester} erfordert Ihre Genehmigung.",
        },
        "approval_decided": {
            "subject": "Genehmigung entschieden: {order_number}",
            "body": "Die Genehmigung fuer Bestellung {order_number} wurde entschieden.",
        },
        "template_deprecated": {
            "subject": "Service-Template veraltet: {template_name}",
            "body": "Das Template '{template_name}' wurde als veraltet markiert.",
        },
        "system_maintenance": {
            "subject": "Wartungshinweis: {title}",
            "body": "{message}",
        },
    }

    def create_event_notification(self, event_type: str, recipient_id: str,
                                   recipient_email: str, context: dict) -> NotificationModel:
        tmpl = self.EVENT_TEMPLATES.get(event_type, {
            "subject": event_type,
            "body": str(context),
        })
        subject = tmpl["subject"].format_map({**context, "reason": context.get("reason", "")})
        body = tmpl["body"].format_map({**context, "reason": context.get("reason", ""), "message": context.get("message", "")})

        notification = self.send(event_type, recipient_email, recipient_id, subject, body)

        if self.email_sender:
            self.email_sender.send(recipient_email, subject, body)

        return notification
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add app/services/notification_service.py tests/unit/test_notification_events.py
git commit -m "feat: add create_event_notification with templates and email sender integration"
```

---

### Task 4: Backend — Wire Notification Triggers

**Files:**
- Modify: `app/services/order_service.py`
- Modify: `app/api/v1/orders.py` (submit endpoint triggers notification)

- [ ] **Step 1: Add notification trigger to order submit**

In `app/api/v1/orders.py`, in the `submit_order` endpoint, after the order is submitted successfully (around line 353, after the `return jsonify` block is prepared), add notification creation:

```python
    # Send notification
    from app.services.notification_service import NotificationService
    try:
        notif_service = NotificationService(g.db_session)
        notif_service.create_event_notification(
            event_type="order_submitted",
            recipient_id=submitted.requester_id,
            recipient_email=f"{submitted.requester_id}@marketplace.local",
            context={
                "order_number": submitted.order_number,
                "title": submitted.title or "",
            },
        )
    except Exception:
        pass  # Notification failure should not block submit
```

Add this before the `return jsonify(...)` in the submit_order function.

- [ ] **Step 2: Run existing submit tests to verify no regression**

Run: `pytest tests/integration/test_order_submit_api.py -v --tb=short`

- [ ] **Step 3: Commit**

```bash
git add app/api/v1/orders.py
git commit -m "feat: trigger order_submitted notification on order submit"
```

---

### Task 5: Frontend — Notifications API + Hooks

**Files:**
- Create: `frontend/src/api/notifications.ts`
- Create: `frontend/src/hooks/useNotifications.ts`

- [ ] **Step 1: Create API client**

```typescript
// frontend/src/api/notifications.ts
import { apiClient } from './client'

export interface Notification {
  id: string
  event_type: string
  recipient_email: string
  recipient_id: string
  subject: string
  body: string
  status: string
  attempts: number
  created_at: string
  sent_at: string | null
  error_message: string | null
  read_at: string | null
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  limit: number
  offset: number
}

export const notificationsApi = {
  async list(token: string, params?: { limit?: number; offset?: number }): Promise<NotificationListResponse> {
    const qs = new URLSearchParams()
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    const query = qs.toString()
    return (await apiClient.get(`/api/v1/notifications${query ? `?${query}` : ''}`, token)) as NotificationListResponse
  },

  async markRead(token: string, id: string): Promise<Notification> {
    return (await apiClient.patch(`/api/v1/notifications/${id}/read`, {}, token)) as Notification
  },

  async markAllRead(token: string): Promise<{ marked_count: number }> {
    return (await apiClient.patch('/api/v1/notifications/read-all', {}, token)) as { marked_count: number }
  },

  async unreadCount(token: string): Promise<{ count: number }> {
    return (await apiClient.get('/api/v1/notifications/unread-count', token)) as { count: number }
  },
}
```

- [ ] **Step 2: Create hooks**

```typescript
// frontend/src/hooks/useNotifications.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/notifications'
import { useAuthStore } from '../store/authStore'

export function useNotifications(params?: { limit?: number; offset?: number }) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['notifications', params],
    queryFn: () => notificationsApi.list(token!, params),
    enabled: !!token,
  })
}

export function useUnreadCount() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.unreadCount(token!),
    enabled: !!token,
    refetchInterval: 60_000,
  })
}

export function useMarkRead() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(token!, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })
}

export function useMarkAllRead() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(token!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })
}
```

- [ ] **Step 3: Run TS check + tests**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/notifications.ts frontend/src/hooks/useNotifications.ts
git commit -m "feat(frontend): add notifications API client and hooks with polling"
```

---

### Task 6: Frontend — Notifications Page + Sidebar Badge

**Files:**
- Rewrite: `frontend/src/pages/Notifications.tsx`
- Modify: `frontend/src/components/Layout/Sidebar.tsx`
- Rewrite: `frontend/tests/pages/Notifications.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/Notifications.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Notifications from '../../src/pages/Notifications'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/notifications', () => ({
  notificationsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'n1', event_type: 'order_submitted', recipient_email: 'u@t',
          recipient_id: 'user-1', subject: 'Bestellung ORD-1 eingereicht',
          body: 'Ihre Bestellung wurde eingereicht.', status: 'sent',
          attempts: 0, created_at: '2026-01-15T10:00:00Z', sent_at: '2026-01-15T10:00:00Z',
          error_message: null, read_at: null,
        },
        {
          id: 'n2', event_type: 'approval_requested', recipient_email: 'u@t',
          recipient_id: 'user-1', subject: 'Genehmigung erforderlich',
          body: 'Eine Genehmigung wird benoetigt.', status: 'sent',
          attempts: 0, created_at: '2026-01-14T10:00:00Z', sent_at: '2026-01-14T10:00:00Z',
          error_message: null, read_at: '2026-01-14T11:00:00Z',
        },
      ],
      total: 2, limit: 50, offset: 0,
    }),
    unreadCount: vi.fn().mockResolvedValue({ count: 1 }),
    markRead: vi.fn().mockResolvedValue({}),
    markAllRead: vi.fn().mockResolvedValue({ marked_count: 1 }),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Notifications />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Notifications', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'user-1', display_name: 'User', email: 'u@t', roles: ['requester'] },
    })
  })

  it('renders notifications heading', async () => {
    renderPage()
    expect(await screen.findByText('Benachrichtigungen')).toBeInTheDocument()
  })

  it('renders notification subjects', async () => {
    renderPage()
    expect(await screen.findByText('Bestellung ORD-1 eingereicht')).toBeInTheDocument()
    expect(await screen.findByText('Genehmigung erforderlich')).toBeInTheDocument()
  })

  it('shows alle als gelesen button', async () => {
    renderPage()
    expect(await screen.findByText('Alle als gelesen markieren')).toBeInTheDocument()
  })

  it('shows unread indicator on unread notification', async () => {
    renderPage()
    const items = await screen.findAllByTestId('notification-item')
    expect(items[0]).toHaveAttribute('data-unread', 'true')
    expect(items[1]).toHaveAttribute('data-unread', 'false')
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement Notifications page**

```tsx
// frontend/src/pages/Notifications.tsx
import { useState } from 'react'
import { useNotifications, useMarkRead, useMarkAllRead } from '../hooks/useNotifications'
import type { Notification } from '../api/notifications'

const EVENT_BADGES: Record<string, { label: string; color: string }> = {
  order_submitted: { label: 'Order', color: 'bg-blue-100 text-blue-700' },
  order_approved: { label: 'Order', color: 'bg-green-100 text-green-700' },
  order_rejected: { label: 'Order', color: 'bg-red-100 text-red-700' },
  order_provisioned: { label: 'Order', color: 'bg-green-100 text-green-700' },
  order_failed: { label: 'Order', color: 'bg-red-100 text-red-700' },
  approval_requested: { label: 'Approval', color: 'bg-yellow-100 text-yellow-700' },
  approval_decided: { label: 'Approval', color: 'bg-yellow-100 text-yellow-700' },
  template_deprecated: { label: 'System', color: 'bg-gray-100 text-gray-700' },
  system_maintenance: { label: 'System', color: 'bg-gray-100 text-gray-700' },
}

function NotificationItem({ notif, onRead }: { notif: Notification; onRead: () => void }) {
  const isUnread = !notif.read_at
  const badge = EVENT_BADGES[notif.event_type] ?? { label: notif.event_type, color: 'bg-gray-100 text-gray-600' }
  const date = new Date(notif.created_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })

  return (
    <div
      data-testid="notification-item"
      data-unread={String(isUnread)}
      onClick={() => isUnread && onRead()}
      className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer ${isUnread ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
    >
      <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${isUnread ? 'bg-blue-500' : 'bg-gray-300'}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs px-2 py-0.5 rounded-full ${badge.color}`}>{badge.label}</span>
          <span className="text-xs text-gray-400">{date}</span>
        </div>
        <p className={`text-sm ${isUnread ? 'font-semibold text-gray-900' : 'text-gray-600'}`}>{notif.subject}</p>
        <p className="text-xs text-gray-400 mt-0.5 truncate">{notif.body}</p>
      </div>
    </div>
  )
}

export default function Notifications() {
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const { data, isLoading } = useNotifications({ limit: 50 })
  const markRead = useMarkRead()
  const markAllRead = useMarkAllRead()

  const notifications = data?.items ?? []
  const filtered = filter === 'unread' ? notifications.filter((n) => !n.read_at) : notifications

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Benachrichtigungen</h1>
        <button onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending}
          className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50">
          Alle als gelesen markieren
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          Alle
        </button>
        <button onClick={() => setFilter('unread')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'unread' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          Ungelesen
        </button>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Lade Benachrichtigungen...</p>
      ) : filtered.length === 0 ? (
        <p className="text-gray-400">Keine Benachrichtigungen vorhanden</p>
      ) : (
        <div className="space-y-1">
          {filtered.map((n) => (
            <NotificationItem key={n.id} notif={n} onRead={() => markRead.mutate(n.id)} />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Add badge to Sidebar**

In `frontend/src/components/Layout/Sidebar.tsx`:

Add import at top:
```tsx
import { useUnreadCount } from '../../hooks/useNotifications'
```

Inside the `Sidebar` component, add:
```tsx
  const { data: unreadData } = useUnreadCount()
  const unreadCount = unreadData?.count ?? 0
```

In the `NavItemLink` component, add a `badge` optional prop:
```tsx
function NavItemLink({ item, collapsed, badge }: { item: NavItem; collapsed: boolean; badge?: number }) {
```

Add badge rendering inside NavItemLink, after the label span:
```tsx
      {badge && badge > 0 && (
        <span className="ml-auto bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
```

When rendering the Notifications nav item, pass the badge:
```tsx
  <NavItemLink key={item.label} item={item} collapsed={collapsed}
    badge={item.to === '/notifications' ? unreadCount : undefined} />
```

- [ ] **Step 5: Run tests — verify PASS**

Run: `cd frontend && npx vitest run`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Notifications.tsx frontend/tests/pages/Notifications.test.tsx frontend/src/components/Layout/Sidebar.tsx
git commit -m "feat(frontend): rewrite Notifications page with read/unread, add sidebar badge with polling"
```

---

### Task 7: Final Verification

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontend && npx vitest run`

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Run full backend test suite**

Run: `source venv/bin/activate && DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/ -q`

- [ ] **Step 4: Final commit**

```bash
git commit -m "chore: notifications system complete — read/unread, events, email stub, sidebar badge"
```
