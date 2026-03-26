# Feature-Gruppe 10: Kontextabhängige Bestellkonfiguration

**Version:** 1.0
**Datum:** 2026-03-26
**Status:** Draft

---

## Überblick

Diese Feature-Gruppe definiert das Modell, die Regeln und die API-Verträge für eine kontextabhängige Bestellkonfiguration. Der Kerngedanke: Bevor ein Requester einen Service auswählt, legt er seinen **Bestellkontext** fest (Standort, Mandant, Sicherheitsbereich). Dieser Kontext bestimmt dynamisch:

1. welche Services überhaupt angezeigt und bestellbar sind (Feature 10.3),
2. welche Parameterwerte in der Bestellmaske wählbar sind (Feature 10.2).

Die Kontextdaten (Standort-Liste, Netz-Liste etc.) stammen **ausschließlich aus der CMDB**. Das Portal speichert keine CMDB-Entitäten, sondern nur die **Regeln**, die auf Basis dieser Entitäten Einschränkungen definieren. Die Regeln sind über Admin-Endpoints administrierbar.

**Datenquellen:**
- Kontextdaten (Standorte, Netze, Mandanten, Sicherheitsbereiche): CMDB-API (`/api/v1/cmdb/...`, in Dev: CMDB-Stub aus Feature 9.3)
- Regeln (Availability-Regeln, Kontexteinschränkungen): Portal-Datenbank

**Abhängigkeiten zu anderen Feature-Gruppen:**

| Feature | Abhängigkeit |
|---------|-------------|
| Feature 2.1 (Service Catalog) | Context-Filtering erweitert den Catalog-Endpoint (Endpoint 37). Kontextparameter werden als zusätzliche Query-Parameter übergeben. |
| Feature 2.1 (DependencyRules) | Kontext-Einschränkungsregeln (Feature 10.2) werden nach Auflösung der Template-internen DependencyRules angewendet. Die Reihenfolge ist definiert: erst Template-Regeln, dann Kontext-Regeln. |
| Feature 3.1 (Order CRUD) | Der Bestellkontext wird als Pflichtbestandteil einer Order gespeichert und ist nach dem ersten Submit unveränderlich. |
| Feature 9.3 (CMDB-Stub) | Im Entwicklungsmodus liefert der CMDB-Stub die Kontextdaten. Die API-Contracts sind identisch. |

---

## Feature 10.1: Bestellkontext-Modell

### User Story

Als Requester möchte ich vor der Service-Auswahl meinen Bestellkontext (Standort, Mandant, Sicherheitsbereich, Netz) festlegen, damit mir nur Services und Konfigurationsoptionen angezeigt werden, die in meinem Kontext verfügbar und für mich berechtigt sind.

---

### Logisches Datenmodell

#### OrderContext

```
OrderContext {
  location_id:       string          // CMDB-ID des Standorts (z.B. "loc-berlin")
  tenant_id:         string          // CMDB-ID des Mandanten (z.B. "ten-corp")
  security_zone_id:  string          // CMDB-ID des Sicherheitsbereichs (z.B. "sz-medium")
  network_id:        string          // CMDB-ID des Netzes (z.B. "net-ber-dmz")
}
```

**Semantik:**
- `location_id`, `tenant_id` und `security_zone_id` sind Pflichtfelder für jeden Bestellkontext.
- `network_id` ist optional zum Zeitpunkt der Kontext-Auswahl; es kann service-spezifisch im Bestellformular ausgefüllt werden, sofern das Template einen Netz-Parameter enthält.
- Ein Bestellkontext ist kein eigenständiges persistiertes Objekt — er ist ein strukturierter Input-Block, der zur Kontextauflösung (Endpoints 2 und 3) und als Pflichtfeld einer Order (Feature 3.1) dient.
- Eine Order speichert den Kontext zum Zeitpunkt der Erstellung unveränderlich. Spätere Änderungen an CMDB-Daten wirken sich nicht auf bestehende Orders aus.

#### ResolvedContext

Ein `ResolvedContext` ist das Ergebnis der Kontext-Auflösung: Der Server reichert die vom Client gelieferten CMDB-IDs mit den aktuellen Klartext-Daten aus der CMDB an.

```
ResolvedContext {
  location: {
    id:     string
    name:   string
    code:   string
    region: string
  }
  tenant: {
    id:   string
    name: string
    code: string
  }
  security_zone: {
    id:          string
    name:        string
    level:       integer
    description: string
  }
  network: {             // optional, nur wenn network_id angegeben
    id:                string
    name:              string
    cidr:              string
    type:              string
    location_id:       string
    security_zone_id:  string
  } | null
  available_networks: Network[]  // alle Netze, die in location_id + security_zone_id verfügbar sind
}
```

---

### Ablauf: Kontext-Auswahl (Schritt 0 vor Service-Auswahl)

Der Bestellprozess beginnt mit einem expliziten Schritt vor der Service-Auswahl:

1. **Standort wählen** — Der User wählt aus der CMDB-Standortliste.
2. **Mandant wählen** — Der User wählt aus der CMDB-Mandantenliste. Nur Mandanten, für die der User berechtigt ist, werden angezeigt.
3. **Sicherheitsbereich wählen** — Der User wählt einen Sicherheitsbereich. Nur Sicherheitsbereiche, die am gewählten Standort verfügbar sind, werden angezeigt.
4. **Kontext auflösen** — Das Frontend ruft Endpoint 2 auf, um den Kontext zu validieren und die verfügbaren Netze zu laden.
5. **Service-Auswahl** — Der Service-Catalog wird mit dem Kontext gefiltert (Feature 10.3).

Netzauswahl erfolgt entweder im Kontext-Schritt (wenn standortweit eindeutig) oder später im Service-spezifischen Bestellformular.

---

### Requirements

