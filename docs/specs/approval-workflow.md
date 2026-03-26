# Feature-Gruppe 8: Approval-Workflow

> **Status:** Draft v1.0
> **Erstellt:** 2026-03-26
> **Umfang:** 3 Features, Requirements REQ-01–REQ-52, Validation Rules VAL-01–VAL-30, API Endpoints 1–17, Edge Cases EC-01–EC-36
> **Abhängigkeiten:** Feature-Gruppe 1 (identity-access.md), Feature-Gruppe 3 (order-lifecycle.md), Feature-Gruppe 6 (resources-notifications-admin.md)

---

## Produktentscheidung: Positionierung des Approval-Schritts

### Betrachtete Modelle

**Modell A — Bedingter Zweig nach `submitted`:**
```
draft → validated → submitted ──[Approval nötig]──▶ pending_approval → approved → provisioning → done | failed
                                                  └──[kein Approval]──▶ provisioning → done | failed
```

**Modell B — Zwingender Durchlauf durch `pending_approval`:**
```
draft → validated → submitted → pending_approval → approved → provisioning → done | failed
```

### Entscheidung: Modell A

**Begründung:**

Modell A ist die korrekte Wahl aus folgenden Gründen:

1. **Konsistenz mit dem bestehenden Flow:** REQ-154 und REQ-155 in order-lifecycle.md definieren, dass nach `submitted` intern der Provisioning-Trigger ausgelöst wird und die Order bei erster `job_id` zu `provisioning` wechselt. Modell B würde diesen Flow für alle Orders — auch die, die keinen Approval benötigen — mit einem künstlichen Zwischenstatus versehen und bestehende Implementierungen in Feature 4.1 zwingen, auf `approved` statt auf `submitted` zu reagieren.

2. **Separation of Concerns:** Der Submit-Akt (Requester gibt seine Bestellung frei) ist konzeptuell getrennt von der Approval-Entscheidung (Approver gibt die Provisionierung frei). Modell A macht diesen Unterschied explizit — `submitted` bedeutet "Requester hat abgesendet", `pending_approval` bedeutet "wartet auf Freigabe". Modell B vermischt die Semantik.

3. **Weniger Breaking Changes:** Modell A ist eine Erweiterung des bestehenden Flows — der direkte Pfad `submitted → provisioning` bleibt für Bestellungen ohne Approval-Pflicht unverändert. Feature 4.1 muss nur lernen, bei `approved` statt bei `submitted` den Dispatch auszulösen — und nur für Orders, die durch `pending_approval` gelaufen sind.

4. **Bessere Audit-Transparenz:** Orders ohne Approval-Pflicht erreichen `provisioning` direkt, was im Audit-Log klar erkennbar ist. Wäre immer ein `approved`-Status vorhanden, müsste man unterscheiden, ob ein Mensch oder das System "genehmigt" hat.

### Erweiterter Statusfluss

```
draft → validated → submitted ──[approval_required = false]──▶ provisioning → done | failed
                                └──[approval_required = true]──▶ pending_approval ──[genehmigt]──▶ approved → provisioning → done | failed
                                                                                   └──[abgelehnt]──▶ rejected
                                                                                   └──[Timeout]────▶ rejected
```

**Vollständige OrderStatus-Erweiterung:**
```
draft           — Order wird aufgebaut
validated       — Alle Items valide
submitted       — Requester hat abgesendet, Approval-Prüfung läuft
pending_approval — Wartet auf Approver-Entscheidung
approved        — Genehmigt, Provisioning-Trigger wird ausgelöst
rejected        — Abgelehnt (durch Approver oder Timeout)
provisioning    — Provisioning-Job läuft
done            — Alle Items erfolgreich provisioniert
failed          — Provisioning fehlgeschlagen
```

---

## Notwendige Nacharbeiten in order-lifecycle.md

Die folgenden Änderungen an `order-lifecycle.md` sind als Folge dieser Spec erforderlich. Sie werden in order-lifecycle.md als Änderungsanforderung markiert und müssen synchron mit der Implementierung dieser Spec umgesetzt werden.

### 1. OrderStatus-Enum (Datenmodell-Sektion)

Die Enum-Definition muss um folgende Werte erweitert werden:
```
pending_approval — Wartet auf Approver-Entscheidung (nach submitted, wenn Approval-Regel greift)
approved         — Von Approver freigegeben, Provisioning-Trigger ausstehend
rejected         — Abgelehnt durch Approver oder automatisch nach Timeout
```

### 2. REQ-154 (Provisioning-Trigger)

REQ-154 definiert aktuell: "Das System löst nach dem Submit intern den Provisioning-Trigger aus."

Neue Formulierung: "Das System prüft nach erfolgreichem Submit, ob für die Order Approval-Pflicht besteht (Feature 8.1). Besteht keine Approval-Pflicht, löst das System den Provisioning-Trigger unmittelbar aus und die Order wechselt zu `provisioning` (wie bisher). Besteht Approval-Pflicht, wechselt die Order zu `pending_approval`. Der Provisioning-Trigger wird erst nach dem Übergang zu `approved` ausgelöst."

### 3. REQ-157 (Statusübergänge)

REQ-157 definiert die erlaubten Übergänge. Die Statusmaschine muss um folgende Übergänge erweitert werden:
- `submitted → pending_approval` (wenn Approval-Regel greift)
- `pending_approval → approved` (durch Approver)
- `pending_approval → rejected` (durch Approver oder Timeout)
- `approved → provisioning` (Provisioning-Trigger nach Approval)
- `rejected` ist Terminalzustand (kein Rückwärtsübergang)

### 4. Endpoint 46, 47, 56 (Status-Felder)

Alle Endpoints, die `status` zurückgeben oder nach `status` filtern, müssen die neuen Enum-Werte `pending_approval`, `approved` und `rejected` unterstützen.

### 5. Endpoint 57 (SSE-Events)

Das SSE-Event `order_status_changed` muss die neuen Status-Werte in `old_status`/`new_status` transportieren können. Zusätzlich wird ein neues Event-Typ `approval_decision` benötigt:
```
event: approval_decision
data: { "order_id": "uuid", "decision": "approved | rejected", "decided_by": "uuid | null",
        "reason": "string | null", "timestamp": "ISO-8601" }
```

### 6. Statusmaschinen-Übersicht

Die Diagramme und Transitions-Tabelle in der Statusmaschinen-Übersicht müssen die neuen Zustände und Übergänge enthalten.

---

## Logisches Datenmodell (Ergänzung)

Das folgende Datenmodell ergänzt das Order-Datenmodell aus order-lifecycle.md.

### ApprovalRule

```
ApprovalRule {
  id:                    string (UUID)
  name:                  string                   // Beschreibender Name der Regel
  rule_type:             ApprovalRuleType (Enum)  // cost_threshold | service_type | always
  threshold_eur:         decimal (optional)        // Nur bei rule_type = cost_threshold
  service_type_slug:     string (optional)         // Nur bei rule_type = service_type; Template-Slug-Präfix oder exakter Slug
  is_active:             boolean
  created_by:            string (UUID)             // Admin-ID
  created_at:            ISO-8601 datetime
  updated_at:            ISO-8601 datetime
}
```

