# Feature-Gruppe 11: OrderItemGroup, Quantity & Per-Instance-Parameter

**Version:** 1.0
**Datum:** 2026-03-26
**Status:** Draft

> **Umfang:** 3 Features, Requirements REQ-01–REQ-49, Validation Rules VAL-01–VAL-31,
> API Endpoints 1–17, Edge Cases EC-01–EC-38
>
> **Abhängigkeiten:**
> - Feature-Gruppe 2 (service-catalog.md) — ParameterDefinition, ServiceTemplate
> - Feature-Gruppe 3 (order-lifecycle.md) — OrderItem, Order-Status-Maschine, Submit-Flow
> - Feature-Gruppe 4 (provisioning-engine.md) — Dispatch-Event-Format, IPAM-Integration (4.4)
> - Feature-Gruppe 8 (approval-workflow.md) — Kostensumme für Approval-Schwellwerte
> - Feature-Gruppe 10 (context-dependent-ordering.md) — OrderContext, bleibt unverändert anwendbar

---

## Überblick und Designentscheidungen

### Erweiterungsansatz

Dieses Feature erweitert das bestehende OrderItem-Modell um drei orthogonale Konzepte, die unabhängig und kombiniert einsetzbar sind:

1. **Gruppe (Feature 11.1):** Optionale logische Zusammenfassung mehrerer OrderItems unter einem gemeinsamen Namen.
2. **Quantity (Feature 11.2):** Skalierung eines einzelnen OrderItems auf N identische Instanzen eines Services.
3. **Per-Instance-Parameter (Feature 11.3):** Differenzierung, welche Parameter bei Quantity > 1 geteilt, automatisch generiert oder manuell pro Instanz gesetzt werden.

### Rückwärtskompatibilität

OrderItems ohne `group_id` und mit `quantity = 1` verhalten sich exakt wie bisher. Alle bestehenden Endpoints, Status-Übergänge und Dispatch-Events sind unverändert gültig. Clients, die die neuen Felder nicht senden, erhalten Defaults (`group_id = null`, `quantity = 1`).

### Rollback-Entscheidung bei Gruppen-Fehlern

Schlägt ein einzelnes Item innerhalb einer Gruppe fehl, betrifft der Rollback **nur dieses Item**, nicht die gesamte Gruppe. Die Gruppe ist eine logische UI-Einheit, kein atomarer Transaktionsblock. Die Order kann trotz einzelner fehlgeschlagener Items den Status `done` mit `partial` erreichen (analog zur bestehenden Multi-Item-Logik in Feature 4.6). Eine Gruppe gilt als `failed`, wenn **alle** ihre Items fehlgeschlagen sind.

Diese Entscheidung entspricht dem bestehenden Verhalten bei Multi-Service-Orders: jedes Item ist ein eigenständiger Provisioning-Job.

---

## Logisches Datenmodell (Erweiterung)

### OrderItemGroup (neue Entität)

```
OrderItemGroup {
  id:           string (UUID)            // interne ID, serverseitig generiert, unveränderlich
  order_id:     string (UUID)            // FK auf Order, unveränderlich nach Erstellung
  name:         string                   // logischer Name der Gruppe, z.B. "Web-Cluster", max. 100 Zeichen
  description:  string (optional)        // optionale Beschreibung, max. 500 Zeichen
  position:     integer                  // Reihenfolge der Gruppe in der Order (1-basiert, lückenlos)
  created_at:   ISO-8601 datetime
  updated_at:   ISO-8601 datetime
}
```

### OrderItem — Erweiterungen

Die folgenden Felder werden zum bestehenden OrderItem-Modell (order-lifecycle.md) hinzugefügt:

```
OrderItem {
  // ... alle bestehenden Felder unverändert ...

  // NEU:
  group_id:            string (UUID) | null      // Referenz auf OrderItemGroup; null = ungrupiertes Item
  quantity:            integer                   // Anzahl identischer Instanzen; Default: 1; Min: 1; Max: 50
  instance_parameters: InstanceParameterSet[]    // Array der Länge = quantity; leer wenn quantity = 1
                                                 // und keine per_instance-Parameter existieren
}
```

### InstanceParameterSet (neue Entität, inline in OrderItem)

```
InstanceParameterSet {
  instance_index:  integer   // 0-basierter Index der Instanz (0 bis quantity-1)
  parameters:      object    // Key-Value-Map; enthält NUR Parameter mit per_instance = true
                             // Parameter mit per_instance = "auto" sind NICHT enthalten
                             // (werden serverseitig generiert)
}
```

### ParameterDefinition — Erweiterung (Änderung an Feature 2.1)

Das bestehende ParameterDefinition-Modell (service-catalog.md) erhält ein neues optionales Feld:

```
ParameterDefinition {
  // ... alle bestehenden Felder unverändert ...

  // NEU:
  per_instance: boolean | "auto"  // false (Default) | true | "auto"
                                  // false  = shared — gleicher Wert für alle Instanzen (CPU, RAM, OS)
                                  // true   = unique — muss pro Instanz manuell gesetzt werden
                                  // "auto" = automatisch generiert — Hostname (Prefix+Seq), IP (IPAM)
}
```

### Auto-Generierungsregeln (systemseitig, nicht im Template konfigurierbar)

```
AutoGenerationRule {
  parameter_key:   string    // z.B. "hostname", "ip_address"
  strategy:        Enum      // hostname_sequence | ipam_reservation
}
```

- `hostname_sequence`: Wert = `<prefix>-<NNN>`, wobei `<prefix>` aus dem shared Parameter `hostname_prefix`
  stammt (oder aus dem Template-Slug, wenn kein Prefix-Parameter existiert) und `<NNN>` eine dreistellige
  laufende Nummer ist. Die Sequenz ist pro Batch atomar zu reservieren.
- `ipam_reservation`: Wert = IP-Adresse, die via IPAM-Integration (Feature 4.4) reserviert wird.
  Pro Instanz wird eine separate IP reserviert. Die Reservierungen erfolgen im Submit-Schritt.

---

## Inhaltsverzeichnis