- REQ-01: Das System MUSS einen Endpoint bereitstellen, der einen gegebenen OrderContext gegen die CMDB validiert und einen ResolvedContext zurückgibt.
- REQ-02: Ein OrderContext ist nur gültig, wenn alle angegebenen CMDB-IDs in der CMDB existieren und zueinander konsistent sind: `network_id` (wenn angegeben) muss zum angegebenen `location_id` gehören.
- REQ-03: Der Sicherheitsbereich (`security_zone_id`) muss am angegebenen Standort (`location_id`) verfügbar sein. Verfügbar bedeutet: mindestens ein Netz an diesem Standort hat diese `security_zone_id`.
- REQ-04: Das System MUSS die für einen Requester erlaubten Mandanten einschränken können. Die Zuordnung User → erlaubte Mandanten wird über eine Konfiguration im Portal verwaltet (nicht in der CMDB). Wenn keine Einschränkung konfiguriert ist, sind alle CMDB-Mandanten erlaubt.
- REQ-05: Das System MUSS die für einen Requester erlaubten Sicherheitsbereiche einschränken können. Die Einschränkung erfolgt über Tenant-Restrictions (Feature 10.2, REQ-19). Wenn keine Einschränkung definiert ist, sind alle Sicherheitsbereiche erlaubt.
- REQ-06: Der ResolvedContext MUSS die Liste aller am Standort + Sicherheitsbereich verfügbaren Netze enthalten (`available_networks`).
- REQ-07: Das System MUSS einen Endpoint bereitstellen, der die für einen gegebenen Kontext (location_id, security_zone_id) verfügbaren Netze zurückgibt. Dieser Endpoint delegiert an die CMDB-API (Endpoint 9 aus Feature 9.3) mit den entsprechenden Filtern.
- REQ-08: Eine Order MUSS einen vollständigen OrderContext enthalten (location_id, tenant_id, security_zone_id sind Pflicht). Das Fehlen eines dieser Felder verhindert die Order-Erstellung.
- REQ-09: Ein gespeicherter OrderContext in einer Order ist nach dem Übergang in den Status `submitted` unveränderlich. Im Status `draft` darf der Kontext geändert werden; eine Änderung invalidiert alle bereits konfigurierten Order-Items (die Parameter-Validierung muss erneut durchgeführt werden).
- REQ-10: Das System MUSS Mandantenberechtigungen pro User über einen Admin-Endpoint verwaltbar machen. Eine Zuordnung `user_id → [tenant_id, ...]` wird im Portal gespeichert. Wenn für einen User keine Zuordnung existiert, sind alle Mandanten erlaubt.
- REQ-11: Das System MUSS beim Auflösen eines Kontexts die CMDB live anfragen (kein permanenter Cache). Ein kurzlebiger Request-Scoped-Cache (max. 30 Sekunden) ist erlaubt, um CMDB-Anfragen innerhalb eines Checkout-Flows zu reduzieren.
- REQ-12: Wenn die CMDB nicht erreichbar ist, MUSS das System mit einem spezifischen Fehler antworten (`cmdb_unavailable`), der sich von einem Validierungsfehler unterscheidet. Der Bestellprozess wird blockiert, bis die CMDB wieder erreichbar ist.

---

### Validation Rules

- VAL-01: `location_id` — Pflichtfeld, darf nicht leer sein — Fehlermeldung: `"location_id is required"`
- VAL-02: `location_id` — Muss eine in der CMDB bekannte Location-ID sein — Fehlermeldung: `"Location '{id}' not found in CMDB"`
- VAL-03: `tenant_id` — Pflichtfeld, darf nicht leer sein — Fehlermeldung: `"tenant_id is required"`
- VAL-04: `tenant_id` — Muss eine in der CMDB bekannte Tenant-ID sein — Fehlermeldung: `"Tenant '{id}' not found in CMDB"`
- VAL-05: `tenant_id` — Der anfragende User muss für diesen Mandanten berechtigt sein — Fehlermeldung: `"You are not authorized to order for tenant '{id}'"`
- VAL-06: `security_zone_id` — Pflichtfeld, darf nicht leer sein — Fehlermeldung: `"security_zone_id is required"`
- VAL-07: `security_zone_id` — Muss eine in der CMDB bekannte Security-Zone-ID sein — Fehlermeldung: `"Security zone '{id}' not found in CMDB"`
- VAL-08: `security_zone_id` + `location_id` — Die Sicherheitszone muss am angegebenen Standort verfügbar sein (d.h. mindestens ein Netz an diesem Standort liegt in dieser Zone) — Fehlermeldung: `"Security zone '{security_zone_id}' is not available at location '{location_id}'"`
- VAL-09: `network_id` (wenn angegeben) — Muss eine in der CMDB bekannte Network-ID sein — Fehlermeldung: `"Network '{id}' not found in CMDB"`
- VAL-10: `network_id` (wenn angegeben) + `location_id` — Das Netz muss zum angegebenen Standort gehören — Fehlermeldung: `"Network '{network_id}' does not belong to location '{location_id}'"`
- VAL-11: `network_id` (wenn angegeben) + `security_zone_id` — Das Netz muss in der angegebenen Sicherheitszone liegen — Fehlermeldung: `"Network '{network_id}' is not in security zone '{security_zone_id}'"`

---

### API Contract

**Endpoint 1: Kontext auflösen und validieren**

- Endpoint: `POST /api/v1/context/resolve`
- Auth: requester, approver, admin
- Request Body:
```json
{
  "location_id": "loc-berlin",
  "tenant_id": "ten-corp",
  "security_zone_id": "sz-medium",
  "network_id": "net-ber-dmz"
}
```
- Response 200:
```json
{
  "valid": true,
  "context": {
    "location": {
      "id": "loc-berlin",
      "name": "Berlin HQ",
      "code": "BER",
      "region": "DE-NORTH"
    },
    "tenant": {
      "id": "ten-corp",
      "name": "Corporate IT",
      "code": "CORP"
    },
    "security_zone": {
      "id": "sz-medium",
      "name": "MEDIUM",
      "level": 2,
      "description": "DMZ, kontrollierter Zugang"
    },
    "network": {
      "id": "net-ber-dmz",
      "name": "Berlin DMZ",
      "cidr": "10.10.1.0/24",
      "type": "dmz",
      "location_id": "loc-berlin",
      "security_zone_id": "sz-medium"
    },
    "available_networks": [
      {
        "id": "net-ber-dmz",
        "name": "Berlin DMZ",
        "cidr": "10.10.1.0/24",
        "type": "dmz",
        "location_id": "loc-berlin",
        "security_zone_id": "sz-medium"
      }
    ]
  },
  "violations": []
}
```
- Response 200 (ungültiger Kontext — immer HTTP 200, Violations im Body):
```json
{
  "valid": false,
  "context": null,
  "violations": [
    {
      "field": "security_zone_id",
      "code": "zone_not_available_at_location",
      "message": "Security zone 'sz-high' is not available at location 'loc-munich'"
    }
  ]
}
```
- Response 503:
```json
{
  "error": "cmdb_unavailable",
  "message": "CMDB is currently unavailable. Please try again later."
}
```

**Endpoint 2: Verfügbare Netze für Kontext abrufen**

- Endpoint: `GET /api/v1/context/networks`
- Auth: requester, approver, admin
- Query Params:
```
location_id:       string (required)
security_zone_id:  string (required)
```
- Response 200:
```json
{
  "networks": [
    {
      "id": "net-ber-dmz",
      "name": "Berlin DMZ",
      "cidr": "10.10.1.0/24",
      "type": "dmz",
      "location_id": "loc-berlin",
      "security_zone_id": "sz-medium"
    }
  ]
}
```
- Response 400: `{"error": "validation_error", "message": "location_id is required"}`
- Response 404: `{"error": "not_found", "message": "Location 'loc-xyz' not found in CMDB"}`
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

**Endpoint 3: Erlaubte Mandanten für den aktuellen User abrufen**

- Endpoint: `GET /api/v1/context/tenants`
- Auth: requester, approver, admin
- Hinweis: Gibt alle Mandanten zurück, für die der authentifizierte User berechtigt ist. Filtert die CMDB-Mandantenliste gegen die Portal-seitige User-Tenant-Zuordnung.
- Response 200:
```json
{
  "tenants": [
    {"id": "ten-corp", "name": "Corporate IT", "code": "CORP"}
  ]
}
```
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

**Endpoint 4: Verfügbare Sicherheitsbereiche für Standort abrufen**

