# Feature-Gruppe 2: Service Catalog & Template-Modell

> **Nummerierungsstand (Einstieg):** REQ-100, VAL-47, EC-66, Endpoint 37
> **Nummerierungsstand (Ende):** REQ-125, VAL-71, EC-80, Endpoint 44
> **Geändert:** ServiceTemplate um `estimated_cost_eur_per_month` und `approval_always_required` erweitert (Abhängigkeit Feature 8.1 Approval-Workflow)

---

## Abhängigkeiten zu anderen Feature-Gruppen

| Feature | Abhängigkeit |
|---------|-------------|
| Feature 3.1 (Checkout-Flow) | Liest ServiceTemplates und ParameterDefinitions, um das Order-Formular aufzubauen. Ein Service im Warenkorb referenziert immer eine konkrete Template-Version (`template_id` + `template_version`). |
| Feature 3.2 (Bestellstatus-Tracking) | Order-Items tragen `service_slug` und `template_version` für die Anzeige. |
| Feature 4.1 (OpenTofu Job-Dispatcher) | Nutzt `tofu_module_source` und `tofu_variable_name`-Mappings aus dem ServiceTemplate, um den Tofu-Aufruf zu konstruieren. |
| Feature 4.5 (Datenbank-Provisioning) | ServiceTemplates vom Typ `database` steuern, welche Engine-Typen und Versionen provisioniert werden dürfen. |

---

## Feature 2.1 — Service Catalog: Logisches Template-Modell

### User Story

Als Requester möchte ich aus einem Katalog verfügbarer IT-Services auswählen und die Parameter pro Service konfigurieren, damit meine Bestellung vollständig und korrekt für das automatisierte Provisioning vorbereitet ist.

---

### Logisches Datenmodell

Das Datenmodell ist quellenagnostisch: Die Datenstrukturen können aus einer Datenbank, YAML-Dateien, einer externen API oder einer Kombination davon stammen. Die API-Contracts definieren das Austauschformat; die interne Persistierung ist nicht Bestandteil dieser Spec.

#### ServiceTemplate

```
ServiceTemplate {
  id:                 string (UUID)          // interne ID, unveränderlich
  slug:               string                 // menschenlesbarer Bezeichner, URL-sicher (z.B. "vm-linux", "db-postgres")
  version:            string                 // SemVer (z.B. "1.0.0", "2.1.3")
  type:               ServiceType (Enum)     // vm | database | container | storage | network | custom
  display_name:       string                 // Anzeigename im Catalog (z.B. "Linux Virtual Machine")
  description:        string                 // Kurzbeschreibung für Catalog-Ansicht (max. 500 Zeichen)
  category:           string                 // freie Kategorie-Zuordnung (z.B. "Compute", "Database")
  icon_identifier:    string (optional)      // Bezeichner für Frontend-Icon, kein URL
  parameters:         ParameterDefinition[]  // geordnete Liste aller Parameter
  status:             TemplateStatus (Enum)  // active | deprecated | disabled
  tofu_module_source: string                 // Tofu-Modul-Pfad oder Registry-Referenz
  created_at:         ISO-8601 datetime
  deprecated_at:      ISO-8601 datetime (optional)
  deprecated_by:      string (UUID, optional) // ID des Nachfolger-Templates
  estimated_cost_eur_per_month: decimal (optional)   // Geschätzte monatliche Kosten in EUR, genutzt für Approval-Schwellwertregeln (Feature 8.1)
  approval_always_required:     boolean (default: false) // Erzwingt Approval unabhängig von Approval-Regeln (Feature 8.1)
  metadata:           object (optional)      // erweiterbare Key-Value-Paare für künftige Felder
}
```

#### ParameterDefinition

```
ParameterDefinition {
  key:                string                 // interner Bezeichner, unique innerhalb eines Templates (z.B. "cpu_cores")
  label:              string                 // Anzeigename im Formular (z.B. "CPU-Kerne")
  description:        string (optional)      // Hilfetextfür den User
  type:               ParameterType (Enum)   // string | integer | float | boolean | enum | range_integer | range_float | size_bytes
  required:           boolean
  default_value:      any (optional)         // muss dem type entsprechen
  tofu_variable_name: string                 // Name der OpenTofu-Variable (snake_case, unique innerhalb des Templates)
  display_order:      integer                // Reihenfolge der Darstellung im Formular
  group:              string (optional)      // Gruppierung verwandter Parameter (z.B. "Netzwerk", "Storage")
  constraints:        ParameterConstraints   // typ-spezifische Einschränkungen (s.u.)
  depends_on:         DependencyRule[]       // Bedingungen, unter denen dieser Parameter sichtbar/aktiv ist
  affects_options_of: string[]               // keys anderer Parameter, deren Optionen sich bei Änderung dieses Parameters ändern
}
```

#### ParameterConstraints (typ-spezifisch)

