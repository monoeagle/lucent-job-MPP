# Feature-Gruppe 3: Order Lifecycle + JSON Export

> **Status:** Draft v1.1
> **Erstellt:** 2026-03-26
> **Geändert:** 2026-03-26 — Approval-Workflow integriert (Feature-Gruppe 8, approval-workflow.md)
> **Ersetzt:** `docs/specs/order-process.md` (Features 3.1–3.4, Session-basierter Checkout)
> **Umfang:** 4 Features, Requirements REQ-126–REQ-191, Validation Rules VAL-71–VAL-107, API Endpoints 45–67, Edge Cases EC-81–EC-128
> **Abhängigkeiten:** Feature-Gruppe 2 (service-catalog.md), Feature-Gruppe 4 (provisioning-engine.md), Feature-Gruppe 8 (approval-workflow.md)

---

> **Migrationshinweis:** Diese Spec ersetzt `order-process.md` vollständig. Das Session-basierte Checkout-Modell (60-Min-Timeout, 4-Schritt-Flow, 1 Order = 1 Service) wird durch ein Draft-basiertes, persistentes Multi-Service-Modell abgelöst. Der Approval-Workflow ist als Feature-Gruppe 8 (approval-workflow.md) separat spezifiziert und in dieser Spec an den relevanten Stellen referenziert (REQ-154, REQ-157, OrderStatus-Enum, SSE-Events).

---

## Inhaltsverzeichnis