- Endpoint: `GET /api/v1/context/security-zones`
- Auth: requester, approver, admin
- Query Params:
```
location_id: string (required)
```
- Hinweis: Gibt nur Sicherheitsbereiche zurück, die am Standort tatsächlich verfügbar sind (d.h. mindestens ein Netz an diesem Standort liegt in dieser Zone). Delegiert an CMDB Endpoint 11 + interne Filterung.
- Response 200:
```json
{
  "security_zones": [
    {
      "id": "sz-medium",
      "name": "MEDIUM",
      "level": 2,
      "description": "DMZ, kontrollierter Zugang"
    },
    {
      "id": "sz-low",
      "name": "LOW",
      "level": 1,
      "description": "Interne Systeme, kein Internetzugang"
    }
  ]
}
```
- Response 400: `{"error": "validation_error", "message": "location_id is required"}`
- Response 404: `{"error": "not_found", "message": "Location 'loc-xyz' not found in CMDB"}`
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

**Endpoint 5: User-Tenant-Zuordnung verwalten (Admin)**

- Endpoint: `PUT /api/v1/admin/context/user-tenant-assignments/{user_id}`
- Auth: admin
- Request Body:
```json
{
  "tenant_ids": ["ten-corp", "ten-dev"]
}
```
- Hinweis: Leeres Array `[]` bedeutet: User hat keinen Zugriff auf irgendeinen Mandanten. `null` oder fehlender Body ist ein Validierungsfehler. Um alle Mandanten zu erlauben, muss der Eintrag gelöscht werden (DELETE).
- Response 200:
```json
{
  "user_id": "usr-abc123",
  "tenant_ids": ["ten-corp", "ten-dev"],
  "updated_at": "2026-03-26T10:00:00Z"
}
```
- Response 400: `{"error": "validation_error", "violations": [{"field": "tenant_ids", "message": "tenant_ids must be an array"}]}`
- Response 404: `{"error": "not_found", "message": "User 'usr-xyz' not found"}`

**Endpoint 6: User-Tenant-Zuordnung abrufen (Admin)**

- Endpoint: `GET /api/v1/admin/context/user-tenant-assignments/{user_id}`
- Auth: admin
- Response 200 (Zuordnung existiert):
```json
{
  "user_id": "usr-abc123",
  "tenant_ids": ["ten-corp"],
  "updated_at": "2026-03-26T10:00:00Z"
}
```
- Response 200 (keine Einschränkung konfiguriert):
```json
{
  "user_id": "usr-abc123",
  "tenant_ids": null,
  "note": "No restriction configured. User has access to all tenants.",
  "updated_at": null
}
```
- Response 404: `{"error": "not_found", "message": "User 'usr-xyz' not found"}`

**Endpoint 7: User-Tenant-Zuordnung löschen (Admin)**

- Endpoint: `DELETE /api/v1/admin/context/user-tenant-assignments/{user_id}`
- Auth: admin
- Hinweis: Löscht die Einschränkung. Der User erhält danach Zugriff auf alle Mandanten.
- Response 204: Kein Body
- Response 404: `{"error": "not_found", "message": "User 'usr-xyz' not found"}`

---

### Edge Cases

- EC-01: User wählt einen Standort, für den kein Netz in seiner gewählten Sicherheitszone existiert → Endpoint 4 gibt eine leere Liste zurück, kein Fehler. Das Frontend muss dem User eine verständliche Meldung zeigen. Der Kontext-Auflösungs-Endpoint (Endpoint 1) gibt `valid: false` mit entsprechender Violation.
- EC-02: User wählt einen Mandanten, für den er laut Portal-Konfiguration nicht berechtigt ist → Endpoint 1 gibt `valid: false` mit Violation `"You are not authorized to order for tenant '{id}'"`. Endpoint 3 gibt diesen Mandanten gar nicht erst zurück.
- EC-03: CMDB ist temporär nicht erreichbar während der Kontext-Auflösung → HTTP 503 mit `cmdb_unavailable`. Kein Fallback auf gecachte Daten, da gecachte Berechtigungsdaten ein Sicherheitsrisiko darstellen.
- EC-04: User ändert den Kontext einer Order im Status `draft` → Das System setzt alle Order-Items auf `invalid` (oder entfernt sie, abhängig von Feature-3.1-Implementierung) und gibt eine Warnung zurück, dass vorherige Konfigurationen möglicherweise nicht mehr gültig sind.
- EC-05: Admin löscht die Tenant-Zuordnung eines Users, der gerade eine Order im Status `draft` hat → Das System revalidiert alle betroffenen Draft-Orders asynchron. Orders, deren Kontext durch die neue Einschränkung ungültig wird, werden auf `invalid_context` markiert. Der Requester wird per E-Mail benachrichtigt und muss den Kontext anpassen, bevor die Order weiterverarbeitet werden kann.
- EC-06: `network_id` aus einem anderen Standort als `location_id` → VAL-10 schlägt fehl. Kein CMDB-Lookup für das Netz wenn `location_id` bereits ungültig ist (Fail-Fast bei location_id-Fehler).
- EC-07: Alle Mandanten-IDs in der User-Tenant-Zuordnung beziehen sich auf nicht mehr in der CMDB existierende Mandanten → Endpoint 3 gibt eine leere Liste zurück. Keine automatische Bereinigung der Portal-Konfiguration. Admin muss die Zuordnung manuell aktualisieren.

---

## Feature 10.2: Kontextabhängige Parameter-Einschränkungen

### User Story

Als Administrator möchte ich Regeln definieren können, die Parameter-Optionen im Bestellformular basierend auf dem Bestellkontext (Standort, Mandant, Sicherheitsbereich) einschränken, damit kontextspezifische Einschränkungen (z.B. max. 8 CPU-Kerne in der DMZ) automatisch durchgesetzt werden.

---

### Logisches Datenmodell

#### ContextRestriction

Eine Kontexteinschränkungsregel verknüpft eine Kontext-Bedingung mit einem Einschränkungs-Effekt auf einen bestimmten Template-Parameter.

```
ContextRestriction {
  id:               string (UUID)       // interne ID
  name:             string              // beschreibender Name für Admin-UI (z.B. "CPU-Limit DMZ")
  description:      string (optional)   // erläuternder Text
  template_slug:    string | null       // gilt nur für dieses Template (null = gilt für alle Templates)
  condition:        ContextCondition    // wann die Regel greift
  effect:           ParameterEffect     // was die Regel tut
  priority:         integer             // bei Konflikten: höhere Zahl = höhere Priorität
  active:           boolean             // Regel aktiv oder deaktiviert
  created_at:       ISO-8601 datetime
  updated_at:       ISO-8601 datetime
}
```

#### ContextCondition

```
ContextCondition {
  location_ids:      string[] | null    // null = gilt für alle Standorte
  tenant_ids:        string[] | null    // null = gilt für alle Mandanten
  security_zone_ids: string[] | null    // null = gilt für alle Sicherheitsbereiche
  network_types:     string[] | null    // null = gilt für alle Netztypen ("dmz", "internal", "mgmt")
}
```