```
// Für type = "integer" oder "float":
IntegerConstraints {
  min: number (optional)
  max: number (optional)
  step: number (optional)      // erlaubte Schrittweite
  unit: string (optional)      // Anzeigeeinheit (z.B. "Kerne", "GB", "MB/s")
}

// Für type = "string":
StringConstraints {
  min_length: integer (optional)
  max_length: integer (optional)
  pattern:    string (optional)  // regulärer Ausdruck (ECMA-262)
  allowed_values: string[] (optional)  // Whitelist; wenn gesetzt, ist dies eine freie Enum-Alternative
}

// Für type = "enum":
EnumConstraints {
  options: EnumOption[]         // statische Optionsliste (kann durch DynamicOptions überschrieben werden)
}

EnumOption {
  value:   string               // technischer Wert (geht in JSON-Export)
  label:   string               // Anzeigename
  enabled: boolean              // false = Option existiert, ist aber nicht wählbar (z.B. veraltet)
  metadata: object (optional)   // erweiterbar, z.B. {"region": "de-1"}
}

// Für type = "range_integer" oder "range_float":
RangeConstraints {
  min:  number
  max:  number
  step: number (optional)
  unit: string (optional)
}

// Für type = "size_bytes":
SizeBytesConstraints {
  min_bytes: integer
  max_bytes: integer
  display_unit: string          // bevorzugte Anzeigeeinheit: "GB" | "TB" | "MB"
  // Eingabe erfolgt in display_unit, Storage in Bytes
}

// Für type = "boolean":
// keine zusätzlichen Constraints nötig
```

#### DependencyRule

```
DependencyRule {
  parameter_key: string         // key des Parameters, von dem diese Abhängigkeit abhängt
  operator:      string         // "eq" | "neq" | "in" | "not_in" | "gt" | "lt" | "gte" | "lte"
  value:         any            // Vergleichswert (oder Array bei "in"/"not_in")
  effect:        string         // "visible" | "required" | "disabled"
  // Semantik: Wenn [parameter_key] [operator] [value], dann ist dieser Parameter [effect]
  // Wenn effect = "visible": Parameter ist nur sichtbar, wenn Bedingung erfüllt
  // Wenn effect = "required": Parameter ist nur required, wenn Bedingung erfüllt
  // Wenn effect = "disabled": Parameter ist nicht editierbar (wird mit default_value befüllt)
}
```

#### JSON-Export-Struktur (Schnittstelle zu OpenTofu)

```
TofuVariablesPayload {
  module_source: string                      // aus ServiceTemplate.tofu_module_source
  variables: {
    [tofu_variable_name]: resolved_value     // nur Parameter, deren depends_on vollständig erfüllt sind
  }
}
```

Regeln für den JSON-Export:
- Parameter mit nicht erfüllten `depends_on`-Bedingungen werden **nicht** in das Payload aufgenommen.
- Werte werden in dem Typ übergeben, der dem `type` entspricht (integer als Zahl, nicht als String).
- `size_bytes`-Parameter werden immer als Integer in Bytes exportiert, unabhängig von der Anzeigeeinheit.
- Boolean-Parameter werden als `true`/`false` exportiert.
- Enum-Parameter exportieren den `value` (nicht den `label`) der gewählten Option.

---

### Requirements

