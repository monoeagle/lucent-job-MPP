# Notifications System — Design Spec

**Ziel:** In-App Notifications mit read/unread-Status, automatischer Erstellung bei Events, E-Mail-Stub mit Protokoll, Sidebar-Badge und erweiterter Notifications-Seite.

---

## Backend-Erweiterungen

### Neues Feld: read_at

`NotificationModel` erhaelt `read_at` (DateTime, nullable). Null = ungelesen, Timestamp = gelesen. Erfordert Alembic-Migration.

### Neue Endpoints

| Endpoint | Methode | Beschreibung | Auth |
|----------|---------|-------------|------|
| `/api/v1/notifications/{id}/read` | PATCH | Einzelne Notification als gelesen markieren | login |
| `/api/v1/notifications/read-all` | PATCH | Alle eigenen Notifications als gelesen markieren | login |
| `/api/v1/notifications/unread-count` | GET | Anzahl ungelesener Notifications | login |

### Bestehende Endpoints (unveraendert)

| Endpoint | Methode | Auth |
|----------|---------|------|
| `/api/v1/notifications` | GET | login (eigene) |
| `/api/v1/admin/notifications` | GET | admin (alle) |

Die GET-Response wird um `read_at` Feld erweitert.

### Automatische Notification-Erstellung

Events die Notifications ausloesen:

| Event | Empfaenger | event_type | Trigger-Ort |
|-------|-----------|------------|-------------|
| Order submitted | Requester | `order_submitted` | OrderService.submit_order |
| Order approved | Requester | `order_approved` | ApprovalService.approve |
| Order rejected | Requester | `order_rejected` | ApprovalService.reject |
| Order provisioned | Requester | `order_provisioned` | ProvisioningService.dispatch_order |
| Order failed | Requester | `order_failed` | ProvisioningService (on failure) |
| Approval requested | Alle Approver | `approval_requested` | ApprovalService.create_approval_request |
| Approval decided | Requester | `approval_decided` | ApprovalService.approve/reject |
| Template deprecated | Requester mit aktiven Orders | `template_deprecated` | CatalogService (admin endpoint) |
| System maintenance | Alle User | `system_maintenance` | Manuell via Admin-API |

**Mechanismus:** `NotificationService.create_event_notification(event_type, recipient_id, recipient_email, context)` wird direkt in den bestehenden Services aufgerufen. Kein Event-Bus. Die Methode erstellt die Notification und ruft den EmailSender auf.

### E-Mail-Stub

Interface `EmailSender` mit Methode `send(to_email, subject, body)`.
`StubEmailSender` implementiert das Interface und loggt die E-Mail ins Python-Logging (kein echter Versand).

Jede Notification die erstellt wird, geht durch den EmailSender. Das Protokoll ist die `notifications`-Tabelle selbst — `recipient_email`, `recipient_id`, `subject`, `body`, `sent_at`, `event_type` sind bereits vorhanden. Admins sehen das Protokoll ueber den bestehenden `GET /api/v1/admin/notifications` Endpoint.

---

## Frontend

### Notifications-Seite (ersetzt Platzhalter)

Pfad: `/notifications` (bereits geroutet)

Layout:
- Titel "Benachrichtigungen" + "Alle als gelesen markieren"-Button (rechts)
- Filter-Tabs: Alle | Ungelesen
- Liste der Notifications, neueste zuerst
- Ungelesene: fetter Text + blauer Punkt links
- Gelesene: normaler Text, grauer Punkt
- Klick auf Notification markiert als gelesen
- Event-Type als farbiger Badge (Order=blau, Approval=gelb, System=grau)
- Leer-State: "Keine Benachrichtigungen vorhanden"

### Sidebar-Badge

Kleiner roter Badge (Kreis mit Zahl) am Notifications-Menuepunkt in der Sidebar.
- Zeigt Anzahl ungelesener Notifications
- Verschwindet bei 0
- Polling: `useQuery` mit `refetchInterval: 60_000` auf `/api/v1/notifications/unread-count`
- Badge auch im collapsed-Modus sichtbar (am Icon)

### E-Mail-Protokoll (Admin)

Die bestehende Admin-Notifications-Seite (falls vorhanden) oder der bestehende Admin-Endpoint liefert bereits alle Felder fuer das Protokoll. Keine neue Admin-UI noetig — die Daten sind via `GET /api/v1/admin/notifications` abrufbar mit: Datum, Empfaenger (E-Mail + User-ID), Betreff, Body, Status, Event-Type.

---

## Betroffene Dateien

### Backend — Aendern
- `app/data/db/models/notification.py` — `read_at` Feld
- `app/services/notification_service.py` — `mark_read`, `mark_all_read`, `unread_count`, `create_event_notification`
- `app/api/v1/notifications.py` — 3 neue Endpoints + `read_at` in Serialisierung
- `app/services/order_service.py` — Notification-Trigger bei submit_order
- `app/services/approval_service.py` — Notification-Trigger bei approve/reject/create_approval_request

### Backend — Neu
- `app/data/clients/email_sender.py` — EmailSender Interface + StubEmailSender
- Alembic Migration fuer `read_at` Spalte

### Frontend — Aendern
- `frontend/src/pages/Notifications.tsx` — Komplett ueberarbeiten
- `frontend/src/components/Layout/Sidebar.tsx` — Badge am Notifications-Icon

### Frontend — Neu
- `frontend/src/api/notifications.ts` — API-Client (list, markRead, markAllRead, unreadCount)
- `frontend/src/hooks/useNotifications.ts` — Hooks (useNotifications, useUnreadCount, useMarkRead, useMarkAllRead)

### Tests
- `tests/integration/test_notification_read_api.py` — read, read-all, unread-count Endpoints
- `tests/unit/test_notification_events.py` — create_event_notification fuer alle Event-Types
- `frontend/tests/pages/Notifications.test.tsx` — Ueberarbeiten
- `frontend/tests/components/Layout/Sidebar.test.tsx` — Badge-Test hinzufuegen

---

## Abgrenzung

- Kein echter E-Mail-Versand (nur Stub + Log-Protokoll)
- Keine Push-Notifications (Browser)
- Keine Notification-Preferences pro User
- Keine SSE/WebSocket (Polling alle 60s reicht)
- Keine Admin-UI fuer System-Maintenance Notifications (manuell via API)
- Keine Notification-Templates (Subject/Body werden inline generiert)
