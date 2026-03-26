# Feature-Gruppe 9: Entwicklungs- und Test-Infrastruktur

**Version:** 1.0
**Datum:** 2026-03-26
**Status:** Draft

---

## Überblick

Diese Feature-Gruppe definiert die Infrastruktur, die ausschließlich für Entwicklung und Test benötigt wird. Sie ersetzt externe Abhängigkeiten (Active Directory, GitLab, CMDB) durch kontrollierte Stubs und Mocks und stellt konsistente Testdaten über einen Fixture-Mechanismus bereit.

**Geltungsbereich:** Ausschließlich Entwicklungs- und Testumgebungen. Keines der hier definierten Features darf in einer Produktionsumgebung aktiv sein.

**Abhängigkeiten zu anderen Feature-Gruppen:**
- Gruppe 1 (Identity & Access): Auth-Stub ersetzt den AD-basierten Authentifizierungsfluss aus Feature 1.1/1.2
- Gruppe 2 (Service Catalog): CMDB-Stub liefert Optionswerte, die Feature 2.1 dynamisch auflöst
- Gruppe 3 (Order Lifecycle): Test-Fixtures decken alle Order-Status aus Feature 3.3 ab
- Gruppe 4 (Provisioning Engine): GitLab-Mock ersetzt den echten Pipeline-Trigger aus Feature 4.1
- Gruppe 8 (Approval Workflow): Test-Fixtures decken ApprovalRequest-Status aus Feature 8.2 ab

---

## Feature 9.1: Auth-Stub

**User Story:**
Als Entwickler möchte ich mich im Entwicklungsmodus ohne Active Directory mit vordefinierten Dummy-Usern anmelden können, damit ich alle rollenbasierten Funktionen des Portals ohne AD-Anbindung testen kann.

---

### Requirements

- REQ-01: Das System MUSS einen Auth-Modus `stub` unterstützen, der ausschließlich über die Environment-Variable `AUTH_MODE=stub` aktiviert wird.
- REQ-02: Wenn `AUTH_MODE=stub` gesetzt ist, wird JEDE Authentifizierungsanfrage ausschließlich gegen die lokale Stub-Benutzerliste geprüft. Die AD/LDAP-Anbindung wird vollständig umgangen.
- REQ-03: Wenn `AUTH_MODE` nicht gesetzt oder auf einen anderen Wert als `stub` gesetzt ist, MUSS der Auth-Stub vollständig inaktiv sein. Stub-Endpunkte dürfen nicht erreichbar sein.
- REQ-04: Beim Systemstart MUSS geprüft werden, ob `AUTH_MODE=stub` in Kombination mit `ENV=production` (oder äquivalentem Produktions-Flag) gesetzt ist. In diesem Fall MUSS der Start mit einer expliziten Fehlermeldung abgebrochen werden.
- REQ-05: Der Auth-Stub MUSS folgende vier vordefinierte Dummy-User bereitstellen:

  | Username        | Anzeigename         | E-Mail                        | Rollen                  |
  |-----------------|---------------------|-------------------------------|-------------------------|
  | test-requester  | Test Requester      | requester@test.local          | requester               |
  | test-approver   | Test Approver       | approver@test.local           | approver                |
  | test-admin      | Test Admin          | admin@test.local              | admin                   |
  | test-multi      | Test Multi Role     | multi@test.local              | requester, approver     |

- REQ-06: Alle Dummy-User MÜSSEN das statische Passwort `stub-password` akzeptieren. Eine Passwortvalidierung gegen externe Systeme findet nicht statt.
- REQ-07: Der Auth-Stub MUSS einen Login ohne Passwort unterstützen: Wenn das Passwort-Feld leer oder nicht übergeben wird, wird der User dennoch authentifiziert (nur im Stub-Modus).
- REQ-08: Der Auth-Stub MUSS einen JWT-Token generieren, der strukturell und inhaltlich identisch zum Token des Produktivmodus ist. Insbesondere MÜSSEN folgende Claims enthalten sein: `sub` (username), `roles` (Array), `email`, `display_name`, `iat`, `exp`.
- REQ-09: Die Token-Laufzeit im Stub-Modus MUSS konfigurierbar sein (Environment-Variable `STUB_TOKEN_TTL_SECONDS`, Standardwert: 86400).
- REQ-10: Das JWT-Signing-Secret im Stub-Modus MUSS über `JWT_SECRET` konfiguriert werden. Ist `JWT_SECRET` nicht gesetzt und `AUTH_MODE=stub`, MUSS ein statisches Fallback-Secret `stub-jwt-secret-dev-only` verwendet werden. Diese Verwendung MUSS beim Start geloggt werden (Warn-Level).
- REQ-11: Stub-User-Daten DÜRFEN NICHT in einer Datenbank gespeichert werden. Sie liegen ausschließlich im Arbeitsspeicher (hardcodiert oder aus einer Konfigurationsdatei geladen).
- REQ-12: Der Stub MUSS im Response-Header `X-Auth-Mode: stub` zurückgeben, damit Clients und Tests den aktiven Modus erkennen können.
- REQ-13: Ein Login-Versuch mit einem unbekannten Username (nicht in der Stub-Liste) MUSS mit HTTP 401 abgelehnt werden, auch im Stub-Modus.
- REQ-14: Token-Invalidierung (Logout) im Stub-Modus MUSS clientseitig erfolgen (Token-Deletion). Eine serverseitige Blacklist ist im Stub-Modus nicht erforderlich.

---

### Validation Rules

- VAL-01: Feld `username` im Login-Request — MUSS nicht-leer sein — Fehlermeldung: `"username is required"`
- VAL-02: Feld `username` im Login-Request — MUSS einem der vier definierten Stub-Usernamen entsprechen — Fehlermeldung: `"invalid credentials"`
- VAL-03: `AUTH_MODE` Environment-Variable — Erlaubte Werte: `stub`, `ldap` (oder nicht gesetzt) — Fehlermeldung beim Start: `"Unknown AUTH_MODE value: {value}. Allowed: stub, ldap"`
- VAL-04: Kombination `AUTH_MODE=stub` + `ENV=production` — MUSS beim Start abgefangen werden — Fehlermeldung: `"FATAL: AUTH_MODE=stub must not be used in production environment. Aborting."`