### ApprovalRuleType (Enum)

```
cost_threshold  — Greift wenn geschätzte Gesamtkosten der Order > threshold_eur
service_type    — Greift wenn mindestens ein OrderItem den angegebenen Template-Slug (oder Slug-Präfix) referenziert
always          — Greift immer, unabhängig von Inhalt oder Kosten
```

### ApprovalRequest

```
ApprovalRequest {
  id:                    string (UUID)
  order_id:              string (UUID)             // Referenz auf die Order
  status:                ApprovalRequestStatus     // pending | approved | rejected | expired
  approval_rule_ids:     string[]                  // IDs der Regeln, die den Approval ausgelöst haben
  requested_at:          ISO-8601 datetime         // Zeitpunkt der automatischen Erstellung
  deadline_at:           ISO-8601 datetime         // Zeitpunkt des automatischen Ablaufs
  decided_by:            string (UUID, optional)   // User-ID des Approvers (null bei Timeout-Ablehnung)
  decided_at:            ISO-8601 datetime (optional)
  decision_reason:       string (optional)         // Begründung bei Ablehnung; optional bei Genehmigung
  extended_by:           string (UUID, optional)   // Admin-ID, der die Frist verlängert hat
  extended_at:           ISO-8601 datetime (optional)
  original_deadline_at:  ISO-8601 datetime (optional) // Ursprüngliche Frist vor Verlängerung
}
```

### ApprovalRequestStatus (Enum)

```
pending   — Wartet auf Entscheidung
approved  — Genehmigt durch Approver
rejected  — Abgelehnt durch Approver oder automatisch nach Timeout
expired   — Interner Übergangsstatus (wird sofort zu rejected; nicht extern sichtbar)
```

---

## Feature 8.1: Approval-Regeln & Schwellwerte

### User Story

Als Admin möchte ich konfigurieren, unter welchen Bedingungen eine Bestellung vor der Provisionierung manuell genehmigt werden muss, damit kostenintensive oder risikoreiche Services nicht automatisch ohne Kontrolle bereitgestellt werden.

---

### Requirements

- **REQ-01:** Ein Admin kann Approval-Regeln erstellen, bearbeiten, deaktivieren und löschen. Nur Benutzer mit der Rolle `admin` haben Schreibzugriff auf Approval-Regeln.
- **REQ-02:** Das System unterstützt drei Regeltypen: `cost_threshold` (Kosten-Schwellwert), `service_type` (Service-Typ-basiert) und `always` (immer Approval).
- **REQ-03:** Eine `cost_threshold`-Regel wird ausgelöst, wenn die geschätzte Gesamtkosten der Order den konfigurierten Schwellwert in EUR überschreiten. Die Kostenschätzung basiert auf den Kostenangaben in den ServiceTemplates (Feld `estimated_cost_eur_per_month` — siehe Nacharbeiten-Hinweis am Ende dieser Sektion).
- **REQ-04:** Eine `service_type`-Regel wird ausgelöst, wenn mindestens ein OrderItem einen Template-Slug referenziert, der exakt dem `service_type_slug`-Wert der Regel entspricht oder mit dem `service_type_slug`-Wert als Präfix beginnt (Präfix-Matching mit Trennzeichen `/`). Beispiel: Regel mit `service_type_slug = "vm"` trifft auf `"vm"`, `"vm/linux"`, `"vm/windows"`, aber nicht auf `"vmware"`.
- **REQ-05:** Eine `always`-Regel löst bei jeder Order Approval aus, unabhängig von Inhalt oder Kosten.
- **REQ-06:** Es können mehrere aktive Approval-Regeln gleichzeitig existieren. Das System wertet alle aktiven Regeln aus. Greift mindestens eine Regel, ist Approval-Pflicht für die Order gegeben.
- **REQ-07:** Approval-Regeln werden beim Submit einer Order ausgewertet (Zeitpunkt: unmittelbar nach dem Statusübergang `validated → submitted`). Die Auswertung ist synchron — das Ergebnis bestimmt, ob die Order zu `pending_approval` oder direkt zu `provisioning` übergeht.
- **REQ-08:** Wenn keine aktive Approval-Regel auf eine Order zutrifft, wechselt die Order direkt von `submitted` zu `provisioning` (bestehender Pfad gemäß order-lifecycle.md REQ-154, nach Anpassung).
- **REQ-09:** Wenn mindestens eine aktive Approval-Regel zutrifft, erstellt das System automatisch einen `ApprovalRequest`-Record mit Status `pending` und setzt die Order auf `pending_approval`. Der `ApprovalRequest` speichert die IDs aller zutreffenden Regeln in `approval_rule_ids`.
- **REQ-10:** Die Standard-Deadline für einen `ApprovalRequest` ist 48 Stunden ab dem Zeitpunkt der Erstellung (`requested_at + 48h`). Diese Frist ist systemweit konfigurierbar (Admin-Einstellung, Default: 48h, Minimum: 1h, Maximum: 720h / 30 Tage).
- **REQ-11:** Eine deaktivierte Approval-Regel (`is_active = false`) wird bei der Auswertung nicht berücksichtigt. Bestehende `ApprovalRequests`, die durch die nun deaktivierte Regel ausgelöst wurden, bleiben unberührt und werden weiter bearbeitet.
- **REQ-12:** Das Löschen einer Approval-Regel ist nur möglich, wenn keine `ApprovalRequests` mit Status `pending` auf diese Regel referenzieren. Andernfalls gibt das System HTTP 409 zurück. Deaktivieren ist immer möglich.
- **REQ-13:** Änderungen an Approval-Regeln (inkl. Schwellwertänderungen) wirken ausschließlich auf zukünftige Submits. Bereits laufende `ApprovalRequests` (Status `pending`) werden durch Regeländerungen nicht beeinflusst.
- **REQ-14:** Das ServiceTemplate-Modell (Feature 2.1) wird um ein optionales Feld `approval_always_required: boolean (default: false)` erweitert. Ist dieses Flag für mindestens ein OrderItem-Template auf `true` gesetzt, löst das System unabhängig von konfigurierten Regeln einen `ApprovalRequest` aus. Dieses Flag wirkt wie eine implizite `always`-Regel auf Template-Ebene.
- **REQ-15:** Ein Admin kann alle konfigurierten Approval-Regeln auflisten (aktive und inaktive). Ein Requester oder Approver kann keine Approval-Regeln lesen (HTTP 403).
- **REQ-16:** Jede Erstellung, Änderung, Aktivierung und Deaktivierung einer Approval-Regel wird im Audit-Log erfasst (Feature 7.2: actor_id, action, entity_type = "approval_rule", entity_id, timestamp, changed_fields).

---

### Validation Rules