Semantik: Alle angegebenen Bedingungen müssen gleichzeitig zutreffen (AND-Verknüpfung). Eine `null`-Liste bedeutet "keine Einschränkung auf dieses Feld". Beispiel: `security_zone_ids: ["sz-medium"]` + `location_ids: null` bedeutet: greift in allen Standorten, sofern der Sicherheitsbereich `sz-medium` ist.

#### ParameterEffect

```
ParameterEffect {
  parameter_key: string         // key des Parameters im Template (muss im Template existieren, wenn template_slug gesetzt)
  effect_type:   EffectType     // "limit_max" | "limit_min" | "filter_options" | "set_value" | "disable"
  value:         any            // Effekt-abhängig (s.u.)
}
```

**EffectType-Semantik:**

| effect_type      | value-Typ     | Bedeutung |
|------------------|---------------|-----------|
| `limit_max`      | number        | Setzt das Maximum des Parameters (überschreibt Template-Constraint, falls strenger) |
| `limit_min`      | number        | Setzt das Minimum des Parameters |
| `filter_options` | string[]      | Nur diese Optionswerte sind erlaubt (bei enum-Parametern). Intersection mit Template-Optionen. |
| `set_value`      | any           | Setzt den Parameter auf einen festen Wert und macht ihn nicht editierbar |
| `disable`        | null          | Blendet den Parameter vollständig aus (verhält sich wie `depends_on`-Effekt `"disabled"`) |

**Prioritätsauflösung bei mehreren Regeln auf demselben Parameter:**
- Für `limit_max`: Es gilt der **niedrigste** (restriktivste) Maximalwert aller greifenden Regeln, unabhängig von `priority`.
- Für `limit_min`: Es gilt der **höchste** (restriktivste) Minimalwert aller greifenden Regeln, unabhängig von `priority`.
- Für `filter_options`: Es gilt die **Schnittmenge** aller greifenden Regeln, unabhängig von `priority`.
- Für `set_value` und `disable`: Die Regel mit der höchsten `priority` gewinnt. Bei Gleichstand gewinnt die zuletzt aktualisierte Regel.
- `disable` hat **immer Vorrang** vor `set_value`, wenn beide auf demselben Parameter greifen.

#### Zusammenspiel mit Template-internen DependencyRules

Die Reihenfolge der Regelanwendung ist fest:
1. Template-interne `DependencyRules` werden ausgewertet (bestimmen Sichtbarkeit und required-Status von Parametern).
2. Kontext-Einschränkungsregeln (`ContextRestrictions`) werden auf die nach Schritt 1 sichtbaren Parameter angewendet.
3. Das Ergebnis aus Schritt 2 ist der finale Zustand des Formulars.

Wenn eine `ContextRestriction` einen Parameter betrifft, der durch DependencyRules ausgeblendet ist, wird die ContextRestriction ignoriert (sie hat keine Wirkung auf einen nicht sichtbaren Parameter).

---

### Requirements

- REQ-13: Das System MUSS einen Datentyp `ContextRestriction` verwalten, der eine Kontext-Bedingung mit einem Parameter-Effekt verknüpft.
- REQ-14: Jede `ContextRestriction` kann auf ein spezifisches Template (`template_slug`) oder auf alle Templates (null) angewendet werden.
- REQ-15: Das System MUSS einen Endpoint bereitstellen, der für einen gegebenen Kontext und ein gegebenes Template alle greifenden `ContextRestrictions` auflöst und als fertigen, eingeschränkten Parametersatz zurückgibt.
- REQ-16: Die Auflösung der Kontext-Einschränkungen MUSS nach der Auflösung der Template-internen DependencyRules erfolgen. Kontext-Einschränkungen auf nicht sichtbare Parameter werden ignoriert.
- REQ-17: Wenn eine `ContextRestriction` vom Typ `limit_max` einen Wert unterhalb des aktuell im Formular eingestellten Parameterwerts setzt, muss das Frontend den Wert auf das neue Maximum clampieren und den User informieren.
- REQ-18: Das System MUSS Admin-Endpoints für CRUD-Operationen auf `ContextRestrictions` bereitstellen.
- REQ-19: `ContextRestrictions` können auch für die Einschränkung von Mandanten auf Sicherheitsbereiche genutzt werden. Wenn eine Regel `effect_type: "disable"` auf einen Parameter mit `key: "__context_security_zone"` setzt (reservierter Pseudoparameter), wird die gesamte Bestellung mit diesem Kontext blockiert. Dies ist der Mechanismus, über den z.B. `ten-finance` für `sz-medium` gesperrt werden kann.
- REQ-20: Das System MUSS beim Speichern einer `ContextRestriction` validieren, dass der `parameter_key` im angegebenen Template existiert, wenn `template_slug` nicht null ist.
- REQ-21: Das System MUSS beim Auflösen von `filter_options`-Regeln sicherstellen, dass die Schnittmenge niemals leer ist, wenn der betreffende Parameter `required: true` ist. Wenn die Schnittmenge leer wäre, wird die Situation als Konfigurationsfehler gewertet und ein spezifischer Fehler zurückgegeben (`context_configuration_error`).
- REQ-22: Die Kontext-Einschränkungsauflösung MUSS deterministisch sein: gleicher Kontext + gleiche Regeln = immer gleiche Einschränkungen.
- REQ-23: Das System MUSS eine Preview-Funktion bereitstellen, die einem Admin zeigt, welche Einschränkungen für einen hypothetischen Kontext gelten würden, ohne eine Order zu erstellen.
- REQ-24: Deaktivierte Regeln (`active: false`) DÜRFEN NICHT in die Auflösung einbezogen werden.
- REQ-25: Das System MUSS einen Endpoint bereitstellen, der alle greifenden `ContextRestrictions` für einen gegebenen Kontext auflistet (nicht aufgelöst, sondern als Regelliste), um Debugging und Transparenz zu ermöglichen.

---

### Validation Rules

