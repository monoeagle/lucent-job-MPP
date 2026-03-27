# Subscriptions System — Design Spec

**Ziel:** Subscriptions als laufende Services mit vollem Lifecycle (bestellen, aendern, kuendigen). Jedes OrderItem wird bei Submit zur Subscription. Gruppen werden zu GroupSubscriptions. Alle Aktionen des Requesters erfordern Approval.

---

## Konzept

Eine Subscription repraesentiert einen bestellten Service ueber seinen gesamten Lebenszyklus. Sie entsteht bei Order-Submit. Jedes OrderItem wird zu einer Subscription. OrderItemGroups werden zu GroupSubscriptions die Bulk-Aktionen ermoeglichen.

Hierarchie:
```
GroupSubscription (optional, fuer Cluster)
├── Subscription (Web-VM 1) — active
├── Subscription (Web-VM 2) — active
├── Subscription (Web-VM 3) — cancelled  ← einzeln gekuendigt
└── Subscription (DB)       — active
```

Einzel-Items ohne Gruppe → Subscription ohne GroupSubscription.

---

## Datenmodell

### SubscriptionModel (neue Tabelle `subscriptions`)

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | String(36), PK | UUID |
| order_item_id | String(36), FK, unique | Referenz auf OrderItem |
| group_subscription_id | String(36), FK, nullable | Referenz auf GroupSubscription |
| requester_id | String(100) | Besteller |
| status | String(30) | Lifecycle-Status |
| display_name | String(200) | Von OrderItem uebernommen |
| template_slug | String(64) | Service-Template |
| template_version | String(20) | Template-Version |
| parameters | JSONB | Aktuelle Konfiguration (aenderbar bei Change) |
| monthly_cost_eur | Decimal, nullable | Geschaetzte Monatskosten |
| activated_at | DateTime, nullable | Zeitpunkt der Aktivierung |
| cancelled_at | DateTime, nullable | Zeitpunkt der Kuendigung |
| created_at | DateTime | Erstellungszeitpunkt |
| updated_at | DateTime | Letztes Update |

### GroupSubscriptionModel (neue Tabelle `group_subscriptions`)

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | String(36), PK | UUID |
| order_item_group_id | String(36), FK, nullable | Referenz auf OrderItemGroup |
| name | String(100) | Gruppenname |
| requester_id | String(100) | Besteller |
| created_at | DateTime | Erstellungszeitpunkt |
| updated_at | DateTime | Letztes Update |

Status der Gruppe ist abgeleitet: active wenn mindestens 1 Subscription active, cancelled wenn alle cancelled.

---

## Status-Flow

```
ordered → pending_approval → approved → provisioning → active
                                                          │
                                              ┌───────────┤
                                              ▼           ▼
                                    change_pending    cancel_pending
                                              │           │
                                              ▼           ▼
                                    pending_approval  pending_approval
                                              │           │
                                              ▼           ▼
                                        approved      approved
                                              │           │
                                              ▼           ▼
                                    active (updated)  cancelled
```

Erlaubte Status-Werte: `ordered`, `pending_approval`, `approved`, `provisioning`, `active`, `change_pending`, `cancel_pending`, `cancelled`

---

## Aktionen und Rollen

| Aktion | Requester | Approver | Admin |
|--------|-----------|----------|-------|
| Bestellen (neue Subscription via Order) | initiiert | genehmigt | beides |
| Konfiguration aendern (Change-Request) | initiiert | genehmigt | beides |
| Kuendigen (einzeln) | initiiert | genehmigt | beides |
| Gruppe komplett kuendigen | initiiert | genehmigt | beides |
| Gruppe komplett approven | — | ja | ja |
| Status einsehen | eigene | zugewiesene | alle |

Jede Aktion des Requesters (bestellen, aendern, kuendigen) erzeugt einen Approval-Request der vom Approver genehmigt werden muss.

---

## Aenderungs-Flow (Change-Request)

1. Requester klickt "Aendern" auf einer aktiven Subscription
2. Wizard/Formular oeffnet sich mit aktuellen Parametern vorausgefuellt
3. User aendert Parameter (z.B. CPU 4 → 8)
4. Submit: Subscription-Status wechselt zu `change_pending`, neuer ApprovalRequest wird erstellt, gewuenschte Parameter als `pending_parameters` gespeichert
5. Approver genehmigt → Status `approved` → Reprovisioning → Parameter aktualisiert → Status `active`
6. Approver lehnt ab → Status zurueck auf `active` mit unveraenderten Parametern

Aenderungs-Daten werden in einer neuen JSONB-Spalte `pending_changes` am SubscriptionModel gespeichert:
```json
{
  "type": "change",
  "parameters": { "cpu_cores": 8, "ram_gb": 64 },
  "reason": "Kapazitaetserhoehung",
  "requested_at": "2026-03-27T10:00:00Z"
}
```

Nach Genehmigung werden `pending_changes` in `parameters` uebernommen und `pending_changes` auf null gesetzt.

---

## Kuendigungs-Flow

1. Requester klickt "Kuendigen" (Einzel oder Gruppe)
2. Bestaetigungsdialog mit Grund-Pflichtfeld
3. Submit: Status wechselt zu `cancel_pending`, neuer ApprovalRequest
4. Approver genehmigt → Deprovisionierung → Status `cancelled`, `cancelled_at` gesetzt
5. Approver lehnt ab → Status zurueck auf `active`