- **VAL-01:** `name` bei Regelanlage — Pflichtfeld, 3–100 Zeichen, eindeutig systemweit (case-insensitiv) — `"Der Regelname ist ein Pflichtfeld (3–100 Zeichen) und muss eindeutig sein."`
- **VAL-02:** `rule_type` — Pflichtfeld, muss ein gültiger Enum-Wert sein (`cost_threshold`, `service_type`, `always`) — `"Ungültiger Regeltyp. Erlaubte Werte: cost_threshold, service_type, always."`
- **VAL-03:** `threshold_eur` bei `rule_type = cost_threshold` — Pflichtfeld, positiver Dezimalwert > 0, max. 2 Dezimalstellen, max. 9.999.999,99 — `"Der Kostenschwellwert muss ein positiver Betrag in EUR sein (max. 9.999.999,99)."`
- **VAL-04:** `threshold_eur` bei `rule_type != cost_threshold` — Feld muss leer/null sein — `"Der Kostenschwellwert ist nur für Regeltyp 'cost_threshold' zulässig."`
- **VAL-05:** `service_type_slug` bei `rule_type = service_type` — Pflichtfeld, muss ein gültiger Slug-Wert sein (Kleinbuchstaben, Ziffern, Bindestriche, Schrägstriche; kein führender/abschließender Schrägstrich) — `"Der Service-Typ-Slug ist für Regeltyp 'service_type' erforderlich und muss ein gültiges Slug-Format haben."`
- **VAL-06:** `service_type_slug` bei `rule_type != service_type` — Feld muss leer/null sein — `"Der Service-Typ-Slug ist nur für Regeltyp 'service_type' zulässig."`
- **VAL-07:** Regeltyp `always` — Darf keine `threshold_eur`- oder `service_type_slug`-Felder enthalten — `"Regeln vom Typ 'always' haben keine weiteren Konfigurationsfelder."`
- **VAL-08:** Löschen einer Regel mit offenen `ApprovalRequests` — Nur wenn keine `pending`-ApprovalRequests auf die Regel referenzieren — `"Die Regel kann nicht gelöscht werden, da noch offene Genehmigungsanfragen existieren. Bitte deaktivieren Sie die Regel stattdessen."`

---

### API Contract

**Endpoint 1: List approval rules**
```
GET /api/v1/approval-rules
```
Query Params:
- `is_active` (optional, boolean — filtert nach aktiven/inaktiven Regeln)
- `rule_type` (optional, Enum: cost_threshold | service_type | always)
- `limit` (optional, integer, default 50, max 200)
- `offset` (optional, integer, default 0)

Response 200:
```json
{
  "total": 5,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "rule_type": "cost_threshold | service_type | always",
      "threshold_eur": 500.00,
      "service_type_slug": null,
      "is_active": true,
      "created_by": "uuid",
      "created_at": "ISO-8601 datetime",
      "updated_at": "ISO-8601 datetime"
    }
  ]
}
```
Response 401: Unauthorized
Response 403: Forbidden — nur Admins

---

**Endpoint 2: Create approval rule**
```
POST /api/v1/approval-rules
```
Request Body:
```json
{
  "name": "string (required, 3–100 chars)",
  "rule_type": "cost_threshold | service_type | always",
  "threshold_eur": "decimal (required if rule_type = cost_threshold, else omit)",
  "service_type_slug": "string (required if rule_type = service_type, else omit)",
  "is_active": "boolean (optional, default: true)"
}
```
Response 201:
```json
{
  "id": "uuid",
  "name": "string",
  "rule_type": "string",
  "threshold_eur": "decimal | null",
  "service_type_slug": "string | null",
  "is_active": true,
  "created_by": "uuid",
  "created_at": "ISO-8601 datetime",
  "updated_at": "ISO-8601 datetime"
}
```
Response 400: Validation error (VAL-01 bis VAL-07)
Response 401: Unauthorized
Response 403: Forbidden — nur Admins
Response 409: Name bereits vorhanden (VAL-01)

---

**Endpoint 3: Update approval rule**
```
PATCH /api/v1/approval-rules/{rule_id}
```
Request Body (alle Felder optional, nur geänderte Felder übermitteln):
```json
{
  "name": "string (3–100 chars)",
  "threshold_eur": "decimal | null",
  "service_type_slug": "string | null",
  "is_active": "boolean"
}
```
Hinweis: `rule_type` kann nach Erstellung nicht geändert werden.

Response 200: Vollständige ApprovalRule-Repräsentation (wie Endpoint 2 Response 201)
Response 400: Validation error
Response 401: Unauthorized
Response 403: Forbidden — nur Admins
Response 404: Regel nicht gefunden
Response 409: Name bereits vorhanden oder `rule_type`-Änderung versucht

---

**Endpoint 4: Delete approval rule**
```
DELETE /api/v1/approval-rules/{rule_id}
```
Response 204: No Content
Response 401: Unauthorized
Response 403: Forbidden — nur Admins
Response 404: Regel nicht gefunden
Response 409: Offene ApprovalRequests referenzieren diese Regel (VAL-08)

---

**Endpoint 5: Evaluate approval rules for an order (dry run)**
```
POST /api/v1/approval-rules/evaluate
```
Beschreibung: Gibt zurück, welche Regeln für eine gegebene Order greifen würden. Dient der Voransicht im Frontend (kein Statusübergang, keine Seiteneffekte). Nur für Admins und Approver.

Request Body:
```json
{
  "order_id": "uuid (required)"
}
```
Response 200:
```json
{
  "order_id": "uuid",
  "approval_required": true,
  "matched_rules": [
    {
      "rule_id": "uuid",
      "rule_name": "string",
      "rule_type": "string",
      "match_reason": "string"
    }
  ]
}
```
Response 400: `order_id` fehlt oder ungültig
Response 401: Unauthorized
Response 403: Forbidden — nur Admins und Approver
Response 404: Order nicht gefunden

---

### Edge Cases

- **EC-01:** Admin ändert einen Kosten-Schwellwert von 500 EUR auf 1.000 EUR, während eine Order mit Kosten von 600 EUR im Status `pending_approval` ist → Die Änderung wirkt nicht auf laufende ApprovalRequests (REQ-13). Der bestehende ApprovalRequest bleibt `pending` und muss wie vorgesehen entschieden werden.
- **EC-02:** Admin deaktiviert die einzige aktive Approval-Regel, während 10 Orders im Status `pending_approval` sind → Die laufenden ApprovalRequests bleiben unverührt (`pending`). Neue Orders ab diesem Zeitpunkt benötigen keinen Approval mehr. Die 10 Orders müssen manuell entschieden werden.
- **EC-03:** Zwei Admins erstellen gleichzeitig eine Approval-Regel mit demselben Namen → Das System verwendet einen Unique-Constraint auf `name` (case-insensitiv). Einer der Requests erhält HTTP 409.
- **EC-04:** Eine Order enthält ein OrderItem mit `approval_always_required = true` im Template-Snapshot und keine aktive Approval-Regel greift → Das Template-Flag wirkt als implizite Regel (REQ-14). Die Order wechselt zu `pending_approval`. Im `ApprovalRequest` ist `approval_rule_ids` leer; stattdessen wird ein Feld `triggered_by_template_flags: ["template_slug/version"]` gesetzt.
- **EC-05:** Kostenberechnung für `cost_threshold`-Regel: Ein OrderItem referenziert ein Template, das kein `estimated_cost_eur_per_month` enthält (Feld fehlt oder ist null) → Dieses Item trägt 0 EUR zur Gesamtkosten-Summe bei. Die Regel greift nur, wenn die Summe der Items mit bekannten Kosten den Schwellwert überschreitet.
- **EC-06:** Admin versucht, eine `always`-Regel zu löschen, aber es gibt 3 offene ApprovalRequests, von denen 2 noch zusätzlich durch andere Regeln ausgelöst wurden → Die Löschung ist dennoch nicht möglich, solange irgendein `pending`-ApprovalRequest die zu löschende Regel in `approval_rule_ids` enthält (VAL-08).