- VAL-12: `ContextRestriction.name` — Pflichtfeld, 3–100 Zeichen — Fehlermeldung: `"name must be between 3 and 100 characters"`
- VAL-13: `ContextRestriction.template_slug` — Wenn angegeben: muss einem bekannten Template-Slug entsprechen — Fehlermeldung: `"Template slug '{slug}' not found"`
- VAL-14: `ContextCondition.location_ids` — Wenn angegeben: jede ID muss in der CMDB bekannt sein — Fehlermeldung: `"Location '{id}' not found in CMDB"`
- VAL-15: `ContextCondition.tenant_ids` — Wenn angegeben: jede ID muss in der CMDB bekannt sein — Fehlermeldung: `"Tenant '{id}' not found in CMDB"`
- VAL-16: `ContextCondition.security_zone_ids` — Wenn angegeben: jede ID muss in der CMDB bekannt sein — Fehlermeldung: `"Security zone '{id}' not found in CMDB"`
- VAL-17: `ContextCondition.network_types` — Wenn angegeben: erlaubte Werte sind `"dmz"`, `"internal"`, `"mgmt"` — Fehlermeldung: `"Invalid network type '{type}'. Allowed: dmz, internal, mgmt"`
- VAL-18: `ParameterEffect.effect_type` — Muss einer der erlaubten Werte sein: `"limit_max"`, `"limit_min"`, `"filter_options"`, `"set_value"`, `"disable"` — Fehlermeldung: `"Unknown effect_type. Allowed: limit_max, limit_min, filter_options, set_value, disable"`
- VAL-19: `ParameterEffect.value` bei `effect_type: "limit_max"` oder `"limit_min"` — Muss eine Zahl sein — Fehlermeldung: `"value must be a number for effect_type 'limit_max'/'limit_min'"`
- VAL-20: `ParameterEffect.value` bei `effect_type: "filter_options"` — Muss ein nicht-leeres Array von Strings sein — Fehlermeldung: `"value must be a non-empty array of strings for effect_type 'filter_options'"`
- VAL-21: `ParameterEffect.parameter_key` — Wenn `template_slug` gesetzt: muss als `key` im referenzierten Template existieren oder der reservierte Pseudoparameter `"__context_security_zone"` sein — Fehlermeldung: `"Parameter key '{key}' not found in template '{slug}'"`
- VAL-22: `ContextRestriction.priority` — Muss eine nicht-negative ganze Zahl sein — Fehlermeldung: `"priority must be a non-negative integer"`
- VAL-23: `ParameterEffect.effect_type: "limit_max"` — `value` muss größer als das Template-definierte `min` des Parameters sein — Fehlermeldung: `"limit_max value {v} is below the template's minimum for parameter '{key}'"`

---

### API Contract

**Endpoint 8: Kontextabhängige Parameter-Einschränkungen auflösen**

- Endpoint: `POST /api/v1/context/resolve-restrictions`
- Auth: requester, approver, admin
- Hinweis: Gibt den aufgelösten Parametersatz für ein Template unter Berücksichtigung aller greifenden ContextRestrictions zurück. Dieser Endpoint ist der zentrale Auflösungs-Endpoint für das Bestellformular.
- Request Body:
```json
{
  "context": {
    "location_id": "loc-berlin",
    "tenant_id": "ten-corp",
    "security_zone_id": "sz-medium",
    "network_id": "net-ber-dmz"
  },
  "template_slug": "vm-linux",
  "template_version": "1.0.0"
}
```
- Response 200:
```json
{
  "template_slug": "vm-linux",
  "template_version": "1.0.0",
  "context_blocked": false,
  "applied_restrictions": [
    {
      "restriction_id": "restr-abc123",
      "name": "CPU-Limit DMZ",
      "parameter_key": "cpu_cores",
      "effect_type": "limit_max",
      "effective_value": 8
    }
  ],
  "parameters": [
    {
      "key": "cpu_cores",
      "original_constraints": {
        "min": 1,
        "max": 32
      },
      "effective_constraints": {
        "min": 1,
        "max": 8
      },
      "context_restricted": true
    }
  ]
}
```
- Response 200 (Kontext blockiert durch `__context_security_zone` Pseudoparameter-Regel):
```json
{
  "template_slug": "vm-linux",
  "template_version": "1.0.0",
  "context_blocked": true,
  "block_reason": "Tenant 'ten-finance' is not permitted to order in security zone 'sz-medium'.",
  "applied_restrictions": [],
  "parameters": []
}
```
- Response 400: `{"error": "validation_error", "message": "template_slug is required"}`
- Response 404: `{"error": "not_found", "message": "Template 'vm-linux@1.0.0' not found"}`
- Response 409:
```json
{
  "error": "context_configuration_error",
  "message": "Restriction 'restr-xyz' would result in an empty option set for required parameter 'disk_type'. Please review restriction configuration.",
  "restriction_id": "restr-xyz",
  "parameter_key": "disk_type"
}
```
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

**Endpoint 9: Alle greifenden Regeln für Kontext auflisten (Debug)**

- Endpoint: `POST /api/v1/context/applicable-restrictions`
- Auth: admin
- Request Body: identisch zu Endpoint 8
- Response 200:
```json
{
  "context": {
    "location_id": "loc-berlin",
    "tenant_id": "ten-corp",
    "security_zone_id": "sz-medium"
  },
  "template_slug": "vm-linux",
  "restrictions": [
    {
      "id": "restr-abc123",
      "name": "CPU-Limit DMZ",
      "priority": 10,
      "condition": {
        "location_ids": null,
        "tenant_ids": null,
        "security_zone_ids": ["sz-medium"],
        "network_types": null
      },
      "effect": {
        "parameter_key": "cpu_cores",
        "effect_type": "limit_max",
        "value": 8
      },
      "active": true
    }
  ]
}
```

**Endpoint 10: ContextRestriction erstellen (Admin)**

- Endpoint: `POST /api/v1/admin/context/restrictions`
- Auth: admin
- Request Body:
```json
{
  "name": "CPU-Limit DMZ",
  "description": "Maximale CPU-Kerne in der DMZ-Zone ist 8.",
  "template_slug": null,
  "condition": {
    "location_ids": null,
    "tenant_ids": null,
    "security_zone_ids": ["sz-medium"],
    "network_types": null
  },
  "effect": {
    "parameter_key": "cpu_cores",
    "effect_type": "limit_max",
    "value": 8
  },
  "priority": 10,
  "active": true
}
```
- Response 201:
```json
{
  "id": "restr-abc123",
  "name": "CPU-Limit DMZ",
  "template_slug": null,
  "condition": { "...": "..." },
  "effect": { "...": "..." },
  "priority": 10,
  "active": true,
  "created_at": "2026-03-26T10:00:00Z",
  "updated_at": "2026-03-26T10:00:00Z"
}
```
- Response 400: `{"error": "validation_error", "violations": [{"field": "effect.value", "message": "value must be a number for effect_type 'limit_max'"}]}`
- Response 409: `{"error": "conflict", "message": "A restriction with this name already exists."}`

**Endpoint 11: ContextRestriction auflisten (Admin)**

- Endpoint: `GET /api/v1/admin/context/restrictions`
- Auth: admin
- Query Params:
```
template_slug:     string (optional, filter)
active:            boolean (optional, default: keine Filterung)
security_zone_id:  string (optional, filter: Regeln, die diese Zone betreffen)
limit:             integer (optional, default: 20, max: 100)
offset:            integer (optional, default: 0)
```
- Response 200:
```json
{
  "total": 1,
  "data": [
    {
      "id": "restr-abc123",
      "name": "CPU-Limit DMZ",
      "template_slug": null,
      "condition": { "security_zone_ids": ["sz-medium"], "location_ids": null, "tenant_ids": null, "network_types": null },
      "effect": { "parameter_key": "cpu_cores", "effect_type": "limit_max", "value": 8 },
      "priority": 10,
      "active": true,
      "created_at": "2026-03-26T10:00:00Z",
      "updated_at": "2026-03-26T10:00:00Z"
    }
  ]
}
```

**Endpoint 12: ContextRestriction aktualisieren (Admin)**

- Endpoint: `PUT /api/v1/admin/context/restrictions/{restriction_id}`
- Auth: admin
- Request Body: identisch zu POST (vollständige Ressource)
- Response 200: aktualisierte Ressource
- Response 404: `{"error": "not_found", "message": "Restriction '{id}' not found"}`
- Response 400: Validierungsfehler (identisches Format wie POST)