- **REQ-100:** Das System muss ServiceTemplates mit einem eindeutigen Composite-Key aus `slug` + `version` verwalten. Zwei Templates mit gleichem `slug` und gleicher `version` dürfen nicht existieren.
- **REQ-101:** ServiceTemplates sind nach ihrer Erstellung unveränderlich. Eine inhaltliche Änderung an einem Template (Parameter, Constraints, tofu_module_source) erfordert das Anlegen einer neuen Version mit erhöhter SemVer-Versionsnummer.
- **REQ-102:** Das System muss mindestens die ServiceTypes `vm`, `database`, `container`, `storage`, `network` und `custom` unterstützen. Der Typ `custom` dient als Erweiterungspunkt für zukünftige Service-Arten.
- **REQ-103:** Ein ServiceTemplate muss mindestens einen Parameter vom Typ `required: true` enthalten.
- **REQ-104:** Jeder `tofu_variable_name` innerhalb eines Templates muss eindeutig sein. Über verschiedene Templates hinweg dürfen gleiche Namen verwendet werden.
- **REQ-105:** Das System muss zwischen den Template-Status unterscheiden: `active` (bestellbar), `deprecated` (weiterhin bestellbar, aber mit Hinweis, dass eine neuere Version existiert), `disabled` (nicht bestellbar, nur noch in historischen Bestellungen sichtbar).
- **REQ-106:** Ein Template kann nur auf `deprecated` gesetzt werden, wenn `deprecated_by` auf ein aktives Nachfolger-Template verweist.
- **REQ-107:** Ein Template kann nur auf `disabled` gesetzt werden, wenn keine offenen Orders (Status: `pending`, `approved`, `provisioning`) dieses Template verwenden.
- **REQ-108:** Der Service Catalog muss filterbar sein nach: `type`, `category`, `status`. Standard-Filter beim Laden: `status = active`.
- **REQ-109:** Der Service Catalog muss nach `display_name` und `description` durchsuchbar sein (case-insensitive Substring-Suche).
- **REQ-110:** Wenn ein Requester einen Service zum Warenkorb hinzufügt (Feature 3.1), wird immer die spezifische Template-Version gespeichert, die zum Zeitpunkt der Auswahl aktiv war. Spätere Template-Updates wirken sich nicht auf bestehende Order-Items aus.
- **REQ-111:** Das System muss `DependencyRules` zur Laufzeit auflösen können: Wenn Parameter A einen bestimmten Wert hat, werden abhängige Parameter B dynamisch sichtbar, required oder disabled.
- **REQ-112:** Das System muss einen Endpoint bereitstellen, der für einen gegebenen Parameterwert die dynamisch verfügbaren Optionen eines abhängigen Parameters zurückgibt (z.B.: OS = "windows" → verfügbare Disk-Typen = ["ntfs", "refs"]).
- **REQ-113:** Der JSON-Export für OpenTofu darf ausschließlich Parameter enthalten, deren `depends_on`-Bedingungen vollständig erfüllt sind. Nicht erfüllte Parameter werden weggelassen, nicht mit `null` gefüllt.
- **REQ-114:** `size_bytes`-Parameter werden im JSON-Export immer als Integer in Bytes repräsentiert, unabhängig von der Anzeigeeinheit, die dem User präsentiert wird.
- **REQ-115:** Das System muss Kombinationsvalidierungen unterstützen, die mehrere Parameter gemeinsam prüfen (z.B. CPU + RAM müssen eine zulässige Kombination ergeben). Diese Regeln sind im Template als `cross_parameter_rules` definiert.
- **REQ-116:** Die Katalog-API muss Paginierung unterstützen (Cursor-basiert oder Offset/Limit).
- **REQ-117:** Für die Order-Erstellung (Feature 3.1) muss das System eine Parameter-Validierung gegen das Template anbieten, die alle Validation Rules und DependencyRules auswertet und eine vollständige Liste aller Violations zurückgibt — keine Fail-Fast-Logik.
- **REQ-118:** Ein Template muss versioniert abrufbar sein: Sowohl die neueste Version als auch eine spezifische Version über `slug` + `version` müssen abrufbar sein.
- **REQ-119:** Wenn ein `deprecated`-Template abgerufen wird, muss die Response eine Referenz auf das Nachfolger-Template enthalten (`deprecated_by` mit Template-ID und Slug der Nachfolger-Version).
- **REQ-120:** Das System muss einen strukturierten Diff zwischen zwei Versionen desselben Templates (gleicher `slug`, unterschiedliche `version`) zurückgeben können, der hinzugefügte, entfernte und geänderte Parameter ausweist.
- **REQ-121:** Parameter vom Typ `enum` können entweder statische Optionen (in `constraints.options`) oder dynamisch aufgelöste Optionen haben. Beide Varianten müssen über denselben API-Vertrag abgefragt werden können.
- **REQ-122:** Eine Multi-Service-Bestellung (mehrere ServiceTemplates in einer Order) muss gegen jedes Template individuell validiert werden. Es gibt keine templateübergreifenden Constraints.
- **REQ-123:** Das System muss einen Admin-Endpoint bereitstellen, über den neue Templates registriert werden können. Die Registrierung ist eine atomare Operation — entweder wird das gesamte Template übernommen oder abgelehnt (keine Teilregistrierung).
- **REQ-124:** Templates vom Typ `custom` müssen mindestens `tofu_module_source` und einen Parameter enthalten. Es gibt keine weiteren erzwungenen Parameter für diesen Typ.
- **REQ-125:** Das System muss `cross_parameter_rules` vor dem Persistieren eines Templates validieren: Alle referenzierten `parameter_key`-Werte müssen in den `parameters` des Templates existieren.

---

### Validation Rules