---

### Nacharbeiten-Hinweis: ServiceTemplate-Erweiterung

Feature 8.1 setzt voraus, dass `ServiceTemplate` (Feature 2.1, service-catalog.md) um folgende Felder erweitert wird:

- `estimated_cost_eur_per_month: decimal (optional)` — geschätzte monatliche Kosten für Kosten-Schwellwert-Regeln
- `approval_always_required: boolean (default: false)` — erzwingt Approval unabhängig von Regeln

Diese Felder müssen in service-catalog.md ergänzt werden (REQ-Nummern nach aktuellem Stand der Gruppe 2 fortlaufend vergeben).

---

## Feature 8.2: Approval-Workflow (1-stufig)

### User Story

Als Approver möchte ich eine Liste aller ausstehenden Genehmigungsanfragen sehen und für jede Anfrage die Details der zugrundeliegenden Bestellung einsehen, genehmigen oder ablehnen können, damit die Provisionierung freigegebener Bestellungen starten kann und ungeeignete Bestellungen zurückgewiesen werden.

---

### Requirements

- **REQ-17:** Ein Approver kann alle `ApprovalRequests` mit Status `pending` system weit einsehen. Ein Requester kann den `ApprovalRequest` nur für seine eigenen Orders einsehen (kein Zugriff auf fremde Approval-Requests). Ein Admin kann alle `ApprovalRequests` lesen.
- **REQ-18:** Der Approver sieht je ApprovalRequest: Order-Details (order_number, title, business_reason, item_count, requester_id, requested_at, deadline_at), die ausgelösten Regeln, und die geschätzten Gesamtkosten der Order.
- **REQ-19:** Ein Approver kann einen `ApprovalRequest` genehmigen (`decision: approved`). Eine optionale Begründung kann im Feld `decision_reason` hinterlegt werden. Das System setzt `ApprovalRequest.status = approved`, `decided_by = approver_id`, `decided_at = now()`.
- **REQ-20:** Bei Genehmigung wechselt die Order atomar von `pending_approval` zu `approved`. Unmittelbar danach (innerhalb derselben Systemoperation) wechselt die Order von `approved` zu `provisioning`, indem der Provisioning-Trigger ausgelöst wird (Feature 4.1, identisch zu REQ-154 in order-lifecycle.md). Der Status `approved` ist ein kurzlebiger Durchgangsstatus, der im Audit-Log erfasst wird.
- **REQ-21:** Ein Approver kann einen `ApprovalRequest` ablehnen (`decision: rejected`). Die Begründung im Feld `decision_reason` ist bei Ablehnung Pflicht. Das System setzt `ApprovalRequest.status = rejected`, `decided_by = approver_id`, `decided_at = now()`.
- **REQ-22:** Bei Ablehnung wechselt die Order atomar von `pending_approval` zu `rejected`. `rejected` ist ein Terminalzustand — die Order kann nicht mehr verändert oder erneut submitted werden.
- **REQ-23:** Self-Approval-Prävention: Ist die Konfiguration `allow_self_approval = false` (systemweite Admin-Einstellung, Default: false), darf ein Approver eine Bestellung nicht genehmigen oder ablehnen, wenn er selbst der `requester_id` der Order entspricht. In diesem Fall gibt das System HTTP 403 zurück. Bei `allow_self_approval = true` ist Self-Approval erlaubt.
- **REQ-24:** Das System sendet beim Erstellen eines `ApprovalRequests` eine Benachrichtigung an alle aktiven Approver (E-Mail via Feature 6.1). Die Benachrichtigung enthält: order_number, Requester-Name, order_title, business_reason, Anzahl der Items, deadline_at und einen direkten Link zum Approval-Endpoint.
- **REQ-25:** Das System sendet bei Genehmigung oder Ablehnung eine Benachrichtigung an den Requester der Order (E-Mail via Feature 6.1). Die Benachrichtigung enthält: order_number, Entscheidung (genehmigt/abgelehnt), entschieden von (Approver-Name), decision_reason (bei Ablehnung), und ggf. Hinweis auf automatischen Start der Provisionierung.
- **REQ-26:** Ein Approver kann die vollständigen Order-Details (alle Items mit Parametern) einer `pending_approval`-Order einsehen, auch wenn er nicht der Requester ist. Dieser erweiterte Lesezugriff gilt nur für Orders im Status `pending_approval` und nur für Approver- und Admin-Rollen.
- **REQ-27:** Jede Approval-Entscheidung (Genehmigung und Ablehnung) wird im Audit-Log erfasst (Feature 7.2): actor_id (Approver), action (`approval_approved` oder `approval_rejected`), entity_type = "approval_request", entity_id, order_id, decision_reason, timestamp.
- **REQ-28:** Nur ein Approver oder Admin kann eine Entscheidung treffen. Ein Requester kann keine Genehmigungen oder Ablehnungen auslösen (HTTP 403).
- **REQ-29:** Die Approval-Entscheidung ist endgültig und unveränderlich. Es gibt kein "Rückgängigmachen" einer Entscheidung. Ein genehmigter ApprovalRequest kann nicht nachträglich abgelehnt werden und umgekehrt.
- **REQ-30:** Die Approver-Liste für Benachrichtigungen (REQ-24) umfasst alle Benutzer, denen in Active Directory die Approver-Rolle zugewiesen ist und deren Account aktiv ist. Die Liste wird zum Zeitpunkt der Notification-Erstellung dynamisch aus dem Identity-System abgerufen (Feature 1.2).

---

### Validation Rules

- **VAL-09:** Berechtigung für Approval-Entscheidung — User muss Rolle `approver` oder `admin` haben — `"Sie haben keine Berechtigung, Genehmigungsentscheidungen zu treffen."`
- **VAL-10:** ApprovalRequest-Status für Entscheidung — ApprovalRequest muss Status `pending` haben — `"Diese Genehmigungsanfrage wurde bereits entschieden oder ist abgelaufen."`
- **VAL-11:** `decision_reason` bei Ablehnung — Pflichtfeld, 10–1.000 Zeichen — `"Eine Begründung ist bei Ablehnung erforderlich (10–1.000 Zeichen)."`
- **VAL-12:** `decision_reason` bei Genehmigung — Optional, wenn angegeben max. 1.000 Zeichen — `"Die Begründung darf maximal 1.000 Zeichen enthalten."`
- **VAL-13:** Self-Approval-Schutz (wenn `allow_self_approval = false`) — `decided_by` darf nicht gleich `requester_id` der Order sein — `"Sie können keine eigene Bestellung genehmigen oder ablehnen."`
- **VAL-14:** Berechtigung zum Lesen fremder ApprovalRequests — Requester kann nur ApprovalRequests eigener Orders lesen — `"Sie haben keinen Zugriff auf diese Genehmigungsanfrage."`