- [Feature 3.1: Order CRUD](#feature-31-order-crud)
- [Feature 3.2: Order Validation](#feature-32-order-validation)
- [Feature 3.3: Order Submit + Status-Machine](#feature-33-order-submit--status-machine)
- [Feature 3.4: JSON Export für GitLab / OpenTofu](#feature-34-json-export-für-gitlab--opentofu)
- [Statusmaschinen-Übersicht](#statusmaschinen-übersicht)
- [Abhängigkeitsmatrix](#abhängigkeitsmatrix)

---

## Logisches Datenmodell

Das Datenmodell ist quellenagnostisch. Die API-Contracts definieren das Austauschformat; die interne Persistierung ist nicht Bestandteil dieser Spec.

### Order

```
Order {
  id:              string (UUID)           // interne ID, unveränderlich, serverseitig generiert
  order_number:    string                  // menschenlesbare Bestellnummer (z.B. "ORD-2026-00042"), serverseitig generiert
  requester_id:    string (UUID)           // ID des bestellenden Users (aus Auth-Context)
  status:          OrderStatus (Enum)      // draft | validated | submitted | pending_approval | approved | rejected | provisioning | done | failed
  title:           string                  // freier Titel der Bestellung (z.B. "Web-Cluster Q2"), max. 100 Zeichen
  business_reason: string                  // Begründung / Geschäftszweck, Pflichtfeld, max. 500 Zeichen
  desired_date:    ISO-8601 date (optional) // Wunschtermin Bereitstellung
  items:           OrderItem[]             // geordnete Liste der bestellten Services (min. 1 bei Submit)
  created_at:      ISO-8601 datetime
  updated_at:      ISO-8601 datetime
  submitted_at:    ISO-8601 datetime (optional)
  metadata:        object (optional)       // erweiterbare Key-Value-Paare
}
```

### OrderItem

```
OrderItem {
  id:               string (UUID)          // interne Item-ID, unveränderlich
  order_id:         string (UUID)          // Referenz auf die übergeordnete Order
  template_slug:    string                 // slug des ServiceTemplates (aus Feature 2.1)
  template_version: string                 // SemVer der Template-Version zum Zeitpunkt der Auswahl
  display_name:     string                 // Snapshot des ServiceTemplate.display_name zum Zeitpunkt der Auswahl
  parameters:       object                 // Key-Value-Map: ParameterDefinition.key → Wert (Snapshot)
  position:         integer                // Reihenfolge des Items in der Order (1-basiert)
  validation_state: ItemValidationState    // unchecked | valid | invalid
  validation_errors: ValidationViolation[] // leer wenn valid oder unchecked
  created_at:       ISO-8601 datetime
  updated_at:       ISO-8601 datetime
}
```

### ValidationViolation

```
ValidationViolation {
  parameter_key: string          // betroffener Parameter-Key (oder "_order" für Order-Level-Fehler)
  rule:          string          // Bezeichner der verletzten Regel (z.B. "required", "min", "cross_parameter")
  message:       string          // menschenlesbare Fehlermeldung
}
```

### OrderStatus (Enum)

```
draft            — Order wird aufgebaut, noch nicht zur Validierung eingereicht
validated        — Alle Items valide, Order bereit zum Submit
submitted        — Requester hat abgesendet; System prüft Approval-Pflicht
pending_approval — Wartet auf Approver-Entscheidung (nach submitted, wenn Approval-Regel greift)
approved         — Von Approver freigegeben, Provisioning-Trigger ausstehend
rejected         — Abgelehnt durch Approver oder automatisch nach Timeout (Terminalzustand)
provisioning     — Provisioning-Job läuft
done             — Alle Items erfolgreich provisioniert
failed           — Provisioning fehlgeschlagen (Details in Provisioning-Engine)
```

---

## Feature 3.1: Order CRUD

### User Story

Als Requester möchte ich eine Bestellung schrittweise aufbauen, mehrere IT-Services hinzufügen und die Zusammensetzung vor dem Absenden frei anpassen, damit ich komplexe Infrastrukturanforderungen in einer einzigen Bestellung bündeln kann.

---

### Requirements

- **REQ-126:** Ein Requester kann jederzeit eine neue Draft-Order erstellen. Die Order erhält initial Status `draft`, eine serverseitig generierte `id` (UUID) und eine menschenlesbare `order_number`. Das `title`-Feld ist Pflicht bei der Erstellung.
- **REQ-127:** Eine Draft-Order kann beliebig viele OrderItems enthalten. Das Minimum beim Absenden (Feature 3.3) beträgt 1 Item. Beim Erstellen der Order sind noch keine Items erforderlich.
- **REQ-128:** Ein Requester kann einer Draft-Order neue OrderItems hinzufügen. Jedes Item referenziert ein ServiceTemplate über `template_slug` + `template_version`. Das System speichert einen unveränderlichen Snapshot von `display_name` und `parameters` zum Zeitpunkt der Item-Erstellung.
- **REQ-129:** Ein Requester kann die Parameter eines bestehenden OrderItems bearbeiten, solange die Order den Status `draft` hat. Die Änderung setzt `validation_state` des Items zurück auf `unchecked` und den Order-Status auf `draft` (falls er `validated` war).
- **REQ-130:** Ein Requester kann ein OrderItem aus einer Draft-Order entfernen. Enthält die Order danach keine Items mehr, bleibt sie als leere Draft-Order erhalten (wird nicht automatisch gelöscht).
- **REQ-131:** Ein Requester kann `title`, `business_reason` und `desired_date` einer Draft-Order bearbeiten. Diese Felder sind ausschließlich im Status `draft` editierbar.
- **REQ-132:** Ein Requester kann eine Draft-Order löschen. Eine Order mit Status `validated`, `submitted`, `provisioning`, `done` oder `failed` kann nicht gelöscht werden.
- **REQ-133:** Beim Hinzufügen eines Items prüft das System, ob das referenzierte ServiceTemplate existiert und den Status `active` oder `deprecated` hat. Templates mit Status `disabled` dürfen nicht als neue Items hinzugefügt werden.
- **REQ-134:** Wird ein `deprecated`-Template als Item hinzugefügt, enthält die Response einen `warning`-Block mit dem Hinweis, dass eine neuere Version existiert, sowie der ID und dem Slug der Nachfolger-Version. Die Item-Erstellung wird dennoch durchgeführt.
- **REQ-135:** Die Item-Reihenfolge innerhalb einer Order ist durch das Feld `position` definiert. Beim Hinzufügen eines neuen Items erhält es automatisch die nächste freie Position (max. bestehende `position` + 1). Ein Requester kann die Reihenfolge der Items per PATCH-Request auf der Order anpassen.
- **REQ-136:** Jeder lesende und schreibende Zugriff auf eine Order erfordert, dass der authentifizierte User entweder der `requester_id` der Order entspricht oder die Rolle `admin` trägt. Andere User erhalten HTTP 403.
- **REQ-137:** Das System muss eine paginierte Liste aller Orders eines Requesters liefern können (eigene Orders), filterbar nach `status`. Admins können alle Orders systemweit abfragen.
- **REQ-138:** Das System persistiert Orders dauerhaft. Es gibt keinen automatischen Ablauf oder automatisches Löschen von Draft-Orders.

---

### Validation Rules

- **VAL-71:** `title` — Pflichtfeld, 3–100 Zeichen — `"Der Titel ist ein Pflichtfeld (3–100 Zeichen)."`
- **VAL-72:** `business_reason` — Pflichtfeld beim Submit (Feature 3.3), max. 500 Zeichen. Beim Erstellen einer Draft-Order ohne `business_reason` wird kein Fehler ausgelöst, aber das Feld muss vor dem Submit gefüllt sein — `"Eine Begründung ist erforderlich (max. 500 Zeichen)."`
- **VAL-73:** `desired_date` — Optional. Wenn angegeben, muss das Datum in der Zukunft liegen (mind. aktueller Tag + 1 Werktag) — `"Der Wunschtermin muss mindestens 1 Werktag in der Zukunft liegen."`
- **VAL-74:** `template_slug` beim Hinzufügen eines Items — Muss einem existierenden ServiceTemplate entsprechen — `"Das angegebene Service-Template existiert nicht."`
- **VAL-75:** `template_version` beim Hinzufügen eines Items — Muss eine existierende Version des angegebenen Slugs sein — `"Die angegebene Template-Version existiert nicht."`
- **VAL-76:** Template-Status beim Hinzufügen eines Items — Template muss Status `active` oder `deprecated` haben — `"Dieses Template ist deaktiviert und kann nicht mehr bestellt werden."`
- **VAL-77:** Bearbeiten / Löschen von Items — Nur zulässig wenn Order-Status = `draft` — `"Bestellpositionen können nur in einer Entwurfs-Bestellung bearbeitet werden."`
- **VAL-78:** Löschen einer Order — Nur zulässig wenn Order-Status = `draft` — `"Nur Entwurfs-Bestellungen können gelöscht werden."`
- **VAL-79:** Zugriffsberechtigung — Authentifizierter User muss `requester_id` der Order sein oder Rolle `admin` tragen — `"Sie haben keine Berechtigung, auf diese Bestellung zuzugreifen."`
- **VAL-80:** `position` beim Neuordnen — Alle `position`-Werte der Items müssen eindeutig und lückenlos von 1 bis n sein — `"Die Reihenfolge der Bestellpositionen ist ungültig."`

---

### API Contract

**Endpoint 45: Create a new draft order**
```
POST /api/v1/orders
```
Request Body:
```json
{
  "title": "string (required, 3–100 chars)",
  "business_reason": "string (optional, max 500 chars)",
  "desired_date": "string (ISO-8601 date, optional)"
}
```
Response 201:
```json
{
  "id": "uuid",
  "order_number": "ORD-2026-00042",
  "status": "draft",
  "title": "string",
  "business_reason": "string | null",
  "desired_date": "string | null",
  "items": [],
  "created_at": "ISO-8601 datetime",
  "updated_at": "ISO-8601 datetime"
}
```
Response 400: Validation error — `title` fehlt oder ungültig
Response 401: Unauthorized
Response 403: Forbidden — fehlende Requester-Rolle

---

**Endpoint 46: Get order by ID**
```
GET /api/v1/orders/{order_id}
```
Response 200:
```json
{
  "id": "uuid",
  "order_number": "string",
  "requester_id": "uuid",
  "status": "draft | validated | submitted | pending_approval | approved | rejected | provisioning | done | failed",
  "title": "string",
  "business_reason": "string | null",
  "desired_date": "string | null",
  "items": [
    {
      "id": "uuid",
      "template_slug": "string",
      "template_version": "string",
      "display_name": "string",
      "parameters": { "key": "value" },
      "position": 1,
      "validation_state": "unchecked | valid | invalid",
      "validation_errors": [],
      "created_at": "ISO-8601 datetime",
      "updated_at": "ISO-8601 datetime"
    }
  ],
  "submitted_at": "ISO-8601 datetime | null",
  "created_at": "ISO-8601 datetime",
  "updated_at": "ISO-8601 datetime"
}
```
Response 401: Unauthorized
Response 403: Forbidden — kein Zugriff auf diese Order
Response 404: Order nicht gefunden

---

**Endpoint 47: List orders (paginated)**
```
GET /api/v1/orders
```
Query Params:
- `status` (optional, Enum: draft | validated | submitted | pending_approval | approved | rejected | provisioning | done | failed)
- `requester_id` (optional, nur für Admins — filtert nach spezifischem Requester)
- `limit` (optional, integer, default 20, max 100)
- `offset` (optional, integer, default 0)

Response 200:
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": "uuid",
      "order_number": "string",
      "status": "string",
      "title": "string",
      "item_count": 3,
      "created_at": "ISO-8601 datetime",
      "updated_at": "ISO-8601 datetime"
    }
  ]
}
```
Response 401: Unauthorized
Response 403: Forbidden — Requester versucht `requester_id` eines anderen Users zu setzen

---

**Endpoint 48: Update order metadata**
```
PATCH /api/v1/orders/{order_id}
```
Request Body (alle Felder optional, nur geänderte Felder übermitteln):
```json
{
  "title": "string (3–100 chars)",
  "business_reason": "string (max 500 chars)",
  "desired_date": "string (ISO-8601 date) | null"
}
```
Response 200: Vollständige Order-Repräsentation (wie Endpoint 46)
Response 400: Validation error
Response 403: Forbidden — kein Zugriff oder Order nicht im Status `draft`
Response 404: Order nicht gefunden
Response 409: Order ist nicht im Status `draft` und kann nicht bearbeitet werden

---

**Endpoint 49: Delete draft order**
```
DELETE /api/v1/orders/{order_id}
```
Response 204: No Content
Response 403: Forbidden — kein Zugriff
Response 404: Order nicht gefunden
Response 409: Order ist nicht im Status `draft`

---

**Endpoint 50: Add item to order**
```
POST /api/v1/orders/{order_id}/items
```
Request Body:
```json
{
  "template_slug": "string (required)",
  "template_version": "string (SemVer, required)",
  "parameters": { "key": "value" }
}
```
Response 201:
```json
{
  "item": {
    "id": "uuid",
    "template_slug": "string",
    "template_version": "string",
    "display_name": "string",
    "parameters": { "key": "value" },
    "position": 1,
    "validation_state": "unchecked",
    "validation_errors": [],
    "created_at": "ISO-8601 datetime",
    "updated_at": "ISO-8601 datetime"
  },
  "warning": {
    "type": "template_deprecated",
    "message": "string",
    "successor_slug": "string",
    "successor_version": "string"
  }
}
```
Das Feld `warning` ist nur vorhanden, wenn das Template den Status `deprecated` hat.

Response 400: Validation error — Template nicht gefunden, deaktiviert oder ungültige Parameter-Struktur
Response 403: Forbidden — kein Zugriff oder Order nicht im Status `draft`
Response 404: Order nicht gefunden
Response 409: Order ist nicht im Status `draft`

---

**Endpoint 51: Update order item parameters**
```
PATCH /api/v1/orders/{order_id}/items/{item_id}
```
Request Body:
```json
{
  "parameters": { "key": "value" }
}
```
Response 200: Vollständige OrderItem-Repräsentation (validation_state wird auf `unchecked` zurückgesetzt)
Response 400: Validation error
Response 403: Forbidden — kein Zugriff oder Order nicht im Status `draft`
Response 404: Order oder Item nicht gefunden
Response 409: Order ist nicht im Status `draft`

---

**Endpoint 52: Remove item from order**
```
DELETE /api/v1/orders/{order_id}/items/{item_id}
```
Response 204: No Content
Response 403: Forbidden — kein Zugriff oder Order nicht im Status `draft`
Response 404: Order oder Item nicht gefunden
Response 409: Order ist nicht im Status `draft`

---

**Endpoint 53: Reorder items**
```
PUT /api/v1/orders/{order_id}/items/positions
```
Request Body:
```json
{
  "positions": [
    { "item_id": "uuid", "position": 1 },
    { "item_id": "uuid", "position": 2 }
  ]
}
```
Alle Items der Order müssen im Request enthalten sein. `positions`-Werte müssen lückenlos von 1 bis n sein.

Response 200: Vollständige Order-Repräsentation (wie Endpoint 46)
Response 400: Validation error — fehlende Items, Lücken in Positionswerten, doppelte Werte
Response 403: Forbidden — kein Zugriff oder Order nicht im Status `draft`
Response 404: Order nicht gefunden
Response 409: Order ist nicht im Status `draft`

---

### Edge Cases

- **EC-81:** Requester fügt ein Item hinzu, während das Template von `deprecated` auf `disabled` wechselt (Race Condition) → Das System prüft den Template-Status atomar beim Item-Anlegen. Ist das Template bei der Prüfung `disabled`, wird HTTP 400 mit VAL-76 zurückgegeben, auch wenn der Request millisekunden zuvor noch valid gewesen wäre.
- **EC-82:** Requester versucht, `requester_id` einer anderen Person beim Order-Update zu überschreiben → `requester_id` ist unveränderlich nach Erstellung. PATCH-Requests, die `requester_id` im Body enthalten, ignorieren das Feld ohne Fehler.
- **EC-83:** Order hat Status `validated`, Requester ändert ein Item-Parameter → Order-Status wechselt zurück zu `draft`, betroffenes Item bekommt `validation_state = unchecked`, alle anderen Items behalten ihren `validation_state`.
- **EC-84:** Requester versucht, eine leere Order (keine Items) zu validieren oder einzureichen → HTTP 409 mit Fehlermeldung: "Die Bestellung enthält keine Positionen."
- **EC-85:** Admin ruft die Order-Liste eines nicht-existierenden `requester_id` ab → Leere Liste, HTTP 200 (kein 404, da die Abfrage selbst valid ist).
- **EC-86:** Zwei simultane PATCH-Requests auf dasselbe OrderItem → Optimistic Locking oder DB-seitige Serialisierung. Der zweite Request erhält HTTP 409 mit Hinweis auf konkurrierenden Zugriff.
- **EC-87:** `desired_date` wird explizit auf `null` gesetzt → Feld wird geleert. Wenn das Datum bereits vergangen ist (z.B. Order wurde lange nicht abgeschlossen), ist das Feld nicht mehr VAL-73-geprüft — die Validierung auf Zukunftsdatum erfolgt nur beim Setzen/Ändern, nicht beim Lesen.
- **EC-88:** Requester fügt das gleiche Template (gleicher Slug, gleiche Version) mehrfach hinzu → Erlaubt. Mehrere OrderItems können das gleiche Template referenzieren (z.B. zwei identisch konfigurierte VMs). Jedes Item erhält eine eigene UUID und Position.

---

## Feature 3.2: Order Validation

### User Story

Als Requester möchte ich meine Bestellung vor dem Absenden validieren lassen, damit ich sicher sein kann, dass alle konfigurierten Services korrekt parametrisiert sind und das Provisioning ohne Fehler starten kann.

---

### Requirements

- **REQ-139:** Der Requester kann eine Validierung explizit auslösen. Das System validiert alle Items der Order gegen ihre jeweiligen ServiceTemplate-Schemas (Feature 2.1, REQ-117). Die Validierung kann jederzeit im Status `draft` angefordert werden.
- **REQ-140:** Die Validierung prüft je Item: (a) alle `required`-Parameter sind vorhanden und nicht leer, (b) alle Werte erfüllen die `constraints` des jeweiligen Parameters, (c) `DependencyRules` werden korrekt ausgewertet — abhängige required-Parameter werden nur geprüft, wenn ihre Bedingung erfüllt ist, (d) `cross_parameter_rules` innerhalb des Templates werden ausgewertet.
- **REQ-141:** Die Validierung ist nicht Fail-Fast: Das System sammelt alle Violations aller Items und gibt das vollständige Ergebnis in einer Response zurück.
- **REQ-142:** Wenn alle Items valide sind, wechselt die Order vom Status `draft` zu `validated`. Dieser Übergang ist atomar mit dem Schreiben der Validierungsergebnisse.
- **REQ-143:** Wenn mindestens ein Item invalid ist, bleibt der Order-Status `draft`. Alle Items erhalten ihren individuellen `validation_state` (`valid` oder `invalid`) und die zugehörigen `validation_errors`.
- **REQ-144:** Eine Validierung gegen ein `deprecated`-Template ist möglich. Das System gibt zusätzlich zu den Validierungsergebnissen eine Warnung aus, dass eine neuere Template-Version existiert.
- **REQ-145:** Eine bereits `validated` Order bleibt `validated`, wenn keine Items geändert wurden. Das erneute Auslösen der Validierung ist idempotent — der Status wechselt nicht, wenn alle Items weiterhin valide sind.
- **REQ-146:** Das System muss sicherstellen, dass das ServiceTemplate (`template_slug` + `template_version`) zum Zeitpunkt der Validierung noch im System existiert. Wurde ein Template (unerwarteterweise) aus dem System entfernt, wird das betroffene Item als `invalid` markiert mit der Violation: `"Das referenzierte Template existiert nicht mehr im System."`
- **REQ-147:** Die Validierung einer Order mit Status `submitted`, `provisioning`, `done` oder `failed` ist nicht möglich. Das System gibt HTTP 409 zurück.

---

### Validation Rules

- **VAL-81:** Order-Status für Validierung — Order muss Status `draft` oder `validated` haben — `"Die Validierung kann nur für Entwurfs-Bestellungen angefordert werden."`
- **VAL-82:** Mindestanzahl Items — Order muss mindestens 1 Item enthalten — `"Die Bestellung enthält keine Positionen und kann nicht validiert werden."`
- **VAL-83:** Pflichtparameter je Item — Jeder Parameter mit `required: true` (unter Berücksichtigung von DependencyRules) muss einen Wert haben und darf nicht `null`, leer oder fehlend sein — `"Das Feld '{label}' ist ein Pflichtfeld."`
- **VAL-84:** Numerische Constraints je Item — Wert muss innerhalb von `[min, max]` liegen, `step`-Konformität muss erfüllt sein — `"Der Wert für '{label}' muss zwischen {min} und {max} liegen."`
- **VAL-85:** Enum-Constraints je Item — Übermittelter Wert muss in den erlaubten Optionen enthalten und als `enabled: true` markiert sein — `"Der Wert '{value}' ist für '{label}' nicht zulässig."`
- **VAL-86:** String-Constraints je Item — Wert muss `min_length`, `max_length` und `pattern` (falls gesetzt) erfüllen — `"Der Wert für '{label}' erfüllt nicht die Formatanforderungen."`
- **VAL-87:** size_bytes-Constraints je Item — Wert in Bytes muss zwischen `min_bytes` und `max_bytes` liegen — `"Der Speicherwert für '{label}' liegt außerhalb des erlaubten Bereichs."`
- **VAL-88:** cross_parameter_rules je Item — Parameterkombination muss alle definierten Kombinationsregeln des Templates erfüllen — `"Die Kombination von '{param_a}' und '{param_b}' ist nicht zulässig: {regel_beschreibung}."`
- **VAL-89:** `business_reason` beim Übergang zu `validated` — Muss vorhanden und nicht leer sein. Wenn leer, wird die Order als `invalid` markiert, kein Status-Übergang — `"Eine Begründung ist für die Einreichung erforderlich."`

---

### API Contract

**Endpoint 54: Trigger order validation**
```
POST /api/v1/orders/{order_id}/validate
```
Request Body: leer (kein Body erforderlich)

Response 200:
```json
{
  "order_id": "uuid",
  "order_status": "validated | draft",
  "all_valid": true,
  "validated_at": "ISO-8601 datetime",
  "item_results": [
    {
      "item_id": "uuid",
      "template_slug": "string",
      "template_version": "string",
      "position": 1,
      "validation_state": "valid | invalid",
      "violations": [
        {
          "parameter_key": "string",
          "rule": "string",
          "message": "string"
        }
      ],
      "warning": {
        "type": "template_deprecated",
        "message": "string",
        "successor_slug": "string",
        "successor_version": "string"
      }
    }
  ]
}
```
Das Feld `warning` pro Item ist nur vorhanden, wenn das Template `deprecated` ist.

Response 401: Unauthorized
Response 403: Forbidden — kein Zugriff
Response 404: Order nicht gefunden
Response 409: Order ist nicht im Status `draft` oder `validated`

---

### Edge Cases

- **EC-89:** Validierung wird ausgelöst, während ein anderer Request zeitgleich ein Item der Order bearbeitet (Race Condition) → Die Validierung liest den konsistenten State vor dem parallelen Schreibvorgang. DB-seitige Transaktionsisolation stellt sicher, dass nicht ein halb-geschriebenes Item validiert wird. Die Validierung und das Item-Update sperren die Order-Zeile nicht dauerhaft — es liegt kein Deadlock vor, aber das Item-Update nach der Validierung setzt `validation_state` korrekt auf `unchecked` zurück.
- **EC-90:** Order enthält 50 Items, alle mit Parametern — Validierung muss für alle 50 Items vollständig durchgeführt werden. Kein Timeout-Abbruch innerhalb vernünftiger Grenzen (Zielwert: < 2 Sekunden für 50 Items unter normaler Last).
- **EC-91:** Ein ServiceTemplate wird zwischen Item-Hinzufügen und Validierung auf `disabled` gesetzt → Das Template-Snapshot im Item ist unveränderlich. Die Validierung prüft gegen den gespeicherten Template-Slug + Version. REQ-146 greift nur, wenn das Template komplett aus dem System entfernt wurde — `disabled`-Status verhindert keine Validierung gegen einen bereits referenzierten Snapshot.
- **EC-92:** Order ist bereits `validated`, Validierung wird erneut angefragt ohne Änderungen → HTTP 200, alle Items `valid`, `order_status = validated`. Kein Statuswechsel, keine doppelten DB-Writes (Idempotenz per REQ-145).
- **EC-93:** `cross_parameter_rules` referenziert Parameter, die durch `depends_on` nicht aktiv sind → Die cross_parameter_rule wird nicht ausgewertet, wenn einer der beteiligten Parameter durch DependencyRule inaktiv ist. Die Regel gilt nur für aktive Parameter-Kombinationen.
- **EC-94:** Validierung schlägt serverseitig fehl (DB-Fehler während Ergebnis-Persistierung) → HTTP 500. Der Order-Status verbleibt unverändert (`draft`). Es darf kein Partial-Write entstehen (atomare Transaktion für Validierungsergebnisse).

---

## Feature 3.3: Order Submit + Status-Machine

### User Story

Als Requester möchte ich eine validierte Bestellung verbindlich abschicken, damit die Provisioning-Engine gestartet wird und meine Infrastruktur automatisiert bereitgestellt wird.

---

### Requirements

- **REQ-148:** Ein Requester kann eine Order nur im Status `validated` absenden. Der Submit löst den Statusübergang `validated → submitted` aus.
- **REQ-149:** Beim Submit prüft das System erneut serverseitig, dass die Order mindestens 1 Item enthält und `business_reason` nicht leer ist. Diese Prüfung ist eine Sicherheitsnetz-Validierung — der Submit soll nicht auf eine unvollständige Order durchgeführt werden können.
- **REQ-150:** Der Submit ist idempotent-geschützt: Wird eine Order, die bereits `submitted` ist, erneut submitted, gibt das System HTTP 409 zurück. Es darf kein zweiter Provisioning-Job ausgelöst werden.
- **REQ-151:** Nach erfolgreichem Submit setzt das System `submitted_at` auf den aktuellen Server-Timestamp und die Order bekommt Status `submitted`. Dieser Übergang ist atomar.
- **REQ-152:** Das System stellt nach dem Submit eine Bestellbestätigung bereit mit: `order_id`, `order_number`, aktuellem Status (`submitted`), Anzahl der Items und Link zur Order-Detail-Seite.
- **REQ-153:** Nach dem Submit ist die Order schreibgeschützt: Items können nicht mehr hinzugefügt, geändert oder gelöscht werden. Metadaten-Felder (`title`, `business_reason`, `desired_date`) sind ebenfalls nicht mehr editierbar.
- **REQ-154:** Das System prüft nach erfolgreichem Submit, ob für die Order Approval-Pflicht besteht (Feature 8.1, approval-workflow.md). Besteht keine Approval-Pflicht, löst das System den Provisioning-Trigger unmittelbar aus und die Order wechselt zu `provisioning` (wie bisher). Der Trigger stellt für jedes OrderItem ein separates Dispatch-Event in die interne Job-Queue ein: `{ order_id, order_item_id, template_slug, template_version, parameters, requester_id }`. Feature 4.1 (OpenTofu Job-Dispatcher) konsumiert diese Events. Besteht Approval-Pflicht, wechselt die Order zu `pending_approval`. Der Provisioning-Trigger wird erst nach dem Übergang zu `approved` ausgelöst (Feature 8.2).
- **REQ-155:** Der Statusübergang von `submitted` zu `provisioning` erfolgt, sobald Feature 4.1 die erste `job_id` für mindestens ein OrderItem persistiert hat. Die Order-Ebene spiegelt damit den aggregierten Status der Items wider.
- **REQ-156:** Der Statusübergang zu `done` erfolgt, wenn alle OrderItems erfolgreich provisioniert wurden (Feature 4.2 meldet alle Items als `active`). Der Statusübergang zu `failed` erfolgt, wenn mindestens ein Item dauerhaft fehlgeschlagen ist und kein Retry mehr möglich ist (Feature 4.6).
- **REQ-157:** Statusübergänge sind ausschließlich in der definierten Reihenfolge erlaubt. Erlaubte Übergänge: `draft → validated → submitted → provisioning → done | failed` (Pfad ohne Approval-Pflicht) sowie `submitted → pending_approval` (wenn Approval-Regel greift), `pending_approval → approved` (durch Approver), `pending_approval → rejected` (durch Approver oder Timeout), `approved → provisioning` (Provisioning-Trigger nach Approval). `rejected` ist ein Terminalzustand — kein Rückwärtsübergang ist zulässig. Rückwärtsübergänge generell (außer dem impliziten Reset durch Item-Bearbeitung `validated → draft`) sind nicht erlaubt.
- **REQ-158:** Das System liefert Status-Updates über Server-Sent Events (SSE) an das Frontend. Jeder Statusübergang der Order und jedes OrderItems wird als SSE-Event gesendet.
- **REQ-159:** Der Submit-Endpoint ist idempotenz-geschützt durch einen optionalen `Idempotency-Key`-Header (UUID). Wird ein Request mit gleichem `Idempotency-Key` innerhalb von 24 Stunden wiederholt, gibt das System die gecachte Response zurück ohne erneuten Submit.

---

### Validation Rules

- **VAL-90:** Order-Status für Submit — Order muss Status `validated` haben — `"Die Bestellung muss vor dem Absenden validiert werden."`
- **VAL-91:** Mindestanzahl Items beim Submit — Order muss mindestens 1 Item enthalten — `"Die Bestellung enthält keine Positionen und kann nicht abgesendet werden."`
- **VAL-92:** `business_reason` beim Submit — Darf nicht leer sein — `"Eine Begründung ist für das Absenden der Bestellung erforderlich."`
- **VAL-93:** Duplikat-Submit-Schutz — Eine bereits `submitted`, `provisioning`, `done` oder `failed` Order darf nicht erneut submitted werden — `"Diese Bestellung wurde bereits abgesendet."`
- **VAL-94:** `Idempotency-Key`-Header — Wenn angegeben, muss es sich um eine gültige UUID v4 handeln — `"Der Idempotency-Key muss eine gültige UUID sein."`

---

### API Contract

**Endpoint 55: Submit order**
```
POST /api/v1/orders/{order_id}/submit
```
Request Headers:
- `Idempotency-Key: uuid (optional)`

Request Body: leer (kein Body erforderlich)

Response 200:
```json
{
  "order_id": "uuid",
  "order_number": "string",
  "status": "submitted",
  "item_count": 3,
  "submitted_at": "ISO-8601 datetime",
  "message": "Ihre Bestellung wurde erfolgreich eingereicht."
}
```
Response 401: Unauthorized
Response 403: Forbidden — kein Zugriff
Response 404: Order nicht gefunden
Response 409: Order ist nicht im Status `validated` (mit `reason`-Feld: aktueller Status der Order)

---

**Endpoint 56: Get order status (polling fallback)**
```
GET /api/v1/orders/{order_id}/status
```
Response 200:
```json
{
  "order_id": "uuid",
  "order_number": "string",
  "status": "draft | validated | submitted | pending_approval | approved | rejected | provisioning | done | failed",
  "item_statuses": [
    {
      "item_id": "uuid",
      "position": 1,
      "template_slug": "string",
      "provisioning_status": "pending | provisioning | done | failed | not_started",
      "job_id": "string | null"
    }
  ],
  "submitted_at": "ISO-8601 datetime | null",
  "updated_at": "ISO-8601 datetime"
}
```
Response 401: Unauthorized
Response 403: Forbidden
Response 404: Order nicht gefunden

---

**Endpoint 57: Order status SSE stream**
```
GET /api/v1/orders/{order_id}/events
```
Request Headers:
- `Accept: text/event-stream`

SSE Event-Typen:
```
event: order_status_changed
data: { "order_id": "uuid", "old_status": "string", "new_status": "string", "timestamp": "ISO-8601" }

event: item_status_changed
data: { "order_id": "uuid", "item_id": "uuid", "old_status": "string", "new_status": "string", "job_id": "string | null", "timestamp": "ISO-8601" }

event: approval_decision
data: { "order_id": "uuid", "decision": "approved | rejected", "decided_by": "uuid | null", "reason": "string | null", "timestamp": "ISO-8601" }

event: order_completed
data: { "order_id": "uuid", "final_status": "done | failed", "timestamp": "ISO-8601" }
```
Response 200: SSE-Stream (Content-Type: text/event-stream)
Response 401: Unauthorized
Response 403: Forbidden
Response 404: Order nicht gefunden

---

### Edge Cases

- **EC-95:** Requester submitted eine Order, während zeitgleich ein Admin das letzte Item löscht (Race Condition) → Submit und Item-Löschung konkurrieren. Der Submit prüft atomar (DB-Transaktion) die Item-Anzahl. Gewinnt der Submit, wird die Order korrekt abgesendet. Gewinnt das Löschen, schlägt der Submit mit HTTP 409 fehl: "Die Bestellung enthält keine Positionen."
- **EC-96:** SSE-Verbindung wird unterbrochen, während `provisioning` läuft → Der Client reconnectet per `Last-Event-ID`-Header. Das System sendet alle Events, die seit der letzten empfangenen Event-ID aufgelaufen sind. Fehlt `Last-Event-ID`, sendet das System das aktuelle Status-Snapshot-Event.
- **EC-97:** Feature 4.1 kann kein Dispatch-Event für ein Item in die Queue stellen (Queue voll, Systemfehler) → Der Provisioning-Trigger-Mechanismus behandelt diesen Fehler intern (Feature 4.1, REQ-50). Die Order verbleibt im Status `submitted`. Feature 4.6 (Rollback) greift nach erschöpftem Retry.
- **EC-98:** Requester submittet mit `Idempotency-Key`, erster Request schlägt mit HTTP 500 fehl (serverseitiger Fehler) → Der `Idempotency-Key` darf nur gecacht werden, wenn der erste Request erfolgreich war (HTTP 200). Fehlerhafte Responses werden nicht gecacht — der Retry mit gleichem Key löst einen neuen Submit-Versuch aus.
- **EC-99:** Alle Items einer Order werden von Feature 4.2 als `done` gemeldet, aber danach kommt noch ein verspätetes `failed`-Event für ein Item (Netzwerklatenz) → Das System nimmt Status-Übergänge auf Order-Ebene nur vorwärts vor. Wurde `done` erreicht, wird kein nachträglicher `failed`-Übergang mehr akzeptiert. Das verspätete Event wird ignoriert und geloggt.
- **EC-100:** Order wird submitted, Provisioning-Trigger wird gesendet, aber die DB schlägt beim Persistieren von `submitted_at` fehl → Der Submit-Vorgang muss als atomare Transaktion implementiert werden. Schlägt die Persistierung fehl, wird kein Dispatch-Event gesendet. Der Submit gilt als fehlgeschlagen — HTTP 500 an den Client.

---

## Feature 3.4: JSON Export für GitLab / OpenTofu

### User Story

Als System möchte ich aus einer validierten oder abgesendeten Bestellung ein strukturiertes JSON-Dokument generieren, damit die OpenTofu-Provisioning-Engine die Infrastruktur anhand der Bestellparameter automatisiert bereitstellen kann.

---

### Requirements

- **REQ-160:** Das System muss einen Endpoint bereitstellen, der für eine Order (Status `validated` oder `submitted`) ein JSON-Export-Dokument generiert, das alle OrderItems als separate Tofu-Blöcke enthält.
- **REQ-161:** Der JSON-Export ist nur lesend — er verändert keine Daten und keinen Order-Status.
- **REQ-162:** Für jedes OrderItem wird ein separater Export-Block erstellt. Der Block enthält `module_source` (aus `ServiceTemplate.tofu_module_source`) und `variables` (aus den Item-Parametern, gemappt auf `tofu_variable_name`).
- **REQ-163:** Das Mapping von OrderItem-Parametern auf Tofu-Variablen folgt der Regel aus Feature 2.1 (service-catalog.md): Der Schlüssel im `variables`-Objekt ist `ParameterDefinition.tofu_variable_name`. Der Wert ist der im OrderItem gespeicherte Parameter-Wert, typisiert gemäß `ParameterDefinition.type`.
- **REQ-164:** Parameter, deren `depends_on`-Bedingungen nicht erfüllt sind (ausgewertet anhand der im OrderItem gespeicherten Parameter-Werte), werden nicht in den `variables`-Block aufgenommen. Sie werden weggelassen, nicht mit `null` belegt (analog REQ-113 aus Feature 2.1).
- **REQ-165:** `size_bytes`-Parameter werden im Export immer als Integer in Bytes exportiert, unabhängig von der Anzeigeeinheit (analog REQ-114 aus Feature 2.1).
- **REQ-166:** Enum-Parameter exportieren den `value` der gewählten Option (nicht den `label`).
- **REQ-167:** Boolean-Parameter werden als `true`/`false` exportiert (JSON-Boolean, nicht als String).
- **REQ-168:** Integer- und Float-Parameter werden als JSON-Zahlen exportiert (nicht als Strings).
- **REQ-169:** Der Export-Block pro Item enthält zusätzlich Metadaten: `order_item_id`, `template_slug`, `template_version` und `position`. Diese Metadaten sind für das Provisioning-System zur Zuordnung gedacht, gehen aber nicht als Tofu-Variablen in den `variables`-Block ein.
- **REQ-170:** Das System nutzt den Template-Snapshot, der im OrderItem gespeichert ist (Zeitpunkt der Item-Erstellung), um das Tofu-Variable-Mapping aufzulösen. Spätere Template-Änderungen (neue Versionen) haben keinen Einfluss auf den Export bestehender Orders.
- **REQ-171:** Der Export-Endpoint muss auch von internen Services (Feature 4.1, Job-Dispatcher) aufrufbar sein, nicht nur vom Frontend. Die Authentifizierung erfolgt über denselben Auth-Mechanismus wie alle anderen Endpoints (Service-Account oder User-Token).
- **REQ-172:** Wenn eine Order den Status `provisioning`, `done` oder `failed` hat, ist der Export-Endpoint weiterhin verfügbar — für Debugging- und Audit-Zwecke. Es wird jedoch ein `readonly_notice`-Feld in der Response gesetzt.

---

### Validation Rules

- **VAL-95:** Order-Status für Export — Order muss Status `validated`, `submitted`, `provisioning`, `done` oder `failed` haben — `"Der JSON-Export ist nur für validierte oder abgesendete Bestellungen verfügbar."`
- **VAL-96:** Order muss mindestens 1 Item enthalten — `"Die Bestellung enthält keine Positionen, die exportiert werden könnten."`
- **VAL-97:** Template-Snapshot-Konsistenz — Das System muss für jedes Item das Template-Schema (ParameterDefinition-Liste mit `tofu_variable_name`) abrufbar haben. Kann das Schema für einen Item-Snapshot nicht aufgelöst werden, wird das Item im Export mit einem `error`-Block markiert und kein partielles Mapping versucht — `"Template-Schema für Item {item_id} konnte nicht aufgelöst werden."`

---

### API Contract

**Endpoint 58: Export order as OpenTofu JSON**
```
GET /api/v1/orders/{order_id}/export/tofu
```
Query Params:
- `format` (optional, default: `json`) — aktuell nur `json` unterstützt

Response 200:
```json
{
  "order_id": "uuid",
  "order_number": "string",
  "exported_at": "ISO-8601 datetime",
  "readonly_notice": "string | null",
  "items": [
    {
      "order_item_id": "uuid",
      "template_slug": "string",
      "template_version": "string",
      "position": 1,
      "module_source": "string",
      "variables": {
        "vm_name": "web-server-01",
        "cpu_cores": 4,
        "ram_gb": 16,
        "disk_size_bytes": 107374182400,
        "os_type": "ubuntu-22-04",
        "enable_backup": true
      },
      "error": null
    }
  ]
}
```

Wenn ein Item nicht aufgelöst werden kann:
```json
{
  "order_item_id": "uuid",
  "template_slug": "string",
  "template_version": "string",
  "position": 2,
  "module_source": null,
  "variables": null,
  "error": {
    "code": "template_schema_unresolvable",
    "message": "Template-Schema für Item {item_id} konnte nicht aufgelöst werden."
  }
}
```

Response 400: `format` ist kein unterstützter Wert
Response 401: Unauthorized
Response 403: Forbidden — kein Zugriff auf diese Order
Response 404: Order nicht gefunden
Response 409: Order-Status ist `draft` — Export nicht verfügbar

---

**Endpoint 59: Export single order item as OpenTofu JSON**
```
GET /api/v1/orders/{order_id}/items/{item_id}/export/tofu
```
Response 200:
```json
{
  "order_id": "uuid",
  "order_item_id": "uuid",
  "template_slug": "string",
  "template_version": "string",
  "position": 1,
  "module_source": "string",
  "variables": {
    "vm_name": "string",
    "cpu_cores": 4
  },
  "exported_at": "ISO-8601 datetime"
}
```
Response 401: Unauthorized
Response 403: Forbidden
Response 404: Order oder Item nicht gefunden
Response 409: Order-Status ist `draft` — Export nicht verfügbar

---

### Edge Cases

- **EC-101:** Ein OrderItem referenziert `template_version = "1.0.0"`, die Template-Version wurde nach der Item-Erstellung aus dem System entfernt (unerwarteter Admin-Eingriff) → Das System kann das ParameterDefinition-Schema für das Mapping nicht laden. Das Item erscheint im Export mit `error.code = "template_schema_unresolvable"`. Die anderen Items werden weiterhin korrekt exportiert (partieller Export).
- **EC-102:** Ein Parameter hat `depends_on`-Bedingung, die auf einen anderen Parameter referenziert, der selbst durch eine weitere `depends_on`-Bedingung inaktiv ist (transitiv) → Das System wertet `depends_on`-Bedingungen rekursiv aus. Ein Parameter ist nur dann aktiv, wenn alle transitiven Abhängigkeiten erfüllt sind. Inaktive Parameter werden aus dem Export ausgeschlossen.
- **EC-103:** Order hat 20 Items, jedes mit 30 Parametern — Export muss vollständig und ohne Timeout generiert werden. Kein Lazy-Loading oder partieller Export ohne `error`-Indikator.
- **EC-104:** Feature 4.1 ruft `GET /export/tofu` auf, während der Requester zeitgleich die Order-Detail-Seite aufruft → Der Export-Endpoint ist idempotent und lesend. Keine Konflikte möglich — beide Requests können parallel beantwortet werden.
- **EC-105:** Ein `size_bytes`-Parameter hat den Wert `0` (z.B. optionaler zusätzlicher Disk) → Wird als `0` (Integer) exportiert, nicht weggelassen. Null-Werte bei aktiven Parametern werden exportiert. Nur inaktive Parameter (durch `depends_on`) werden weggelassen.
- **EC-106:** Enum-Parameter-Wert im OrderItem entspricht keiner `enabled: true`-Option im Template-Snapshot (z.B. Option wurde nachträglich deaktiviert — aber der Snapshot ist unveränderlich) → Der gespeicherte Wert wird unverändert exportiert. Der Export prüft nicht erneut die `enabled`-Bedingung — das ist Aufgabe der Validierung (Feature 3.2). Beim Export wird das, was gespeichert wurde, exportiert.
- **EC-107:** `readonly_notice` ist gesetzt (Order im Status `provisioning`, `done`, `failed`) — Feature 4.1 greift auf den Export zu → `readonly_notice` ist ein reines Informationsfeld für Frontend-Anzeige. Feature 4.1 ignoriert es und verarbeitet `items` direkt.

---

## Statusmaschinen-Übersicht

### Order-Statusmaschine

```
                     ┌─────────────────────────────────────────┐
                     │  Item-Änderung durch Requester          │
                     │  (validated → draft, implizit)          │
                     ▼                                         │
┌───────┐  validate  ┌───────────┐  submit   ┌───────────┐    │
│ draft │───────────▶│ validated │──────────▶│ submitted │────┘
└───────┘            └───────────┘           └───────────┘
    │                                              │
    │ DELETE                        ┌──────────────┴──────────────┐
    ▼                               │ keine Approval-Pflicht       │ Approval-Pflicht
 (gelöscht)                         │ (Provisioning-Trigger)       │
                                    ▼                              ▼
                             ┌──────────────┐         ┌──────────────────┐
                             │ provisioning │         │ pending_approval  │
                             └──────────────┘         └──────────────────┘
                                  │      │                  │          │
                  alle Items done │      │ mind. 1          │ approved │ rejected
                                  │      │ Item failed      ▼          ▼
                                  ▼      ▼           ┌──────────┐ ┌──────────┐
                              ┌──────┐ ┌────────┐    │ approved │ │ rejected │
                              │ done │ │ failed │    └──────────┘ └──────────┘
                              └──────┘ └────────┘         │       (Terminal)
                                                           │ Provisioning-Trigger
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

**Erlaubte Transitionen (System-initiiert):**

| Von | Nach | Auslöser |
|-----|------|---------|
| `draft` | `validated` | `POST /validate` — alle Items valid |
| `validated` | `draft` | Item-PATCH oder Item-DELETE durch Requester |
| `validated` | `submitted` | `POST /submit` durch Requester |
| `submitted` | `provisioning` | Feature 4.1 persistiert erste `job_id` (kein Approval erforderlich) |
| `submitted` | `pending_approval` | Approval-Regel greift (Feature 8.1) |
| `pending_approval` | `approved` | Approver erteilt Freigabe (Feature 8.2) |
| `pending_approval` | `rejected` | Approver lehnt ab oder Timeout (Feature 8.2/8.3) |
| `approved` | `provisioning` | Provisioning-Trigger nach Approval (Feature 8.2) |
| `provisioning` | `done` | Feature 4.2 meldet alle Items als `active` |
| `provisioning` | `failed` | Feature 4.6 meldet dauerhaften Fehler |

**Nicht erlaubte Transitionen (werden mit HTTP 409 abgelehnt):**

- `submitted → validated` oder früher
- `pending_approval → submitted` oder früher
- `approved → pending_approval` oder früher
- `rejected → *` (Terminalzustand)
- `provisioning → submitted` oder früher
- `done → *` (Terminalzustand)
- `failed → *` (Terminalzustand)

---

### OrderItem-Provisioning-Status

OrderItems haben einen separaten Provisioning-Status, der von Feature 4.1/4.2 verwaltet wird:

```
not_started → provisioning → done
                          └──→ failed
```

| Status | Bedeutung |
|--------|-----------|
| `not_started` | Dispatch-Event noch nicht konsumiert |
| `provisioning` | Job wurde an GitLab/OpenTofu übergeben |
| `done` | Erfolgreich provisioniert |
| `failed` | Dauerhafter Fehler nach Retry-Exhaustion |

---

## Abhängigkeitsmatrix

| Diese Spec | Abhängig von | Schnittstelle |
|-----------|-------------|--------------|
| Feature 3.1 (Order CRUD) | Feature 2.1 (Service Catalog) | `GET /api/v1/catalog/templates/{slug}` — Prüfung ob Template existiert und Status `active`/`deprecated`; Snapshot von `display_name` |
| Feature 3.2 (Order Validation) | Feature 2.1 (Service Catalog) | Endpoint 43 (Validate order parameters) — Validierung der Item-Parameter gegen Template-Schema inkl. DependencyRules und cross_parameter_rules |
| Feature 3.3 (Order Submit) | Feature 4.1 (OpenTofu Job-Dispatcher) | Dispatch-Event `{ order_id, order_item_id, template_slug, template_version, parameters, requester_id }` je Item in interne Job-Queue (ersetzt das bisherige einfache Event aus REQ-44) |
| Feature 3.3 (Order Submit) | Feature 4.2 (Provisioning-Status-Sync) | Status-Callbacks: Feature 4.2 meldet Item-Status-Updates zurück → löst Order-Statusübergang aus |
| Feature 3.3 (Order Submit) | Feature 4.6 (Fehlerbehandlung & Rollback) | Feature 4.6 meldet dauerhaften Fehler → löst Order-Status `failed` aus |
| Feature 3.4 (JSON Export) | Feature 2.1 (Service Catalog) | Template-Schema-Lookup für `tofu_variable_name`-Mapping; Template-Snapshot aus OrderItem |
| Feature 3.4 (JSON Export) | Feature 4.1 (OpenTofu Job-Dispatcher) | Feature 4.1 konsumiert `GET /api/v1/orders/{order_id}/export/tofu` (Endpoint 58) |

### Hinweis: Anpassung REQ-44 (provisioning-engine.md)

REQ-44 in provisioning-engine.md definiert das konsumierte Event als:
```
{ order_id, service_id, parameters, requester_id }
```

Mit der neuen Multi-Service-Order-Architektur ändert sich das Event-Format zu:
```
{ order_id, order_item_id, template_slug, template_version, parameters, requester_id }
```

`service_id` entfällt zugunsten von `template_slug` + `template_version` (konsistent mit Feature 2.1). `order_item_id` ist neu und erlaubt Feature 4.1 die Zuordnung von Job-IDs zu spezifischen OrderItems. Diese Änderung muss in provisioning-engine.md (REQ-44, REQ-46) nachgezogen werden.

---

## Nummerierungsstand

> **Einstieg:** REQ-126, VAL-71, EC-81, Endpoint 45
> **Ende:** REQ-172, VAL-97, EC-107, Endpoint 59