- **VAL-47:** `slug` — Muss dem Muster `^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$` entsprechen — "Slug darf nur Kleinbuchstaben, Ziffern und Bindestriche enthalten und muss mit einem alphanumerischen Zeichen beginnen und enden (3–64 Zeichen)."
- **VAL-48:** `version` — Muss gültige SemVer-Notation sein (MAJOR.MINOR.PATCH, optional Pre-release) gemäß semver.org — "Versionsformat ungültig. Erwartet: MAJOR.MINOR.PATCH (z.B. '1.0.0')."
- **VAL-49:** `slug` + `version` (Composite-Key) — Kombination muss systemweit eindeutig sein — "Ein Template mit diesem Slug und dieser Version existiert bereits."
- **VAL-50:** `type` — Muss ein gültiger `ServiceType`-Enum-Wert sein — "Unbekannter Service-Typ. Erlaubte Werte: vm, database, container, storage, network, custom."
- **VAL-51:** `display_name` — Pflichtfeld, 3–100 Zeichen — "Anzeigename muss zwischen 3 und 100 Zeichen lang sein."
- **VAL-52:** `description` — Optional, max. 500 Zeichen — "Beschreibung darf maximal 500 Zeichen lang sein."
- **VAL-53:** `tofu_module_source` — Pflichtfeld, nicht leer, max. 500 Zeichen, muss einem der Muster entsprechen: lokaler Pfad (`./...`), Registry-Referenz (`registry.terraform.io/...`), Git-URL (`git::https://...`) — "Ungültige Tofu-Modulquelle. Erlaubte Formate: lokaler Pfad, Terraform Registry oder Git-URL."
- **VAL-54:** `parameters` — Muss mindestens einen Eintrag mit `required: true` enthalten — "Ein Template muss mindestens einen Pflichtparameter definieren."
- **VAL-55:** `ParameterDefinition.key` — Muss dem Muster `^[a-z_][a-z0-9_]{0,62}$` entsprechen und innerhalb des Templates eindeutig sein — "Parameterschlüssel darf nur Kleinbuchstaben, Ziffern und Unterstriche enthalten, muss mit einem Buchstaben oder Unterstrich beginnen und innerhalb des Templates eindeutig sein."
- **VAL-56:** `ParameterDefinition.tofu_variable_name` — Muss dem Muster `^[a-z_][a-z0-9_]{0,62}$` entsprechen (snake_case) und innerhalb des Templates eindeutig sein — "Tofu-Variablenname muss snake_case sein und innerhalb des Templates eindeutig sein."
- **VAL-57:** `ParameterDefinition.type` — Muss ein gültiger `ParameterType`-Enum-Wert sein — "Unbekannter Parametertyp. Erlaubte Werte: string, integer, float, boolean, enum, range_integer, range_float, size_bytes."
- **VAL-58:** `ParameterDefinition.default_value` — Wenn angegeben, muss der Wert dem deklarierten `type` entsprechen und alle Constraints erfüllen — "Standardwert entspricht nicht dem deklarierten Typ oder verletzt Constraints."
- **VAL-59:** `IntegerConstraints.min` / `IntegerConstraints.max` — Wenn beide angegeben: `min` muss kleiner als `max` sein — "Der Mindestwert muss kleiner als der Maximalwert sein."
- **VAL-60:** `IntegerConstraints.step` — Wenn angegeben: muss positiv sein und kleiner oder gleich `(max - min)` — "Schrittweite muss positiv und kleiner oder gleich dem Wertebereich sein."
- **VAL-61:** `EnumConstraints.options` — Muss mindestens eine Option mit `enabled: true` enthalten — "Eine Enum-Option muss mindestens einen wählbaren Wert definieren."
- **VAL-62:** `EnumOption.value` — Werte innerhalb einer `options`-Liste müssen eindeutig sein — "Optionswerte innerhalb eines Parameters müssen eindeutig sein."
- **VAL-63:** `SizeBytesConstraints.min_bytes` / `max_bytes` — `min_bytes` muss >= 0 und kleiner als `max_bytes` sein — "Minimale Bytegröße muss nicht-negativ und kleiner als die maximale Bytegröße sein."
- **VAL-64:** `SizeBytesConstraints.display_unit` — Muss einer der erlaubten Werte sein: "MB", "GB", "TB" — "Ungültige Anzeigeeinheit. Erlaubte Werte: MB, GB, TB."
- **VAL-65:** `DependencyRule.parameter_key` — Muss einem existierenden `key` innerhalb desselben Templates entsprechen — "Abhängigkeit referenziert einen nicht existierenden Parameter."
- **VAL-66:** `DependencyRule.operator` — Muss einer der erlaubten Werte sein: "eq", "neq", "in", "not_in", "gt", "lt", "gte", "lte" — "Unbekannter Operator in Abhängigkeitsregel."
- **VAL-67:** `DependencyRule.effect` — Muss einer der erlaubten Werte sein: "visible", "required", "disabled" — "Unbekannter Effekt in Abhängigkeitsregel. Erlaubte Werte: visible, required, disabled."
- **VAL-68:** `cross_parameter_rules[].parameter_keys` — Alle referenzierten Keys müssen als `ParameterDefinition.key` im Template existieren — "Kombinationsregel referenziert einen nicht existierenden Parameter."
- **VAL-69:** Beim Setzen auf `deprecated`: `deprecated_by` ist Pflicht und muss auf ein Template mit `status = active` verweisen — "Ein Template kann nur als veraltet markiert werden, wenn ein aktives Nachfolger-Template angegeben wird."
- **VAL-70:** Beim Setzen auf `disabled`: Das Template darf keine offenen Orders (Status: pending, approved, provisioning) referenzieren — "Template kann nicht deaktiviert werden, solange offene Bestellungen existieren."
- **VAL-71:** `estimated_cost_eur_per_month` — Wenn angegeben, muss positiver Dezimalwert sein, max. 2 Nachkommastellen — "Die geschätzten monatlichen Kosten müssen ein positiver EUR-Betrag sein."

---

### API Contract

#### Endpoint 37 — List Service Templates (Catalog)