---

### API Contract

**Endpoint 6: List approval requests**
```
GET /api/v1/approval-requests
```
Query Params:
- `status` (optional, Enum: pending | approved | rejected)
- `order_id` (optional, UUID — filtert auf eine spezifische Order)
- `requester_id` (optional, UUID — nur für Admins und Approver)
- `limit` (optional, integer, default 20, max 100)
- `offset` (optional, integer, default 0)

Hinweis: Requesters sehen nur ihre eigenen ApprovalRequests (serverseitige Filterung auf `requester_id = authenticated_user_id`).

Response 200:
```json
{
  "total": 12,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": "uuid",
      "order_id": "uuid",
      "order_number": "string",
      "order_title": "string",
      "requester_id": "uuid",
      "requester_name": "string",
      "status": "pending | approved | rejected",
      "approval_rule_ids": ["uuid"],
      "triggered_by_template_flags": ["template_slug/version"],
      "requested_at": "ISO-8601 datetime",
      "deadline_at": "ISO-8601 datetime",
      "decided_by": "uuid | null",
      "decided_at": "ISO-8601 datetime | null",
      "decision_reason": "string | null"
    }
  ]
}
```
Response 401: Unauthorized
Response 403: Forbidden — Requester versucht `requester_id` eines anderen Users zu setzen

---

**Endpoint 7: Get approval request by ID**
```
GET /api/v1/approval-requests/{approval_request_id}
```
Response 200:
```json
{
  "id": "uuid",
  "order_id": "uuid",
  "order_number": "string",
  "order_title": "string",
  "order_business_reason": "string",
  "order_item_count": 3,
  "estimated_total_cost_eur": 1200.00,
  "requester_id": "uuid",
  "requester_name": "string",
  "status": "pending | approved | rejected",
  "approval_rule_ids": ["uuid"],
  "matched_rules": [
    {
      "rule_id": "uuid",
      "rule_name": "string",
      "rule_type": "string",
      "match_reason": "string"
    }
  ],
  "triggered_by_template_flags": ["template_slug/version"],
  "requested_at": "ISO-8601 datetime",
  "deadline_at": "ISO-8601 datetime",
  "decided_by": "uuid | null",
  "decided_by_name": "string | null",
  "decided_at": "ISO-8601 datetime | null",
  "decision_reason": "string | null",
  "extended_by": "uuid | null",
  "extended_at": "ISO-8601 datetime | null",
  "original_deadline_at": "ISO-8601 datetime | null"
}
```
Response 401: Unauthorized
Response 403: Forbidden — Requester versucht fremden ApprovalRequest zu lesen
Response 404: ApprovalRequest nicht gefunden

---

**Endpoint 8: Approve an approval request**
```
POST /api/v1/approval-requests/{approval_request_id}/approve
```
Request Body:
```json
{
  "decision_reason": "string (optional, max 1000 chars)"
}
```
Response 200:
```json
{
  "approval_request_id": "uuid",
  "order_id": "uuid",
  "order_number": "string",
  "decision": "approved",
  "decided_by": "uuid",
  "decided_at": "ISO-8601 datetime",
  "order_status": "provisioning",
  "message": "Die Bestellung wurde genehmigt. Die Provisionierung wurde gestartet."
}
```
Response 401: Unauthorized
Response 403: Forbidden — fehlende Rolle oder Self-Approval-Schutz (VAL-09, VAL-13)
Response 404: ApprovalRequest nicht gefunden
Response 409: ApprovalRequest ist nicht mehr `pending` (VAL-10) oder Provisioning-Trigger-Fehler

---

**Endpoint 9: Reject an approval request**
```
POST /api/v1/approval-requests/{approval_request_id}/reject
```
Request Body:
```json
{
  "decision_reason": "string (required, 10–1000 chars)"
}
```
Response 200:
```json
{
  "approval_request_id": "uuid",
  "order_id": "uuid",
  "order_number": "string",
  "decision": "rejected",
  "decided_by": "uuid",
  "decided_at": "ISO-8601 datetime",
  "order_status": "rejected",
  "message": "Die Bestellung wurde abgelehnt."
}
```
Response 400: Validation error — `decision_reason` fehlt oder zu kurz (VAL-11)
Response 401: Unauthorized
Response 403: Forbidden — fehlende Rolle oder Self-Approval-Schutz (VAL-09, VAL-13)
Response 404: ApprovalRequest nicht gefunden
Response 409: ApprovalRequest ist nicht mehr `pending` (VAL-10)

---

**Endpoint 10: Get order details for approval (extended read)**
```
GET /api/v1/approval-requests/{approval_request_id}/order-details
```
Beschreibung: Gibt die vollständigen Order-Details (alle Items mit Parametern) zurück. Nur für Approver und Admins. Kein Requester-Zugriff.

Response 200: Vollständige Order-Repräsentation (wie Endpoint 46 aus order-lifecycle.md, inklusive aller Items mit Parametern)

Zusätzliches Feld im Response:
```json
{
  "approval_context": {
    "approval_request_id": "uuid",
    "status": "pending",
    "deadline_at": "ISO-8601 datetime",
    "matched_rules": [...]
  }
}
```
Response 401: Unauthorized
Response 403: Forbidden — nur Approver und Admins
Response 404: ApprovalRequest nicht gefunden

---

### Edge Cases

