# My Services + My Requests + Review Requests — Design Spec

**Ziel:** Resources und Subscriptions zu "My Services" zusammenfuehren, Orders und eigene Approvals zu "My Requests" kombinieren, Review Requests um Details und Bulk-Aktionen erweitern. Rein Frontend, kein Backend noetig.

---

## 1. My Services (Resources + Subscriptions zusammengefuehrt)

Die aktuelle Resources-Seite und Subscriptions-Seite werden zu einer einheitlichen Seite zusammengefuehrt.

**Route:** `/my-services` (bestehend). `/subscriptions` wird Redirect auf `/my-services?tab=subscriptions`.

**Layout:**
- Titel "My Services"
- Tabs: "Aktive Services" | "Subscriptions" | "Alle"
- "Aktive Services" zeigt Resources (provisionierte Items) aus bestehender Resources-API
- "Subscriptions" zeigt Subscription-Lifecycle aus Subscriptions-API
- "Alle" zeigt beides zusammen
- Suchfeld ueber der Liste (filtert nach display_name)
- Status-Filter-Chips (active, ordered, pending, cancelled)

**Sidebar:** "My Services" bleibt. "Subscriptions" Menuepunkt wird entfernt (integriert als Tab).

**Bestehende Endpoints die genutzt werden:**
- `GET /api/v1/resources` (fuer Resources-Tab)
- `GET /api/v1/subscriptions` (fuer Subscriptions-Tab)

---

## 2. My Requests (Orders + Approvals kombiniert)

Neue Seite die eigene Bestellungen und eigene Genehmigungsentscheidungen kombiniert.

**Route:** `/my-requests` (neu). `/orders` wird Redirect auf `/my-requests?tab=orders`.

**Layout:**
- Titel "My Requests"
- Tabs: "Meine Bestellungen" | "Meine Genehmigungen"
- "Meine Bestellungen" zeigt OrderList (bestehende Logik)
- "Meine Genehmigungen" zeigt Approvals wo der aktuelle User als decided_by eingetragen ist (approved/rejected Eintraege)
- Jeder Tab hat eigene Status-Filter

**Sidebar:** "Meine Bestellungen" Label wird zu "My Requests", Route aendert sich auf `/my-requests`.

**Bestehende Endpoints:**
- `GET /api/v1/orders` (fuer Orders-Tab)
- `GET /api/v1/approvals` (fuer Approvals-Tab — zeigt decided-by-me)

---

## 3. Review Requests verbessern

Die bestehende Approvals-Seite wird um Details und Bulk-Aktionen erweitert.

**Route:** `/reviews` (bestehend, unveraendert)

### Mehr Details

Jeder Approval-Eintrag zeigt:
- Order-Titel (nicht nur Order-ID)
- Template-Namen der bestellten Items
- Geschaetzte Kosten (Summe)
- Requester-Name
- Aufklappbarer Detail-Bereich mit vollstaendiger Parameter-Uebersicht
- Deadline mit Farbindikator (gelb wenn < 24h, rot wenn ueberschritten)

### Filter

Status-Tabs: Pending | Approved | Rejected | Alle

### Bulk-Aktionen

- Checkbox pro Approval-Eintrag (nur bei pending sichtbar)
- "Alle auswaehlen" Checkbox im Header
- "Ausgewaehlte genehmigen" Button (gruen, disabled wenn nichts ausgewaehlt)
- "Ausgewaehlte ablehnen" Button (rot, disabled wenn nichts ausgewaehlt, oeffnet Grund-Dialog)
- Nach Bulk-Aktion: Liste wird aktualisiert, Erfolgsmeldung

**Bestehende Endpoints:**
- `GET /api/v1/approvals/pending` (Liste)
- `POST /api/v1/approvals/{id}/approve`
- `POST /api/v1/approvals/{id}/reject`
- Bulk-Aktionen: Frontend ruft Einzel-Endpoints in Schleife auf (kein neuer Backend-Endpoint)

---

## Betroffene Dateien

### Frontend — Neu
- `frontend/src/pages/MyServices.tsx` — Kombinierte Seite mit Tabs (Resources + Subscriptions)
- `frontend/src/pages/MyRequests.tsx` — Kombinierte Seite mit Tabs (Orders + Approvals)
- `frontend/tests/pages/MyServices.test.tsx`
- `frontend/tests/pages/MyRequests.test.tsx`

### Frontend — Aendern
- `frontend/src/pages/Approvals.tsx` — Details + Bulk-Aktionen
- `frontend/src/components/Layout/Sidebar.tsx` — Labels: "My Services" bleibt, "Subscriptions" entfernen, "Meine Bestellungen" → "My Requests"
- `frontend/src/App.tsx` — Neue Routes + Redirects (/subscriptions → /my-services, /orders → /my-requests)
- `frontend/tests/pages/Approvals.test.tsx` — Erweitern

### Frontend — Entfernen (optional)
- `frontend/src/pages/Resources.tsx` — Wird durch MyServices ersetzt (oder als Subkomponente wiederverwendet)
- `frontend/src/pages/Subscriptions.tsx` — Wird in MyServices integriert

### Backend
- Keine Aenderungen

---

## Abgrenzung

- Keine neuen Backend-Endpoints
- Keine neuen DB-Tabellen
- Kein echter Bulk-Approve-Endpoint (Frontend ruft Einzel-Endpoints)
- Keine Subscription-Aenderungen innerhalb MyServices (Link zu SubscriptionDetail)
- Keine Echtzeit-Updates