- **Endpoint:** `GET /api/v1/catalog/templates`
- **Auth:** requester, approver, admin
- **Query Params:**
  ```
  status:   string (optional, default: "active")       // "active" | "deprecated" | "disabled" | "all"
  type:     string (optional)                           // filter by ServiceType
  category: string (optional)                           // filter by category (exact match, case-insensitive)
  q:        string (optional)                           // full-text search in display_name and description
  limit:    integer (optional, default: 20, max: 100)
  offset:   integer (optional, default: 0)
  ```
- **Response 200:**
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
        "created_at": "2025-01-15T08:00:00Z",
        "deprecated_at": null,
        "deprecated_by": null
      }
    ],
    "total": 42,
    "limit": 20,
    "offset": 0
  }
  ```
  Hinweis: Die Catalog-Liste enthält keine `parameters`. Parameter werden über Endpoint 38 abgerufen.
- **Response 400:** `{ "error": "INVALID_FILTER", "message": "..." }` — Ungültiger Status- oder Type-Wert.
- **Response 401:** Nicht authentifiziert.

---

#### Endpoint 38 — Get Service Template Details

- **Endpoint:** `GET /api/v1/catalog/templates/{slug}`
- **Auth:** requester, approver, admin
- **Query Params:**
  ```
  version: string (optional)  // SemVer; wenn nicht angegeben, wird die neueste aktive Version zurückgegeben
  ```
- **Response 200:**
  ```json
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
    "tofu_module_source": "git::https://gitlab.internal/tofu-modules/vm-linux.git?ref=v2.0.0",
    "parameters": [
      {
        "key": "cpu_cores",
        "label": "CPU-Kerne",
        "description": "Anzahl der virtuellen CPU-Kerne.",
        "type": "integer",
        "required": true,
        "default_value": 2,
        "tofu_variable_name": "cpu_cores",
        "display_order": 1,
        "group": "Compute",
        "constraints": {
          "min": 1,
          "max": 64,
          "step": 1,
          "unit": "Kerne"
        },
        "depends_on": [],
        "affects_options_of": []
      },
      {
        "key": "os_type",
        "label": "Betriebssystem",
        "description": null,
        "type": "enum",
        "required": true,
        "default_value": null,
        "tofu_variable_name": "os_type",
        "display_order": 3,
        "group": "System",
        "constraints": {
          "options": [
            { "value": "ubuntu-22.04", "label": "Ubuntu 22.04 LTS", "enabled": true },
            { "value": "ubuntu-24.04", "label": "Ubuntu 24.04 LTS", "enabled": true },
            { "value": "windows-server-2022", "label": "Windows Server 2022", "enabled": true }
          ]
        },
        "depends_on": [],
        "affects_options_of": ["disk_type"]
      },
      {
        "key": "disk_type",
        "label": "Disk-Typ",
        "description": "Verfügbare Typen hängen vom gewählten Betriebssystem ab.",
        "type": "enum",
        "required": true,
        "default_value": null,
        "tofu_variable_name": "disk_type",
        "display_order": 5,
        "group": "Storage",
        "constraints": {
          "options": []
        },
        "depends_on": [
          {
            "parameter_key": "os_type",
            "operator": "neq",
            "value": null,
            "effect": "visible"
          }
        ],
        "affects_options_of": []
      }
    ],
    "cross_parameter_rules": [
      {
        "rule_id": "cpu-ram-ratio",
        "description": "RAM muss mindestens 2 GB pro CPU-Kern betragen.",
        "parameter_keys": ["cpu_cores", "ram_gb"],
        "expression": "ram_gb >= cpu_cores * 2",
        "error_message": "RAM muss mindestens 2 GB pro CPU-Kern betragen."
      }
    ],
    "created_at": "2025-01-15T08:00:00Z",
    "deprecated_at": null,
    "deprecated_by": null,
    "estimated_cost_eur_per_month": 120.50,
    "approval_always_required": false,
    "metadata": {}
  }
  ```
- **Response 200 (deprecated template):** Wie oben, zusätzlich:
  ```json
  {
    "status": "deprecated",
    "deprecated_at": "2025-06-01T00:00:00Z",
    "deprecated_by": {
      "id": "9c6e4f11-1234-5678-abcd-ef0123456789",
      "slug": "vm-linux",
      "version": "3.0.0"
    }
  }
  ```
- **Response 404:** `{ "error": "TEMPLATE_NOT_FOUND", "message": "No template found for slug 'vm-linux' and version '2.0.0'." }`
- **Response 410:** `{ "error": "TEMPLATE_DISABLED", "message": "This template has been disabled and is no longer available." }` — Nur für `disabled` Templates, wenn kein expliziter Version-Parameter übergeben wurde. Bei expliziter Versionsangabe wird auch ein `disabled` Template zurückgegeben (für historische Ansicht in Orders).

---

#### Endpoint 39 — List Template Versions

- **Endpoint:** `GET /api/v1/catalog/templates/{slug}/versions`
- **Auth:** requester, approver, admin
- **Query Params:**
  ```
  status: string (optional, default: "all")  // filter by TemplateStatus
  ```
- **Response 200:**
  ```json
  {
    "slug": "vm-linux",
    "versions": [
      {
        "id": "9c6e4f11-1234-5678-abcd-ef0123456789",
        "version": "3.0.0",
        "status": "active",
        "created_at": "2025-10-01T00:00:00Z"
      },
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "version": "2.0.0",
        "status": "deprecated",
        "deprecated_at": "2025-06-01T00:00:00Z"
      }
    ]
  }
  ```
- **Response 404:** `{ "error": "SLUG_NOT_FOUND", "message": "No templates found for slug 'vm-linux'." }`

---

#### Endpoint 40 — Get Template Version Diff

- **Endpoint:** `GET /api/v1/catalog/templates/{slug}/diff`
- **Auth:** approver, admin
- **Query Params:**
  ```
  from_version: string (required)  // SemVer der Basisversion
  to_version:   string (required)  // SemVer der Zielversion
  ```
- **Response 200:**
  ```json
  {
    "slug": "vm-linux",
    "from_version": "2.0.0",
    "to_version": "3.0.0",
    "changes": {
      "added_parameters": [
        { "key": "backup_enabled", "label": "Backup aktivieren", "type": "boolean" }
      ],
      "removed_parameters": [
        { "key": "legacy_bios", "label": "Legacy BIOS" }
      ],
      "modified_parameters": [
        {
          "key": "cpu_cores",
          "changes": {
            "constraints.max": { "from": 32, "to": 64 }
          }
        }
      ],
      "tofu_module_source_changed": {
        "from": "git::https://gitlab.internal/tofu-modules/vm-linux.git?ref=v2.0.0",
        "to": "git::https://gitlab.internal/tofu-modules/vm-linux.git?ref=v3.0.0"
      }
    }
  }
  ```
- **Response 400:** `{ "error": "INVALID_VERSION", "message": "from_version and to_version are required and must be valid SemVer strings." }`
- **Response 404:** `{ "error": "VERSION_NOT_FOUND", "message": "..." }` — Eine der Versionen existiert nicht.

---

#### Endpoint 41 — Resolve Dynamic Parameter Options

- **Endpoint:** `POST /api/v1/catalog/templates/{slug}/resolve-options`
- **Auth:** requester, approver, admin
- **Query Params:**
  ```
  version: string (optional)  // SemVer; Standard: neueste aktive Version
  ```
- **Request Body:**
  ```json
  {
    "parameter_key": "disk_type",
    "current_values": {
      "os_type": "windows-server-2022",
      "cpu_cores": 4
    }
  }
  ```
  `current_values`: Key-Value-Map der bereits befüllten Parameter. Wird genutzt, um abhängige Optionen aufzulösen.
- **Response 200:**
  ```json
  {
    "parameter_key": "disk_type",
    "options": [
      { "value": "ntfs", "label": "NTFS", "enabled": true },
      { "value": "refs", "label": "ReFS", "enabled": true }
    ],
    "is_visible": true,
    "is_required": true,
    "is_disabled": false
  }
  ```
  `is_visible`, `is_required`, `is_disabled` geben den aufgelösten Zustand des Parameters basierend auf den `depends_on`-Regeln zurück.
- **Response 400:** `{ "error": "UNKNOWN_PARAMETER", "message": "Parameter 'disk_type' does not exist in template 'vm-linux' v2.0.0." }`
- **Response 404:** Template nicht gefunden.

---

#### Endpoint 42 — List Service Categories

- **Endpoint:** `GET /api/v1/catalog/categories`
- **Auth:** requester, approver, admin
- **Response 200:**
  ```json
  {
    "categories": [
      { "name": "Compute", "template_count": 5 },
      { "name": "Database", "template_count": 3 },
      { "name": "Network", "template_count": 2 }
    ]
  }
  ```
  Nur Kategorien mit mindestens einem Template im Status `active` oder `deprecated` werden zurückgegeben.

---

#### Endpoint 43 — Validate Order Parameters Against Template

- **Endpoint:** `POST /api/v1/catalog/templates/{slug}/validate`
- **Auth:** requester, approver, admin
- **Query Params:**
  ```
  version: string (optional)  // SemVer; Standard: neueste aktive Version
  ```
- **Request Body:**
  ```json
  {
    "parameters": {
      "cpu_cores": 4,
      "ram_gb": 4,
      "os_type": "ubuntu-22.04",
      "disk_type": "ext4",
      "disk_size_bytes": 107374182400
    }
  }
  ```
- **Response 200** (immer HTTP 200, Violations im Body):
  ```json
  {
    "valid": false,
    "violations": [
      {
        "parameter_key": "ram_gb",
        "rule": "cross_parameter_rule:cpu-ram-ratio",
        "message": "RAM muss mindestens 2 GB pro CPU-Kern betragen. Erwartet: >= 8 GB, erhalten: 4 GB."
      },
      {
        "parameter_key": "disk_type",
        "rule": "VAL-constraints",
        "message": "Wert 'ext4' ist für os_type 'windows-server-2022' nicht erlaubt."
      }
    ],
    "warnings": [
      {
        "parameter_key": null,
        "type": "TEMPLATE_DEPRECATED",
        "message": "This template version is deprecated. A newer version (3.0.0) is available."
      }
    ]
  }
  ```
  Bei `valid: true` ist `violations` ein leeres Array. `warnings` enthält nicht-blockierende Hinweise (z.B. Template deprecated).
- **Response 404:** Template nicht gefunden.
- **Response 422:** `{ "error": "DISABLED_TEMPLATE", "message": "Validation is not available for disabled templates." }`

---

#### Endpoint 44 — Register New Template (Admin)

- **Endpoint:** `POST /api/v1/admin/catalog/templates`
- **Auth:** admin
- **Request Body:**
  ```json
  {
    "slug": "vm-linux",
    "version": "3.0.0",
    "type": "vm",
    "display_name": "Linux Virtual Machine",
    "description": "Standard-Linux-VM mit konfigurierbaren CPU-, RAM- und Storage-Werten.",
    "category": "Compute",
    "icon_identifier": "server-linux",
    "tofu_module_source": "git::https://gitlab.internal/tofu-modules/vm-linux.git?ref=v3.0.0",
    "parameters": [ "..." ],
    "cross_parameter_rules": [ "..." ],
    "estimated_cost_eur_per_month": 120.50,
    "approval_always_required": false,
    "metadata": {}
  }
  ```
- **Response 201:**
  ```json
  {
    "id": "9c6e4f11-1234-5678-abcd-ef0123456789",
    "slug": "vm-linux",
    "version": "3.0.0",
    "status": "active",
    "created_at": "2026-03-26T10:00:00Z"
  }
  ```
- **Response 400:** `{ "error": "VALIDATION_ERROR", "violations": [ { "field": "slug", "message": "..." } ] }` — Strukturvalidierungsfehler (VAL-47 bis VAL-70). Die Operation ist atomar: Entweder alles wird übernommen oder nichts.
- **Response 409:** `{ "error": "DUPLICATE_TEMPLATE", "message": "A template with slug 'vm-linux' and version '3.0.0' already exists." }`
- **Response 403:** Unzureichende Berechtigung (nicht admin).

---

#### Endpoint 44b — Update Template Status (Admin)

- **Endpoint:** `PATCH /api/v1/admin/catalog/templates/{id}/status`
- **Auth:** admin
- **Request Body:**
  ```json
  {
    "status": "deprecated",
    "deprecated_by": "9c6e4f11-1234-5678-abcd-ef0123456789"
  }
  ```
  `deprecated_by` ist Pflicht bei `status = "deprecated"`. Bei `status = "disabled"` ist kein zusätzliches Feld erforderlich.
- **Response 200:**
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "slug": "vm-linux",
    "version": "2.0.0",
    "status": "deprecated",
    "deprecated_at": "2026-03-26T10:05:00Z",
    "deprecated_by": {
      "id": "9c6e4f11-1234-5678-abcd-ef0123456789",
      "slug": "vm-linux",
      "version": "3.0.0"
    }
  }
  ```
