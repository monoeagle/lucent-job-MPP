# Feature-Spezifikationen: Gruppe 4 — Provisioning-Engine

> **Status:** Draft v1.2 — Approval-Workflow als zweiter Dispatch-Trigger ergänzt (REQ-44)
> **Erstellt:** 2026-03-26
> **Letzte Änderung:** 2026-03-26
> **Umfang:** 7 Features, Requirements REQ-44–REQ-103, Validation Rules VAL-23–VAL-46, API Endpoints 18–34, Edge Cases EC-30–EC-66
> **Abhängigkeit:** Gruppe 3 "Bestellprozess & Workflow" (Features 3.1–3.4, insb. Multi-Service-Order-Modell und Item-basierter Dispatch)

---

## Inhaltsverzeichnis

- [Feature 4.1: OpenTofu Job-Dispatcher](#feature-41-opentofu-job-dispatcher)
- [Feature 4.2: Provisioning-Status-Sync](#feature-42-provisioning-status-sync)
- [Feature 4.3: AD-Integration — Computer-Objekt](#feature-43-ad-integration--computer-objekt)
- [Feature 4.4: IPAM-Integration — IP-Reservierung](#feature-44-ipam-integration--ip-reservierung)
- [Feature 4.5: Datenbank-Provisioning](#feature-45-datenbank-provisioning)
- [Feature 4.6: Fehlerbehandlung & Rollback](#feature-46-fehlerbehandlung--rollback)
- [Feature 4.7: Idempotenz-Schutz](#feature-47-idempotenz-schutz)
- [Orchestrierungsreihenfolge](#orchestrierungsreihenfolge)
- [Abhängigkeitsmatrix](#abhängigkeitsmatrix)

---

## Orchestrierungsreihenfolge

Die Orchestrierung wird **pro OrderItem** ausgeführt, nicht pro Order. Eine Order mit mehreren OrderItems kann mehrere parallele Orchestrierungsläufe haben. Der Order-Status aggregiert den Status aller Items.

### VM-Provisioning (pro OrderItem mit `template_slug` vom Typ `vm`)
1. Idempotenz-Check (Feature 4.7) — OrderItem noch nicht provisioniert?
2. IPAM: IP reservieren (Feature 4.4)
3. AD: Computer-Objekt anlegen (Feature 4.3)
4. OpenTofu: Job auslösen mit IP + AD-Daten (Feature 4.1)
5. Status-Sync bis `done` oder `failed` für das OrderItem (Feature 4.2)
6. Bei Fehler: Rollback in umgekehrter Reihenfolge (Feature 4.6)

### Datenbank-Provisioning (pro OrderItem mit `template_slug` vom Typ `database`)
1. Idempotenz-Check (Feature 4.7) — OrderItem noch nicht provisioniert?
2. IPAM: IP reservieren, falls DB-Instanz Netzwerkadresse benötigt (Feature 4.4)
3. OpenTofu: Job auslösen (kein AD-Computer-Objekt für DB-Instanzen) (Feature 4.1)
4. Status-Sync bis `done` oder `failed` für das OrderItem (Feature 4.2)
5. Zugangsdaten sicher an Requester übergeben (Feature 4.5)
6. Bei Fehler: Rollback (IP freigeben, Tofu-State bereinigen) (Feature 4.6)

> Hinweis: Für Datenbanken wird kein AD-Computer-Objekt angelegt. AD-Integration (Feature 4.3) ist ausschliesslich für VM- und Container-Typen vorgesehen.

---

## Feature 4.1: OpenTofu Job-Dispatcher

**User Story:**
Als System möchte ich nach Freigabe einer Bestellung (oder bei Bestellungen ohne Approval-Pflicht) automatisch einen OpenTofu-Job auslösen, damit die Infrastruktur-Provisionierung ohne manuellen Eingriff gestartet wird.

---

### Requirements

- **REQ-44:** Das System konsumiert das interne Event `{ order_id, order_item_id, template_slug, template_version, parameters, requester_id }` aus der Job-Queue, das von Feature 3.3 (order-lifecycle.md) pro OrderItem eingestellt wird. Das Event wird einmal pro OrderItem erzeugt, nicht einmal pro Order. Jedes OrderItem im `provisioning_status` `pending` ohne zugeordnete `job_id` wird als ausstehend betrachtet. Die Order wechselt auf Order-Ebene zu `provisioning`, sobald das erste Item mit dem Dispatch beginnt. Das Dispatch-Event wird durch zwei gleichwertige Auslöser in die Job-Queue eingestellt: (a) **Direktes Submit** — der Order-Status wechselt zu `submitted`, wenn für den betreffenden Service keine Approval-Pflicht besteht (Feature 3.3); (b) **Approval-Entscheidung** — der Order-Status wechselt zu `approved`, nachdem ein Approver die Bestellung genehmigt hat (Feature 3.3, Approval-Workflow). In beiden Fällen ist das Event-Format identisch: `{ order_id, order_item_id, template_slug, template_version, parameters, requester_id }`. Der Dispatcher unterscheidet die Herkunft des Events nicht; für ihn ist ausschliesslich das Vorliegen des Events in der Queue relevant.
- **REQ-45:** Der Dispatcher unterstützt zwei Auslösemethoden, die per System-Konfiguration umschaltbar sind: (a) Gitlab CI/CD Pipeline-Trigger via API (`POST /projects/:id/trigger/pipeline`) oder (b) direkter OpenTofu API-Call (für lokale Umgebungen ohne Gitlab). Die aktive Methode ist im Admin-Bereich sichtbar und dokumentiert. Ein Wechsel erfordert Server-Neustart.
- **REQ-46:** Beim Pipeline-Trigger werden die OrderItem-Parameter als Gitlab CI/CD Variables übergeben. Jede Variable wird als `TF_VAR_<tofu_variable_name>` übergeben, wobei `tofu_variable_name` aus dem zugehörigen ServiceTemplate (service-catalog.md) stammt und nicht identisch mit dem `field_name` des Bestellformulars sein muss. Sensible Parameter (Passwörter, Secrets) werden als Gitlab "masked variable" gekennzeichnet.
- **REQ-47:** Der Dispatcher erhält vom Auslöse-System (Gitlab oder Tofu direkt) eine eindeutige Job-ID (`job_id` oder `pipeline_id`). Diese wird sofort im jeweiligen **OrderItem** persistiert (nicht auf Order-Ebene). Mehrere Items derselben Order können parallel dispatched werden und erhalten jeweils eine eigene `job_id`. Die Order-Ebene wechselt zu `provisioning`, sobald das erste OrderItem seinen Dispatch startet.
- **REQ-48:** Der Status-Übergang des OrderItems von `pending` zu `provisioning` (auf `provisioning_status`-Ebene) und das Persistieren der `job_id` am OrderItem erfolgen in einer atomischen DB-Transaktion. Gleichzeitig wechselt die Order-Ebene in einer dieselben Transaktion zu `provisioning`, sofern sie noch im Status `submitted` ist. Schlägt das Persistieren fehl, wird der ausgelöste Job als "orphaned" betrachtet und über Feature 4.7 (Idempotenz) erkannt.
- **REQ-49:** Der Dispatcher ist ausschliesslich asynchron. Er wartet nicht auf den Abschluss des Tofu-Jobs. Die Statusverfolgung übernimmt Feature 4.2.
- **REQ-50:** Der Dispatcher unterstützt einen konfigurierbaren Retry-Mechanismus: Bei Fehler beim Auslösen (Netzwerk, Gitlab-API-Fehler) werden maximal 3 Versuche unternommen, mit exponentiellem Backoff (1 min, 5 min, 15 min). Nach dem dritten Fehlschlag wechselt der Status zu `failed` und Feature 4.6 (Rollback) wird ausgelöst.
- **REQ-51:** Für jedes ausgelöste OrderItem wird ein Dispatch-Log-Eintrag angelegt, der enthält: `order_id`, `order_item_id`, `job_id`, `dispatch_method` (gitlab | tofu_direct), `dispatched_at`, `attempt_count`, `dispatcher_response_raw` (gefiltert, ohne Secrets). Pro Order können mehrere Dispatch-Log-Einträge existieren (einer pro Item).
- **REQ-52:** Der Dispatcher prüft vor dem Auslösen pro OrderItem, ob alle Voraussetzungen erfüllt sind: IPAM-Reservierung vorhanden (falls ServiceType des referenzierten `template_slug` = `vm` oder `container`), AD-Computer-Objekt vorhanden (falls ServiceType = `vm` oder `container`). Der ServiceType wird aus dem ServiceTemplate (service-catalog.md) über `template_slug` und `template_version` ermittelt, nicht über ein `service_category`-Feld der Bestellung. Fehlt eine Voraussetzung, wird der Dispatch für dieses Item mit Fehler abgebrochen und Feature 4.6 ausgelöst.

---

### Validation Rules

- **VAL-23:** Gitlab-Token (Konfiguration) — Darf nicht leer sein, muss Format `glpat-[A-Za-z0-9_-]{20}` oder `glptt-[a-f0-9]{40}` erfüllen — `"Der Gitlab-Token hat ein ungültiges Format."`
- **VAL-24:** Gitlab-Projekt-ID (Konfiguration) — Muss eine positive Ganzzahl sein — `"Die Gitlab-Projekt-ID muss eine positive Ganzzahl sein."`
- **VAL-25:** Bestellparameter vor Dispatch — Alle als `required: true` markierten Parameter des Service-Schemas müssen vorhanden und valide sein — `"Die Bestellung enthält unvollständige Parameter und kann nicht provisioniert werden."`
- **VAL-26:** `job_id` nach Dispatch — Muss vom Auslöse-System zurückgeliefert werden und darf nicht leer sein — `"Der Job-Dispatcher hat keine gültige Job-ID zurückgeliefert."`

---

### API Contract

**Endpoint 18: Get dispatcher configuration (admin)**
```
GET /api/v1/admin/dispatcher/config
```
Response 200:
```json
{
  "dispatch_method": "gitlab | tofu_direct",
  "gitlab_project_id": "integer | null",
  "gitlab_api_url": "string | null",
  "tofu_api_url": "string | null",
  "retry_max_attempts": "integer",
  "retry_backoff_minutes": [1, 5, 15],
  "gitlab_token_configured": "boolean"
}
```
Response 401: Nicht authentifiziert
Response 403: Nur Admin

---

**Endpoint 19: Get dispatch log for an order (admin)**
```
GET /api/v1/admin/orders/{order_id}/dispatch-log
```
Response 200:
```json
{
  "order_id": "uuid",
  "dispatch_entries": [
    {
      "entry_id": "uuid",
      "order_item_id": "uuid",
      "template_slug": "string",
      "template_version": "string",
      "job_id": "string | null",
      "dispatch_method": "gitlab | tofu_direct",
      "dispatched_at": "ISO8601 datetime",
      "attempt_count": "integer",
      "status": "success | failed | retrying",
      "error_message": "string | null"
    }
  ]
}
```
Response 404: Bestellung nicht gefunden
Response 403: Nur Admin

---

**Endpoint 20: Manually trigger dispatch for an order item (admin)**
```
POST /api/v1/admin/orders/{order_id}/items/{item_id}/dispatch
```
Request Body: (leer — alle Parameter werden aus dem OrderItem und dem ServiceTemplate gelesen)
```json
{}
```
Response 202:
```json
{
  "order_id": "uuid",
  "order_item_id": "uuid",
  "template_slug": "string",
  "template_version": "string",
  "job_id": "string",
  "dispatched_at": "ISO8601 datetime",
  "dispatch_method": "gitlab | tofu_direct"
}
```
Response 400: Voraussetzungen nicht erfüllt (IPAM oder AD fehlt)
Response 404: Bestellung oder OrderItem nicht gefunden
Response 409: OrderItem nicht im `provisioning_status` `pending` oder `job_id` bereits vorhanden (Idempotenz, siehe Feature 4.7)
Response 503: Dispatch-System nicht erreichbar

---

### Edge Cases

- **EC-30:** Gitlab-API antwortet mit HTTP 5xx beim Pipeline-Trigger — Retry-Mechanismus (REQ-50) greift. Nach 3 Versuchen: Status `failed`, Rollback (Feature 4.6), Admin-Benachrichtigung.
- **EC-31:** Gitlab-API nimmt den Request an (HTTP 200), liefert aber keine `pipeline_id` in der Response — VAL-26 schlägt fehl. Der Job gilt als nicht ausgelöst. Retry-Mechanismus startet. Das betroffene OrderItem bleibt im `provisioning_status` `pending`, die Order bleibt im Status `submitted` (sofern noch kein anderes Item dispatched wurde).
- **EC-32:** Zwei parallele Dispatcher-Instanzen (horizontale Skalierung) versuchen, dasselbe OrderItem auszulösen — Der `provisioning_status`-Übergang `pending` → `provisioning` am OrderItem erfolgt atomar mit DB-Level-Lock oder Optimistic Locking (REQ-94). Nur eine Instanz gewinnt (affected rows = 1), die andere erkennt den Statuswechsel (affected rows = 0) und bricht ab. Items anderer Orders oder andere Items derselben Order werden davon nicht blockiert.
- **EC-33:** Der ausgelöste Gitlab-Job wird manuell in Gitlab abgebrochen (nicht vom Portal) — Feature 4.2 erkennt den `cancelled`-Status beim nächsten Sync-Zyklus und setzt den Bestellstatus auf `failed`. Feature 4.6 wird ausgelöst.
- **EC-34:** Die Bestellung enthält einen Parameter mit einem Sonderzeichen, das Gitlab CI/CD Variables nicht unterstützen — Das Backend escapet die Variable vor dem Übertragen. Zeichen ausserhalb `[A-Za-z0-9_.-]` werden URL-encoded übergeben. Das Tofu-Modul ist für diese Kodierung dokumentiert.
- **EC-35:** Der Dispatcher-Job-Prozess stirbt nach dem Auslösen eines Items, aber vor dem Persistieren der `job_id` am OrderItem — REQ-48 greift: Kein Persistieren = kein Statuswechsel am Item. Feature 4.7 (REQ-97) erkennt beim nächsten Startup-Check das OrderItem mit `provisioning_status` `pending`, älter als 5 Minuten und ohne `job_id`, und prüft via deduplication gegen Gitlab anhand der `order_item_id`. Existiert ein Job, wird die `job_id` am Item nachgetragen und `provisioning_status` auf `provisioning` gesetzt. Existiert keiner, wird erneut ausgelöst. Andere Items der Order sind von diesem Ausfall nicht betroffen.

---

## Feature 4.2: Provisioning-Status-Sync

**User Story:**
Als System möchte ich den aktuellen Status eines laufenden OpenTofu-Jobs kontinuierlich ins Portal synchronisieren, damit Requestern und Admins jederzeit der aktuelle Provisioning-Fortschritt angezeigt wird.

---

### Requirements

- **REQ-53:** Das Portal synchronisiert den Provisioning-Status über eine der zwei Methoden: (a) Polling: Das Portal fragt regelmässig (alle 60 Sekunden, konfigurierbar) die Gitlab- oder Tofu-API nach dem Status der `job_id` ab. (b) Webhook: Gitlab/Tofu sendet Status-Updates aktiv an das Portal. Beide Methoden können parallel aktiv sein. Eingehende Webhooks überschreiben den Polling-Status, sofern der Zeitstempel des Webhook-Events neuer ist.
- **REQ-54:** Gitlab-Pipeline-Status wird auf den internen Portal-Status gemappt:
  - `created | waiting_for_resource | pending` → `provisioning` (keine Änderung)
  - `running` → `provisioning` (keine Änderung, aber `provisioning_progress`-Felder werden aktualisiert)
  - `success` → `active` (Statusübergang, Ressourcen-Outputs aus Tofu-State werden gespeichert)
  - `failed | canceled` → `failed` (Statusübergang, Feature 4.6 wird ausgelöst)
  - `skipped | manual` → keine Aktion (unerwarteter Zustand, Admin wird benachrichtigt)
- **REQ-55:** Bei einem Übergang zu `active` extrahiert das System die Tofu-Outputs aus dem Job-Artefakt (oder Tofu-State-API). Folgende Outputs werden erwartet und in `provisioned_resources` der Bestellung gespeichert: `ip_address`, `hostname`, `fqdn` (nur VM/Container), `db_connection_string`, `db_username` (nur Datenbank), weitere service-spezifische Outputs gemäss Tofu-Modul-Dokumentation.
- **REQ-56:** Status-Updates werden in `order_status_history` protokolliert (mit `changed_by: "system"`) und lösen einen SSE-Event aus (Feature 3.2, Endpoint 9/10).
- **REQ-57:** Bei laufendem Provisioning (`provisioning`-Status) wird ein `provisioning_progress`-Objekt in der Bestellantwort mitgeliefert: `{ "step": "string", "step_number": "integer", "total_steps": "integer", "updated_at": "ISO8601 datetime" }`. Die Schritte werden aus den Gitlab-Job-Log-Annotations oder Tofu-State-Transitions extrahiert, sofern verfügbar; andernfalls wird nur der Zeitstempel aktualisiert.
- **REQ-58:** Bleibt ein Job länger als das konfigurierbare `provisioning_timeout` (Default: 60 Minuten, Range: 5–240 Minuten) im Status `provisioning`, gilt er als timed-out. Das System setzt den Status auf `failed` mit `failure_reason: "Provisioning-Timeout nach {X} Minuten."` und löst Feature 4.6 aus.
- **REQ-59:** Der Polling-Job läuft pro `order_id` im Status `provisioning`. Wechselt die Bestellung in einen Endzustand (`active` oder `failed`), wird der Polling-Job für diese Bestellung beendet.

---

### Validation Rules

- **VAL-27:** Webhook-Signatur — Eingehende Webhook-Requests müssen einen gültigen HMAC-SHA256-Signature-Header (`X-Gitlab-Token` oder `X-Hub-Signature-256`) tragen. Ungültige Signatures werden mit HTTP 401 abgelehnt und geloggt — `"Ungültige Webhook-Signatur. Request abgelehnt."`
- **VAL-28:** Polling-Intervall (Konfiguration) — Ganzzahl 10–3600 Sekunden — `"Das Polling-Intervall muss zwischen 10 und 3600 Sekunden liegen."`
- **VAL-29:** Provisioning-Timeout (Konfiguration) — Ganzzahl 5–240 Minuten — `"Der Provisioning-Timeout muss zwischen 5 und 240 Minuten liegen."`
- **VAL-30:** Tofu-Output-Vollständigkeit — Bei Übergang zu `active` müssen alle service-typ-spezifisch erforderlichen Outputs vorhanden sein. Fehlt ein Pflicht-Output, wechselt der Status zu `failed` statt `active` — `"Provisioning abgeschlossen, aber erforderliche Ressourcen-Outputs fehlen: {missing_fields}."`

---

### API Contract

**Endpoint 21: Webhook receiver for Gitlab/Tofu status updates**
```
POST /api/v1/internal/provisioning/webhook
Headers:
  X-Gitlab-Token: {hmac_signature}
  Content-Type: application/json
```
Request Body (Gitlab-Format):
```json
{
  "object_kind": "pipeline | build",
  "project": { "id": "integer" },
  "object_attributes": {
    "id": "integer (pipeline_id)",
    "status": "string (gitlab pipeline status)",
    "finished_at": "ISO8601 datetime | null"
  },
  "builds": [
    {
      "id": "integer",
      "name": "string",
      "status": "string",
      "stage": "string"
    }
  ]
}
```
Response 200:
```json
{ "received": true, "order_id": "uuid | null" }
```
Response 401: Ungültige Signatur
Response 404: Keine Bestellung zur `pipeline_id` gefunden (ignoriert, aber geloggt)
Response 422: Unverarbeitbares Payload-Format

---

**Endpoint 22: Get provisioning status for an order**
```
GET /api/v1/orders/{order_id}/provisioning-status
```
Response 200:
```json
{
  "order_id": "uuid",
  "status": "provisioning | active | failed",
  "job_id": "string | null",
  "dispatch_method": "gitlab | tofu_direct",
  "provisioning_progress": {
    "step": "string | null",
    "step_number": "integer | null",
    "total_steps": "integer | null",
    "updated_at": "ISO8601 datetime"
  },
  "provisioned_resources": {
    "ip_address": "string | null",
    "hostname": "string | null",
    "fqdn": "string | null"
  },
  "provisioning_started_at": "ISO8601 datetime | null",
  "provisioning_finished_at": "ISO8601 datetime | null",
  "provisioning_timeout_at": "ISO8601 datetime | null"
}
```
Response 404: Bestellung nicht gefunden oder kein Zugriff
Response 401: Nicht authentifiziert

---

**Endpoint 23: Get sync configuration (admin)**
```
GET /api/v1/admin/provisioning/sync-config
```
Response 200:
```json
{
  "polling_enabled": "boolean",
  "polling_interval_seconds": "integer",
  "webhook_enabled": "boolean",
  "webhook_secret_configured": "boolean",
  "provisioning_timeout_minutes": "integer"
}
```
Response 403: Nur Admin

---

**Endpoint 24: Update sync configuration (admin)**
```
PUT /api/v1/admin/provisioning/sync-config
```
Request Body:
```json
{
  "polling_enabled": "boolean",
  "polling_interval_seconds": "integer",
  "webhook_enabled": "boolean",
  "provisioning_timeout_minutes": "integer"
}
```
Response 200: Aktualisierte Konfiguration (gleiches Schema wie GET)
Response 400: Validation-Fehler
Response 403: Nur Admin

---

### Edge Cases

- **EC-36:** Webhook-Event kommt an, bevor der Dispatcher die `job_id` persistiert hat (Race Condition zwischen Feature 4.1 und 4.2) — Das Webhook-Receiver-System versucht, die `pipeline_id` einer Bestellung zuzuordnen. Findet es keine, wird das Event in einer Pending-Webhook-Queue für 5 Minuten gehalten und nach jeweils 30 Sekunden erneut versucht. Danach wird das Event verworfen und geloggt.
- **EC-37:** Polling-Job und eingehender Webhook liefern gleichzeitig unterschiedliche Status für denselben Job — Der Statusübergang ist idempotent. Das neuere `finished_at`-Zeitstempel-Feld gewinnt. Führen beide zum gleichen Zielstatus, wird nur ein Statusübergang ausgeführt. Führen sie zu unterschiedlichen Zielstatussen, gewinnt das chronologisch spätere Event; der Konflikt wird in den Admin-Logs markiert.
- **EC-38:** Tofu-Job endet erfolgreich, aber das Artefakt mit den Outputs ist nicht abrufbar (z.B. Artefakt abgelaufen) — VAL-30 greift: Status wechselt zu `failed`. Fehlermeldung: "Provisioning abgeschlossen, aber Ressourcen-Outputs konnten nicht abgerufen werden." Feature 4.6 wird ausgelöst.
- **EC-39:** Ein einzelner Polling-Zyklus dauert länger als das konfigurierte Intervall (z.B. Gitlab antwortet langsam) — Der nächste Polling-Aufruf für dieselbe Bestellung startet erst, wenn der vorherige abgeschlossen ist (kein paralleles Polling derselben `job_id`). Andere Bestellungen werden davon nicht blockiert.
- **EC-40:** Bestellung wechselt während laufendem Provisioning manuell zu `failed` durch Admin (Feature 4.6 manuell ausgelöst) — Der Polling-Job erkennt beim nächsten Zyklus, dass die Bestellung nicht mehr im Status `provisioning` ist, und beendet sich ohne weitere Aktion. Ein späterer Webhook-Event für denselben Job wird ignoriert.
- **EC-41:** Gitlab meldet `success`, aber das Tofu-Apply hat intern Fehler, die nur im Log sichtbar sind (stille Fehler) — Das System prüft ausschliesslich den Gitlab-Pipeline-Status und die Vollständigkeit der Tofu-Outputs (VAL-30). Stille Fehler ohne Output-Auswirkung können nicht automatisch erkannt werden. Dies ist eine bekannte Limitation; das Tofu-Modul muss so designed sein, dass es bei internen Fehlern den Pipeline-Job explizit fehlschlägt.

---

## Feature 4.3: AD-Integration — Computer-Objekt

**User Story:**
Als System möchte ich bei der Provisionierung einer VM oder eines Containers automatisch ein Computer-Objekt in Active Directory anlegen, damit der neue Server von Beginn an korrekt in der Domain-Infrastruktur registriert ist.

---

### Requirements

- **REQ-60:** Das Anlegen des AD-Computer-Objekts wird ausschliesslich für Service-Kategorien `vm` und `container` durchgeführt. Für `database` wird kein AD-Objekt angelegt (siehe Orchestrierungsreihenfolge).
- **REQ-61:** Der Hostname des Computer-Objekts wird nach einer fest definierten Namenskonvention generiert: `{prefix}-{umgebung}-{sequenznummer}`. Beispiel: `SRV-PROD-0042`. Die Konvention ist per Admin-Konfiguration anpassbar (Präfix, Umgebungskürzel, Länge der Sequenznummer). Die Sequenznummer ist ein systemweit fortlaufender, lückenloses Zähler (kein UUID-Segment).
- **REQ-62:** Vor dem Anlegen wird geprüft, ob ein Computer-Objekt mit demselben Namen bereits in AD existiert. Existiert es, wird der Vorgang abgebrochen und Feature 4.6 ausgelöst (kein Überschreiben bestehender Objekte). Der Fehler wird als `ad_object_conflict` kategorisiert.
- **REQ-63:** Das Computer-Objekt wird in der OU angelegt, die dem Service-Typ und der Umgebung (Prod/Test/Dev, abgeleitet aus dem Bestellparameter `environment`) entspricht. Die OU-Mapping-Tabelle ist per Admin-Konfiguration pflegbar.
- **REQ-64:** Nach dem Anlegen wird das Computer-Objekt mindestens den folgenden AD-Gruppen hinzugefügt: einer umgebungsspezifischen Basis-Gruppe (z.B. `GRP-VM-PROD-ALL`) und einer service-typ-spezifischen Gruppe (z.B. `GRP-VM-WEBSERVER`). Die Gruppe-Mapping-Tabelle ist per Admin-Konfiguration pflegbar.
- **REQ-65:** Der generierte Hostname, der vollständige Distinguished Name (DN) des AD-Objekts und die zugeordneten Gruppen werden in `provisioned_resources` der Bestellung gespeichert, bevor der Tofu-Job ausgelöst wird.
- **REQ-66:** Das AD-Passwort für das Computer-Objekt wird vom System generiert (min. 32 Zeichen, zufällig), im internen Secret-Store gespeichert und als Tofu-Variable übergeben. Es wird niemals im Klartext in Logs oder API-Responses ausgegeben.
- **REQ-67:** Das Anlegen des AD-Objekts erfolgt über eine konfigurierbare AD-Connector-Komponente (LDAPS, Port 636). Verbindungsdaten (Host, Port, Bind-DN, Bind-Passwort) werden als verschlüsselte System-Einstellung gespeichert.

---

### Validation Rules

- **VAL-31:** Hostname-Präfix (Konfiguration) — 2–6 Zeichen, nur `[A-Z]` — `"Der Hostname-Präfix muss aus 2–6 Grossbuchstaben bestehen."`
- **VAL-32:** Umgebungskürzel (Bestellparameter `environment`) — Muss in der konfigurierten Menge gültiger Umgebungen enthalten sein (z.B. PROD, TEST, DEV) — `"Die angegebene Umgebung '{value}' ist nicht zulässig."`
- **VAL-33:** OU-Mapping-Vollständigkeit — Für jede Kombination aus service_category und environment muss ein OU-Eintrag in der Mapping-Tabelle existieren — `"Kein OU-Mapping für Service-Typ '{category}' in Umgebung '{environment}' konfiguriert."`
- **VAL-34:** AD-Gruppen-Existenz — Jede in der Mapping-Tabelle konfigurierte Gruppe muss in AD auffindbar sein — `"Die AD-Gruppe '{group_name}' existiert nicht oder ist nicht erreichbar."`
- **VAL-35:** LDAPS-Verbindung — Alle vier Felder (Host, Port, Bind-DN, Bind-Passwort) müssen konfiguriert sein — `"Die AD-Connector-Konfiguration ist unvollständig."`

---

### API Contract

**Endpoint 25: Get AD connector configuration (admin)**
```
GET /api/v1/admin/ad-connector/config
```
Response 200:
```json
{
  "ldaps_host": "string",
  "ldaps_port": "integer",
  "bind_dn": "string",
  "bind_password_configured": "boolean",
  "hostname_prefix": "string",
  "sequence_number_length": "integer",
  "ou_mappings": [
    {
      "service_category": "vm | container",
      "environment": "string",
      "ou_dn": "string"
    }
  ],
  "group_mappings": [
    {
      "service_category": "vm | container",
      "environment": "string",
      "groups": ["string"]
    }
  ]
}
```
Response 403: Nur Admin

---

**Endpoint 26: Update AD connector configuration (admin)**
```
PUT /api/v1/admin/ad-connector/config
```
Request Body: (gleiches Schema wie GET, mit `bind_password: "string"` statt `bind_password_configured`)
```json
{
  "ldaps_host": "string",
  "ldaps_port": "integer",
  "bind_dn": "string",
  "bind_password": "string",
  "hostname_prefix": "string",
  "sequence_number_length": "integer",
  "ou_mappings": [
    {
      "service_category": "vm | container",
      "environment": "string",
      "ou_dn": "string"
    }
  ],
  "group_mappings": [
    {
      "service_category": "vm | container",
      "environment": "string",
      "groups": ["string"]
    }
  ]
}
```
Response 200: Aktualisierte Konfiguration (ohne `bind_password`, mit `bind_password_configured: true`)
Response 400: Validation-Fehler
Response 403: Nur Admin

---

**Endpoint 27: Test AD connector connectivity (admin)**
```
POST /api/v1/admin/ad-connector/test
```
Request Body: (leer — nutzt gespeicherte Konfiguration)
```json
{}
```
Response 200:
```json
{
  "connected": "boolean",
  "bind_successful": "boolean",
  "latency_ms": "integer",
  "error_message": "string | null"
}
```
Response 403: Nur Admin
Response 503: AD-Verbindung nicht herstellbar (wird im Body beschrieben, nicht als HTTP-Fehler)

---

### Edge Cases

- **EC-42:** Der AD-Connector verliert die Verbindung während des Anlegens (nach LDAP-Add, vor Gruppenverknüpfung) — Das System erkennt beim Reconnect-Versuch, dass das Computer-Objekt bereits existiert (`ad_object_conflict`). Das System versucht, die Gruppenverknüpfung nachzuholen (idempotente LDAP-Modify-Operation). Gelingt es nicht, wird Feature 4.6 mit Rollback ausgelöst.
- **EC-43:** Die Sequenznummer-Generierung führt zu einem Hostname, der bereits existiert (z.B. Sequenznummer wurde extern vergeben) — REQ-62 greift: Anlegen wird abgebrochen. Das System erhöht die Sequenznummer um 1 und versucht einen neuen Hostnamen. Maximal 5 Versuche, danach Fehler und Feature 4.6.
- **EC-44:** Das OU-Ziel existiert nicht mehr in AD (wurde extern gelöscht) — LDAP-Add schlägt mit `noSuchObject` fehl. Feature 4.6 wird ausgelöst. Admin wird benachrichtigt, dass das OU-Mapping veraltet ist.
- **EC-45:** Zwei gleichzeitige Bestellungen für VMs in derselben Umgebung erhalten möglicherweise denselben Sequenznummer-Kandidaten — Die Sequenznummer-Generierung erfolgt atomar über einen DB-Sequence-Lock. Jede Bestellung erhält eine eindeutig reservierte Nummer vor dem LDAP-Call.

---

## Feature 4.4: IPAM-Integration — IP-Reservierung

**User Story:**
Als System möchte ich vor der Provisionierung automatisch eine freie IP-Adresse aus dem richtigen Subnetz im IPAM reservieren und an OpenTofu übergeben, damit keine IP-Konflikte in der Infrastruktur entstehen.

---

### Requirements

- **REQ-68:** Das System reserviert eine IP-Adresse in IPAM (NetBox oder phpIPAM, per System-Konfiguration wählbar) vor dem Auslösen des Tofu-Jobs. Die Reservierung enthält: `ip_address`, `prefix/subnet`, `order_id`, `hostname` (aus Feature 4.3), `reserved_at`, `status: reserved`.
- **REQ-69:** Das Subnetz wird anhand einer Mapping-Tabelle bestimmt: `service_category` + `environment` → `subnet_prefix`. Die Mapping-Tabelle ist per Admin-Konfiguration pflegbar.
- **REQ-70:** Das IPAM-System wählt die nächste verfügbare IP aus dem konfigurierten Subnetz. Das Portal gibt keine spezifische IP vor, sondern delegiert die Auswahl an IPAM. Die zurückgegebene IP wird aus dem IPAM-Response übernommen.
- **REQ-71:** Die reservierte IP-Adresse wird sofort in `provisioned_resources` der Bestellung gespeichert und als Tofu-Variable `TF_VAR_ip_address` übergeben.
- **REQ-72:** Im Fall eines Provisioning-Fehlers (Feature 4.6) wird die reservierte IP in IPAM wieder freigegeben (Status zurück auf `available`). Die Freigabe erfolgt über die IPAM-API mit der `reservation_id`, die beim Reservieren gespeichert wurde.
- **REQ-73:** Falls das Subnetz keine freie IP hat, wird der gesamte Provisioning-Vorgang abgebrochen. Der Bestellstatus wechselt zu `failed` mit `failure_reason: "Kein freier IP-Adressraum im Subnetz {subnet} verfügbar."`.
- **REQ-74:** Für `database`-Provisioning ist die IP-Reservierung optional: Sie erfolgt nur, wenn der Bestellparameter `requires_dedicated_ip: true` gesetzt ist. Andernfalls wird keine IP reserviert.

---

### Validation Rules

- **VAL-36:** Subnetz-Mapping-Vollständigkeit — Für jede Kombination aus service_category und environment muss ein Subnetz-Eintrag existieren — `"Kein Subnetz-Mapping für Service-Typ '{category}' in Umgebung '{environment}' konfiguriert."`
- **VAL-37:** IPAM-API-URL (Konfiguration) — Muss eine gültige HTTPS-URL sein — `"Die IPAM-API-URL muss eine gültige HTTPS-URL sein."`
- **VAL-38:** IPAM-API-Token (Konfiguration) — Darf nicht leer sein — `"Der IPAM-API-Token darf nicht leer sein."`
- **VAL-39:** IPAM-Antwort auf Reservierung — Muss `ip_address` (IPv4 oder IPv6) und `reservation_id` enthalten — `"IPAM hat keine gültige Reservierungsantwort zurückgeliefert."`

---

### API Contract

**Endpoint 28: Get IPAM configuration (admin)**
```
GET /api/v1/admin/ipam/config
```
Response 200:
```json
{
  "ipam_type": "netbox | phpipam",
  "api_url": "string",
  "api_token_configured": "boolean",
  "subnet_mappings": [
    {
      "service_category": "vm | container | database",
      "environment": "string",
      "subnet_prefix": "string (CIDR notation)",
      "ipam_prefix_id": "string | integer"
    }
  ]
}
```
Response 403: Nur Admin

---

**Endpoint 29: Update IPAM configuration (admin)**
```
PUT /api/v1/admin/ipam/config
```
Request Body: (gleiches Schema wie GET, mit `api_token: "string"` statt `api_token_configured`)
```json
{
  "ipam_type": "netbox | phpipam",
  "api_url": "string",
  "api_token": "string",
  "subnet_mappings": [
    {
      "service_category": "vm | container | database",
      "environment": "string",
      "subnet_prefix": "string",
      "ipam_prefix_id": "string | integer"
    }
  ]
}
```
Response 200: Aktualisierte Konfiguration (ohne `api_token`, mit `api_token_configured: true`)
Response 400: Validation-Fehler
Response 403: Nur Admin

---

**Endpoint 30: Get IP reservation details for an order (admin)**
```
GET /api/v1/admin/orders/{order_id}/ip-reservation
```
Response 200:
```json
{
  "order_id": "uuid",
  "reservation_id": "string | integer",
  "ip_address": "string",
  "subnet_prefix": "string",
  "ipam_type": "netbox | phpipam",
  "reserved_at": "ISO8601 datetime",
  "status": "reserved | released",
  "released_at": "ISO8601 datetime | null"
}
```
Response 404: Keine Reservierung für diese Bestellung
Response 403: Nur Admin

---

### Edge Cases

- **EC-46:** IPAM-API ist nicht erreichbar zum Zeitpunkt der Reservierung — Es werden maximal 3 Versuche mit exponentiellem Backoff (30 s, 2 min, 5 min) unternommen. Schlägt auch der dritte Versuch fehl, wechselt der Status zu `failed`. Feature 4.6 wird ausgelöst (es gibt zu diesem Zeitpunkt noch nichts zurückzusetzen).
- **EC-47:** Zwei gleichzeitige Bestellungen reservieren eine IP im gleichen Subnetz (Race Condition) — IPAM selbst ist die Autorität über die IP-Vergabe. Das Portal macht sequentielle IPAM-Reservierungscalls pro Bestellung. IPAM stellt sicher, dass keine doppelte IP vergeben wird. Das Portal verlässt sich auf die Atomarität der IPAM-API.
- **EC-48:** Die reservierte IP wird manuell in IPAM gelöscht, bevor der Tofu-Job sie nutzt — Tofu versucht, die spezifische IP zu binden, und schlägt fehl. Feature 4.2 erkennt den Fehler-Status. Feature 4.6 versucht, die IP in IPAM freizugeben (wird ggf. mit "not found" quittiert, was akzeptiert wird). Der gesamte Provisioning-Vorgang schlägt fehl.
- **EC-49:** Das Subnetz hat noch exakt eine freie IP, und zwei Bestellungen werden simultan eingereicht — Analog EC-47: IPAM ist die Autorität. Eine Bestellung erhält die IP, die andere erhält einen "no available IP"-Fehler von IPAM und wechselt zu `failed` (REQ-73).
- **EC-50:** Rollback nach Feature 4.6: Die IP-Freigabe in IPAM schlägt fehl (API-Fehler) — Die `reservation_id` wird in einer Rollback-Retry-Queue persistiert. Das System versucht die Freigabe alle 10 Minuten für maximal 24 Stunden. Nach Ablauf wird ein Admin-Alert gesendet mit der manuell freizugebenden `reservation_id`.

---

## Feature 4.5: Datenbank-Provisioning

**User Story:**
Als Requester möchte ich nach Bestellung einer Datenbank-Instanz automatisch eine einsatzbereite Datenbank mit Benutzerkonto und Zugangsdaten erhalten, damit mein Team sofort mit der Entwicklung beginnen kann.

---

### Requirements

- **REQ-75:** Das Datenbank-Provisioning wird über ein dediziertes OpenTofu-Modul ausgeführt. Das Modul ist für PostgreSQL und MySQL/MariaDB separat implementiert. Der Datenbanktyp wird aus dem Bestellparameter `db_engine` (enum: `postgresql | mysql`) entnommen.
- **REQ-76:** Das Tofu-Modul legt folgende Ressourcen an: (a) eine DB-Instanz auf dem konfigurierten Ziel-Server, (b) eine Datenbank mit dem Namen aus dem Parameter `db_name`, (c) einen DB-User mit dem Namen aus dem Parameter `db_username`, (d) alle notwendigen Grants (CONNECT, CREATE, SELECT, INSERT, UPDATE, DELETE) für diesen User auf der angelegten Datenbank.
- **REQ-77:** Das initiale DB-Passwort wird vom System generiert (min. 24 Zeichen, zufällig, Komplexitätsanforderungen: min. 1 Grossbuchstabe, 1 Kleinbuchstabe, 1 Ziffer, 1 Sonderzeichen aus `!@#$%^&*()`). Das Passwort wird nicht im Klartext in der DB des Portals gespeichert. Es wird ausschliesslich über den Credential-Delivery-Mechanismus (REQ-80) übermittelt.
- **REQ-78:** Die Verbindungsdaten werden als strukturierter Tofu-Output zurückgeliefert und bei Übergang zu `active` in `provisioned_resources` gespeichert: `db_host`, `db_port`, `db_name`, `db_username`, `db_engine`. Das Passwort ist kein Tofu-Output und wird nicht im State-File gespeichert.
- **REQ-79:** Der `db_name` muss den Konventionen des jeweiligen DB-Engines entsprechen: Für PostgreSQL und MySQL: max. 63 Zeichen, nur `[a-z0-9_]`, muss mit Buchstabe beginnen. Ein gleichnamiges Datenbankobjekt auf demselben Server darf nicht existieren (Vorab-Prüfung über DB-Connector).
- **REQ-80:** Nach erfolgreichem Provisioning (`active`) werden die vollständigen Zugangsdaten (inklusive generiertem Passwort) exakt einmal sicher an den Requester übermittelt. Die Übermittlung erfolgt über einen zeitlich begrenzten, einmalig abrufbaren Secure-Link (Token-basiert, gültig für 48 Stunden, nur einmal abrufbar). Der Link wird per E-Mail und System-Notification gesendet.
- **REQ-81:** Nach Ablauf oder Abruf des Secure-Links ist das Passwort nicht mehr über das Portal abrufbar. Der Requester muss bei Bedarf über einen separaten Passwort-Reset-Flow (ausserhalb des MVP) vorgehen. Die Bestellung enthält nur noch die verbindungsparameter ohne Passwort.
- **REQ-82:** Das Tofu-Modul prüft vor dem Anlegen, ob der Ziel-DB-Server erreichbar ist. Ist er nicht erreichbar, schlägt der Job fehl, und Feature 4.6 wird ausgelöst.
- **REQ-83:** Die Ziel-DB-Server-Konfiguration (Host, Port, Admin-Credentials für Provisionierung) ist per Admin-Konfiguration pflegbar und wird verschlüsselt gespeichert. Pro `db_engine` und `environment` ist ein Ziel-Server konfigurierbar.

---

### Validation Rules

- **VAL-40:** `db_engine` (Bestellparameter) — Muss `postgresql` oder `mysql` sein — `"Der Datenbanktyp '{value}' wird nicht unterstützt."`
- **VAL-41:** `db_name` (Bestellparameter) — Max. 63 Zeichen, Pattern `^[a-z][a-z0-9_]{0,62}$` — `"Der Datenbankname darf nur Kleinbuchstaben, Ziffern und Unterstriche enthalten und muss mit einem Buchstaben beginnen (max. 63 Zeichen)."`
- **VAL-42:** `db_username` (Bestellparameter) — Max. 63 Zeichen, Pattern `^[a-z][a-z0-9_]{0,62}$`, darf keine reservierten System-Benutzernamen sein (z.B. `postgres`, `root`, `admin`, `mysql`) — `"Der Datenbankbenutzername '{value}' ist ungültig oder reserviert."`
- **VAL-43:** `db_name` Eindeutigkeit — Auf dem konfigurierten Ziel-DB-Server darf keine Datenbank mit demselben Namen existieren — `"Eine Datenbank mit dem Namen '{db_name}' existiert bereits auf dem Zielserver."`
- **VAL-44:** Secure-Link-Token — Muss ein kryptographisch sicherer Zufallswert (min. 32 Bytes, URL-safe Base64) sein — (interne Validierung, keine Fehlermeldung an User)

---

### API Contract

**Endpoint 31: Retrieve database credentials via secure link (requester)**
```
GET /api/v1/credentials/{token}
```
(Kein Auth-Header erforderlich — der Token ist das Authentifizierungsmerkmal)

Response 200 (einmalig abrufbar):
```json
{
  "order_id": "uuid",
  "db_host": "string",
  "db_port": "integer",
  "db_name": "string",
  "db_username": "string",
  "db_password": "string",
  "db_engine": "postgresql | mysql",
  "connection_string": "string (jdbc/psql-format)",
  "valid_until": "ISO8601 datetime",
  "warning": "Diese Zugangsdaten werden nur einmal angezeigt. Bitte sicher speichern."
}
```
Response 404: Token nicht gefunden oder bereits abgerufen
Response 410: Token abgelaufen (48 Stunden überschritten)

---

**Endpoint 32: Get database server configuration (admin)**
```
GET /api/v1/admin/db-servers
```
Response 200:
```json
{
  "db_servers": [
    {
      "server_id": "uuid",
      "db_engine": "postgresql | mysql",
      "environment": "string",
      "host": "string",
      "port": "integer",
      "admin_user": "string",
      "admin_password_configured": "boolean"
    }
  ]
}
```
Response 403: Nur Admin

---

**Endpoint 33: Add or update database server configuration (admin)**
```
PUT /api/v1/admin/db-servers/{server_id}
```
Request Body:
```json
{
  "db_engine": "postgresql | mysql",
  "environment": "string",
  "host": "string",
  "port": "integer",
  "admin_user": "string",
  "admin_password": "string"
}
```
Response 200: Aktualisierte Server-Konfiguration (ohne `admin_password`, mit `admin_password_configured: true`)
Response 400: Validation-Fehler
Response 403: Nur Admin

---

### Edge Cases

- **EC-51:** Der Secure-Link wird kurz nach dem Versand der E-Mail zweimal gleichzeitig aufgerufen (z.B. E-Mail-Scanner und echter User) — Der erste Abruf setzt den Token atomar auf `consumed`. Der zweite Abruf erhält HTTP 404. Das System loggt den doppelten Abrufversuch inkl. IP-Adresse für Audit-Zwecke.
- **EC-52:** Die E-Mail mit dem Secure-Link kommt nicht beim Requester an (Spam-Filter o.ä.) — Der Requester kann über die Portal-UI erkennen, dass die Bestellung aktiv ist. Ein manueller "Zugangsdaten erneut senden"-Button ist nicht Teil des MVP. Der Admin kann den Credential-Link im Admin-Bereich einsehen (Sonder-Endpoint ausserhalb MVP, zu klären).
- **EC-53:** Das Tofu-Modul kann den DB-User nicht anlegen, weil ein User mit demselben Namen bereits existiert — Tofu schlägt fehl. Feature 4.2 erkennt den `failed`-Status. Feature 4.6 versucht, die angelegte DB-Instanz zurückzusetzen (Tofu destroy). VAL-43 hätte dies bei `db_name`-Prüfung theoretisch verhindert, aber `db_username`-Konflikte auf Server-Ebene sind separat möglich.
- **EC-54:** Der Ziel-DB-Server hat einen anderen Zeichensatz-Standard als die Bestellparameter implizieren (z.B. UTF-8 vs. latin1) — Das Tofu-Modul setzt Encoding und Collation explizit auf `UTF-8` / `utf8mb4` (für MySQL), unabhängig vom Server-Default. Abweichungen werden als Parameter übergeben, falls der Requester explizit abweicht.
- **EC-55:** Zwei Bestellungen für dieselbe `db_name` auf demselben Server werden gleichzeitig eingereicht — VAL-43 (Vorab-Prüfung) ist ohne Datenbanklock eine Race Condition. Tofu-Modul-Ebene liefert den eigentlichen Schutz: Beide Jobs starten, aber der zweite scheitert an der DB-Engine (UNIQUE-Constraint). Feature 4.6 bereinigt den zweiten Job. Das Portal protokolliert den Konflikt.

---

## Feature 4.6: Fehlerbehandlung & Rollback

**User Story:**
Als System möchte ich bei einem Fehler während der Provisionierung alle bereits angelegten Ressourcen zuverlässig freigeben und den Bestellstatus eindeutig auf `failed` setzen, damit keine Ressourcen-Leichen entstehen und der Requester über den Fehler informiert wird.

---

### Requirements

- **REQ-84:** Feature 4.6 wird ausgelöst durch: (a) Provisioning-Timeout (REQ-58), (b) Fehler beim Job-Dispatch (REQ-50), (c) Gitlab-/Tofu-Job-Status `failed` oder `canceled` (REQ-54), (d) fehlende Tofu-Outputs (VAL-30), (e) Fehler bei IPAM-Reservierung (REQ-73), (f) Fehler beim AD-Objekt-Anlegen, (g) manuellen Admin-Trigger.
- **REQ-85:** Der Rollback erfolgt in der Reihenfolge, die der umgekehrten Orchestrierungsreihenfolge entspricht. Für VM/Container: (1) Tofu destroy (falls Job gestartet wurde), (2) AD-Computer-Objekt löschen (falls angelegt), (3) IPAM-IP freigeben (falls reserviert). Für Datenbank: (1) Tofu destroy, (2) IPAM freigeben (falls reserviert).
- **REQ-86:** Jeder Rollback-Schritt ist atomar und wird unabhängig protokolliert. Schlägt ein Rollback-Schritt fehl, werden die verbleibenden Schritte trotzdem ausgeführt. Fehlgeschlagene Rollback-Schritte werden als "pending manual cleanup" markiert und sind im Admin-Dashboard sichtbar.
- **REQ-87:** Nach Abschluss des Rollbacks (unabhängig vom Erfolg einzelner Schritte) wird der Bestellstatus auf `failed` gesetzt. Die Bestellung bleibt in `failed` unabhängig davon, ob der Rollback vollständig erfolgreich war.
- **REQ-88:** Das `failure_reason`-Feld enthält eine kategorisierte, für Requesters lesbare Fehlermeldung (keine Stack-Traces). Technische Details werden im Server-Log gespeichert. Mögliche Kategorien: `provisioning_timeout`, `dispatcher_unavailable`, `tofu_job_failed`, `missing_outputs`, `ipam_unavailable`, `ad_error`, `manual_cancel`.
- **REQ-89:** Der Requester wird nach Abschluss des Rollbacks per Benachrichtigung (E-Mail und System-Notification) informiert. Die Benachrichtigung enthält: Bestellnummer, Service-Typ, kategorisierten Fehlergrund, Empfehlung (z.B. "Bitte wenden Sie sich an den Support mit Bestellnummer X.").
- **REQ-90:** Ein Admin kann einen Rollback manuell auslösen für Bestellungen im Status `provisioning` oder `failed` (zur Bereinigung unvollständiger Rollbacks). Ein manueller Rollback erzeugt einen neuen `order_status_history`-Eintrag mit `changed_by: "<admin_user_id>"`.
- **REQ-91:** Der Tofu-Destroy-Schritt im Rollback wird als separater Gitlab-Pipeline-Job (`destroy`-Stage) oder direkter Tofu-API-Aufruf ausgelöst. Der `destroy`-Job erhält dieselben Parameter wie der `apply`-Job, plus `TF_VAR_action: destroy`. Der Status dieses Destroy-Jobs wird in `dispatch_log` protokolliert.
- **REQ-92:** Existiert zur Bestellung kein Tofu-State (z.B. weil der Job nie gestartet ist), wird der Tofu-Destroy-Schritt übersprungen und nur IPAM und AD bereinigt.

---

### Validation Rules

- **VAL-45:** Manueller Rollback-Trigger (Admin) — Bestellung muss im Status `provisioning` oder `failed` sein — `"Ein Rollback kann nur für Bestellungen im Status 'provisioning' oder 'failed' ausgelöst werden (aktueller Status: {current_status})."`
- **VAL-46:** Rollback-Bestätigung (Admin) — Der Admin muss bei manuellem Rollback eine Bestätigungs-Flag `confirm: true` im Request mitsenden — `"Bitte bestätigen Sie den Rollback mit dem Feld 'confirm: true'."`

---

### API Contract

**Endpoint 34: Trigger manual rollback for an order (admin)**
```
POST /api/v1/admin/orders/{order_id}/rollback
```
Request Body:
```json
{
  "confirm": true,
  "reason": "string (optional, max 500 chars)"
}
```
Response 202:
```json
{
  "order_id": "uuid",
  "rollback_triggered_at": "ISO8601 datetime",
  "rollback_steps": [
    {
      "step": "tofu_destroy | ad_delete | ipam_release",
      "status": "pending"
    }
  ],
  "triggered_by": "string (admin user_id)"
}
```
Response 400: `confirm` fehlt oder `false`
Response 403: Nur Admin
Response 404: Bestellung nicht gefunden
Response 409: Status nicht `provisioning` oder `failed`

---

**Endpoint 35: Get rollback status and pending manual cleanups (admin)**
```
GET /api/v1/admin/orders/{order_id}/rollback-status
```
Response 200:
```json
{
  "order_id": "uuid",
  "rollback_triggered_at": "ISO8601 datetime | null",
  "rollback_completed_at": "ISO8601 datetime | null",
  "triggered_by": "string (user_id or 'system')",
  "steps": [
    {
      "step": "tofu_destroy | ad_delete | ipam_release",
      "status": "success | failed | skipped | pending",
      "attempted_at": "ISO8601 datetime | null",
      "error_message": "string | null"
    }
  ],
  "pending_manual_cleanups": [
    {
      "step": "string",
      "resource_reference": "string (z.B. AD-DN oder IPAM reservation_id)",
      "instructions": "string"
    }
  ]
}
```
Response 404: Kein Rollback für diese Bestellung
Response 403: Nur Admin

---

### Edge Cases

- **EC-56:** Rollback wird ausgelöst, während der Tofu-`apply`-Job noch läuft — Das System sendet zunächst einen Abbruch-Signal an Gitlab (Cancel Pipeline API). Danach wartet es maximal 2 Minuten auf den `canceled`-Status, bevor der Destroy-Job gestartet wird. Gibt Gitlab nicht zurück, wird der Destroy-Job trotzdem gestartet (Tofu ist idempotent bei destroy).
- **EC-57:** Das AD-Objekt-Löschen im Rollback schlägt fehl (z.B. LDAP-Verbindungsfehler) — REQ-86 greift: Der Schritt wird als `failed` markiert, der Rollback fährt mit dem nächsten Schritt fort. Das AD-Objekt landet in `pending_manual_cleanups` mit dem Distinguished Name und der Anweisung "Manuelles Löschen erforderlich."
- **EC-58:** Ein Rollback wird während eines anderen laufenden Rollbacks ausgelöst (manuell durch Admin) — Das System prüft, ob bereits ein Rollback für diese Bestellung aktiv ist. Ist dies der Fall, wird HTTP 409 zurückgegeben mit "Für diese Bestellung läuft bereits ein Rollback."
- **EC-59:** Tofu-Destroy schlägt fehl (z.B. Ressource schon gelöscht) — Tofu-Destroy ist bei nicht-existenten Ressourcen idempotent (exit code 0 mit "nothing to do"). Nur echter Fehler (exit code != 0) wird als fehlgeschlagen gewertet.
- **EC-60:** Der Requester reicht nach einem fehlgeschlagenen Rollback dieselbe Bestellung erneut ein — Laut REQ-27 (Feature 3.1) wird eine neue Bestellung mit neuer `order_id` erstellt. Das Portal prüft nicht, ob eine vorige Bestellung für denselben Service-Typ vorhanden war. Ein vorheriger, nicht vollständig bereinigter Zustand (z.B. hängender AD-Objekt-Rollback) muss manuell durch den Admin bereinigt werden, bevor die neue Bestellung provisioniert werden kann — das ist dokumentierte Anforderung.

---

## Feature 4.7: Idempotenz-Schutz

**User Story:**
Als System möchte ich sicherstellen, dass eine Bestellung niemals doppelt provisioniert wird, selbst wenn Retries, Timeouts oder parallele Prozesse einen erneuten Dispatch auslösen, damit keine Ressourcen-Duplikate entstehen.

---

### Requirements

- **REQ-93:** Jedes OrderItem hat genau einen zulässigen Übergang des `provisioning_status` von `pending` zu `provisioning`. Dieser Übergang ist mit einem Idempotenz-Key (`order_item_id`) geschützt. Ein zweiter Versuch, dasselbe OrderItem in `provisioning` zu überführen, wird mit einem Konflikt-Fehler abgebrochen. Mehrere Items derselben Order können gleichzeitig diesen Übergang durchlaufen, da der Check pro Item atomar ist.
- **REQ-94:** Der Idempotenz-Check wird als atomischer Datenbankvorgang pro **OrderItem** implementiert: Der `provisioning_status`-Übergang `pending` → `provisioning` am OrderItem erfolgt nur, wenn der aktuelle `provisioning_status` des Items exakt `pending` ist und noch keine `job_id` am Item gesetzt ist. Eine einzelne UPDATE-Query mit diesen Bedingungen in der WHERE-Klausel und Prüfung der betroffenen Zeilen (affected rows = 0 bedeutet: Konflikt).
- **REQ-95:** Bei einem erkannten Idempotenz-Konflikt prüft der Dispatcher, ob für die Bestellung bereits ein aktiver Job in Gitlab/Tofu existiert (anhand der gespeicherten `job_id`). Existiert ein aktiver Job, wird Feature 4.2 (Status-Sync) gestartet, ohne einen neuen Job auszulösen. Existiert kein aktiver Job (z.B. `job_id` vorhanden, aber Job in Gitlab nicht mehr auffindbar), wird der Admin benachrichtigt und manuelles Eingreifen angefordert.
- **REQ-96:** Kommt ein OrderItem-Event aus der Job-Queue, dessen OrderItem bereits den `provisioning_status` `provisioning`, `done` oder `failed` hat, wird es ohne Fehler ignoriert (silent drop). Ein Log-Eintrag wird erstellt.
- **REQ-97:** Falls der Dispatcher nach dem Auslösen des Jobs abstürzt (nach Gitlab-Call, vor DB-Update), erkennt der nächste Startup-Check alle OrderItems mit `provisioning_status` `pending`, die älter als 5 Minuten sind und keine `job_id` haben. Für diese führt der Dispatcher einen deduplication-Check gegen Gitlab aus: Gibt es einen Job, der in den letzten 10 Minuten mit dieser `order_item_id` als Variable gestartet wurde? Ja → `job_id` nachtragen, `provisioning_status` zu `provisioning` überführen. Nein → erneut auslösen.
- **REQ-98:** Der Idempotenz-Mechanismus greift ausschliesslich auf Datenbankebene. Es gibt keine externe Idempotenz-Infrastruktur (Redis, etc.) als harte Anforderung. Die DB-Transaktion ist die einzige Source of Truth.
- **REQ-99:** Manuelle Dispatch-Triggers über Endpoint 20 (Admin) unterliegen demselben Idempotenz-Check wie automatische Dispatchs. Der Admin erhält HTTP 409, wenn das adressierte OrderItem bereits eine `job_id` hat oder sich nicht im `provisioning_status` `pending` befindet.

---

### Validation Rules

(Keine eigenständigen Validation Rules — der Idempotenz-Schutz ist vollständig in REQ-93 bis REQ-99 über DB-Constraints und Statuschecks abgedeckt. Fehlermeldungen bei Konflikten sind in den jeweiligen Endpoint-Responses von Feature 4.1 definiert.)

---

### API Contract

**Endpoint 36: Get idempotency status for an order (admin)**
```
GET /api/v1/admin/orders/{order_id}/idempotency-status
```
Response 200:
```json
{
  "order_id": "uuid",
  "current_status": "string",
  "job_id": "string | null",
  "dispatch_attempt_count": "integer",
  "last_dispatch_attempt_at": "ISO8601 datetime | null",
  "idempotency_conflicts_detected": "integer",
  "deduplication_checks": [
    {
      "checked_at": "ISO8601 datetime",
      "gitlab_job_found": "boolean",
      "action_taken": "noop | job_id_recovered | redispatched | manual_required"
    }
  ]
}
```
Response 404: Bestellung nicht gefunden
Response 403: Nur Admin

---

### Edge Cases

- **EC-61:** Ein Operator startet den Portal-Server neu, während OrderItems im `provisioning_status` `pending` sind — REQ-97 greift: Beim Startup werden alle verwaisten OrderItems (älter als 5 Minuten, `provisioning_status` = `pending`, keine `job_id`) geprüft und ggf. neu dispatched. Items mit bereits gesetzter `job_id` (aber `provisioning_status` noch `pending` infolge des Absturzes) werden per deduplication-Check in Gitlab verifiziert und zu `provisioning` überführt, dann direkt an Feature 4.2 übergeben.
- **EC-62:** Die Job-Queue liefert dasselbe OrderItem-Event zweimal aus (At-Least-Once-Delivery-Semantik) — REQ-96 greift für Items mit `provisioning_status` `provisioning`/`done`/`failed`: das duplizierte Event wird als silent drop verworfen. REQ-94 greift für Items, die noch im `provisioning_status` `pending` sind: Der zweite Dispatch-Versuch scheitert am atomischen DB-Update auf dem OrderItem (affected rows = 0).
- **EC-63:** Admin löst über Endpoint 20 einen manuellen Dispatch aus, während der automatische Dispatcher dieselbe Bestellung gerade verarbeitet — REQ-99 greift: Der erste der beiden Dispatchs (automatisch oder manuell) gewinnt den DB-Lock. Der zweite erhält HTTP 409 (wenn manuell) oder bricht intern ab (wenn automatisch).
- **EC-64:** Ein OrderItem bleibt dauerhaft im `provisioning_status` `pending` stecken, weil der automatische Startup-Check noch nie gelaufen ist (z.B. frisch installiertes System) — Der Startup-Check läuft einmalig bei jedem Server-Start und zusätzlich alle 10 Minuten als zyklischer Job. Er prüft alle OrderItems mit `provisioning_status` `pending`, die älter als 5 Minuten sind. Er ist kein einmaliger Prozess.
- **EC-65:** Der deduplication-Check gegen Gitlab gibt unklare Ergebnisse zurück (z.B. mehrere Jobs mit `order_item_id`-Variable gefunden) — Das System wählt den neuesten Job (nach `created_at`). Alle anderen werden als "orphaned jobs" geloggt und ein Admin-Alert wird gesendet. Der neueste Job wird als massgeblich betrachtet.
- **EC-66:** Teilweises Provisioning — In einer Multi-Item-Order werden 3 von 5 OrderItems erfolgreich provisioniert (`provisioning_status` = `done`), 2 schlagen fehl (`provisioning_status` = `failed`) — Die Order-Ebene wechselt nach Abschluss aller Items zu `failed` (ein einziges fehlgeschlagenes Item setzt den Order-Status auf `failed`). Die 3 erfolgreich provisionierten Items behalten `provisioning_status` = `done` und ihre `provisioned_resources` bleiben erhalten. Feature 4.6 (Rollback) wird ausschliesslich für die 2 fehlgeschlagenen Items ausgelöst; die 3 erfolgreichen Items werden nicht zurückgerollt. Der Admin und der Requester erhalten eine Benachrichtigung, die explizit auflistet, welche Items erfolgreich und welche fehlgeschlagen sind. Ein manueller Rollback über Endpoint 34 bezieht sich weiterhin auf die gesamte Order, rollt aber intern nur Items zurück, die sich in `provisioning` oder `failed` befinden und noch Ressourcen haben, die freigegeben werden können.

---

## Abhängigkeitsmatrix

| Feature | Setzt voraus | Beeinflusst |
|---|---|---|
| 4.1 Job-Dispatcher | order-lifecycle.md 3.1–3.4 (Multi-Item-Dispatch-Event pro OrderItem, `submitted`-Status), 4.4 (IP vorhanden), 4.3 (AD vorhanden, nur VM/Container) | 4.2 (liefert job_id pro Item), 4.6 (bei Dispatch-Fehler), 4.7 (Idempotenz pro Item) |
| 4.2 Status-Sync | 4.1 (job_id pro OrderItem), Gitlab/Tofu API | order-lifecycle.md 3.2 (SSE-Events), 4.5 (Credentials bei done), 4.6 (bei failed) |
| 4.3 AD-Integration | — | 4.1 (Voraussetzung für VM/Container-Dispatch, ServiceType aus template_slug) |
| 4.4 IPAM-Integration | — | 4.1 (Voraussetzung für VM/Container-Dispatch), 4.6 (Rollback-Schritt pro Item) |
| 4.5 DB-Provisioning | 4.1, 4.2, 4.4 (optional) | 4.6 (Rollback) |
| 4.6 Fehlerbehandlung & Rollback | 4.1 (destroy-Job), 4.3 (AD-Delete), 4.4 (IP-Release) | order-lifecycle.md 3.2 (Status failed + SSE), EC-66 (partielles Provisioning) |
| 4.7 Idempotenz-Schutz | 4.1 (integriert, Idempotenz-Key = order_item_id) | Alle Dispatch-Pfade |

**Abhängigkeit zu order-lifecycle.md (Features 3.1–3.4):**

| order-lifecycle.md | Relevanz für Gruppe 4 |
|---|---|
| Feature 3.1 Order-Erstellung | Definiert OrderItem-Struktur mit `template_slug`, `template_version`, `parameters` |
| Feature 3.2 Status-Maschine | Definiert Order-Status `submitted` (Startpunkt für Gruppe 4) und `provisioning`/`done`/`failed` |
| Feature 3.3 Approval-Workflow | Stellt das Dispatch-Event pro OrderItem in die Job-Queue ein (REQ-44) — bei `submitted` (ohne Approval-Pflicht) und bei `approved` (nach Approver-Entscheidung); Event-Format in beiden Fällen identisch |
| Feature 3.4 SSE-Notification | Empfängt Status-Updates von Feature 4.2 für Echtzeit-Anzeige |

---

## Nummerierungsstand nach Gruppe 4

- Requirements: REQ-44 bis REQ-99
- Validation Rules: VAL-23 bis VAL-46
- Endpoints: 18 bis 36
- Edge Cases: EC-30 bis EC-66