**Endpoint 13: ContextRestriction löschen (Admin)**

- Endpoint: `DELETE /api/v1/admin/context/restrictions/{restriction_id}`
- Auth: admin
- Response 204: Kein Body
- Response 404: `{"error": "not_found", "message": "Restriction '{id}' not found"}`

---

### Edge Cases

- EC-08: Zwei `limit_max`-Regeln mit unterschiedlichen `priority`-Werten greifen auf denselben Parameter → Das System nimmt den niedrigsten Maximalwert (restriktivster Wert), unabhängig von Priority. Priority ist nur relevant bei `set_value` und `disable`.
- EC-09: Eine `filter_options`-Regel und eine `limit_max`-Regel greifen gleichzeitig auf denselben Enum-Parameter → Beide Regeln werden angewendet. Das Ergebnis ist die gefilterte Optionsliste. Die `limit_max`-Regel wird auf Enum-Parametern ignoriert (nur für numerische Typen relevant).
- EC-10: `filter_options`-Regel ergibt bei einem `required: true`-Parameter eine leere Schnittmenge → HTTP 409 mit `context_configuration_error`. Admin muss die Regelkonfiguration korrigieren.
- EC-11: Eine Regel referenziert einen `template_slug`, dessen Template auf `disabled` gesetzt wird → Die Regel bleibt erhalten, hat aber keine Wirkung, da das Template nicht mehr bestellbar ist. Kein automatisches Löschen der Regel.
- EC-12: Admin legt eine `set_value`-Regel und eine `disable`-Regel auf denselben Parameter an (gleiche Priorität) → `disable` hat immer Vorrang. Das System loggt den Konflikt auf Warn-Level.
- EC-13: Eine global geltende Regel (`template_slug: null`, `location_ids: null`) trifft auf ein Template, das keinen Parameter mit dem in der Regel referenzierten `parameter_key` hat → Die Regel wird für dieses Template stillschweigend ignoriert. Kein Fehler.
- EC-14: Kontext-Auflösung wird für ein `deprecated`-Template angefragt → Regeln werden normal ausgewertet. Response enthält zusätzlich einen `template_deprecation_hint` mit Verweis auf das Nachfolger-Template.

---

## Feature 10.3: Kontextabhängige Service-Verfügbarkeit

### User Story

Als Requester möchte ich im Service-Catalog nur Services sehen, die in meinem gewählten Bestellkontext (Standort, Mandant, Sicherheitsbereich) verfügbar sind, damit ich keine Bestellungen für nicht verfügbare Services starten kann.

Als Administrator möchte ich die Verfügbarkeit von Service-Templates pro Standort, Mandant und Sicherheitsbereich konfigurieren können, damit ich die Availability-Matrix pflegen kann.

---

### Logisches Datenmodell

#### AvailabilityRule

Eine Verfügbarkeitsregel definiert, ob ein Service-Template in einem Kontext verfügbar ist. Das System verwendet ein **Default-Allow-Modell**: Ein Service ist in einem Kontext verfügbar, sofern keine `deny`-Regel greift. Explizite `allow`-Regeln können genutzt werden, um ein Template auf bestimmte Kontexte einzuschränken (dann gilt Whitelist-Semantik für dieses Template).

```
AvailabilityRule {
  id:               string (UUID)
  name:             string
  description:      string (optional)
  template_slug:    string              // Pflicht: für welches Template gilt diese Regel
  condition:        ContextCondition    // identische Struktur wie in Feature 10.2
  rule_type:        RuleType           // "allow" | "deny"
  priority:         integer
  active:           boolean
  created_at:       ISO-8601 datetime
  updated_at:       ISO-8601 datetime
}
```

**Auflösungslogik:**
1. Wenn keine Regel für ein Template existiert: Template ist verfügbar (Default-Allow).
2. Wenn ausschließlich `deny`-Regeln existieren: Template ist verfügbar, außer eine greifende `deny`-Regel schlägt an.
3. Wenn mindestens eine `allow`-Regel für ein Template existiert: Das Template ist **nur** dann verfügbar, wenn mindestens eine `allow`-Regel greift (Whitelist-Semantik für dieses Template).
4. Wenn eine `deny`-Regel und eine `allow`-Regel gleichzeitig greifen: `deny` gewinnt, außer die `allow`-Regel hat eine höhere `priority`.

#### AvailabilityStatus

```
AvailabilityStatus {
  available:    boolean
  reason:       string | null          // Begründung bei available: false
  rule_id:      string | null          // Regel, die zur Entscheidung geführt hat
}
```

---

### Requirements

- REQ-26: Das System MUSS den Catalog-Endpoint (Endpoint 37 aus Feature 2.1) um optionale Kontext-Parameter (`location_id`, `tenant_id`, `security_zone_id`) erweitern. Wenn Kontext-Parameter angegeben werden, MUSS das Ergebnis nach Verfügbarkeit im angegebenen Kontext gefiltert werden.
- REQ-27: Das System MUSS für jedes zurückgegebene Template im Catalog ein `availability`-Objekt mitliefern, wenn Kontext-Parameter angegeben wurden. Das Objekt enthält `available: true/false` und im Fall `false` eine Begründung.
- REQ-28: Nicht verfügbare Templates (`available: false`) MÜSSEN im Catalog-Response weiterhin enthalten sein, aber als nicht bestellbar markiert. Das Frontend entscheidet, ob es sie ausblendet oder ausgegraut anzeigt. Eine Filteroption `hide_unavailable=true` erlaubt dem Frontend, nicht verfügbare Templates vollständig auszublenden.
- REQ-29: Das System MUSS Admin-Endpoints für CRUD-Operationen auf `AvailabilityRules` bereitstellen.
- REQ-30: Das System MUSS einen Endpoint bereitstellen, der für ein gegebenes Template und einen gegebenen Kontext die Verfügbarkeit prüft und die greifende Regel zurückgibt.
- REQ-31: Das System MUSS beim Versuch, eine Order mit einem nicht verfügbaren Service zu erstellen, die Anfrage mit HTTP 422 (`service_not_available_in_context`) ablehnen. Die Verfügbarkeitsprüfung erfolgt serverseitig als Teil der Order-Validierung, unabhängig von der Frontend-Anzeige.
- REQ-32: Das System MUSS einen Bulk-Availability-Check-Endpoint bereitstellen, der für mehrere Template-Slugs gleichzeitig die Verfügbarkeit in einem Kontext prüft. Dieser Endpoint wird vom Frontend genutzt, um den Catalog in einem einzigen Request zu filtern.
- REQ-33: Die Verfügbarkeitsprüfung MUSS performant sein. Wenn Kontext-Parameter angegeben werden, MUSS der Catalog-Endpoint alle Verfügbarkeitsprüfungen in einem einzigen Datenbankabfrage-Block durchführen (kein N+1-Problem).
- REQ-34: `AvailabilityRules` MÜSSEN unabhängig von `ContextRestrictions` verwaltet werden. Verfügbarkeit (darf ich diesen Service überhaupt sehen?) und Parameter-Einschränkungen (was darf ich konfigurieren?) sind zwei getrennte Konzepte.
- REQ-35: Das System MUSS einen Admin-Endpoint bereitstellen, der die vollständige Availability-Matrix anzeigt: alle Templates × alle CMDB-Standorte × alle Sicherheitsbereiche mit Status `available`/`denied`/`allow-listed`.
- REQ-36: Das System MUSS bei jeder Änderung an Availability-Rules, Context-Restrictions oder Tenant-Zuordnungen eine asynchrone Revalidierung aller betroffenen Draft-Orders auslösen. Betroffene Orders, deren Kontext oder Items durch die neue Regel ungültig werden, werden mit einem `invalid_context`-Flag markiert. Der Requester wird per E-Mail benachrichtigt (Feature 6.1) mit Angabe der betroffenen Order-ID und des Grunds der Invalidierung.
- REQ-37: Die asynchrone Revalidierung (REQ-36) verarbeitet Draft-Orders in Batches (max. 100 pro Durchlauf) und wird innerhalb von 5 Minuten nach der Regeländerung gestartet. Bei Revalidierung werden sowohl die Kontextgültigkeit als auch die Service-Verfügbarkeit und Parameter-Einschränkungen geprüft.
- REQ-38: Eine als `invalid_context` markierte Draft-Order kann vom Requester nicht submitted werden. Der Requester muss zuerst den Kontext anpassen oder betroffene Items entfernen, wodurch das `invalid_context`-Flag aufgehoben wird. Die erneute Validierung (Feature 3.2) setzt das Flag zurück, wenn alle Regeln erfüllt sind.