- **EC-07:** Zwei Approver treffen gleichzeitig eine Entscheidung für denselben ApprovalRequest (Race Condition) → Das System verwendet einen atomaren Update-Mechanismus (DB-seitiges CAS: `UPDATE WHERE status = 'pending'`). Der erste Request gewinnt, erhält HTTP 200. Der zweite Request erhält HTTP 409 (VAL-10: "Diese Genehmigungsanfrage wurde bereits entschieden.").
- **EC-08:** Approver genehmigt eine Order, aber der Provisioning-Trigger (Feature 4.1) schlägt fehl (Queue voll, Systemfehler) → Der ApprovalRequest wird als `approved` persistiert, die Order wechselt zu `approved`. Der Provisioning-Trigger-Fehler wird von Feature 4.1 (REQ-50) behandelt. Der Status verbleibt bei `approved` bis der Trigger erfolgreich war — keine Rücknahme der Approval-Entscheidung.
- **EC-09:** Active Directory ist beim Abrufen der Approver-Liste für Benachrichtigungen nicht erreichbar → Die Benachrichtigungen (REQ-24) werden in eine Retry-Queue eingestellt. Der ApprovalRequest wird dennoch korrekt erstellt und die Order wechselt zu `pending_approval`. Die Benachrichtigung wird nachgeliefert, sobald AD erreichbar ist. Kann die Approver-Liste nach erschöpften Retries nicht aufgelöst werden, wird ein Admin-Alert ausgelöst.
- **EC-10:** Es gibt keine aktiven Approver im System (alle AD-Approver-Accounts deaktiviert) → Der `ApprovalRequest` wird erstellt, die Order wechselt zu `pending_approval`. Das System erkennt beim Erstellen, dass die Benachrichtigungsempfänger-Liste leer ist, und erzeugt stattdessen einen Admin-Alert: "Kein aktiver Approver verfügbar — Order {order_number} wartet auf Genehmigung." Der ApprovalRequest bleibt offen bis ein Approver verfügbar ist oder der Admin die Frist verlängert.
- **EC-11:** Requester versucht, den ApprovalRequest seiner eigenen Order zu genehmigen (Self-Approval, `allow_self_approval = false`) → HTTP 403 mit Fehlermeldung "Sie können keine eigene Bestellung genehmigen oder ablehnen." (VAL-13). Der ApprovalRequest bleibt `pending`.
- **EC-12:** Requester versucht, den ApprovalRequest einer Order abzurufen, die nicht ihm gehört → HTTP 403 (VAL-14). Keine Information über die Existenz des fremden ApprovalRequests wird preisgegeben.
- **EC-13:** Order wechselt zu `pending_approval`, aber kurz danach wird die Order aus einem anderen Code-Pfad versucht zu stornieren (kein Cancel-Feature, aber ein direkter DB-Eingriff durch Admin) → `pending_approval` ist nach REQ-157 (ergänzt) kein editierbarer Zustand. Administrative Aktionen auf Orders in `pending_approval` sind nur über die Approval-Reject-Entscheidung möglich.
- **EC-14:** Approver entscheidet eine Anfrage, die bereits per Timeout abgelaufen ist, aber das Timeout-Job noch nicht gelaufen ist (Zeitfenster zwischen Deadline und nächstem Cron-Lauf) → Das System prüft beim Empfang der Entscheidung, ob `deadline_at` bereits überschritten ist. Ist dies der Fall, wird HTTP 409 zurückgegeben: "Die Frist für diese Genehmigungsanfrage ist abgelaufen."

---

## Feature 8.3: Automatische Ablehnung bei Timeout

### User Story

Als System möchte ich ausstehende Genehmigungsanfragen automatisch ablehnen, wenn die konfigurierte Frist abgelaufen ist, damit Orders nicht unbegrenzt im Zustand `pending_approval` verbleiben und der Requester zeitnah informiert wird.

Als Admin möchte ich die Frist einer spezifischen Genehmigungsanfrage verlängern können, damit außergewöhnliche Fälle (Urlaub, Eskalation) ohne manuellen Eingriff in die Datenbank behandelt werden können.

---

### Requirements

- **REQ-31:** Das System prüft zyklisch (Intervall: konfigurierbar, Default: 15 Minuten) alle `ApprovalRequests` mit Status `pending`, deren `deadline_at` in der Vergangenheit liegt. Diese werden automatisch abgelehnt.
- **REQ-32:** Bei automatischer Ablehnung durch Timeout setzt das System: `ApprovalRequest.status = rejected`, `decided_by = null` (System-Entscheidung), `decided_at = now()`, `decision_reason = "Automatische Ablehnung: Die Genehmigungsfrist von {X} Stunden ist abgelaufen."`. Der Text enthält die tatsächlich konfigurierte Frist in Stunden.
- **REQ-33:** Bei automatischer Ablehnung durch Timeout wechselt die Order atomar von `pending_approval` zu `rejected`. `rejected` ist Terminalzustand.
- **REQ-34:** Das System sendet bei Timeout-Ablehnung eine Benachrichtigung an den Requester der Order (E-Mail via Feature 6.1). Die Benachrichtigung enthält: order_number, Hinweis auf abgelaufene Frist, Hinweis dass eine neue Bestellung erstellt werden kann. Kein Hinweis auf interne Systemdetails.
- **REQ-35:** Das System sendet bei Timeout-Ablehnung zusätzlich eine Benachrichtigung an alle aktiven Approver (E-Mail via Feature 6.1). Die Benachrichtigung informiert, dass die Order {order_number} automatisch abgelehnt wurde, da keine Entscheidung innerhalb der Frist getroffen wurde.
- **REQ-36:** Ein Admin kann die Deadline eines `pending`-ApprovalRequests verlängern. Die neue Deadline muss in der Zukunft liegen (mindestens 1 Stunde ab jetzt). Die maximale Gesamtlaufzeit eines ApprovalRequests (Original-Deadline + alle Verlängerungen) ist auf 720 Stunden (30 Tage) ab `requested_at` begrenzt.
- **REQ-37:** Das System speichert bei einer Verlängerung: `extended_by = admin_id`, `extended_at = now()`, `original_deadline_at = bisheriger deadline_at-Wert` (nur beim ersten Verlängern), `deadline_at = neue_deadline`. Mehrfache Verlängerungen durch denselben oder verschiedene Admins sind möglich (bis zur 720h-Grenze).
- **REQ-38:** Das System sendet beim Verlängern der Frist eine Benachrichtigung an den Requester: order_number, neue Deadline, Hinweis dass ein Approver noch keine Entscheidung getroffen hat.
- **REQ-39:** Das System sendet beim Verlängern der Frist eine Benachrichtigung an alle aktiven Approver: order_number, neue Deadline, Name des verlängernden Admins.
- **REQ-40:** Das Timeout-Verarbeitungs-Job ist idempotent: Wird derselbe `ApprovalRequest` in zwei aufeinanderfolgenden Cron-Läufen zur Ablehnung markiert (z.B. wegen Fehler im ersten Lauf nach Teilschreibung), darf kein doppelter Statusübergang oder doppelte Benachrichtigung entstehen. Atomares Update: `UPDATE WHERE status = 'pending' AND deadline_at < now()`.
- **REQ-41:** Jede automatische Ablehnung wird im Audit-Log erfasst (Feature 7.2): actor_id = null (System), action = `approval_timeout_rejected`, entity_type = `approval_request`, entity_id, order_id, timestamp.
- **REQ-42:** Jede Fristverlängerung durch einen Admin wird im Audit-Log erfasst (Feature 7.2): actor_id = admin_id, action = `approval_deadline_extended`, entity_type = `approval_request`, entity_id, old_deadline, new_deadline, timestamp.
- **REQ-43:** Das System stellt einen Admin-Endpoint bereit, über den alle `ApprovalRequests` mit bald ablaufender Frist (innerhalb der nächsten konfigurierten Warnschwelle, Default: 4 Stunden) abgerufen werden können. Dieser Endpoint dient dem Admin-Dashboard (Feature 7.1) zur Anzeige von "Dringlichkeitswarnungen".

---

### Validation Rules