Bei Gruppen-Kuendigung: Alle Subscriptions der Gruppe werden einzeln auf `cancel_pending` gesetzt, ein einzelner ApprovalRequest fuer die ganze Gruppe.

---

## Subscription-Erstellung (Trigger)

Bei Order-Submit (nach erfolgreichem Approval bzw. direkt wenn kein Approval noetig):

1. Fuer jede OrderItemGroup → GroupSubscription erstellen
2. Fuer jedes OrderItem → Subscription erstellen
   - Wenn Item in einer Gruppe → `group_subscription_id` setzen
   - `parameters` von OrderItem uebernehmen
   - `status` = `ordered` (wird durch Approval-Flow weitergeschaltet)
   - `monthly_cost_eur` aus Template uebernehmen

---

## API-Endpoints

### User-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/v1/subscriptions` | GET | Eigene Subscriptions (Filter: status, template_slug) |
| `/api/v1/subscriptions/{id}` | GET | Subscription-Detail |
| `/api/v1/subscriptions/{id}/change` | POST | Change-Request initiieren (body: parameters, reason) |
| `/api/v1/subscriptions/{id}/cancel` | POST | Cancel-Request initiieren (body: reason) |
| `/api/v1/subscriptions/groups` | GET | Eigene Gruppen-Subscriptions |
| `/api/v1/subscriptions/groups/{id}` | GET | Gruppen-Detail mit allen Subscriptions |
| `/api/v1/subscriptions/groups/{id}/cancel` | POST | Alle Items der Gruppe kuendigen (body: reason) |

### Admin-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/v1/admin/subscriptions` | GET | Alle Subscriptions (Filter: status, requester_id) |
| `/api/v1/admin/subscriptions/{id}/status` | PATCH | Status manuell aendern (Admin-Override) |

---

## Frontend

### Sidebar
`Subscriptions`-Menuepunkt wird aktiviert (aktuell disabled/grau). Route: `/subscriptions`

### Subscriptions-Seite (`/subscriptions`)
- Liste aller eigenen Subscriptions
- Filter: Status (active, cancelled, pending), Gruppen/Einzeln
- Suchfeld
- Sortierung nach Name, Status, Datum
- Gruppen-Subscriptions als aufklappbare Sektionen
- Status-Badge pro Subscription
- Schnellaktionen: Aendern, Kuendigen (nur bei active)

### Subscription-Detail (`/subscriptions/{id}`)
- Aktuelle Konfiguration (Parameter als Key-Value-Liste)
- Status mit Timeline (ordered → approved → active)
- Aktions-Buttons: "Aendern", "Kuendigen" (nur bei active, nur Requester/Admin)
- Pending Changes anzeigen falls vorhanden
- Kosten-Info
- Bei Gruppe: Liste der enthaltenen Items mit Einzel-Status

---

## Betroffene Dateien

### Backend — Neu
- `app/data/db/models/subscription.py` — SubscriptionModel + GroupSubscriptionModel
- `app/data/repositories/subscription_repository.py` — CRUD + Queries
- `app/services/subscription_service.py` — Lifecycle-Logik, Change/Cancel-Flows
- `app/api/v1/subscriptions.py` — REST-Endpoints (user + admin)
- Alembic Migration fuer subscriptions + group_subscriptions Tabellen
- `tests/integration/test_subscription_api.py`
- `tests/integration/test_subscription_lifecycle_api.py`
- `tests/unit/test_subscription_service.py`

### Backend — Aendern
- `app/data/db/models/__init__.py` — Neue Modelle registrieren
- `app/__init__.py` — Blueprint registrieren
- `app/api/v1/orders.py` — Subscription-Erstellung bei Submit-Erfolg

### Frontend — Neu
- `frontend/src/types/subscription.ts` — TypeScript-Typen
- `frontend/src/api/subscriptions.ts` — API-Client
- `frontend/src/hooks/useSubscriptions.ts` — Query-Hooks
- `frontend/src/pages/Subscriptions.tsx` — Uebersichtsseite
- `frontend/src/pages/SubscriptionDetail.tsx` — Detailseite
- `frontend/src/components/subscriptions/SubscriptionCard.tsx` — Listeneintrag
- `frontend/src/components/subscriptions/SubscriptionGroupSection.tsx` — Gruppen-Container
- `frontend/tests/pages/Subscriptions.test.tsx`
- `frontend/tests/pages/SubscriptionDetail.test.tsx`

### Frontend — Aendern
- `frontend/src/components/Layout/Sidebar.tsx` — Subscriptions aktivieren
- `frontend/src/App.tsx` — Neue Routes

---

## Abgrenzung

- Kein Abrechnungs-/Billing-System
- Kein SLA-Tracking
- Kein Kontingent-Management
- Keine automatische Kuendigung nach Ablauf
- Reprovisioning bei Aenderung ist Stub (wie bestehender GitLab-Mock)
- Superadmin + Debug-Ansichten kommen spaeter
- Keine Notification-Integration in diesem Schritt (kann spaeter einfach hinzugefuegt werden)