---

### Validation Rules

- VAL-24: `AvailabilityRule.template_slug` — Pflichtfeld, muss einem bekannten Template-Slug entsprechen — Fehlermeldung: `"Template slug '{slug}' not found"`
- VAL-25: `AvailabilityRule.rule_type` — Muss `"allow"` oder `"deny"` sein — Fehlermeldung: `"rule_type must be 'allow' or 'deny'"`
- VAL-26: `AvailabilityRule.name` — Pflichtfeld, 3–100 Zeichen — Fehlermeldung: `"name must be between 3 and 100 characters"`
- VAL-27: `AvailabilityRule.priority` — Muss eine nicht-negative ganze Zahl sein — Fehlermeldung: `"priority must be a non-negative integer"`
- VAL-28: `ContextCondition`-Felder — Identische Validierung wie in Feature 10.2 (VAL-14 bis VAL-17)
- VAL-29: Kontext-Parameter im Catalog-Endpoint — Wenn `location_id` angegeben: muss in der CMDB bekannt sein — Fehlermeldung: `{"error": "validation_error", "message": "Location '{id}' not found in CMDB"}`

---

### API Contract

**Endpoint 14: Catalog mit Kontext-Filter (Erweiterung von Endpoint 37)**

- Endpoint: `GET /api/v1/catalog/templates`
- Auth: requester, approver, admin
- Hinweis: Dies ist eine Erweiterung des bestehenden Endpoints 37 aus Feature 2.1. Neue Kontext-Parameter werden hinzugefügt. Bestehende Parameter bleiben unverändert.
- Neue Query Params (zusätzlich zu den bestehenden):
```
location_id:       string (optional)   // CMDB Location-ID
tenant_id:         string (optional)   // CMDB Tenant-ID
security_zone_id:  string (optional)   // CMDB Security-Zone-ID
hide_unavailable:  boolean (optional, default: false)  // nicht verfügbare Templates ausblenden
```
- Hinweis: Wenn keiner der Kontext-Parameter angegeben wird, verhält sich der Endpoint identisch wie in Feature 2.1 (keine Verfügbarkeitsfilterung).
- Response 200 (mit Kontext-Parametern):
```json
{
  "data": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "slug": "vm-linux",
      "version": "2.0.0",
      "type": "vm",
      "display_name": "Linux Virtual Machine",
      "description": "Standard-Linux-VM mit konfigurierbaren CPU-, RAM- und Storage-Werten.",
      "category": "Compute",
      "icon_identifier": "server-linux",
      "status": "active",
      "estimated_cost_eur_per_month": 120.00,
      "approval_always_required": false,
      "availability": {
        "available": true,
        "reason": null,
        "rule_id": null
      }
    },
    {
      "id": "7ab12c34-...",
      "slug": "vm-windows",
      "version": "1.0.0",
      "type": "vm",
      "display_name": "Windows Virtual Machine",
      "description": "Windows VM (Windows Server 2022).",
      "category": "Compute",
      "icon_identifier": "server-windows",
      "status": "active",
      "estimated_cost_eur_per_month": 180.00,
      "approval_always_required": false,
      "availability": {
        "available": false,
        "reason": "Windows VMs are not available at location 'loc-munich'.",
        "rule_id": "avail-rule-xyz"
      }
    }
  ],
  "total": 2,
  "limit": 20,
  "offset": 0
}
```
- Response 400: `{"error": "validation_error", "message": "Location 'loc-xyz' not found in CMDB"}`
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

**Endpoint 15: Verfügbarkeit einzelnes Template prüfen**

- Endpoint: `GET /api/v1/catalog/templates/{slug}/availability`
- Auth: requester, approver, admin
- Query Params:
```
location_id:       string (required)
tenant_id:         string (required)
security_zone_id:  string (required)
```
- Response 200:
```json
{
  "template_slug": "vm-windows",
  "context": {
    "location_id": "loc-munich",
    "tenant_id": "ten-corp",
    "security_zone_id": "sz-low"
  },
  "availability": {
    "available": false,
    "reason": "Windows VMs are not available at location 'loc-munich'.",
    "rule_id": "avail-rule-xyz",
    "rule_name": "Kein Windows in München"
  }
}
```
- Response 404: `{"error": "not_found", "message": "Template 'vm-unknown' not found"}`
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

**Endpoint 16: Bulk-Availability-Check**

- Endpoint: `POST /api/v1/catalog/availability-check`
- Auth: requester, approver, admin
- Request Body:
```json
{
  "context": {
    "location_id": "loc-munich",
    "tenant_id": "ten-corp",
    "security_zone_id": "sz-low"
  },
  "template_slugs": ["vm-linux", "vm-windows", "db-postgresql"]
}
```
- Response 200:
```json
{
  "context": {
    "location_id": "loc-munich",
    "tenant_id": "ten-corp",
    "security_zone_id": "sz-low"
  },
  "results": [
    {
      "template_slug": "vm-linux",
      "available": true,
      "reason": null,
      "rule_id": null
    },
    {
      "template_slug": "vm-windows",
      "available": false,
      "reason": "Windows VMs are not available at location 'loc-munich'.",
      "rule_id": "avail-rule-xyz"
    },
    {
      "template_slug": "db-postgresql",
      "available": true,
      "reason": null,
      "rule_id": null
    }
  ]
}
```
- Response 400: `{"error": "validation_error", "violations": [{"field": "context.location_id", "message": "location_id is required"}]}`
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

**Endpoint 17: AvailabilityRule erstellen (Admin)**