---

### API Contract

**Endpoint 1: Login (Stub)**

- Endpoint: `POST /api/v1/auth/login`
- Hinweis: Identische URL wie der Produktiv-Login. Routing erfolgt intern über den aktiven Auth-Mode.
- Request Body:
```json
{
  "username": "test-requester",
  "password": "stub-password"
}
```
- Response 200:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "username": "test-requester",
    "display_name": "Test Requester",
    "email": "requester@test.local",
    "roles": ["requester"]
  },
  "expires_at": "2026-03-27T12:00:00Z"
}
```
- Response Headers: `X-Auth-Mode: stub`
- Response 401:
```json
{
  "error": "invalid_credentials",
  "message": "invalid credentials"
}
```
- Response 400:
```json
{
  "error": "validation_error",
  "message": "username is required"
}
```
- Response 503: Wird im Stub-Modus nicht zurückgegeben (kein externer Aufruf)

**Endpoint 2: Stub-User-Liste (nur im Stub-Modus)**

- Endpoint: `GET /api/v1/dev/auth/stub-users`
- Beschreibung: Gibt die Liste aller verfügbaren Stub-User zurück. Dient zur Orientierung in der Entwicklung.
- Zugriff: Nur wenn `AUTH_MODE=stub`. Gibt HTTP 404 zurück, wenn Stub-Modus nicht aktiv.
- Response 200:
```json
{
  "stub_users": [
    {
      "username": "test-requester",
      "display_name": "Test Requester",
      "email": "requester@test.local",
      "roles": ["requester"],
      "hint": "Login without password or use 'stub-password'"
    },
    {
      "username": "test-approver",
      "display_name": "Test Approver",
      "email": "approver@test.local",
      "roles": ["approver"],
      "hint": "Login without password or use 'stub-password'"
    },
    {
      "username": "test-admin",
      "display_name": "Test Admin",
      "email": "admin@test.local",
      "roles": ["admin"],
      "hint": "Login without password or use 'stub-password'"
    },
    {
      "username": "test-multi",
      "display_name": "Test Multi Role",
      "email": "multi@test.local",
      "roles": ["requester", "approver"],
      "hint": "Use for self-approval tests"
    }
  ],
  "static_password": "stub-password",
  "note": "Auth-Stub is active. Never use in production."
}
```

---

### Edge Cases

- EC-01: `AUTH_MODE=stub` wird zur Laufzeit geändert (z.B. per Config-Reload) → Das System MUSS einen Neustart erfordern. Ein Hot-Reload des Auth-Modus ist nicht erlaubt.
- EC-02: Stub-User sendet einen bereits abgelaufenen Token → Standard-Token-Validierung greift. HTTP 401 mit `"error": "token_expired"`.
- EC-03: Zwei parallele Login-Anfragen für denselben Stub-User → Beide werden erfolgreich beantwortet. Keine Session-Collision, da Stub zustandslos ist.
- EC-04: `AUTH_MODE=stub` gesetzt, aber `JWT_SECRET` fehlt → System startet mit Fallback-Secret und loggt Warnung. Kein Start-Abbruch.
- EC-05: Login-Request enthält Passwort `""` (leerer String) → Wird wie "kein Passwort" behandelt und akzeptiert (REQ-07).
- EC-06: Login-Request für `test-multi` → Token enthält `"roles": ["requester", "approver"]`. Alle Berechtigungsprüfungen beider Rollen MÜSSEN für diesen User bestehen.
- EC-07: Endpoint 2 (`GET /api/v1/dev/auth/stub-users`) wird im Produktivmodus aufgerufen → HTTP 404, kein Hinweis auf Existenz des Endpoints.

---

## Feature 9.2: GitLab-Mock

**User Story:**
Als Entwickler möchte ich einen lokalen GitLab-Mock nutzen, der Pipeline-Trigger entgegennimmt, einen konfigurierbaren Status-Verlauf simuliert und Webhook-Callbacks ans Portal sendet, damit ich den gesamten Provisioning-Flow ohne echte GitLab-Instanz testen kann.

---

### Requirements

- REQ-15: Der GitLab-Mock MUSS einen HTTP-Server bereitstellen, der den GitLab-API-Endpunkt `POST /api/v4/projects/:project_id/trigger/pipeline` implementiert.
- REQ-16: Der Mock MUSS alle empfangenen TF_VAR_-Variablen aus dem Request-Body persistieren (In-Memory oder SQLite). Diese Daten MÜSSEN über eine Inspect-API abrufbar sein (siehe Endpoint 5).
- REQ-17: Nach Eingang eines Pipeline-Triggers MUSS der Mock eine Pipeline-ID generieren (eindeutig, numerisch aufsteigend oder UUID).
- REQ-18: Der Mock MUSS den folgenden Status-Verlauf für jede Pipeline simulieren: `pending` → `running` → `success` (Standardverhalten).
- REQ-19: Der Status-Verlauf MUSS konfigurierbar sein, sodass statt `success` der Endstatus `failed` simuliert werden kann. Konfiguration: Environment-Variable `GITLAB_MOCK_PIPELINE_RESULT` mit den Werten `success` (Standard) oder `failed`.
- REQ-20: Die Zeitverzögerung zwischen den Status-Übergängen MUSS konfigurierbar sein:
  - `GITLAB_MOCK_DELAY_PENDING_MS` (Standard: 500 ms): Verweildauer in `pending`
  - `GITLAB_MOCK_DELAY_RUNNING_MS` (Standard: 3000 ms): Verweildauer in `running`
- REQ-21: Der Mock MUSS nach jedem Status-Übergang einen Webhook-Callback an die im Trigger-Request konfigurierte oder per Environment-Variable (`PORTAL_WEBHOOK_URL`) definierte URL senden.
- REQ-22: Das Webhook-Payload MUSS dem GitLab Pipeline-Webhook-Format entsprechen (siehe API Contract, Endpoint 4).
- REQ-23: Eine konfigurierbare Fehlerrate MUSS unterstützt werden: `GITLAB_MOCK_FAILURE_RATE` (Float 0.0–1.0, Standard: 0.0). Bei ausgelöster Fehlerrate wird der Pipeline-Trigger mit HTTP 500 beantwortet (kein Pipeline-Objekt erstellt).
- REQ-24: Der Mock MUSS eine Admin-API bereitstellen, über die alle empfangenen Pipelines und deren Status inspiziert werden können (Endpoint 5).
- REQ-25: Der Mock MUSS einen Reset-Endpoint bereitstellen, der alle gespeicherten Pipelines löscht (Endpoint 6).
- REQ-26: Alle eingehenden Requests MÜSSEN im Applikations-Log des Mocks protokolliert werden (Timestamp, Pipeline-ID, TF_VAR_-Keys, Status).
- REQ-27: Der GitLab-Mock MUSS als separater Prozess/Service laufen und NICHT in den Haupt-API-Server des Portals integriert sein. Empfohlener Port: konfigurierbar über `GITLAB_MOCK_PORT` (Standard: 8929).
- REQ-28: Der Mock MUSS `GET /api/v4/projects/:project_id/pipelines/:pipeline_id` implementieren, damit das Portal den aktuellen Status pollen kann (Fallback zu Webhook).

---

### Validation Rules

- VAL-05: Feld `token` im Trigger-Request — MUSS vorhanden und nicht-leer sein — Fehlermeldung: `{"message": "401 Unauthorized"}`
- VAL-06: Feld `ref` im Trigger-Request — MUSS vorhanden und nicht-leer sein — Fehlermeldung: `{"message": "ref is required"}`
- VAL-07: `GITLAB_MOCK_FAILURE_RATE` — MUSS ein Float im Bereich [0.0, 1.0] sein — Fehlermeldung beim Start: `"GITLAB_MOCK_FAILURE_RATE must be between 0.0 and 1.0, got: {value}"`
- VAL-08: `GITLAB_MOCK_PIPELINE_RESULT` — Erlaubte Werte: `success`, `failed` — Fehlermeldung beim Start: `"GITLAB_MOCK_PIPELINE_RESULT must be 'success' or 'failed', got: {value}"`
- VAL-09: `PORTAL_WEBHOOK_URL` — MUSS eine gültige HTTP/HTTPS-URL sein, wenn gesetzt — Fehlermeldung beim Start: `"PORTAL_WEBHOOK_URL is not a valid URL: {value}"`

---

### API Contract

**Endpoint 3: Pipeline Trigger (GitLab-kompatibel)**

- Endpoint: `POST /api/v4/projects/:project_id/trigger/pipeline`
- Request Body (application/x-www-form-urlencoded oder JSON):
```json
{
  "token": "trigger-token-stub",
  "ref": "main",
  "variables": {
    "TF_VAR_order_id": "ord-123",
    "TF_VAR_template_slug": "vm-linux",
    "TF_VAR_template_version": "1.2.0",
    "TF_VAR_order_item_id": "item-456",
    "TF_VAR_cpu_cores": "4",
    "TF_VAR_ram_gb": "8"
  }
}
```
- Response 201 (Pipeline erstellt):
```json
{
  "id": 42,
  "project_id": 10,
  "sha": "abc123def456",
  "ref": "main",
  "status": "pending",
  "created_at": "2026-03-26T10:00:00Z",
  "web_url": "http://localhost:8929/stub-project/-/pipelines/42"
}
```
- Response 401: `{"message": "401 Unauthorized"}` (ungültiges Token)
- Response 500: `{"message": "500 Internal Server Error"}` (simulierter Fehler via Fehlerrate)

**Endpoint 4: Webhook-Callback-Payload (vom Mock an das Portal gesendet)**

- Methode: `POST {PORTAL_WEBHOOK_URL}`
- Payload bei Status-Übergang:
```json
{
  "object_kind": "pipeline",
  "object_attributes": {
    "id": 42,
    "ref": "main",
    "status": "running",
    "created_at": "2026-03-26T10:00:00Z",
    "finished_at": null,
    "duration": null
  },
  "project": {
    "id": 10,
    "name": "stub-project"
  },
  "builds": []
}
```
- Payload bei `success` (finished_at und duration befüllt):
```json
{
  "object_kind": "pipeline",
  "object_attributes": {
    "id": 42,
    "ref": "main",
    "status": "success",
    "created_at": "2026-03-26T10:00:00Z",
    "finished_at": "2026-03-26T10:00:04Z",
    "duration": 3
  },
  "project": {
    "id": 10,
    "name": "stub-project"
  },
  "builds": []
}
```

**Endpoint 5: Inspect — empfangene Pipelines**

- Endpoint: `GET /dev/gitlab-mock/pipelines`
- Query Params: `status` (optional, Filter: `pending`, `running`, `success`, `failed`), `limit` (optional, Standard: 50)
- Response 200:
```json
{
  "total": 3,
  "pipelines": [
    {
      "pipeline_id": 42,
      "project_id": 10,
      "ref": "main",
      "current_status": "success",
      "trigger_token": "trigger-token-stub",
      "received_at": "2026-03-26T10:00:00Z",
      "finished_at": "2026-03-26T10:00:04Z",
      "variables": {
        "TF_VAR_order_id": "ord-123",
        "TF_VAR_template_slug": "vm-linux",
        "TF_VAR_template_version": "1.2.0",
        "TF_VAR_order_item_id": "item-456",
        "TF_VAR_cpu_cores": "4",
        "TF_VAR_ram_gb": "8"
      },
      "status_history": [
        {"status": "pending", "timestamp": "2026-03-26T10:00:00Z"},
        {"status": "running", "timestamp": "2026-03-26T10:00:00.500Z"},
        {"status": "success", "timestamp": "2026-03-26T10:00:03.500Z"}
      ],
      "webhook_callbacks_sent": [
        {"status": "pending", "url": "http://portal:3000/api/v1/webhooks/gitlab", "http_status": 200, "timestamp": "2026-03-26T10:00:00Z"},
        {"status": "running", "url": "http://portal:3000/api/v1/webhooks/gitlab", "http_status": 200, "timestamp": "2026-03-26T10:00:00.500Z"},
        {"status": "success", "url": "http://portal:3000/api/v1/webhooks/gitlab", "http_status": 200, "timestamp": "2026-03-26T10:00:03.500Z"}
      ]
    }
  ]
}
```

**Endpoint 6: Reset — alle Pipelines löschen**

- Endpoint: `DELETE /dev/gitlab-mock/pipelines`
- Response 204: Kein Body
- Response 200 (mit Bestätigung):
```json
{
  "deleted": 42,
  "message": "All pipeline records cleared."
}
```

**Endpoint 7: Pipeline-Status abrufen (GitLab-kompatibel)**

- Endpoint: `GET /api/v4/projects/:project_id/pipelines/:pipeline_id`
- Response 200:
```json
{
  "id": 42,
  "project_id": 10,
  "status": "success",
  "ref": "main",
  "sha": "abc123def456",
  "created_at": "2026-03-26T10:00:00Z",
  "finished_at": "2026-03-26T10:00:04Z",
  "duration": 3,
  "web_url": "http://localhost:8929/stub-project/-/pipelines/42"
}
```
- Response 404: `{"message": "404 Project Not Found"}` (unbekannte Pipeline-ID)

---

### Edge Cases

- EC-08: Portal sendet denselben Trigger zweimal mit identischen TF_VAR-Werten → Jeder Request erzeugt eine neue, eigenständige Pipeline mit eigener ID. Keine Deduplizierung im Mock.
- EC-09: Webhook-Callback schlägt fehl (Portal nicht erreichbar) → Mock protokolliert Fehler im Log und im `webhook_callbacks_sent`-Array. Status-Simulation läuft dennoch weiter. Kein Retry im Mock.
- EC-10: `GITLAB_MOCK_FAILURE_RATE=1.0` gesetzt → Alle Trigger-Requests werden mit HTTP 500 beantwortet. Keine Pipelines werden erstellt.
- EC-11: Portal fragt Pipeline-Status per GET ab, bevor der Mock die erste Status-Transition ausgelöst hat → Gibt `"status": "pending"` zurück.
- EC-12: Mock wird während einer laufenden Pipeline neu gestartet → In-Memory-Pipelines gehen verloren. Kein persistierter State über Neustarts hinweg (es sei denn, SQLite-Backend ist konfiguriert).
- EC-13: `GITLAB_MOCK_DELAY_RUNNING_MS=0` gesetzt → Übergang `running` → `success`/`failed` erfolgt sofort. Webhook-Callbacks werden dennoch in der korrekten Reihenfolge gesendet.
- EC-14: Zwei parallele Trigger-Requests für denselben `project_id` → Beide Pipelines werden unabhängig simuliert. Pipeline-IDs sind eindeutig (kein Race Condition bei ID-Generierung: atomarer Counter oder UUID).

---

## Feature 9.3: CMDB-Stub

**User Story:**
Als Entwickler möchte ich einen CMDB-Stub nutzen, der Standorte, Netze, Mandanten, Sicherheitsbereiche und Konfigurationsoptionen aus statischen Dateien liefert und API-kompatibel mit der späteren echten CMDB-Anbindung ist, damit der Service Catalog vollständig ohne CMDB-Anbindung funktioniert.

---

### Requirements

- REQ-29: Der CMDB-Stub MUSS aktiviert werden, wenn `CMDB_MODE=stub` gesetzt ist. Im Produktivmodus (`CMDB_MODE=live` oder nicht gesetzt mit `ENV=production`) MUSS der Stub inaktiv sein.
- REQ-30: Die Stub-Daten MÜSSEN aus statischen YAML- oder JSON-Dateien geladen werden. Der Pfad zum Verzeichnis MUSS per `CMDB_STUB_DATA_PATH` konfigurierbar sein (Standard: `./stubs/cmdb/`).
- REQ-31: Der CMDB-Stub MUSS folgende Entitäten bereitstellen:
  - Standorte (`locations`)
  - Netze (`networks`)
  - Mandanten (`tenants`)
  - Sicherheitsbereiche (`security_zones`)
  - Konfigurationsoptionen (`config_options`)
- REQ-32: Die Testdaten MÜSSEN mindestens folgende Realismus-Anforderungen erfüllen:
  - 3 Standorte
  - Je 2–3 Netze pro Standort (verschiedene Typen: DMZ, intern, Mgmt)
  - 2 Mandanten
  - 3 Sicherheitsbereiche (z.B. LOW, MEDIUM, HIGH)
  - Sicherheitszonen sind Standort-spezifisch verknüpft
- REQ-33: Die CMDB-Stub-API MUSS identische Request- und Response-Formate wie die spätere echte CMDB-API verwenden. Das Interface ist maßgeblich für die echte Integration. Abweichungen MÜSSEN dokumentiert werden.
- REQ-34: Der Stub MUSS Filter-Parameter unterstützen (z.B. Netze nach Standort filtern), um reales CMDB-Verhalten zu simulieren.
- REQ-35: Stub-Daten MÜSSEN beim Start geladen und im Arbeitsspeicher gecacht werden. Datei-Änderungen zur Laufzeit erfordern einen Neustart (kein Hot-Reload).
- REQ-36: Der Stub MUSS einen Health-Endpunkt bereitstellen, der anzeigt, ob die Stub-Daten erfolgreich geladen wurden.
- REQ-37: Wenn eine angeforderte Entität nicht in den Stub-Daten vorhanden ist, MUSS HTTP 404 zurückgegeben werden (konsistent mit echtem CMDB-Verhalten).
- REQ-38: Der Stub MUSS als integrierter Bestandteil des Portal-Backends lauffähig sein (kein separater Prozess erforderlich), kann aber auch als separater Service betrieben werden.

---

### Statische Testdaten (Pflichtinhalt)

Die folgenden Daten MÜSSEN in den Stub-Dateien enthalten sein:

**Standorte:**

| ID           | Name          | Code | Region    |
|--------------|---------------|------|-----------|
| loc-berlin   | Berlin HQ     | BER  | DE-NORTH  |
| loc-munich   | Munich DC     | MUC  | DE-SOUTH  |
| loc-hamburg  | Hamburg Edge  | HAM  | DE-NORTH  |

**Netze:**

| ID              | Name              | CIDR            | Typ      | Standort    | Sicherheitszone |
|-----------------|-------------------|-----------------|----------|-------------|-----------------|
| net-ber-dmz     | Berlin DMZ        | 10.10.1.0/24    | dmz      | loc-berlin  | sz-medium       |
| net-ber-intern  | Berlin Internal   | 10.10.10.0/24   | internal | loc-berlin  | sz-low          |
| net-ber-mgmt    | Berlin Mgmt       | 10.10.100.0/24  | mgmt     | loc-berlin  | sz-high         |
| net-muc-dmz     | Munich DMZ        | 10.20.1.0/24    | dmz      | loc-munich  | sz-medium       |
| net-muc-intern  | Munich Internal   | 10.20.10.0/24   | internal | loc-munich  | sz-low          |
| net-ham-intern  | Hamburg Internal  | 10.30.10.0/24   | internal | loc-hamburg | sz-low          |
| net-ham-dmz     | Hamburg DMZ       | 10.30.1.0/24    | dmz      | loc-hamburg | sz-medium       |

**Mandanten:**

| ID           | Name              | Code  |
|--------------|-------------------|-------|
| ten-corp     | Corporate IT      | CORP  |
| ten-dev      | Development       | DEV   |

**Sicherheitsbereiche:**

| ID         | Name   | Level | Beschreibung                         |
|------------|--------|-------|--------------------------------------|
| sz-low     | LOW    | 1     | Interne Systeme, kein Internetzugang |
| sz-medium  | MEDIUM | 2     | DMZ, kontrollierter Zugang           |
| sz-high    | HIGH   | 3     | Management-Netz, eingeschränkter Zugang |

**Konfigurationsoptionen (Beispiele für VM-Parameter):**

| Kategorie   | Key                 | Werte                                             | Abhängigkeit     |
|-------------|---------------------|---------------------------------------------------|------------------|
| os_types    | os_type             | rhel9, ubuntu22, windows2022                      | —                |
| disk_types  | disk_type (rhel9)   | ssd, hdd, nvme                                    | os_type=rhel9    |
| disk_types  | disk_type (windows) | ssd, hdd                                          | os_type=windows  |
| backup_tiers| backup_tier         | none, daily, daily_weekly                         | —                |

---

### Validation Rules

- VAL-10: `CMDB_STUB_DATA_PATH` — Verzeichnis MUSS beim Start existieren und mindestens eine Datei enthalten — Fehlermeldung: `"CMDB stub data path not found or empty: {path}"`
- VAL-11: Filter-Parameter `location_id` bei Netz-Anfragen — MUSS eine bekannte Location-ID sein — Fehlermeldung: `{"error": "not_found", "message": "Location '{id}' not found"}`
- VAL-12: Filter-Parameter `security_zone` — MUSS einem bekannten Sicherheitsbereich entsprechen — Fehlermeldung: `{"error": "not_found", "message": "Security zone '{id}' not found"}`
- VAL-13: Kombination `CMDB_MODE=stub` + `ENV=production` — Fehlermeldung beim Start: `"FATAL: CMDB_MODE=stub must not be used in production environment. Aborting."`

---

### API Contract

**Endpoint 8: Standorte auflisten**

- Endpoint: `GET /api/v1/cmdb/locations`
- Query Params: `region` (optional, Filter nach Region)
- Response 200:
```json
{
  "locations": [
    {
      "id": "loc-berlin",
      "name": "Berlin HQ",
      "code": "BER",
      "region": "DE-NORTH"
    },
    {
      "id": "loc-munich",
      "name": "Munich DC",
      "code": "MUC",
      "region": "DE-SOUTH"
    },
    {
      "id": "loc-hamburg",
      "name": "Hamburg Edge",
      "code": "HAM",
      "region": "DE-NORTH"
    }
  ]
}
```

**Endpoint 9: Netze auflisten**

- Endpoint: `GET /api/v1/cmdb/networks`
- Query Params: `location_id` (optional), `type` (optional: `dmz`, `internal`, `mgmt`), `security_zone` (optional)
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
- Response 404: `{"error": "not_found", "message": "Location 'loc-xyz' not found"}`

**Endpoint 10: Mandanten auflisten**

- Endpoint: `GET /api/v1/cmdb/tenants`
- Response 200:
```json
{
  "tenants": [
    {"id": "ten-corp", "name": "Corporate IT", "code": "CORP"},
    {"id": "ten-dev", "name": "Development", "code": "DEV"}
  ]
}
```

**Endpoint 11: Sicherheitsbereiche auflisten**

- Endpoint: `GET /api/v1/cmdb/security-zones`
- Query Params: `location_id` (optional, gibt nur in diesem Standort vorhandene Zonen zurück)
- Response 200:
```json
{
  "security_zones": [
    {
      "id": "sz-low",
      "name": "LOW",
      "level": 1,
      "description": "Interne Systeme, kein Internetzugang"
    },
    {
      "id": "sz-medium",
      "name": "MEDIUM",
      "level": 2,
      "description": "DMZ, kontrollierter Zugang"
    },
    {
      "id": "sz-high",
      "name": "HIGH",
      "level": 3,
      "description": "Management-Netz, eingeschränkter Zugang"
    }
  ]
}
```

**Endpoint 12: Konfigurationsoptionen auflisten**

- Endpoint: `GET /api/v1/cmdb/config-options`
- Query Params: `category` (optional), `depends_on_key` (optional), `depends_on_value` (optional)
- Beispiel: `GET /api/v1/cmdb/config-options?category=disk_types&depends_on_key=os_type&depends_on_value=rhel9`
- Response 200:
```json
{
  "category": "disk_types",
  "options": [
    {"value": "ssd", "label": "SSD (NVMe)", "depends_on": {"os_type": "rhel9"}},
    {"value": "hdd", "label": "HDD (SATA)", "depends_on": {"os_type": "rhel9"}},
    {"value": "nvme", "label": "NVMe Ultra", "depends_on": {"os_type": "rhel9"}}
  ]
}
```

**Endpoint 13: CMDB-Stub Health**

- Endpoint: `GET /api/v1/cmdb/health`
- Response 200:
```json
{
  "status": "ok",
  "mode": "stub",
  "loaded_entities": {
    "locations": 3,
    "networks": 7,
    "tenants": 2,
    "security_zones": 3,
    "config_options": 10
  },
  "data_path": "./stubs/cmdb/"
}
```
- Response 503: `{"status": "error", "message": "Stub data not loaded"}` (wenn Datei-Ladevorgang fehlgeschlagen)

---

### Edge Cases

- EC-15: `GET /api/v1/cmdb/networks?location_id=loc-berlin` → Gibt nur die 3 Berliner Netze zurück, nicht die aus München oder Hamburg.
- EC-16: `GET /api/v1/cmdb/networks?location_id=loc-unknown` → HTTP 404 mit `"Location 'loc-unknown' not found"`.
- EC-17: `GET /api/v1/cmdb/config-options?category=disk_types&depends_on_key=os_type&depends_on_value=unknown-os` → Leere Options-Liste (kein Fehler): `{"category": "disk_types", "options": []}`.
- EC-18: Stub-Datei enthält fehlerhafte YAML/JSON-Syntax → Start schlägt fehl mit expliziter Fehlermeldung: `"Failed to parse CMDB stub file '{filename}': {parse_error}"`.
- EC-19: `GET /api/v1/cmdb/locations` im Produktivmodus (kein Stub) → Der echte CMDB-Connector antwortet. Dieser Endpunkt existiert in beiden Modi unter derselben URL.
- EC-20: Anfrage auf eine einzelne Ressource nach ID (z.B. `GET /api/v1/cmdb/locations/loc-unknown`) → HTTP 404 mit `{"error": "not_found", "message": "Location 'loc-unknown' not found"}`.

---

## Feature 9.4: Test-Fixtures

**User Story:**
Als Entwickler oder QA möchte ich die Datenbank mit vordefinierten, konsistenten Testdaten befüllen oder auf einen definierten Ausgangszustand zurücksetzen können, damit ich reproduzierbare Testszenarien für alle Entitäten des Portals durchführen kann.

---

### Requirements

- REQ-39: Das System MUSS einen Seed-Mechanismus bereitstellen, der alle Fixture-Daten in die Datenbank lädt. Der Seed MUSS sowohl über einen HTTP-Endpoint als auch über einen CLI-Command aufrufbar sein.
- REQ-40: Das System MUSS einen Reset-Mechanismus bereitstellen, der die Datenbank auf den Fixture-Stand zurücksetzt. Reset bedeutet: alle vorhandenen Daten löschen, dann Fixtures laden (vollständiger Austausch).
- REQ-41: Seed und Reset MÜSSEN in Produktionsumgebungen (`ENV=production`) deaktiviert sein und bei Aufruf HTTP 404 zurückgeben.
- REQ-42: Die Fixtures MÜSSEN als versionierte Dateien (YAML oder JSON) im Projektverzeichnis unter `./stubs/fixtures/` liegen. Der Pfad MUSS per `FIXTURE_DATA_PATH` überschreibbar sein.
- REQ-43: Die Fixtures MÜSSEN folgende Entitäten abdecken:
  - ServiceTemplates (mindestens 3: VM-Linux, VM-Windows, DB-PostgreSQL)
  - Orders in den Status: `draft`, `validated`, `submitted`, `pending_approval`, `approved`, `provisioning`, `provisioned`, `failed`, `rejected`
  - ApprovalRequests: `pending`, `approved`, `rejected`
  - ProvisionedResources (mindestens 2, verknüpft mit `provisioned`-Orders)
- REQ-44: Alle Fixture-Daten MÜSSEN referentiell konsistent sein: Order → ServiceTemplate (existiert), ApprovalRequest → Order (existiert), ProvisionedResource → Order (existiert).
- REQ-45: Jede Fixture-Order MUSS einem der vordefinierten Stub-User aus Feature 9.1 zugeordnet sein (`requester_id` zeigt auf `test-requester` oder `test-multi`).
- REQ-46: ApprovalRequest-Fixtures MÜSSEN dem vordefinierten Stub-Approver-User zugeordnet sein (`approver_id` zeigt auf `test-approver` oder `test-multi`).
- REQ-47: Der Seed-Vorgang MUSS idempotent sein: wiederholter Aufruf DARF NICHT zu Duplikaten führen. Bestehende Fixture-Daten (identifiziert über fixierte IDs) werden überschrieben oder übersprungen.
- REQ-48: Der Seed-Endpoint MUSS eine Zusammenfassung zurückgeben: Anzahl der erstellten/aktualisierten Entitäten pro Typ.
- REQ-49: Der CLI-Command für Seed und Reset MUSS in der Projektdokumentation beschrieben sein. Format: `./manage.sh fixtures seed` und `./manage.sh fixtures reset`.
- REQ-50: Fixture-IDs MÜSSEN fixiert und stabil sein (keine generierten UUIDs). Format: `fix-tpl-vm-linux`, `fix-ord-draft-001`, etc. Dies ermöglicht reproduzierbare Tests mit bekannten IDs.

---

### Fixture-Pflichtinhalt

**ServiceTemplates:**

| ID                  | Slug             | Version | Typ         | Status |
|---------------------|------------------|---------|-------------|--------|
| fix-tpl-vm-linux    | vm-linux         | 1.0.0   | vm          | active |
| fix-tpl-vm-windows  | vm-windows       | 1.0.0   | vm          | active |
| fix-tpl-db-postgres | db-postgresql    | 2.1.0   | database    | active |

**Orders (je ein Beispiel pro Status):**

| ID                      | Template            | Status            | Requester       |
|-------------------------|---------------------|-------------------|-----------------|
| fix-ord-draft-001       | fix-tpl-vm-linux    | draft             | test-requester  |
| fix-ord-validated-001   | fix-tpl-vm-linux    | validated         | test-requester  |
| fix-ord-submitted-001   | fix-tpl-vm-windows  | submitted         | test-requester  |
| fix-ord-pending-appr-001| fix-tpl-vm-windows  | pending_approval  | test-requester  |
| fix-ord-approved-001    | fix-tpl-db-postgres | approved          | test-multi      |
| fix-ord-provisioning-001| fix-tpl-vm-linux    | provisioning      | test-requester  |
| fix-ord-provisioned-001 | fix-tpl-vm-linux    | provisioned       | test-requester  |
| fix-ord-failed-001      | fix-tpl-vm-windows  | failed            | test-requester  |
| fix-ord-rejected-001    | fix-tpl-db-postgres | rejected          | test-multi      |

**ApprovalRequests:**

| ID                   | Order                    | Status   | Approver       |
|----------------------|--------------------------|----------|----------------|
| fix-apr-pending-001  | fix-ord-pending-appr-001 | pending  | test-approver  |
| fix-apr-approved-001 | fix-ord-approved-001     | approved | test-multi     |
| fix-apr-rejected-001 | fix-ord-rejected-001     | rejected | test-approver  |

**ProvisionedResources:**

| ID                   | Order                      | Typ | Hostname           |
|----------------------|----------------------------|-----|--------------------|
| fix-res-vm-001       | fix-ord-provisioned-001    | vm  | vm-fix-001.test.local |
| fix-res-vm-002       | fix-ord-provisioned-001    | vm  | vm-fix-002.test.local |

---

### Validation Rules

- VAL-14: Seed/Reset-Endpoint — MUSS bei `ENV=production` HTTP 404 zurückgeben — keine Fehlermeldung im Body (sicherheitshalber kein Hinweis auf Existenz des Endpoints)
- VAL-15: Fixture-Datei — MUSS beim Laden valide JSON/YAML sein — Fehlermeldung: `"Failed to parse fixture file '{filename}': {parse_error}"`
- VAL-16: Fixture-Referenz — Wenn eine Order auf eine Template-ID verweist, die nicht in den Fixture-Daten enthalten ist, MUSS der Seed mit einem Fehler abbrechen — Fehlermeldung: `"Fixture reference error: Order '{id}' references unknown template '{template_id}'"`
- VAL-17: Fixture-ID-Format — MUSS mit `fix-` beginnen, um Konflikte mit echten Produktionsdaten zu vermeiden — Fehlermeldung beim Laden: `"Invalid fixture ID '{id}': must start with 'fix-'"`

---

### API Contract

**Endpoint 14: Fixtures laden (Seed)**

- Endpoint: `POST /api/v1/dev/fixtures/seed`
- Beschreibung: Lädt alle Fixtures in die Datenbank. Idempotent. Bestehende Fixture-Daten (erkennbar an `fix-`-Präfix) werden überschrieben.
- Request Body: leer oder `{}`
- Response 200:
```json
{
  "status": "seeded",
  "summary": {
    "service_templates": {"created": 3, "updated": 0, "skipped": 0},
    "orders": {"created": 9, "updated": 0, "skipped": 0},
    "approval_requests": {"created": 3, "updated": 0, "skipped": 0},
    "provisioned_resources": {"created": 2, "updated": 0, "skipped": 0}
  },
  "duration_ms": 45
}
```
- Response 404: Kein Body (Produktionsumgebung oder Fixtures deaktiviert)
- Response 500:
```json
{
  "error": "seed_failed",
  "message": "Fixture reference error: Order 'fix-ord-draft-001' references unknown template 'fix-tpl-unknown'"
}
```

**Endpoint 15: Datenbank zurücksetzen (Reset)**

- Endpoint: `POST /api/v1/dev/fixtures/reset`
- Beschreibung: Löscht alle Daten aus der Datenbank (NICHT nur Fixture-Daten, sondern alle Einträge) und lädt anschließend alle Fixtures neu. Irreversibler Vorgang.
- Request Body: `{"confirm": true}` (Pflichtfeld zur Absicherung gegen versehentlichen Aufruf)
- Response 200:
```json
{
  "status": "reset",
  "deleted": {
    "service_templates": 5,
    "orders": 23,
    "approval_requests": 8,
    "provisioned_resources": 12
  },
  "seeded": {
    "service_templates": 3,
    "orders": 9,
    "approval_requests": 3,
    "provisioned_resources": 2
  },
  "duration_ms": 120
}
```
- Response 400: `{"error": "confirmation_required", "message": "Reset requires confirm: true in request body"}`
- Response 404: Kein Body (Produktionsumgebung)

**Endpoint 16: Fixture-Status prüfen**

- Endpoint: `GET /api/v1/dev/fixtures/status`
- Beschreibung: Gibt an, ob Fixtures geladen sind und wie viele Fixture-Datensätze (erkennbar an `fix-`-Präfix) sich in der Datenbank befinden.
- Response 200:
```json
{
  "fixtures_loaded": true,
  "counts": {
    "service_templates": 3,
    "orders": 9,
    "approval_requests": 3,
    "provisioned_resources": 2
  },
  "fixture_data_path": "./stubs/fixtures/",
  "environment": "development"
}
```
- Response 404: Kein Body (Produktionsumgebung)

---

### Edge Cases

- EC-21: Seed wird aufgerufen, während bereits ein Seed-Vorgang läuft (parallele Requests) → Der zweite Request MUSS mit HTTP 409 `"Conflict: fixture seed already in progress"` abgewiesen werden.
- EC-22: Fixture-Datei fehlt oder Verzeichnis ist leer → Seed schlägt fehl: HTTP 500 mit `"No fixture files found in '{path}'"`.
- EC-23: Reset wird ohne `"confirm": true` aufgerufen → HTTP 400. Kein Datenverlust.
- EC-24: Nach Reset wird ein weiterer Reset ausgeführt → Löschphase findet nur Fixture-Daten (kein Produktionsdaten vorhanden), idempotentes Verhalten.
- EC-25: Fixture enthält eine Order im Status `provisioned`, aber keinen passenden ProvisionedResource-Eintrag → Seed lädt trotzdem (keine strukturelle Pflicht-Verknüpfung). Das fehlende ProvisionedResource ist ein Test-Szenario für diesen Grenzfall.
- EC-26: Seed in einer leeren Datenbank (Erst-Setup) → Seed läuft vollständig durch. `"created"`-Zähler sind befüllt, `"updated"` und `"skipped"` sind 0.
- EC-27: Fixture-Datei enthält eine ID ohne `fix-`-Präfix → Seed bricht mit VAL-17-Fehlermeldung ab. Keine partiellen Writes.
- EC-28: CLI-Command `./manage.sh fixtures reset` in Produktion ausgeführt → Command MUSS `ENV` prüfen und mit expliziter Fehlermeldung abbrechen: `"ERROR: fixtures reset is not allowed in production environment"`.
- EC-29: `fix-ord-pending-appr-001` (Status `pending_approval`) wird über den normalen Order-Endpoint abgefragt → Gibt die Order korrekt zurück. Fixture-Daten sind vollwertige Datenbankeinträge.
- EC-30: Seed wird zweimal aufgerufen → Zweiter Aufruf findet alle IDs bereits vorhanden. `"updated"` oder `"skipped"` werden erhöht, keine Duplikate. Idempotenz gemäß REQ-47.

---

## Konfigurationsübersicht

Alle Environment-Variablen dieser Feature-Gruppe im Überblick:

| Variable                        | Feature | Standard       | Beschreibung                                    |
|---------------------------------|---------|----------------|-------------------------------------------------|
| `AUTH_MODE`                     | 9.1     | (nicht gesetzt) | `stub` aktiviert den Auth-Stub                 |
| `STUB_TOKEN_TTL_SECONDS`        | 9.1     | `86400`        | JWT-Token-Laufzeit im Stub-Modus (Sekunden)     |
| `JWT_SECRET`                    | 9.1     | (Pflicht in Prod) | JWT-Signing-Secret                           |
| `ENV`                           | alle    | (nicht gesetzt) | `production` deaktiviert alle Stub/Dev-Features |
| `GITLAB_MOCK_PORT`              | 9.2     | `8929`         | Port des GitLab-Mock-Services                   |
| `GITLAB_MOCK_PIPELINE_RESULT`   | 9.2     | `success`      | Simuliertes Pipeline-Endergebnis                |
| `GITLAB_MOCK_DELAY_PENDING_MS`  | 9.2     | `500`          | Verweildauer in `pending` (ms)                  |
| `GITLAB_MOCK_DELAY_RUNNING_MS`  | 9.2     | `3000`         | Verweildauer in `running` (ms)                  |
| `GITLAB_MOCK_FAILURE_RATE`      | 9.2     | `0.0`          | Anteil fehlgeschlagener Trigger (0.0–1.0)       |
| `PORTAL_WEBHOOK_URL`            | 9.2     | (Pflicht)      | Webhook-Callback-URL des Portals                |
| `CMDB_MODE`                     | 9.3     | (nicht gesetzt) | `stub` aktiviert den CMDB-Stub                 |
| `CMDB_STUB_DATA_PATH`           | 9.3     | `./stubs/cmdb/` | Verzeichnis mit CMDB-Stub-Datendateien         |
| `FIXTURE_DATA_PATH`             | 9.4     | `./stubs/fixtures/` | Verzeichnis mit Fixture-Dateien           |

---

## Produktions-Safeguards (Zusammenfassung)

Folgende Kombinationen MÜSSEN beim Systemstart zum Abbruch führen:

| Kombination                        | Fehlermeldung                                                              |
|------------------------------------|----------------------------------------------------------------------------|
| `AUTH_MODE=stub` + `ENV=production` | `FATAL: AUTH_MODE=stub must not be used in production environment. Aborting.` |
| `CMDB_MODE=stub` + `ENV=production` | `FATAL: CMDB_MODE=stub must not be used in production environment. Aborting.` |

Folgende Endpunkte und CLI-Commands MÜSSEN bei `ENV=production` HTTP 404 zurückgeben bzw. mit Fehler abbrechen:

- `GET /api/v1/dev/auth/stub-users`
- `POST /api/v1/dev/fixtures/seed`
- `POST /api/v1/dev/fixtures/reset`
- `GET /api/v1/dev/fixtures/status`
- `GET /dev/gitlab-mock/pipelines` (separater Service, kein Produktions-Deployment)
- `DELETE /dev/gitlab-mock/pipelines` (separater Service, kein Produktions-Deployment)
- `./manage.sh fixtures reset` (CLI)
- `./manage.sh fixtures seed` (CLI)