- [Feature 11.1: OrderItemGroup — Gruppierung von Items](#feature-111-orderitemgroup--gruppierung-von-items)
- [Feature 11.2: Quantity — Skalierung identischer Server](#feature-112-quantity--skalierung-identischer-server)
- [Feature 11.3: Per-Instance-Parameter — Instanzspezifische Konfiguration](#feature-113-per-instance-parameter--instanzspezifische-konfiguration)
- [Auswirkungen auf bestehende Features](#auswirkungen-auf-bestehende-features)
- [Abhängigkeitsmatrix](#abhängigkeitsmatrix)

---

## Feature 11.1: OrderItemGroup — Gruppierung von Items

### User Story

Als Requester möchte ich mehrere OrderItems unter einem benannten Gruppe zusammenfassen (z.B. "Web-Cluster"), damit ich komplexe Infrastruktur-Bundles übersichtlich strukturieren und als logische Einheit kommunizieren kann.

---

### Requirements

- **REQ-01:** Ein Requester kann einer Draft-Order eine neue OrderItemGroup hinzufügen. Die Gruppe erhält eine serverseitig generierte UUID und wird mit `name` und optionaler `description` gespeichert.

- **REQ-02:** Eine OrderItemGroup kann nur zu einer Order hinzugefügt werden, die den Status `draft` hat. Versuche, Gruppen zu einer Order mit anderem Status hinzuzufügen, werden abgelehnt.

- **REQ-03:** Beim Hinzufügen einer neuen Gruppe erhält sie automatisch die nächste freie `position` (max. bestehende `position` der Gruppen + 1). `position` beginnt bei 1.

- **REQ-04:** Ein Requester kann `name`, `description` und `position` einer bestehenden Gruppe bearbeiten, solange die Order den Status `draft` hat.

- **REQ-05:** Ein Requester kann eine leere Gruppe löschen. Eine Gruppe, der noch OrderItems zugewiesen sind, kann nicht direkt gelöscht werden. Der Requester muss zuerst alle Items aus der Gruppe entfernen oder ihnen `group_id = null` zuweisen.

- **REQ-06:** Ein Requester kann die Gruppenzugehörigkeit eines OrderItems ändern (anderer `group_id`-Wert oder `null`), solange die Order den Status `draft` hat. Das Item behält alle übrigen Eigenschaften unverändert.

- **REQ-07:** Die `position`-Werte der Gruppen innerhalb einer Order müssen jederzeit lückenlos von 1 bis n sein. Beim Löschen einer Gruppe werden die `position`-Werte der verbleibenden Gruppen serverseitig neu nummeriert (1-basiert, aufsteigend nach bisheriger Reihenfolge).

- **REQ-08:** Ungruppierte OrderItems (mit `group_id = null`) sind weiterhin vollständig gültig und verhalten sich wie in Feature-Gruppe 3 definiert. Eine Order muss keine Gruppen enthalten.

- **REQ-09:** In der Order-Gesamtansicht (GET /api/v1/orders/{id}) werden Gruppen und ihre zugehörigen Items gemeinsam zurückgegeben. Ungruppierte Items werden in einem separaten Array `ungrouped_items` geliefert. Die Reihenfolge der Items innerhalb einer Gruppe folgt dem `position`-Feld der Items.

- **REQ-10:** Eine Order kann maximal 20 Gruppen enthalten. Diese Grenze verhindert unübersichtliche Orders und begrenzt den Rendering-Aufwand im Frontend.

- **REQ-11:** Jede Order-Validation (Feature 3.2) prüft alle Items unabhängig von ihrer Gruppenzugehörigkeit. Eine Gruppe gilt als valide, wenn alle ihre Items den `validation_state = valid` haben. Der Gesamt-Order-Status folgt der bestehenden Logik in REQ-148 (order-lifecycle.md).

- **REQ-12:** Bei Order-Submit (Feature 3.3) werden Items unabhängig von Gruppenzugehörigkeit als einzelne Dispatch-Events behandelt. Die Gruppe ist ausschließlich eine logische Einheit, kein atomarer Dispatch-Block.

- **REQ-13:** Beim JSON-Export (Feature 3.4) werden Items innerhalb einer Gruppe unter dem Gruppen-`name` als Kommentar oder Sektionsblock gruppiert, um die Lesbarkeit des Tofu-Exports zu verbessern. Das Format ist in Feature 3.4 zu ergänzen.

---

### Validation Rules

- **VAL-01:** `name` (OrderItemGroup) — Pflichtfeld, 2–100 Zeichen, darf keine führenden oder nachgestellten Leerzeichen enthalten — `"Der Gruppenname ist ein Pflichtfeld (2–100 Zeichen, keine führenden/nachgestellten Leerzeichen)."`

- **VAL-02:** `description` (OrderItemGroup) — Optional, max. 500 Zeichen — `"Die Gruppensbeschreibung darf maximal 500 Zeichen enthalten."`

- **VAL-03:** Gruppen-Erstellung/-Bearbeitung — Nur zulässig wenn Order-Status = `draft` — `"Gruppen können nur in einer Entwurfs-Bestellung verwaltet werden."`

- **VAL-04:** Gruppen-`name` je Order — `name` muss innerhalb derselben Order eindeutig sein (case-insensitive Vergleich) — `"Eine Gruppe mit diesem Namen existiert bereits in der Bestellung."`

- **VAL-05:** Gruppen-Löschung — Gruppe muss leer sein (keine zugewiesenen Items) — `"Die Gruppe enthält noch Bestellpositionen und kann nicht gelöscht werden."`

- **VAL-06:** Anzahl Gruppen — Max. 20 Gruppen pro Order — `"Eine Bestellung kann maximal 20 Gruppen enthalten."`

- **VAL-07:** `group_id` beim Item-Update — Wenn `group_id` angegeben, muss die Gruppe zur selben Order gehören — `"Die angegebene Gruppe gehört nicht zu dieser Bestellung."`

- **VAL-08:** `position` (Gruppen-Neuordnung) — Alle `position`-Werte müssen eindeutig und lückenlos von 1 bis n sein — `"Die Reihenfolge der Gruppen ist ungültig (Werte müssen 1 bis n, lückenlos und eindeutig sein)."`

---

### API Contract

**Endpoint 1: Create an order item group**
```
POST /api/v1/orders/{order_id}/groups

Authorization: Bearer <jwt>  // role: requester or admin

Path Parameters:
  order_id: string (UUID) — target order

Request Body:
{
  "name": "string",          // required, 2–100 chars
  "description": "string"    // optional, max 500 chars
}

Response 201 Created:
{
  "id": "uuid",
  "order_id": "uuid",
  "name": "string",
  "description": "string | null",
  "position": 1,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}

Response 400 Bad Request:
{
  "error": "validation_error",
  "violations": [
    { "field": "name", "message": "string" }
  ]
}

Response 403 Forbidden:
{ "error": "forbidden", "message": "string" }

Response 404 Not Found:
{ "error": "not_found", "message": "Order not found." }

Response 409 Conflict:
{ "error": "conflict", "message": "A group with this name already exists in this order." }

Response 422 Unprocessable Entity:
{ "error": "order_not_editable", "message": "Groups can only be managed in draft orders." }
```

---

**Endpoint 2: Update an order item group**
```
PATCH /api/v1/orders/{order_id}/groups/{group_id}

Authorization: Bearer <jwt>  // role: requester or admin

Path Parameters:
  order_id: string (UUID)
  group_id: string (UUID)

Request Body (all fields optional, send only fields to change):
{
  "name": "string",
  "description": "string | null"
}

Response 200 OK:
{
  "id": "uuid",
  "order_id": "uuid",
  "name": "string",
  "description": "string | null",
  "position": 2,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}

Response 400 Bad Request:
{ "error": "validation_error", "violations": [...] }

Response 403 Forbidden:
{ "error": "forbidden" }

Response 404 Not Found:
{ "error": "not_found", "message": "Group not found." }

Response 409 Conflict:
{ "error": "conflict", "message": "A group with this name already exists in this order." }

Response 422 Unprocessable Entity:
{ "error": "order_not_editable", "message": "Groups can only be managed in draft orders." }
```

---

**Endpoint 3: Delete an order item group**
```
DELETE /api/v1/orders/{order_id}/groups/{group_id}

Authorization: Bearer <jwt>  // role: requester or admin

Response 204 No Content

Response 403 Forbidden:
{ "error": "forbidden" }

Response 404 Not Found:
{ "error": "not_found", "message": "Group not found." }

Response 409 Conflict:
{ "error": "group_not_empty", "message": "Group still contains order items. Remove or reassign items first." }

Response 422 Unprocessable Entity:
{ "error": "order_not_editable", "message": "Groups can only be managed in draft orders." }
```

---

**Endpoint 4: Reorder groups within an order**
```
PUT /api/v1/orders/{order_id}/groups/reorder

Authorization: Bearer <jwt>  // role: requester or admin

Request Body:
{
  "order": [
    { "group_id": "uuid", "position": 1 },
    { "group_id": "uuid", "position": 2 }
  ]
}
// Must include ALL groups of the order. Positions must be 1..n, unique, gap-free.

Response 200 OK:
{
  "groups": [
    { "id": "uuid", "position": 1 },
    { "id": "uuid", "position": 2 }
  ]
}

Response 400 Bad Request:
{ "error": "validation_error", "message": "Positions must be 1..n, unique and gap-free." }

Response 422 Unprocessable Entity:
{ "error": "order_not_editable" }
```

---

**Endpoint 5: Assign or unassign an item to/from a group**
```
PATCH /api/v1/orders/{order_id}/items/{item_id}

// This uses the existing item-update endpoint (Endpoint 49 in order-lifecycle.md).
// New field added to the request body:

Request Body (partial, only new field shown):
{
  "group_id": "uuid | null"   // null to unassign from any group
}

// Response unchanged from Endpoint 49.
// No new endpoint required; group assignment is an item property.
```

---

**Endpoint 6: Get order with groups (extended response)**
```
GET /api/v1/orders/{order_id}

// This extends the existing Endpoint 46 (order-lifecycle.md) response.
// New fields in the response body:

Response 200 OK (extension):
{
  // ... all existing order fields ...
  "groups": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string | null",
      "position": 1,
      "items": [
        { /* full OrderItem object, see order-lifecycle.md */ }
      ],
      "group_validation_state": "valid | invalid | unchecked"
                              // valid   = all items valid
                              // invalid = at least one item invalid
                              // unchecked = at least one item unchecked, none invalid
    }
  ],
  "ungrouped_items": [
    { /* full OrderItem objects with group_id = null */ }
  ]
}
```

---

### Edge Cases

- **EC-01:** Gruppe wird angelegt, dann werden alle Items aus der Gruppe entfernt, dann wird die Order submitted. → Leere Gruppen sind erlaubt beim Submit; sie erzeugen keine Dispatch-Events und erscheinen im JSON-Export als leere Sektion. Die Validation prüft nur Items, nicht ob Gruppen gefüllt sind.

- **EC-02:** Zwei gleichzeitige Requests erstellen eine Gruppe mit demselben `name` in derselben Order (Race Condition). → Das System muss auf Datenbankebene eine Unique-Constraint auf `(order_id, lower(name))` enforzen. Einer der Requests erhält HTTP 409.

- **EC-03:** Item-`position`-Werte innerhalb einer Gruppe überschneiden sich mit Item-`position`-Werten einer anderen Gruppe oder ungruppierten Items. → `position` ist order-weit eindeutig (nicht nur innerhalb der Gruppe). Die bestehende Logik aus REQ-135 (order-lifecycle.md) gilt weiterhin.

- **EC-04:** Eine Gruppe wird gelöscht, während gleichzeitig ein Request ein Item dieser Gruppe bearbeitet. → Item-Bearbeitung gelingt; `group_id` des Items zeigt dann auf eine nicht mehr existente Gruppe. Das System muss dies beim Laden der Order erkennen und `group_id` des betroffenen Items auf `null` setzen (Cleanup-Logik beim GET).

- **EC-05:** `group_id` beim Hinzufügen eines Items zeigt auf eine Gruppe einer anderen Order. → HTTP 400 mit VAL-07. Das System validiert, dass Gruppe und Item zur selben Order gehören.

- **EC-06:** Order wird von `draft` nach `validated` überführt, enthält eine Gruppe mit mindestens einem invaliden Item. → Validation schlägt fehl. Die Response enthält die Validierungsfehler je Item; die Gruppe ist als Kontext angegeben (`group_id` im Fehler-Objekt). Der Order-Status verbleibt bei `draft`.

- **EC-07:** Der Requester versucht, die Gruppenreihenfolge neu zu sortieren (Endpoint 4), sendet aber nicht alle Gruppen der Order. → HTTP 400: "Reorder request must include all groups of the order."

---

## Feature 11.2: Quantity — Skalierung identischer Server

### User Story

Als Requester möchte ich bei der Bestellung eines Services eine Anzahl (Quantity) angeben können, damit ich N identisch konfigurierte Instanzen eines Services in einer einzigen Bestellposition erfassen kann, ohne jede Instanz separat anlegen zu müssen.

---

### Requirements

- **REQ-14:** Ein Requester kann beim Hinzufügen oder Bearbeiten eines OrderItems den Wert `quantity` setzen. Der Default ist `1`. Gültige Werte sind ganzzahlig von 1 bis 50 (inkl.).

- **REQ-15:** Ein OrderItem mit `quantity = 1` verhält sich in allen Aspekten identisch wie ein bisheriges OrderItem. Keine bestehende Logik ändert sich.

- **REQ-16:** Wird `quantity` auf einen Wert > 1 gesetzt, prüft das System, ob das referenzierte ServiceTemplate mindestens einen Parameter mit `per_instance = "auto"` oder `per_instance = true` enthält. Existiert kein einziger solcher Parameter, wird `quantity > 1` abgelehnt, da alle Instanzen vollständig identisch wären (inklusive Hostname und IP), was einen Konfigurationskonflikt erzeugen würde.

- **REQ-17:** Beim Ändern von `quantity` auf einem bestehenden Item wird das `instance_parameters`-Array automatisch angepasst: Wird `quantity` erhöht, werden neue leere `InstanceParameterSet`-Einträge angehängt. Wird `quantity` verringert, werden überschüssige Einträge (von hinten) entfernt. Die verbleibenden Einträge werden nicht verändert.

- **REQ-18:** Die Validation (Feature 3.2) prüft bei `quantity > 1`, ob alle manuell zu befüllenden per-instance Parameter (`per_instance = true`) für jede Instanz einen Wert enthalten. Fehlende Werte erzeugen Validierungsfehler mit `instance_index` im Fehler-Objekt.

- **REQ-19:** Beim Order-Submit (Feature 3.3) expandiert das System ein OrderItem mit `quantity = N` in N separate interne Dispatch-Events. Jedes Event erhält:
  - Die Shared-Parameter des Items (identisch für alle Instanzen)
  - Die instanzspezifischen Parameter aus `instance_parameters[i]` (falls vorhanden)
  - Die auto-generierten Parameter (werden zum Submit-Zeitpunkt erzeugt, s. REQ-20)
  - Eine neue, eindeutige `instance_id` (UUID, serverseitig generiert) als zusätzliches Feld im Event

- **REQ-20:** Zum Submit-Zeitpunkt generiert das System für jeden Parameter mit `per_instance = "auto"` je Instanz den Wert:
  - Strategie `hostname_sequence`: Alle N Hostnamen werden als atomarer Batch aus der Sequenz reserviert. Der Prefix stammt aus dem Parameter `hostname_prefix` des Items (shared) oder, falls nicht vorhanden, aus `template_slug` (die ersten 8 Zeichen, Sonderzeichen durch `-` ersetzt). Das Format ist `<prefix>-<NNN>` mit dreistelliger, nullgefüllter laufende Nummer. Die Sequenz ist global pro Prefix; Kollisionen mit bereits vergebenen Hostnamen werden durch Überspringen der Sequenz vermieden.
  - Strategie `ipam_reservation`: N IPs werden sequenziell via IPAM reserviert (Feature 4.4). Schlägt eine Reservierung fehl, werden bereits reservierte IPs dieses Batches zurückgerollt und der Submit schlägt fehl.

- **REQ-21:** Die auto-generierten Werte werden nach erfolgreicher Generierung im OrderItem persistiert — in einem neuen Feld `generated_parameters` (JSONB, Array der Länge = quantity, analog `instance_parameters`, aber read-only). Sie sind nach dem Submit nicht mehr änderbar.

- **REQ-22:** Im Approval-Workflow (Feature-Gruppe 8) wird die geschätzte Gesamtkosten einer Order berechnet als Summe aller Items, wobei jedes Item mit `quantity > 1` N-fach gewichtet wird: `item_cost = template.estimated_cost_eur_per_month × quantity`. Die bestehende Approval-Schwellwert-Logik (REQ-01 in approval-workflow.md) erhält damit die korrekte Kostenbasis.

- **REQ-23:** Im JSON-Export (Feature 3.4) erzeugt ein Item mit `quantity = N` genau N separate Tofu-Blöcke. Jeder Block enthält den vollständigen Parameter-Satz der jeweiligen Instanz (shared + per-instance + generated). Die Blöcke werden durch einen Kommentar `# Instance <i+1> of <N> — <hostname>` getrennt.

- **REQ-24:** Der Provisioning-Status wird pro Instanz (nicht pro Item) getrackt. Jedes Dispatch-Event erhält ein eigenständiges Provisioning-Tracking. Der Item-Status aggregiert: `done` wenn alle Instanzen `done`, `failed` wenn alle Instanzen `failed`, sonst `provisioning`. Schlägt mindestens eine Instanz fehl, aber nicht alle, ist der Item-Status `partial_failure`.

- **REQ-25:** Bei Quantity-Änderung auf einem Item, das bereits validiert war (`validation_state = valid`), wird `validation_state` auf `unchecked` zurückgesetzt. Der Order-Status wird auf `draft` zurückgesetzt, falls er `validated` war.

---

### Validation Rules

- **VAL-09:** `quantity` — Ganzzahl, Min: 1, Max: 50 — `"Die Anzahl muss eine ganze Zahl zwischen 1 und 50 sein."`

- **VAL-10:** `quantity > 1` ohne per-instance Parameter — Template muss mindestens einen Parameter mit `per_instance = true` oder `per_instance = "auto"` enthalten — `"Dieses Service-Template unterstützt keine Mengenbestellung, da alle Parameter identisch wären (kein per-instance Parameter definiert)."`

- **VAL-11:** `instance_parameters` Array-Länge — Muss exakt gleich `quantity` sein — `"Das Array der instanzspezifischen Parameter muss genau so viele Einträge enthalten wie die bestellte Menge (quantity)."`

- **VAL-12:** `instance_parameters[i].instance_index` — Muss dem Index i entsprechen (0-basiert, lückenlos von 0 bis quantity-1) — `"Die Instanz-Indizes müssen lückenlos von 0 bis quantity-1 sein."`

- **VAL-13:** Per-instance Parameter bei Validation — Alle Parameter mit `per_instance = true` müssen in jedem `instance_parameters[i].parameters`-Objekt einen nicht-null-Wert haben — `"Instanz <i+1>: Der Parameter '<key>' muss für jede Instanz individuell angegeben werden."`

- **VAL-14:** Shared Parameter bei Quantity > 1 — Parameter mit `per_instance = false` dürfen nicht in `instance_parameters[i].parameters` vorkommen; sie werden aus dem Item-Level `parameters`-Objekt gelesen — `"Der Parameter '<key>' ist ein geteilter Parameter und darf nicht instanzspezifisch gesetzt werden."`

- **VAL-15:** Auto-generierte Parameter bei Quantity > 1 — Parameter mit `per_instance = "auto"` dürfen weder in `parameters` noch in `instance_parameters` vorkommen; sie werden serverseitig generiert — `"Der Parameter '<key>' wird automatisch vergeben und darf nicht manuell gesetzt werden."`

- **VAL-16:** `quantity`-Änderung auf submittierten Items — `quantity` kann nur im Status `draft` geändert werden — `"Die Menge kann nur in einer Entwurfs-Bestellung geändert werden."`

---

### API Contract

**Endpoint 7: Add an order item with quantity (extends Endpoint 48 in order-lifecycle.md)**
```
POST /api/v1/orders/{order_id}/items

Authorization: Bearer <jwt>  // role: requester or admin

Request Body (full, with new fields):
{
  "template_slug": "string",         // required
  "template_version": "string",      // required, SemVer
  "parameters": {                    // required; shared parameters only (per_instance=false)
    "<param_key>": "<value>"
  },
  "group_id": "uuid | null",         // optional, default null
  "quantity": 2,                     // optional, default 1; integer 1–50
  "instance_parameters": [           // required when quantity > 1 AND template has per_instance=true params
    {                                // omit entirely when quantity = 1 or no per_instance=true params
      "instance_index": 0,
      "parameters": {
        "<per_instance_param_key>": "<value>"
      }
    },
    {
      "instance_index": 1,
      "parameters": {
        "<per_instance_param_key>": "<value>"
      }
    }
  ]
}

Response 201 Created:
{
  "id": "uuid",
  "order_id": "uuid",
  "template_slug": "string",
  "template_version": "string",
  "display_name": "string",
  "parameters": { "<key>": "<value>" },
  "group_id": "uuid | null",
  "quantity": 2,
  "instance_parameters": [
    { "instance_index": 0, "parameters": { "<key>": "<value>" } },
    { "instance_index": 1, "parameters": { "<key>": "<value>" } }
  ],
  "generated_parameters": null,       // null until submit
  "position": 3,
  "validation_state": "unchecked",
  "validation_errors": [],
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}

Response 400 Bad Request:
{
  "error": "validation_error",
  "violations": [
    {
      "field": "instance_parameters[1].parameters.hostname",
      "instance_index": 1,
      "message": "string"
    }
  ]
}

Response 403 Forbidden:
{ "error": "forbidden" }

Response 404 Not Found:
{ "error": "not_found", "message": "Order or template not found." }

Response 422 Unprocessable Entity:
{ "error": "order_not_editable" }
```

---

**Endpoint 8: Update quantity on an existing order item**
```
PATCH /api/v1/orders/{order_id}/items/{item_id}

// Extends Endpoint 49 (order-lifecycle.md). New fields:

Request Body (partial):
{
  "quantity": 3,
  "instance_parameters": [ ... ]   // optional; server adjusts array size automatically
}

Response 200 OK:
{
  // ... full OrderItem as in Endpoint 7 response ...
  "quantity": 3,
  "instance_parameters": [
    { "instance_index": 0, "parameters": { ... } },
    { "instance_index": 1, "parameters": { ... } },
    { "instance_index": 2, "parameters": {} }    // new entry, empty — must be filled before validation
  ]
}

Response 400, 403, 404, 422: same as Endpoint 7
```

---

**Endpoint 9: Get provisioning status per instance**
```
GET /api/v1/orders/{order_id}/items/{item_id}/instances

Authorization: Bearer <jwt>  // role: requester or admin

Response 200 OK:
{
  "item_id": "uuid",
  "quantity": 3,
  "item_status": "provisioning | done | failed | partial_failure",
  "instances": [
    {
      "instance_index": 0,
      "instance_id": "uuid",       // generated at submit
      "hostname": "web-srv-001",   // from generated_parameters
      "ip_address": "10.0.1.5",   // from generated_parameters
      "provisioning_status": "done | failed | provisioning | pending",
      "job_id": "string | null",
      "error_message": "string | null"
    }
  ]
}

Response 403 Forbidden: { "error": "forbidden" }
Response 404 Not Found: { "error": "not_found" }
```

---

### Edge Cases

- **EC-08:** Requester setzt `quantity = 5`, füllt aber nur 4 `InstanceParameterSet`-Einträge. → HTTP 400 mit VAL-11. Das Array muss genau 5 Einträge haben.

- **EC-09:** Hostname-Sequenz-Reservierung schlägt bei Instanz 3 von 5 fehl (z.B. Sequenz-Overflow oder Datenbankfehler). → Der gesamte Submit-Vorgang wird abgebrochen. Alle bereits reservierten Hostnamen dieses Batches werden freigegeben. Der Order-Status verbleibt bei `validated`. Die Fehlermeldung enthält den Hinweis "Hostname-Generierung fehlgeschlagen; bitte erneut versuchen."

- **EC-10:** IPAM-Reservierung gelingt für IP 1 und IP 2, schlägt für IP 3 fehl (keine freien IPs im Subnetz). → Bereits reservierte IPs dieses Batches (1 und 2) werden freigegeben. Submit schlägt fehl. Fehlermeldung: "Nicht genügend freie IP-Adressen im konfigurierten Subnetz für <N> Instanzen."

- **EC-11:** Requester ändert `quantity` von 3 auf 2, nachdem er alle 3 InstanceParameterSets gefüllt hat. → Der dritte Eintrag (`instance_index = 2`) wird serverseitig entfernt. Die verbleibenden Einträge 0 und 1 bleiben unverändert.

- **EC-12:** `quantity` wird auf 1 gesetzt, `instance_parameters` wird als leeres Array oder `null` gesendet. → Beide Varianten werden akzeptiert. Das System normalisiert auf `instance_parameters = []`.

- **EC-13:** Zwei gleichzeitige Submit-Requests für dieselbe Order (Race Condition). → Idempotenz-Schutz (Feature 4.7) greift. Hostname- und IP-Reservierungen dürfen nicht doppelt erfolgen. Der zweite Request erhält HTTP 409 "Order already submitted."

- **EC-14:** Das ServiceTemplate wird nach Item-Erstellung deprecatiert und die neue Version fügt einen Parameter mit `per_instance = "auto"` hinzu. Das bestehende Item referenziert die alte Version (ohne diesen Parameter). → Das Item wird mit dem Template-Snapshot zum Erstellungszeitpunkt validiert. Die neue `per_instance`-Definition der neuen Version hat keinen Einfluss auf das bestehende Item.

- **EC-15:** `quantity = 50` (Maximum) für ein Template, das keine IPAM-Pflicht hat. → Erlaubt. Nur Hostnamen werden generiert. Kein IPAM-Call.

- **EC-16:** Item mit `quantity = 3` in einer Gruppe: Eine Instanz schlägt beim Provisioning fehl, zwei sind `done`. → Item-Status = `partial_failure`. Gruppen-Aggregat = `partial_failure` (nicht `failed`). Order-Status = `partial_failure` (s. REQ-24). Der Requester kann das fehlgeschlagene Item gezielt neu anstoßen (sofern Retry-Logik in Feature 4.6 unterstützt).

---

## Feature 11.3: Per-Instance-Parameter — Instanzspezifische Konfiguration

### User Story

Als Template-Administrator möchte ich für jeden Parameter eines ServiceTemplates festlegen, ob er bei Mengenbestellungen geteilt (shared), manuell pro Instanz gesetzt (unique) oder automatisch generiert (auto) wird, damit die Provisionierung instanzspezifische Werte (Hostname, IP) korrekt und kollisionsfrei vergibt.

### User Story (Requester-Perspektive)

Als Requester möchte ich bei einer Mengenbestellung sofort sehen, welche Parameter ich pro Instanz ausfüllen muss und welche automatisch vergeben werden, damit ich den Bestellvorgang zügig abschließen kann ohne Informationen doppelt einzugeben.

---

### Requirements

- **REQ-26:** Beim Erstellen oder Bearbeiten eines ServiceTemplates (Feature 2.1) kann ein Template-Administrator für jeden Parameter das Feld `per_instance` setzen. Gültige Werte: `false` (Default), `true`, `"auto"`. Fehlt das Feld, gilt `false`.

- **REQ-27:** Der Wert `"auto"` ist nur für Parameter mit `type = "string"` zulässig. Parameter vom Typ `integer`, `float`, `boolean`, `enum`, `range_integer`, `range_float`, `size_bytes` dürfen nicht `per_instance = "auto"` tragen.

- **REQ-28:** Das System erkennt genau zwei semantische Rollen für `per_instance = "auto"`:
  - Schlüssel `hostname` (oder Parameter mit `tofu_variable_name = "hostname"`): Strategie `hostname_sequence`
  - Schlüssel `ip_address` (oder Parameter mit `tofu_variable_name = "ip_address"`): Strategie `ipam_reservation`
  - Jeder andere Parameter mit `per_instance = "auto"` wird als `hostname_sequence`-Typ behandelt und erhält denselben Prefix-Mechanismus wie Hostnamen. Template-Administratoren werden beim Anlegen solcher Parameter mit einem Warning informiert.

- **REQ-29:** Ein Template kann maximal einen Parameter mit Strategie `hostname_sequence` und maximal einen mit Strategie `ipam_reservation` enthalten. Das System prüft diese Einschränkung beim Template-Speichern.

- **REQ-30:** Beim Abrufen eines ServiceTemplates (Catalog-Endpoint 37/38, service-catalog.md) wird das `per_instance`-Feld je Parameter mitgeliefert. Die Werte sind für das Frontend bindend für die Darstellung des Bestellformulars (shared-Feld / manuell pro Instanz / "wird automatisch vergeben").

- **REQ-31:** Das Frontend (UI-Anforderung, als REQ für das API dokumentiert) muss über einen dedizierten Endpoint abfragen können, wie ein Item mit einer bestimmten Quantity aussehen würde — also welche Parameter shared, manuell und auto sind. Dieser Endpoint liefert die aufgelöste Parameterstruktur für eine gegebene Kombination aus `template_slug`, `template_version` und `quantity`.

- **REQ-32:** Die Validation (Feature 3.2) unterscheidet bei der Parameter-Prüfung zwischen drei Klassen:
  - Shared-Parameter (`per_instance = false`): werden aus `OrderItem.parameters` gelesen und einmal validiert.
  - Per-instance Parameter (`per_instance = true`): werden aus `instance_parameters[i].parameters` gelesen und N-mal validiert (einmal je Instanz).
  - Auto-Parameter (`per_instance = "auto"`): werden nicht validiert (noch nicht gesetzt); nach Submit aus `generated_parameters` gelesen.

- **REQ-33:** Auto-generierte Werte (`generated_parameters`) sind nach dem Submit read-only. Sie können nicht durch den Requester oder Admin geändert werden. Eine Nachbestellung (Re-Submit, falls implementiert) würde neue Werte generieren.

- **REQ-34:** Im Dispatch-Event (REQ-44 in provisioning-engine.md) enthält `parameters` den vollständig aufgelösten Parameter-Satz der jeweiligen Instanz:
  - Shared-Parameter aus `OrderItem.parameters`
  - Per-instance Parameter aus `instance_parameters[i].parameters`
  - Auto-generierte Parameter aus `generated_parameters[i]`
  Alle drei Klassen werden flach gemergt. Im Falle von Key-Konflikten (theoretisch nicht möglich bei korrektem Template-Design, aber als Safety) gewinnen auto-generierte Werte.

- **REQ-35:** Bei `quantity = 1` gibt es kein `instance_parameters`-Array. Alle Parameter (inklusive solcher mit `per_instance = true`) werden aus `OrderItem.parameters` gelesen. `per_instance = "auto"` Parameter werden auch bei `quantity = 1` auto-generiert (1 Hostname, 1 IP).

- **REQ-36:** Template-Administratoren können `per_instance` eines Parameters nachträglich ändern, wenn das Template den Status `draft` hat. Sobald das Template `active` ist, ist `per_instance` unveränderlich (wie alle anderen Parameter-Definitionen; analog zur Template-Unveränderlichkeit in Feature 2.1). Eine Änderung erfordert eine neue Template-Version.

- **REQ-37:** Das System persistiert den `per_instance`-Wert als Teil des unveränderlichen Template-Snapshots im OrderItem. Spätere Template-Änderungen beeinflussen bestehende Items nicht.

---

### Validation Rules

- **VAL-17:** `per_instance` (ParameterDefinition) — Zulässige Werte: `false`, `true`, `"auto"` — `"Der Wert für 'per_instance' muss false, true oder 'auto' sein."`

- **VAL-18:** `per_instance = "auto"` — Nur für Parameter mit `type = "string"` — `"Der Wert 'auto' für 'per_instance' ist nur für Parameter vom Typ 'string' zulässig."`

- **VAL-19:** Maximale auto-Parameter pro Template — Max. 1 Parameter mit Strategie `hostname_sequence`, max. 1 mit Strategie `ipam_reservation` — `"Ein Template darf maximal einen Hostname- und einen IP-Parameter mit per_instance='auto' enthalten."`

- **VAL-20:** Hostname-Parameter Pflichtformat — Parameter mit `tofu_variable_name = "hostname"` und `per_instance = "auto"` muss vorhanden sein, wenn `quantity > 1` und das Template vom Typ `vm` oder `container` ist — `"VM- und Container-Templates mit Quantity > 1 müssen einen auto-generierten Hostname-Parameter enthalten."`

- **VAL-21:** `hostname_prefix` Shared-Parameter — Wenn ein `hostname_sequence`-Parameter existiert, muss das Template einen shared Parameter mit `key = "hostname_prefix"` definieren oder der Prefix wird aus `template_slug` abgeleitet. Der Prefix darf maximal 12 Zeichen lang sein (damit `<prefix>-NNN` <= 16 Zeichen). — `"Der Hostname-Prefix darf maximal 12 Zeichen enthalten."`

- **VAL-22:** Shared-Parameter dürfen nicht in `instance_parameters` gesetzt werden (VAL-14 redundant aufgeführt als Cross-Reference) — `"Der Parameter '<key>' ist als 'shared' definiert und kann nicht pro Instanz überschrieben werden."`

- **VAL-23:** Auto-Parameter dürfen nicht in `parameters` oder `instance_parameters` vorkommen (VAL-15 redundant aufgeführt als Cross-Reference) — `"Der Parameter '<key>' wird automatisch generiert und kann nicht manuell gesetzt werden."`

- **VAL-24:** Per-instance Parameter bei `quantity = 1` — Wenn `quantity = 1`, werden per-instance Parameter (`per_instance = true`) aus `parameters` (flat) gelesen. Fehlende required per-instance Parameter erzeugen Validierungsfehler ohne `instance_index`. — `"Der Parameter '<key>' ist erforderlich."`

- **VAL-25:** `per_instance`-Änderung auf aktivem Template — Nicht zulässig; erfordert neue Template-Version — `"Parameter-Definitionen können bei aktiven Templates nicht geändert werden. Bitte eine neue Template-Version anlegen."`

---

### API Contract

**Endpoint 10: Get resolved parameter structure for a given template + quantity**
```
GET /api/v1/service-templates/{slug}/versions/{version}/parameter-layout

Authorization: Bearer <jwt>  // role: requester or admin

Query Parameters:
  quantity: integer  // required; 1–50

Response 200 OK:
{
  "template_slug": "string",
  "template_version": "string",
  "quantity": 3,
  "shared_parameters": [
    {
      "key": "cpu_cores",
      "label": "CPU Cores",
      "type": "integer",
      "required": true,
      "per_instance": false
    }
  ],
  "per_instance_parameters": [
    {
      "key": "custom_tag",
      "label": "Custom Tag",
      "type": "string",
      "required": false,
      "per_instance": true
    }
  ],
  "auto_parameters": [
    {
      "key": "hostname",
      "label": "Hostname",
      "type": "string",
      "per_instance": "auto",
      "strategy": "hostname_sequence",
      "preview": ["web-srv-001", "web-srv-002", "web-srv-003"]
                 // preview is a best-effort sequence; actual values assigned at submit
    },
    {
      "key": "ip_address",
      "label": "IP-Adresse",
      "type": "string",
      "per_instance": "auto",
      "strategy": "ipam_reservation",
      "preview": null   // IPAM allocation not known before submit
    }
  ]
}

Response 400 Bad Request:
{ "error": "validation_error", "message": "quantity must be between 1 and 50." }

Response 404 Not Found:
{ "error": "not_found", "message": "Template or version not found." }
```

---

**Endpoint 11: Add per_instance field to ParameterDefinition (extends Template Create/Update)**
```
POST /api/v1/service-templates         // extends Endpoint 39 (service-catalog.md)
PATCH /api/v1/service-templates/{id}   // extends Endpoint 40 (service-catalog.md)

// New field in ParameterDefinition within the request body:

Request Body (ParameterDefinition, partial):
{
  "parameters": [
    {
      "key": "hostname",
      "label": "Hostname",
      "type": "string",
      "required": true,
      "tofu_variable_name": "hostname",
      "per_instance": "auto"           // NEW; default: false if omitted
    }
  ]
}

Response: unchanged from Endpoint 39/40.
// If per_instance = "auto" on a non-string type:
Response 400 Bad Request:
{ "error": "validation_error", "violations": [{ "field": "parameters[0].per_instance", "message": "..." }] }
```

---

**Endpoint 12: Get template with per_instance fields (extends Endpoint 38)**
```
GET /api/v1/service-templates/{slug}/versions/{version}

// Response extended: each parameter now includes per_instance field.

Response 200 OK (ParameterDefinition, partial):
{
  "parameters": [
    {
      "key": "cpu_cores",
      "label": "CPU Cores",
      "type": "integer",
      "per_instance": false
    },
    {
      "key": "hostname",
      "label": "Hostname",
      "type": "string",
      "per_instance": "auto"
    }
  ]
}
```

---

**Endpoint 13: Validate order item parameters including per-instance (extends Endpoint 43)**
```
POST /api/v1/orders/{order_id}/items/{item_id}/validate

// Extends Endpoint 43 (service-catalog.md / order-lifecycle.md).
// Validation now covers all three parameter classes.

Request Body (partial, new fields):
{
  "quantity": 2,
  "instance_parameters": [
    { "instance_index": 0, "parameters": { "custom_tag": "prod-a" } },
    { "instance_index": 1, "parameters": { "custom_tag": "prod-b" } }
  ]
}

Response 200 OK (always HTTP 200, violations in body):
{
  "valid": false,
  "violations": [
    {
      "parameter_key": "custom_tag",
      "instance_index": 1,           // NEW: present only for per-instance violations
      "rule": "required",
      "message": "Instanz 2: Der Parameter 'custom_tag' muss für jede Instanz angegeben werden."
    }
  ]
}
```

---

**Endpoint 14: Get generated parameters for a submitted item**
```
GET /api/v1/orders/{order_id}/items/{item_id}/generated-parameters

Authorization: Bearer <jwt>  // role: requester or admin

Response 200 OK:
{
  "item_id": "uuid",
  "quantity": 3,
  "generated_parameters": [
    {
      "instance_index": 0,
      "parameters": {
        "hostname": "web-srv-001",
        "ip_address": "10.0.1.5"
      }
    },
    {
      "instance_index": 1,
      "parameters": {
        "hostname": "web-srv-002",
        "ip_address": "10.0.1.6"
      }
    },
    {
      "instance_index": 2,
      "parameters": {
        "hostname": "web-srv-003",
        "ip_address": "10.0.1.7"
      }
    }
  ]
}

Response 404 Not Found: { "error": "not_found" }
Response 422 Unprocessable Entity:
{ "error": "not_submitted", "message": "Generated parameters are only available after order submit." }
```

---

**Endpoint 15: JSON Export with quantity expansion (extends Endpoint 64 in order-lifecycle.md)**
```
GET /api/v1/orders/{order_id}/export/json

// Response extended: items with quantity > 1 are expanded to N blocks.

Response 200 OK (partial, illustrative structure):
{
  "order_number": "ORD-2026-00042",
  "export_blocks": [
    {
      "group_name": "Web-Cluster",          // null for ungrouped items
      "item_id": "uuid",
      "template_slug": "linux-vm",
      "template_version": "1.2.0",
      "quantity": 3,
      "instances": [
        {
          "instance_index": 0,
          "instance_id": "uuid",
          "comment": "Instance 1 of 3 — web-srv-001",
          "tofu_variables": {
            "TF_VAR_cpu_cores": "4",
            "TF_VAR_ram_gb": "16",
            "TF_VAR_os": "ubuntu-22.04",
            "TF_VAR_hostname": "web-srv-001",
            "TF_VAR_ip_address": "10.0.1.5"
          }
        }
      ]
    }
  ]
}
```

---

**Endpoint 16: SSE — Provisioning status update with instance granularity**
```
GET /api/v1/orders/{order_id}/status-stream

// Extends existing SSE endpoint (order-lifecycle.md / provisioning-engine.md).
// New event types for instance-level updates:

Event: item_instance_status_changed
Data:
{
  "event": "item_instance_status_changed",
  "order_id": "uuid",
  "item_id": "uuid",
  "instance_index": 1,
  "instance_id": "uuid",
  "hostname": "web-srv-002",
  "provisioning_status": "done | failed | provisioning",
  "timestamp": "ISO-8601"
}

Event: item_status_changed (extended)
Data:
{
  "event": "item_status_changed",
  "order_id": "uuid",
  "item_id": "uuid",
  "item_status": "provisioning | done | failed | partial_failure",
  "instances_done": 2,
  "instances_total": 3,
  "timestamp": "ISO-8601"
}
```

---

**Endpoint 17: Admin — Get hostname sequence status**
```
GET /api/v1/admin/hostname-sequences

Authorization: Bearer <jwt>  // role: admin only

Response 200 OK:
{
  "sequences": [
    {
      "prefix": "web-srv",
      "last_issued": 3,
      "next_available": 4,
      "reserved_at": "ISO-8601"
    }
  ]
}
```

---

### Edge Cases

- **EC-17:** Template-Administrator setzt `per_instance = "auto"` auf einem Parameter mit `type = integer`. → HTTP 400 mit VAL-18. Nur `type = "string"` ist für auto zulässig.

- **EC-18:** Template-Administrator definiert zwei Parameter mit `per_instance = "auto"` und beide haben `tofu_variable_name = "hostname"`. → HTTP 400 mit VAL-19. Maximal ein hostname-Strategie-Parameter pro Template.

- **EC-19:** Requester fragt Endpoint 10 mit `quantity = 1` und einem Template ohne jegliche `per_instance`-Parameter ab. → Response enthält `per_instance_parameters = []` und `auto_parameters = []`, nur `shared_parameters`. Gültige Antwort.

- **EC-20:** `generated_parameters` werden abgerufen (Endpoint 14) für eine Order, die noch nicht submitted wurde. → HTTP 422 mit `"not_submitted"`.

- **EC-21:** Beim Submit wird ein Hostname generiert, der bereits in der Sequenz existiert (weil ein paralleler Submit denselben Prefix verwendet hat). → Das System überspringt die vergebenen Nummern und reserviert die nächsten freien Nummern. Die Hostname-Sequenz muss durch einen serialisierten Datenbankzugriff (z.B. SELECT FOR UPDATE oder SERIAL) Kollisionen ausschließen.

- **EC-22:** Requester bearbeitet ein Item und setzt einen `per_instance = "auto"` Parameter manuell in `parameters`. → HTTP 400 mit VAL-15 / VAL-23. Auto-Parameter dürfen nicht manuell gesetzt werden.

- **EC-23:** Template hat `per_instance = true` für einen Parameter, der `required = false` ist. Requester lässt diesen Parameter bei Instanz 2 leer. → Erlaubt. `required = false` bedeutet, der Wert kann leer bleiben — auch instanzspezifisch.

- **EC-24:** Template-Snapshot im OrderItem enthält `per_instance = false` für einen Parameter, das Template wurde seitdem auf Version 2.0 aktualisiert, die denselben Parameter mit `per_instance = true` definiert. Das Item verwendet weiterhin Version 1.x (Snapshot). → Item verwendet die Snapshot-Definition (`per_instance = false`). Der Parameter kommt aus `parameters`, nicht aus `instance_parameters`. Keine Validierungsfehler.

- **EC-25:** Beim Dispatch-Event-Merge (REQ-34) enthalten shared und per-instance denselben Key (z.B. durch Fehler im Template-Design). → Auto-generierte Werte gewinnen. Per-instance überschreibt shared. Der Incident wird ins System-Log geschrieben (WARN-Level) mit Order-ID und Item-ID.

---

## Auswirkungen auf bestehende Features

### Feature 3.2: Order Validation

- Die Validation muss `instance_parameters` prüfen wenn `quantity > 1`.
- Pro-Instanz-Fehler enthalten `instance_index` im `ValidationViolation`-Objekt (neues optionales Feld).
- Eine Order ist nur valide, wenn alle Items valide sind — unabhängig von Gruppenzugehörigkeit.
- Der Gruppen-`validation_state` ist ein abgeleitetes Aggregat, kein persistierter Wert.

### Feature 3.3: Order Submit

- Submit expandiert Items mit `quantity > 1` in N Dispatch-Events.
- Auto-Parameter werden zum Submit-Zeitpunkt atomar generiert (Hostname-Batch, IPAM-Batch).
- Schlägt die Auto-Generierung fehl, wird Submit abgebrochen; Order verbleibt in `validated`.
- Das Dispatch-Event-Format (REQ-44 in provisioning-engine.md) wird um `instance_id` und `instance_index` erweitert.

**Erweitertes Dispatch-Event-Format:**
```json
{
  "order_id": "uuid",
  "order_item_id": "uuid",
  "instance_id": "uuid",
  "instance_index": 0,
  "template_slug": "string",
  "template_version": "string",
  "parameters": { "<key>": "<value>" },
  "requester_id": "uuid",
  "group_id": "uuid | null",
  "group_name": "string | null"
}
```

### Feature 3.4: JSON Export

- Items mit `quantity > 1` erzeugen N Tofu-Blöcke.
- Gruppen-Sektionen werden als Kommentar-Header in den Export eingefügt.
- `instance_id` wird als Kommentar je Block geführt (Tracing).

### Feature 4.4: IPAM-Integration

- IP-Reservierung für `quantity > 1` erfolgt als Batch.
- Rollback bei Teil-Fehlern muss alle bisher reservierten IPs des Batches freigeben.
- IPAM-Integration erhält neuen optionalen Parameter `batch_size` beim Reservierungs-Call.

### Feature 4.6: Fehlerbehandlung & Rollback

- Neuer Item-Status `partial_failure`: Rollback wird nur für die fehlgeschlagene Instanz ausgelöst.
- Erfolgreiche Instanzen werden nicht zurückgerollt.
- Rollback pro Instanz folgt der bestehenden Rollback-Reihenfolge (Feature 4.6 REQ-87 ff.).

### Feature 8.1: Approval-Schwellwerte

- Kostenkalkulation: `item_cost = template.estimated_cost_eur_per_month × quantity`.
- Alle bestehenden Schwellwert-Regeln arbeiten auf der korrekten Gesamtkosten-Basis.

---

## Abhängigkeitsmatrix

| Feature 11 | Abhängig von | Auswirkung auf |
|---|---|---|
| 11.1 OrderItemGroup | 3.1 Order CRUD | Erweitert Order-Response, Item-Modell |
| 11.1 OrderItemGroup | 3.2 Validation | Gruppen-ValidationState als Aggregat |
| 11.1 OrderItemGroup | 3.4 JSON Export | Gruppen-Sektionen im Export |
| 11.2 Quantity | 3.3 Submit | Expand zu N Dispatch-Events |
| 11.2 Quantity | 4.4 IPAM | Batch-IP-Reservierung |
| 11.2 Quantity | 8.1 Approval | N-fache Kostenbasis |
| 11.3 Per-Instance-Parameter | 2.1 Service Catalog | ParameterDefinition-Erweiterung |
| 11.3 Per-Instance-Parameter | 4.1 Dispatcher | Erweitertes Dispatch-Event-Format |
| 11.3 Per-Instance-Parameter | 3.2 Validation | Instanzspezifische Validierung |

---

*Ende der Spezifikation — Feature-Gruppe 11, v1.0, 2026-03-26*