- **Response 400:** `{ "error": "VALIDATION_ERROR", "message": "..." }` — Verletzung von VAL-69 oder VAL-70.
- **Response 404:** Template nicht gefunden.
- **Response 409:** `{ "error": "INVALID_STATUS_TRANSITION", "message": "Cannot transition from 'disabled' to 'deprecated'." }` — Erlaubte Übergänge: `active → deprecated`, `active → disabled`, `deprecated → disabled`. Nicht erlaubt: `disabled → *`, `deprecated → active`.

---

### Edge Cases

- **EC-66:** Ein Requester ruft den Catalog ab, während ein Admin gleichzeitig ein Template auf `disabled` setzt. → Das Template muss für den Requester noch in der laufenden Request-Antwort erscheinen. Konsistenz gilt pro Request, nicht per Live-Stream.
- **EC-67:** Endpoint 38 wird ohne `version`-Parameter für einen Slug aufgerufen, bei dem alle Versionen `deprecated` sind (keine `active`-Version). → Die neueste `deprecated`-Version wird zurückgegeben. Response enthält `"status": "deprecated"` und die Referenz auf `deprecated_by`, sofern vorhanden.
- **EC-68:** Endpoint 38 wird ohne `version`-Parameter für einen Slug aufgerufen, bei dem alle Versionen `disabled` sind. → HTTP 410 `TEMPLATE_DISABLED`.
- **EC-69:** Zwei Admin-Requests registrieren gleichzeitig das gleiche `slug` + `version`-Paar. → Nur einer darf erfolgreich sein (HTTP 201). Der zweite erhält HTTP 409. Datenbankebene muss diesen Unique-Constraint erzwingen.
- **EC-70:** Ein Template enthält einen Parameter mit `depends_on` auf einen anderen Parameter, der selbst ein `depends_on` hat (verschachtelte Abhängigkeiten). → Das System muss transitive Abhängigkeiten korrekt auflösen. Die Auflösung erfolgt in Topologischer Reihenfolge (kein zyklischer Graph erlaubt; zyklische `depends_on` werden bei der Template-Registrierung abgelehnt, REQ-125).
- **EC-71:** Endpoint 41 wird aufgerufen, und `current_values` enthält einen Parameter-Key, der im Template nicht existiert. → Der unbekannte Key wird ignoriert. Nur bekannte Parameter fließen in die Optionsauflösung ein. Keine Fehlermeldung.
- **EC-72:** Endpoint 43 (Validierung) wird für ein Template aufgerufen, dessen Parameter einen `cross_parameter_rule` mit einer Ausdruck-Syntax enthalten, die zur Laufzeit nicht ausgewertet werden kann (z.B. Referenz auf nicht enthaltenen Parameter). → HTTP 500 mit `{ "error": "RULE_EVALUATION_ERROR", "message": "..." }`. Dieser Fehler muss geloggt werden.
- **EC-73:** Ein Template mit `status = active` soll auf `deprecated` gesetzt werden, aber das referenzierte `deprecated_by`-Template existiert nicht. → HTTP 400, VAL-69 greift. Die Operation wird abgelehnt.
- **EC-74:** Ein Template soll auf `disabled` gesetzt werden. Die Prüfung auf offene Orders (REQ-107) liefert zur Prüfzeit keine offenen Orders, aber eine neue Order wird in der Millisekunde zwischen Prüfung und Status-Update angelegt. → Das System muss diese Race Condition durch eine transaktionale Prüfung absichern: Die Status-Änderung und die Order-Prüfung müssen in derselben Transaktion erfolgen. Ist keine transaktionale Absicherung möglich, wird die Status-Änderung abgelehnt und dem Admin ein Retry nahegelegt.
- **EC-75:** Feature 3.1 (Checkout) legt ein Order-Item für Template `vm-linux v2.0.0` an. Unmittelbar danach wird `vm-linux v2.0.0` auf `disabled` gesetzt. → Das Order-Item bleibt erhalten. Die Order referenziert weiterhin die gespeicherte Template-Version. Endpoint 38 mit explizitem `version=2.0.0` gibt das Template zurück (für historische Ansicht). Das Provisioning verwendet die gespeicherten Parameter, nicht das aktuelle Template.
- **EC-76:** Endpoint 43 (Validierung) wird mit einem Parameter aufgerufen, dessen `depends_on`-Bedingung nicht erfüllt ist (Parameter sollte laut Regelwerk nicht sichtbar sein). → Der Parameter wird ignoriert und nicht validiert. Er erscheint auch nicht als Violation. Er wird nicht in den JSON-Export aufgenommen (REQ-113).
- **EC-77:** Ein Admin versucht, eine neue Template-Version mit einer niedrigeren SemVer-Nummer zu registrieren als eine bereits existierende Version des gleichen Slugs (z.B. `v1.5.0` nach `v2.0.0`). → Die Registrierung ist erlaubt (SemVer-Ordnung wird nicht erzwungen). Das System warnt jedoch mit einem `warning`-Feld in der Response: `{ "warning": "LOWER_VERSION_REGISTERED", "message": "A higher version (2.0.0) already exists for slug 'vm-linux'." }`. Die niedrigere Version wird als `active` registriert.
- **EC-78:** Endpoint 37 (Catalog List) wird mit `q` (Suchbegriff) aufgerufen, der nur Leerzeichen enthält. → Der Suchbegriff wird als leer behandelt (trimmen), kein Filter wird angewendet. Alle Templates entsprechend anderen Filtern werden zurückgegeben.
- **EC-79:** Ein Template vom Typ `vm` enthält einen Parameter `disk_size_bytes` vom Typ `size_bytes`. Der User gibt im Formular "500 GB" ein. Im JSON-Export (OpenTofu) muss der Wert `536870912000` (Bytes) stehen, nicht `500`. → Die Konvertierung erfolgt serverseitig beim Aufbau des Tofu-Payloads (REQ-114). Das Frontend übergibt den Wert bereits in Bytes im API-Request (Konvertierung im Frontend obligatorisch, dokumentiert in der API-Spezifikation).
- **EC-80:** Feature 4.1 (Tofu Job-Dispatcher) ruft Template-Details für eine Order ab, deren Template-Version inzwischen `disabled` ist. → Feature 4.1 muss Template-Details immer mit expliziter Versionsangabe abrufen (Endpoint 38 + `version`-Parameter). Disabled Templates sind mit explizitem Version-Parameter weiterhin abrufbar. Dies ist das spezifizierte Verhalten für historische Bestellungen (EC-75).

---

*Stand: 2026-03-26 | Nummerierungsstand Ende: REQ-125, VAL-71, EC-80, Endpoint 44 (44b ist ein Sub-Endpoint, zählt nicht als eigener Endpoint) | Geändert: ServiceTemplate + Endpoint 38/44 um `estimated_cost_eur_per_month` und `approval_always_required` erweitert (Feature 8.1)*