- **VAL-15:** Berechtigung für Fristverlängerung — Nur Admins können Fristen verlängern — `"Nur Administratoren können die Frist einer Genehmigungsanfrage verlängern."`
- **VAL-16:** ApprovalRequest-Status für Verlängerung — ApprovalRequest muss Status `pending` haben — `"Die Frist kann nur für ausstehende Genehmigungsanfragen verlängert werden."`
- **VAL-17:** Neue Deadline bei Verlängerung — Muss mindestens 1 Stunde in der Zukunft liegen — `"Die neue Frist muss mindestens 1 Stunde in der Zukunft liegen."`
- **VAL-18:** Maximale Gesamtlaufzeit — `new_deadline` darf `requested_at + 720h` nicht überschreiten — `"Die Frist kann maximal 30 Tage ab dem Zeitpunkt der Genehmigungsanfrage gesetzt werden."`
- **VAL-19:** Neue Deadline muss nach der aktuellen Deadline liegen — Eine "Verkürzung" der Frist ist nicht erlaubt — `"Die neue Frist muss nach der aktuellen Frist liegen."`

---

### API Contract

**Endpoint 11: Extend approval request deadline**
```
PATCH /api/v1/approval-requests/{approval_request_id}/deadline
```
Request Body:
```json
{
  "new_deadline_at": "string (ISO-8601 datetime, required)"
}
```
Response 200:
```json
{
  "approval_request_id": "uuid",
  "order_id": "uuid",
  "order_number": "string",
  "deadline_at": "ISO-8601 datetime",
  "original_deadline_at": "ISO-8601 datetime",
  "extended_by": "uuid",
  "extended_at": "ISO-8601 datetime",
  "message": "Die Genehmigungsfrist wurde verlängert."
}
```
Response 400: Validation error (VAL-17, VAL-18, VAL-19)
Response 401: Unauthorized
Response 403: Forbidden — nur Admins (VAL-15)
Response 404: ApprovalRequest nicht gefunden
Response 409: ApprovalRequest ist nicht mehr `pending` (VAL-16)

---

**Endpoint 12: List expiring approval requests (admin)**
```
GET /api/v1/approval-requests/expiring
```
Query Params:
- `within_hours` (optional, integer, default 4, max 168 — Warnschwelle in Stunden)
- `limit` (optional, integer, default 20, max 100)
- `offset` (optional, integer, default 0)

Response 200:
```json
{
  "total": 3,
  "limit": 20,
  "offset": 0,
  "within_hours": 4,
  "items": [
    {
      "id": "uuid",
      "order_id": "uuid",
      "order_number": "string",
      "order_title": "string",
      "requester_id": "uuid",
      "requester_name": "string",
      "requested_at": "ISO-8601 datetime",
      "deadline_at": "ISO-8601 datetime",
      "hours_remaining": 2.5
    }
  ]
}
```
Response 401: Unauthorized
Response 403: Forbidden — nur Admins

---

**Endpoint 13: Get approval system configuration**
```
GET /api/v1/approval-config
```
Response 200:
```json
{
  "default_deadline_hours": 48,
  "allow_self_approval": false,
  "timeout_check_interval_minutes": 15,
  "expiry_warning_hours": 4
}
```
Response 401: Unauthorized
Response 403: Forbidden — nur Admins

---

**Endpoint 14: Update approval system configuration**
```
PATCH /api/v1/approval-config
```
Request Body (alle Felder optional):
```json
{
  "default_deadline_hours": "integer (1–720)",
  "allow_self_approval": "boolean",
  "expiry_warning_hours": "integer (1–168)"
}
```
Hinweis: `timeout_check_interval_minutes` ist eine Deployment-Konfiguration und nicht über die API änderbar.

Response 200: Vollständige Konfiguration (wie Endpoint 13)
Response 400: Validation error (VAL-20 bis VAL-22)
Response 401: Unauthorized
Response 403: Forbidden — nur Admins

---

### Validation Rules (Konfiguration)

- **VAL-20:** `default_deadline_hours` — Integer, 1–720 — `"Die Standard-Frist muss zwischen 1 und 720 Stunden liegen."`
- **VAL-21:** `allow_self_approval` — Boolean — `"Der Wert für 'allow_self_approval' muss true oder false sein."`
- **VAL-22:** `expiry_warning_hours` — Integer, 1–168 — `"Die Ablaufwarnfrist muss zwischen 1 und 168 Stunden liegen."`

---

### Edge Cases

- **EC-15:** Timeout-Job läuft, aber die Datenbank ist kurzzeitig nicht erreichbar → Der Job scheitert vollständig ohne Partial-Updates. Beim nächsten Lauf (nach Intervall) werden alle abgelaufenen Requests erneut geprüft — durch Idempotenz (REQ-40) entstehen keine Duplikate.
- **EC-16:** Ein ApprovalRequest hat `deadline_at` in der Vergangenheit, aber ein Approver trifft gleichzeitig eine Entscheidung (Race Condition zwischen Approver und Timeout-Job) → Beide Operationen verwenden atomares `UPDATE WHERE status = 'pending'`. Einer gewinnt. Gewinnt der Timeout-Job: Der Approver erhält HTTP 409 ("Die Frist für diese Genehmigungsanfrage ist abgelaufen."). Gewinnt der Approver: Der Timeout-Job findet keinen `pending`-Record mehr — keine Seiteneffekte.
- **EC-17:** Admin verlängert die Frist eines ApprovalRequests auf 29 Tage 23 Stunden ab `requested_at`, danach versucht ein zweiter Admin, die Frist weiter zu verlängern → Der zweite Verlängerungsversuch über die 720h-Grenze hinaus scheitert mit VAL-18. Der zweite Admin erhält die verbleibende zulässige Zeitspanne in der Fehlermeldung: "Maximale Verlängerung bis {calculated_max_date} möglich."
- **EC-18:** Timeout-Benachrichtigungen an Approver schlagen fehl (AD nicht erreichbar) → Die Timeout-Ablehnung selbst (Status-Update der Order und des ApprovalRequests) wird nicht blockiert. Benachrichtigungen werden wie in EC-09 in Retry-Queue eingestellt. Das Ablehnen der Order hat Vorrang vor der Benachrichtigung.
- **EC-19:** Cron-Job läuft zweimal in schneller Folge (z.B. durch Systemwiederherstellung nach Absturz) → Atomares `UPDATE WHERE status = 'pending' AND deadline_at < now()` stellt sicher, dass derselbe Record nicht doppelt verarbeitet wird. Der zweite Durchlauf findet den Record bereits mit `status = 'rejected'` vor und überspringt ihn.
- **EC-20:** Admin verlängert die Frist auf einen Zeitpunkt, der in der nächsten Sekunde wieder abläuft (Minimum: 1h, VAL-17) → Dies ist durch die Validierungsregel verhindert. Das System prüft: `new_deadline_at >= now() + 1h`.

---

## Statusmaschinen-Übersicht

### Erweiterte Order-Statusmaschine