- Endpoint: `POST /api/v1/admin/context/availability-rules`
- Auth: admin
- Request Body:
```json
{
  "name": "Kein Windows in München",
  "description": "Windows-VMs sind am Standort München nicht verfügbar.",
  "template_slug": "vm-windows",
  "condition": {
    "location_ids": ["loc-munich"],
    "tenant_ids": null,
    "security_zone_ids": null,
    "network_types": null
  },
  "rule_type": "deny",
  "priority": 10,
  "active": true
}
```
- Response 201:
```json
{
  "id": "avail-rule-xyz",
  "name": "Kein Windows in München",
  "template_slug": "vm-windows",
  "condition": { "location_ids": ["loc-munich"], "tenant_ids": null, "security_zone_ids": null, "network_types": null },
  "rule_type": "deny",
  "priority": 10,
  "active": true,
  "created_at": "2026-03-26T10:00:00Z",
  "updated_at": "2026-03-26T10:00:00Z"
}
```
- Response 400: Validierungsfehler

**Endpoint 18: AvailabilityRules auflisten (Admin)**

- Endpoint: `GET /api/v1/admin/context/availability-rules`
- Auth: admin
- Query Params:
```
template_slug: string (optional)
rule_type:     string (optional, "allow" | "deny")
active:        boolean (optional)
limit:         integer (optional, default: 20, max: 100)
offset:        integer (optional, default: 0)
```
- Response 200:
```json
{
  "total": 1,
  "data": [
    {
      "id": "avail-rule-xyz",
      "name": "Kein Windows in München",
      "template_slug": "vm-windows",
      "condition": { "location_ids": ["loc-munich"], "tenant_ids": null, "security_zone_ids": null, "network_types": null },
      "rule_type": "deny",
      "priority": 10,
      "active": true,
      "created_at": "2026-03-26T10:00:00Z",
      "updated_at": "2026-03-26T10:00:00Z"
    }
  ]
}
```

**Endpoint 19: AvailabilityRule aktualisieren (Admin)**

- Endpoint: `PUT /api/v1/admin/context/availability-rules/{rule_id}`
- Auth: admin
- Request Body: identisch zu POST
- Response 200: aktualisierte Ressource
- Response 404: `{"error": "not_found", "message": "Availability rule '{id}' not found"}`

**Endpoint 20: AvailabilityRule löschen (Admin)**

- Endpoint: `DELETE /api/v1/admin/context/availability-rules/{rule_id}`
- Auth: admin
- Response 204: Kein Body
- Response 404: `{"error": "not_found", "message": "Availability rule '{id}' not found"}`

**Endpoint 21: Availability-Matrix abrufen (Admin)**

- Endpoint: `GET /api/v1/admin/context/availability-matrix`
- Auth: admin
- Hinweis: Gibt eine vollständige Matrix über alle Templates × alle CMDB-Standorte × alle CMDB-Sicherheitsbereiche zurück. Die CMDB-Daten werden live abgefragt. Nur für Admin-Debugging geeignet; nicht für den Einsatz im Bestellprozess.
- Query Params:
```
template_slug: string (optional, auf ein Template einschränken)
location_id:   string (optional, auf einen Standort einschränken)
```
- Response 200:
```json
{
  "matrix": [
    {
      "template_slug": "vm-linux",
      "location_id": "loc-berlin",
      "security_zone_id": "sz-low",
      "status": "available",
      "rule_id": null
    },
    {
      "template_slug": "vm-windows",
      "location_id": "loc-munich",
      "security_zone_id": "sz-low",
      "status": "denied",
      "rule_id": "avail-rule-xyz",
      "rule_name": "Kein Windows in München"
    },
    {
      "template_slug": "vm-linux",
      "location_id": "loc-berlin",
      "security_zone_id": "sz-medium",
      "status": "allow-listed",
      "rule_id": "avail-rule-abc",
      "rule_name": "Linux explizit erlaubt in DMZ Berlin"
    }
  ],
  "generated_at": "2026-03-26T10:00:00Z"
}
```
- Response 503: `{"error": "cmdb_unavailable", "message": "CMDB is currently unavailable."}`

---

### Edge Cases

- EC-15: Ein Template hat keine `AvailabilityRules` → Default-Allow: Template ist in jedem Kontext verfügbar. Das `availability`-Objekt im Catalog enthält `available: true, rule_id: null`.
- EC-16: Ein Template hat ausschließlich `allow`-Regeln (Whitelist). Ein Kontext matcht keine davon → Template ist nicht verfügbar. `reason: "Service is not available in the requested context."`, `rule_id: null` (keine spezifische Regel hat die Ablehnung ausgelöst, sie folgt aus der Whitelist-Logik).
- EC-17: `deny`-Regel und `allow`-Regel treffen gleichzeitig zu, gleiche `priority` → `deny` gewinnt. Dieses Verhalten ist dokumentiert und deterministisch.
- EC-18: Ein Requester versucht, eine Order mit `vm-windows` in `loc-munich` zu erstellen (nicht verfügbar), obwohl das Frontend die Einschränkung anzeigt → Der Server prüft die Verfügbarkeit nochmals beim Order-Submit und lehnt mit HTTP 422 ab. Grund: Frontend-State kann veraltet sein (z.B. Admin hat Regel zwischenzeitlich geändert).
- EC-19: Admin erstellt oder ändert eine Deny-Regel, während Draft-Orders existieren, die davon betroffen wären → Das System revalidiert alle Draft-Orders asynchron gegen die neuen Regeln. Betroffene Orders werden auf `invalid_context` markiert und der Requester wird per E-Mail benachrichtigt. Bei Deaktivierung einer Regel (`active: false`) werden betroffene Draft-Orders ebenfalls revalidiert — zuvor eingeschränkte Konfigurationen könnten wieder gültig werden.
- EC-20: Admin löscht ein Template, für das noch `AvailabilityRules` existieren → Die Regeln werden als verwaist markiert (orphaned). Sie haben keine Wirkung, da das Template nicht mehr im Catalog erscheint. Beim nächsten Admin-Aufruf von Endpoint 18 werden verwaiste Regeln mit einem `orphaned: true`-Flag in der Response markiert. Kein automatisches Löschen.
- EC-21: Bulk-Availability-Check enthält einen `template_slug`, der nicht existiert → Das entsprechende Element im `results`-Array enthält `"available": false, "reason": "Template not found."`. Der gesamte Request schlägt nicht fehl.
- EC-22: Alle Templates an einem Standort werden durch `deny`-Regeln geblockt → Der Catalog gibt eine leere `data`-Liste zurück (wenn `hide_unavailable: true`). Dies ist kein Fehler. Das Frontend muss diesen Zustand als "keine Services verfügbar" kommunizieren.

---

## Nummerierungsstand Feature-Gruppe 10

> **Nummerierungsstand (Einstieg):** REQ-01, VAL-01, EC-01, Endpoint 1
> **Nummerierungsstand (Ende):** REQ-38, VAL-29, EC-22, Endpoint 21
> **Letzte Änderung:** 2026-03-26 — REQ-36..38 ergänzt (asynchrone Draft-Revalidierung bei Regeländerungen), EC-05/EC-19 aktualisiert