```
                     ┌─────────────────────────────────────────────────┐
                     │  Item-Änderung durch Requester                  │
                     │  (validated → draft, implizit)                  │
                     ▼                                                  │
┌───────┐  validate  ┌───────────┐  submit   ┌───────────┐            │
│ draft │───────────▶│ validated │──────────▶│ submitted │────────────┘
└───────┘            └───────────┘           └─────┬─────┘
    │                                              │
    │ DELETE                         ┌─────────────┴──────────────┐
    ▼                                │                            │
 (gelöscht)                 [Approval nötig]              [kein Approval]
                                     │                            │
                                     ▼                            │
                          ┌──────────────────┐                    │
                          │ pending_approval  │                    │
                          └────────┬─────────┘                    │
                                   │                              │
                    ┌──────────────┼──────────────┐              │
                    │              │              │              │
              [genehmigt]    [abgelehnt]    [Timeout]           │
                    │              │              │              │
                    ▼              ▼              ▼              │
                ┌──────────┐  ┌──────────┐  ┌──────────┐       │
                │ approved │  │ rejected │  │ rejected │       │
                └────┬─────┘  └──────────┘  └──────────┘       │
                     │        (Terminal)     (Terminal)         │
                     │                                          │
                     └──────────────────┬───────────────────────┘
                                        │
                                        ▼
                               ┌──────────────┐
                               │ provisioning │
                               └──────────────┘
                                    │      │
                    alle Items done │      │ mind. 1 Item failed
                                    ▼      ▼
                                ┌──────┐ ┌────────┐
                                │ done │ │ failed │
                                └──────┘ └────────┘
```

### Vollständige Transitions-Tabelle

| Von | Nach | Auslöser | Bedingung |
|-----|------|----------|-----------|
| `draft` | `validated` | `POST /orders/{id}/validate` | Alle Items valide |
| `validated` | `draft` | Item-PATCH oder Item-DELETE | Requester-Aktion |
| `validated` | `submitted` | `POST /orders/{id}/submit` | Requester-Aktion |
| `submitted` | `pending_approval` | System (intern nach Submit) | Mindestens eine Approval-Regel greift |
| `submitted` | `provisioning` | System (intern nach Submit, via Feature 4.1) | Keine Approval-Regel greift |
| `pending_approval` | `approved` | `POST /approval-requests/{id}/approve` | Approver- oder Admin-Entscheidung |
| `pending_approval` | `rejected` | `POST /approval-requests/{id}/reject` | Approver- oder Admin-Entscheidung |
| `pending_approval` | `rejected` | System (Timeout-Job) | `deadline_at` überschritten |
| `approved` | `provisioning` | System (intern nach Approve, via Feature 4.1) | Automatisch nach Approval |
| `provisioning` | `done` | Feature 4.2 | Alle Items `active` |
| `provisioning` | `failed` | Feature 4.6 | Dauerhafter Fehler nach Retry-Exhaustion |

### Terminalzustände

| Status | Grund |
|--------|-------|
| `done` | Alle Items erfolgreich provisioniert |
| `failed` | Provisioning dauerhaft fehlgeschlagen |
| `rejected` | Abgelehnt durch Approver oder Timeout |

### ApprovalRequest-Statusmaschine

```
┌─────────┐  Approver genehmigt  ┌──────────┐
│ pending │─────────────────────▶│ approved │
│         │  Approver lehnt ab   └──────────┘
│         │─────────────────────▶┌──────────┐
│         │  Timeout-Job         │ rejected │
│         │─────────────────────▶└──────────┘
└─────────┘
```

---

## Abhängigkeitsmatrix

| Diese Spec | Abhängig von | Schnittstelle |
|-----------|-------------|--------------|
| Feature 8.1 (Approval-Regeln) | Feature 1.1/1.2 (Identity & Access) | JWT-Auth, Rollen-Prüfung (`admin`-Rolle für Schreibzugriff) |
| Feature 8.1 (Approval-Regeln) | Feature 2.1 (Service Catalog) | `estimated_cost_eur_per_month` und `approval_always_required` aus ServiceTemplate (Erweiterung nötig — siehe Nacharbeiten) |
| Feature 8.1 (Approval-Regeln) | Feature 3.3 (Order Submit) | Regelauswertung wird durch Submit ausgelöst; Status-Übergang `submitted → pending_approval` oder `submitted → provisioning` |
| Feature 8.2 (Approval-Workflow) | Feature 1.1/1.2 (Identity & Access) | JWT-Auth, Rollen-Prüfung (`approver`/`admin`), AD-Lookup für aktive Approver-Liste (Benachrichtigungen) |
| Feature 8.2 (Approval-Workflow) | Feature 3.3 (Order Submit) | Statusübergänge `pending_approval → approved → provisioning` und `pending_approval → rejected`; Provisioning-Trigger-Auslösung nach Approval |
| Feature 8.2 (Approval-Workflow) | Feature 4.1 (OpenTofu Job-Dispatcher) | Dispatch-Event nach Approval-Entscheidung: identisch zu bisherigem Submit-Trigger — `{ order_id, order_item_id, template_slug, template_version, parameters, requester_id }` |
| Feature 8.2 (Approval-Workflow) | Feature 6.1 (E-Mail-Benachrichtigungen) | Benachrichtigung an Approver bei neuem ApprovalRequest (REQ-24); Benachrichtigung an Requester bei Entscheidung (REQ-25) |
| Feature 8.2 (Approval-Workflow) | Feature 7.2 (Audit-Log) | Jede Approval-Entscheidung wird geloggt (REQ-27) |
| Feature 8.3 (Timeout) | Feature 8.2 (Approval-Workflow) | Timeout-Job setzt ApprovalRequest auf `rejected`; identische Statustransition wie manuelle Ablehnung |
| Feature 8.3 (Timeout) | Feature 6.1 (E-Mail-Benachrichtigungen) | Timeout-Benachrichtigung an Requester (REQ-34) und Approver (REQ-35) |
| Feature 8.3 (Timeout) | Feature 7.1 (Admin-Dashboard) | Endpoint 12 liefert ablaufende Anfragen für Dashboard-Warnungen (REQ-43) |
| Feature 8.3 (Timeout) | Feature 7.2 (Audit-Log) | Automatische Ablehnungen werden geloggt (REQ-41); Fristverlängerungen werden geloggt (REQ-42) |

### Änderungsanforderungen an andere Specs

| Spec | Änderung | Auslöser |
|------|----------|---------|
| order-lifecycle.md | OrderStatus-Enum um `pending_approval`, `approved`, `rejected` erweitern | Feature 8.1/8.2 |
| order-lifecycle.md | REQ-154 (Provisioning-Trigger) anpassen — bedingte Auslösung nach Submit | Feature 8.1 |
| order-lifecycle.md | REQ-157 (Statusübergänge) um neue Transitionen erweitern | Feature 8.1/8.2/8.3 |
| order-lifecycle.md | Endpoints 46, 47, 56 um neue Status-Werte erweitern | Feature 8.1 |
| order-lifecycle.md | Endpoint 57 (SSE) um Event-Typ `approval_decision` erweitern | Feature 8.2 |
| order-lifecycle.md | Statusmaschinen-Übersicht und Abhängigkeitsmatrix aktualisieren | Feature 8.1/8.2/8.3 |
| service-catalog.md | ServiceTemplate um `estimated_cost_eur_per_month` und `approval_always_required` erweitern | Feature 8.1 (REQ-03, REQ-14) |

---

## Nummerierungsstand

> **Einstieg:** REQ-01, VAL-01, EC-01, Endpoint 1
> **Ende:** REQ-43, VAL-22, EC-20, Endpoint 14
