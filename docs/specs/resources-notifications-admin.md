# Feature-Spezifikationen: Gruppen 5–7 — Ressourcen, Benachrichtigungen, Administration

> **Status:** Draft v1.1 — Approval-Events in Feature 6.1 (E-Mail) und Feature 7.2 (Audit-Log) ergänzt
> **Erstellt:** 2026-03-26
> **Letzte Änderung:** 2026-03-26
> **Umfang:** 5 Features, Requirements REQ-01–REQ-67, Validation Rules VAL-01–VAL-29, API Endpoints 1–22, Edge Cases EC-01–EC-45
> **Abhängigkeiten:** Gruppe 1 (identity-access.md), Gruppe 3 (order-lifecycle.md), Gruppe 4 (provisioning-engine.md)

---

## Inhaltsverzeichnis

- [Gruppe 5: Ressourcen-Verwaltung](#gruppe-5-ressourcen-verwaltung)
  - [Feature 5.1: Meine Ressourcen (Übersicht)](#feature-51-meine-ressourcen-übersicht)
- [Gruppe 6: Benachrichtigungen](#gruppe-6-benachrichtigungen)
  - [Feature 6.1: E-Mail-Benachrichtigungen](#feature-61-e-mail-benachrichtigungen)
  - [Feature 6.2: Zugangsdaten-Lieferung](#feature-62-zugangsdaten-lieferung)
- [Gruppe 7: Administration & Governance](#gruppe-7-administration--governance)
  - [Feature 7.1: Admin-Dashboard](#feature-71-admin-dashboard)
  - [Feature 7.2: Audit-Log](#feature-72-audit-log)
- [Abhängigkeitsmatrix](#abhängigkeitsmatrix)

---

## Logisches Datenmodell (gruppenübergreifend)

### ProvisionedResource

```
ProvisionedResource {
  id:               string (UUID)          // serverseitig generiert, unveränderlich
  order_id:         string (UUID)          // Referenz auf die Order (aus order-lifecycle.md)
  order_item_id:    string (UUID)          // Referenz auf das OrderItem
  requester_id:     string (UUID)          // aus der Order übernommen
  service_type:     string                 // Enum: vm | database | container
  status:           string                 // active | decommissioned | error
  hostname:         string | null          // FQDN oder Kurzname (nur vm/container)
  ip_address:       string | null          // IPv4-Adresse (nur vm/container, ggf. database)
  db_host:          string | null          // DB-Host (nur database)
  db_port:          integer | null         // DB-Port (nur database)
  db_name:          string | null          // DB-Name (nur database)
  db_username:      string | null          // DB-User (nur database)
  db_engine:        string | null          // postgresql | mysql (nur database)
  order_number:     string                 // menschenlesbare Bestellnummer (Snapshot)
  template_slug:    string                 // Template-Slug zum Zeitpunkt der Bestellung
  provisioned_at:   ISO-8601 datetime      // Zeitpunkt des Übergangs zu "active"
  created_at:       ISO-8601 datetime
  updated_at:       ISO-8601 datetime
}
```

> Hinweis: Der Datensatz wird durch Feature 4.2 (REQ-55) befüllt, wenn der Provisioning-Job
> erfolgreich abgeschlossen wird. Diese Spec definiert Lese- und Verwaltungszugriffe.

### CredentialToken

```
CredentialToken {
  id:               string (UUID)
  order_item_id:    string (UUID)          // Referenz auf das OrderItem (Datenbank-Bestellung)
  requester_id:     string (UUID)
  token:            string                 // kryptographisch zufällig, min. 32 Bytes, URL-sicher (Base64url)
  status:           string                 // pending | consumed | expired | revoked
  created_at:       ISO-8601 datetime
  expires_at:       ISO-8601 datetime      // created_at + 48 Stunden
  consumed_at:      ISO-8601 datetime | null
  consumed_ip:      string | null          // IP des abrufenden Clients
  created_by:       string                 // "system" oder admin user_id (bei manuellem Re-Issue)
}
```

### NotificationRecord

```
NotificationRecord {
  id:               string (UUID)
  recipient_id:     string (UUID)          // User-ID
  recipient_email:  string                 // E-Mail-Adresse zum Sendezeitpunkt (Snapshot)
  event_type:       string                 // Enum: order_submitted | provisioning_done | provisioning_failed | approval_requested | approval_approved | approval_rejected | approval_timeout_warning
  order_id:         string (UUID)
  template_key:     string                 // Schlüssel des verwendeten E-Mail-Templates
  status:           string                 // pending | sent | failed | retry_exhausted
  attempt_count:    integer                // Startwert: 0
  last_attempt_at:  ISO-8601 datetime | null
  next_attempt_at:  ISO-8601 datetime | null
  sent_at:          ISO-8601 datetime | null
  error_message:    string | null
  created_at:       ISO-8601 datetime
}
```

### AuditLogEntry

```
AuditLogEntry {
  id:               string (UUID)          // unveränderlich, serverseitig generiert
  timestamp:        ISO-8601 datetime      // Zeitpunkt der Aktion (UTC), unveränderlich
  actor_type:       string                 // Enum: user | system | service_account
  actor_id:         string                 // User-ID, "system" oder Service-Account-ID
  actor_name:       string                 // Snapshot des Displaynamens zum Zeitpunkt der Aktion
  action:           string                 // Enum (vollständige Liste: siehe REQ-55)
  resource_type:    string                 // Enum: order | order_item | resource | credential_token | user | service_template | system_config | audit_log
  resource_id:      string | null          // UUID der betroffenen Ressource
  resource_ref:     string | null          // menschenlesbare Referenz (z.B. Bestellnummer)
  result:           string                 // Enum: success | failure | partial
  detail:           object | null          // kontextspezifische Zusatzinformationen (kein Passwort, kein Secret)
  ip_address:       string | null          // Client-IP (nur bei User-Aktionen)
}
```

---

## Gruppe 5: Ressourcen-Verwaltung

---

## Feature 5.1: Meine Ressourcen (Übersicht)

**User Story:**
Als Requester möchte ich alle aktiven Ressourcen, die aus meinen Bestellungen provisioniert wurden, in einer Übersicht sehen, damit ich den Überblick über meine IT-Ressourcen behalte und bei Bedarf auf die zugehörige Bestellung navigieren kann.

---

### Requirements

- **REQ-01:** Das System stellt eine Liste aller `ProvisionedResource`-Datensätze bereit, deren `requester_id` der ID des authentifizierten Users entspricht. Ein Requester sieht ausschliesslich seine eigenen Ressourcen.

- **REQ-02:** Pro Ressource werden folgende Felder in der Listenansicht zurückgeliefert: `id`, `service_type`, `status`, `hostname` (null für Datenbanken), `ip_address` (null, falls nicht zutreffend), `db_host` + `db_port` + `db_name` + `db_engine` (null, falls nicht zutreffend), `order_number`, `order_id`, `template_slug`, `provisioned_at`.

- **REQ-03:** Die Liste unterstützt Filterung nach `service_type` (Enum: vm | database | container, Mehrfachwahl zulässig). Ist kein Filter gesetzt, werden alle Ressourcen zurückgeliefert.

- **REQ-04:** Die Liste unterstützt Filterung nach `status` (Enum: active | decommissioned | error, Mehrfachwahl zulässig). Ist kein Filter gesetzt, werden alle Status zurückgeliefert.

- **REQ-05:** Die Liste ist standardmässig nach `provisioned_at` absteigend sortiert. Eine alternative Sortierung nach `service_type` (alphabetisch aufsteigend) ist über den Query-Parameter `sort_by` konfigurierbar.

- **REQ-06:** Die Liste ist paginiert. Standardseitengrösse: 20 Einträge. Maximale Seitengrösse: 100 Einträge. Die Antwort enthält immer `total_count`, `page`, `page_size` und `has_next_page`.

- **REQ-07:** Für jede Ressource liefert die API eine direkte Referenz auf die zugehörige Order: `order_id` und `order_number`. Die Navigation zur Order-Detailseite (GET /api/v1/orders/{order_id}) erfolgt clientseitig anhand dieser Felder.

- **REQ-08:** Ein Admin kann die Ressourcenliste beliebiger User einsehen. Der Zugriff erfolgt über denselben Endpoint mit einem zusätzlichen Query-Parameter `requester_id`. Ohne diesen Parameter liefert der Endpoint immer nur die eigenen Ressourcen des authentifizierten Users zurück — auch bei Admin-Rolle.

- **REQ-09:** Ressourcen im Status `decommissioned` werden in der Standardansicht nicht ausgeblendet. Sie sind durch den Status-Filter auffindbar. Das Feld `decommissioned_at` (ISO-8601 datetime | null) wird in der Response mitgeliefert.

- **REQ-10:** Die Detailansicht einer einzelnen Ressource liefert zusätzlich: `order_item_id`, alle verfügbaren Verbindungsfelder (vollständig, nicht gefiltert), sowie einen Link zum Credential-Token-Status (nur für Datenbanken, nur falls `status = active`): `credential_status` (Enum: available | consumed | expired | none).

---

### Validation Rules

- **VAL-01:** Query-Parameter `service_type` — Muss einer oder mehrere der Werte `vm`, `database`, `container` sein (kommasepariert) — `"Ungültiger service_type-Filter. Erlaubte Werte: vm, database, container."`

- **VAL-02:** Query-Parameter `status` — Muss einer oder mehrere der Werte `active`, `decommissioned`, `error` sein (kommasepariert) — `"Ungültiger status-Filter. Erlaubte Werte: active, decommissioned, error."`

- **VAL-03:** Query-Parameter `page_size` — Muss eine positive Ganzzahl sein, maximal 100 — `"page_size muss zwischen 1 und 100 liegen."`

- **VAL-04:** Query-Parameter `sort_by` — Muss einer der Werte `provisioned_at` (default) oder `service_type` sein — `"Ungültiger sort_by-Wert. Erlaubte Werte: provisioned_at, service_type."`

- **VAL-05:** Query-Parameter `requester_id` (Admin-Zugriff) — Muss eine valide UUID sein und zu einem existierenden User gehören — `"Der angegebene requester_id ist ungültig oder der User existiert nicht."`

---

### API Contract

**Endpoint 1: List provisioned resources for authenticated user (requester/admin)**
```
GET /api/v1/resources
```
Query Parameters:
```
service_type  string  optional  Kommaseparierte Werte: vm,database,container
status        string  optional  Kommaseparierte Werte: active,decommissioned,error
sort_by       string  optional  provisioned_at (default) | service_type
page          integer optional  default: 1
page_size     integer optional  default: 20, max: 100
requester_id  uuid    optional  Nur für admin-Rolle. Ohne diesen Parameter = eigene Ressourcen.
```
Response 200:
```json
{
  "data": [
    {
      "id": "uuid",
      "service_type": "vm | database | container",
      "status": "active | decommissioned | error",
      "hostname": "string | null",
      "ip_address": "string | null",
      "db_host": "string | null",
      "db_port": "integer | null",
      "db_name": "string | null",
      "db_engine": "postgresql | mysql | null",
      "order_number": "string",
      "order_id": "uuid",
      "template_slug": "string",
      "provisioned_at": "ISO8601 datetime",
      "decommissioned_at": "ISO8601 datetime | null"
    }
  ],
  "pagination": {
    "total_count": "integer",
    "page": "integer",
    "page_size": "integer",
    "has_next_page": "boolean"
  }
}
```
Response 400: Ungültige Query-Parameter (VAL-01 bis VAL-05)
Response 401: Nicht authentifiziert
Response 403: `requester_id`-Parameter ohne Admin-Rolle

---

**Endpoint 2: Get provisioned resource detail (requester/admin)**
```
GET /api/v1/resources/{resource_id}
```
Response 200:
```json
{
  "id": "uuid",
  "order_id": "uuid",
  "order_item_id": "uuid",
  "order_number": "string",
  "requester_id": "uuid",
  "service_type": "vm | database | container",
  "status": "active | decommissioned | error",
  "hostname": "string | null",
  "ip_address": "string | null",
  "db_host": "string | null",
  "db_port": "integer | null",
  "db_name": "string | null",
  "db_username": "string | null",
  "db_engine": "postgresql | mysql | null",
  "template_slug": "string",
  "provisioned_at": "ISO8601 datetime",
  "decommissioned_at": "ISO8601 datetime | null",
  "credential_status": "available | consumed | expired | none",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```
Response 401: Nicht authentifiziert
Response 403: Ressource gehört nicht dem authentifizierten User (ausser Admin)
Response 404: Ressource nicht gefunden

---

### Edge Cases

- **EC-01:** Ein Requester ruft die Ressourcenliste ab, hat aber noch keine abgeschlossenen Bestellungen — Die API liefert HTTP 200 mit `data: []` und `total_count: 0`. Kein 404.

- **EC-02:** Eine Ressource existiert, die zugehörige Order wurde inzwischen gelöscht (Datenkonsistenzfehler) — `order_number` und `order_id` werden als gespeicherter Snapshot zurückgeliefert. Der Link zur Order-Detailseite liefert 404; das Frontend muss diesen Fall gesondert behandeln.

- **EC-03:** Ein Requester versucht, die Ressource eines anderen Users über `GET /api/v1/resources/{resource_id}` abzurufen — HTTP 403 (nicht 404), um keine Informationen über die Existenz fremder Ressourcen preiszugeben.

- **EC-04:** Admin-Benutzer ruft Ressourcenliste ohne `requester_id` auf — Es werden ausschliesslich die eigenen Ressourcen des Admins zurückgeliefert, sofern der Admin selbst Ressourcen hat. Kein impliziter "alle Ressourcen"-Modus.

- **EC-05:** Grosse Ressourcenliste (z.B. 10.000 Einträge) — Paginierung verhindert Performance-Einbrüche. Der Endpoint darf keine ungepaginierte Vollabfrage erlauben. `page_size > 100` wird mit HTTP 400 abgewiesen.

---

## Gruppe 6: Benachrichtigungen

---

## Feature 6.1: E-Mail-Benachrichtigungen

**User Story:**
Als Requester möchte ich automatisch per E-Mail über kritische Statusübergänge meiner Bestellungen informiert werden, damit ich ohne aktives Monitoring im Portal über den Fortschritt und das Ergebnis meiner IT-Anfragen informiert bin.

---

### Requirements

- **REQ-11:** Das System sendet E-Mail-Benachrichtigungen bei folgenden Ereignissen, ausgelöst durch den jeweiligen Statusübergang (Fire-and-Forget — der Statusübergang selbst wird nicht blockiert):
  - `order_submitted`: Bestellung wechselt von `validated` zu `submitted` (Feature 3.3)
  - `provisioning_done`: Bestellung wechselt zu `done` (Feature 4.2, REQ-54)
  - `provisioning_failed`: Bestellung wechselt zu `failed` (Feature 4.6, REQ-87)
  - `approval_requested`: Eine Bestellung mit Approval-Pflicht wurde eingereicht und eine ApprovalRequest wurde erstellt (Feature 3.3, Approval-Workflow). Empfänger: alle zuständigen Approver (nicht der Requester). Template-Pflichtinhalte: `order_id`, `order_number`, Requester-Name, Service-Zusammenfassung (Liste der bestellten Services), Gesamtkosten, Approval-Deadline.
  - `approval_approved`: Ein Approver hat die Bestellung genehmigt, Order-Status wechselt zu `approved` (Feature 3.3). Empfänger: Requester. Template-Pflichtinhalte: `order_id`, `order_number`, Name des Approvers, Kommentar des Approvers (kann leer sein).
  - `approval_rejected`: Ein Approver oder das System (Timeout) hat die Bestellung abgelehnt, Order-Status wechselt zu `rejected` (Feature 3.3). Empfänger: Requester. Template-Pflichtinhalte: `order_id`, `order_number`, Name des Approvers oder `"System (Fristablauf)"`, Ablehnungsgrund (Freitext des Approvers oder fixer Text `"Freigabefrist abgelaufen"` bei Timeout).
  - `approval_timeout_warning`: Automatische Erinnerung, wenn die Approval-Deadline in weniger als 4 Stunden abläuft und die Bestellung noch im Status `pending_approval` ist. Empfänger: alle zuständigen Approver. Template-Pflichtinhalte: `order_id`, `order_number`, verbleibende Zeit bis Deadline, exakte Deadline (ISO-8601 mit Zeitzone). Das System sendet pro ApprovalRequest maximal eine `approval_timeout_warning`; eine erneute Warnung wird nicht ausgelöst, falls die Bestellung zwischenzeitlich bereits entschieden wurde.

- **REQ-12:** Benachrichtigungen sind ausschliesslich template-basiert. HTML- und Text-Inhalte werden nicht im Anwendungscode hartcodiert. Templates werden als Dateien im Dateisystem verwaltet (Template-Verzeichnis ist per Admin-Konfiguration pflegbar). Jedes Template hat einen eindeutigen `template_key`.

- **REQ-13:** Jede Benachrichtigungs-E-Mail enthält mindestens folgende Pflichtfelder, die vom Template gerendert werden: Bestellnummer, Service-Typ(en) der bestellten Items, Requester-Name, Zeitstempel des Ereignisses, direkter Link zur Bestelldetailseite im Portal.

- **REQ-14:** Zusätzlich zum Pflichtinhalt enthält die `provisioning_failed`-E-Mail: kategorisierten Fehlergrund (`failure_reason` aus REQ-88 der provisioning-engine.md) sowie die Handlungsempfehlung für den Requester.

- **REQ-15:** Das System legt für jede zu sendende E-Mail einen `NotificationRecord` an, bevor der Sendeversuch gestartet wird. Status: `pending`. Nach erfolgreichem Senden: `sent`. Bei Fehler: `failed`.

- **REQ-16:** Bei Fehlschlag des Sendeversuchs (SMTP-Fehler, Timeout, Verbindungsfehler) wird die Benachrichtigung erneut versucht. Maximale Anzahl Versuche: 3 (inkl. Erstversuch). Wartezeiten zwischen den Versuchen: exponentieller Backoff (1 Minute, 5 Minuten). Nach dem dritten Fehlschlag wird der Status auf `retry_exhausted` gesetzt. Es werden keine weiteren Versuche unternommen.

- **REQ-17:** Benachrichtigungen mit Status `retry_exhausted` sind im Admin-Dashboard sichtbar (Feature 7.1, REQ-40). Ein Admin kann eine einzelne Benachrichtigung manuell erneut auslösen (erzeugt einen neuen `NotificationRecord` mit `attempt_count: 0`, der ursprüngliche bleibt in `retry_exhausted`).

- **REQ-18:** Der Absender aller System-E-Mails (From-Adresse und Anzeigename) ist per Admin-Konfiguration pflegbar. Reply-To ist separat konfigurierbar und kann von der From-Adresse abweichen.

- **REQ-19:** Die E-Mail-Adresse des Empfängers wird zum Sendezeitpunkt aus dem User-Profil (Feature 1.1, LDAP-Attribut) gelesen und im `NotificationRecord` als Snapshot gespeichert. Ändert sich die E-Mail-Adresse des Users nach dem Anlegen des Records, wird die im Record gespeicherte Adresse verwendet.

- **REQ-20:** Das System unterstützt ausschliesslich SMTP als Versandprotokoll (konfigurierbar: Host, Port, TLS, Benutzername, Passwort). SMTP-Credentials werden verschlüsselt gespeichert.

- **REQ-21:** Alle Benachrichtigungsereignisse erzeugen einen Audit-Log-Eintrag (Feature 7.2, REQ-55) mit `action: notification_sent` oder `action: notification_failed`.

---

### Validation Rules

- **VAL-06:** SMTP-Host (Konfiguration) — Darf nicht leer sein, muss ein valider Hostname oder eine IPv4-Adresse sein — `"Der SMTP-Host ist ungültig oder leer."`

- **VAL-07:** SMTP-Port (Konfiguration) — Muss eine Ganzzahl zwischen 1 und 65535 sein — `"Der SMTP-Port muss zwischen 1 und 65535 liegen."`

- **VAL-08:** Absender-E-Mail (Konfiguration) — Muss ein valides E-Mail-Format gemäss RFC 5321 haben — `"Die Absender-E-Mail-Adresse hat ein ungültiges Format."`

- **VAL-09:** Template-Datei — Für jeden `event_type` muss ein Template mit dem konfigurierten `template_key` im Template-Verzeichnis existieren und lesbar sein — `"Das E-Mail-Template '{template_key}' wurde nicht gefunden oder ist nicht lesbar."`

- **VAL-10:** Empfänger-E-Mail — Die aus dem User-Profil gelesene E-Mail-Adresse muss ein valides Format gemäss RFC 5321 haben. Ist sie ungültig, wird der `NotificationRecord` mit `status: failed` und `error_message: "Ungültige Empfänger-E-Mail-Adresse"` angelegt und der Retry-Mechanismus nicht gestartet — `"Die E-Mail-Adresse des Empfängers ist ungültig. Benachrichtigung wird nicht gesendet."`

---

### API Contract

**Endpoint 3: Get notification records for an order (admin/requester)**
```
GET /api/v1/orders/{order_id}/notifications
```
Authorization: Requester sieht nur eigene Orders. Admin sieht alle.

Response 200:
```json
{
  "data": [
    {
      "id": "uuid",
      "event_type": "order_submitted | provisioning_done | provisioning_failed | approval_requested | approval_approved | approval_rejected | approval_timeout_warning",
      "status": "pending | sent | failed | retry_exhausted",
      "attempt_count": "integer",
      "last_attempt_at": "ISO8601 datetime | null",
      "sent_at": "ISO8601 datetime | null",
      "error_message": "string | null",
      "template_key": "string",
      "created_at": "ISO8601 datetime"
    }
  ]
}
```
Response 401: Nicht authentifiziert
Response 403: Keine Berechtigung für diese Order
Response 404: Order nicht gefunden

---

**Endpoint 4: Manually re-trigger a failed notification (admin)**
```
POST /api/v1/admin/notifications/{notification_id}/retry
```
Response 202:
```json
{
  "new_notification_id": "uuid",
  "original_notification_id": "uuid",
  "status": "pending",
  "created_at": "ISO8601 datetime"
}
```
Response 400: Benachrichtigung hat Status `sent` (kein Retry nötig) oder `pending` (Versuch läuft bereits)
Response 403: Nur Admin
Response 404: Benachrichtigung nicht gefunden

---

**Endpoint 5: Get SMTP configuration (admin)**
```
GET /api/v1/admin/config/smtp
```
Response 200:
```json
{
  "host": "string",
  "port": "integer",
  "tls_enabled": "boolean",
  "username": "string",
  "from_address": "string",
  "from_name": "string",
  "reply_to": "string | null"
}
```
Hinweis: Das SMTP-Passwort wird nicht zurückgeliefert.
Response 403: Nur Admin

---

**Endpoint 6: Update SMTP configuration (admin)**
```
PUT /api/v1/admin/config/smtp
```
Request Body:
```json
{
  "host": "string",
  "port": "integer",
  "tls_enabled": "boolean",
  "username": "string",
  "password": "string (optional, nur bei Änderung angeben)",
  "from_address": "string",
  "from_name": "string",
  "reply_to": "string | null"
}
```
Response 200: Aktualisierte Konfiguration (ohne Passwort, wie Endpoint 5)
Response 400: Validierungsfehler (VAL-06 bis VAL-08)
Response 403: Nur Admin

---

### Edge Cases

- **EC-06:** Der SMTP-Server ist zum Zeitpunkt des Sendeversuchs nicht erreichbar (Netzwerkfehler) — Der Retry-Mechanismus (REQ-16) greift. Der Statusübergang der Order ist bereits abgeschlossen und wird nicht rückgängig gemacht.

- **EC-07:** Eine E-Mail wird als "gesendet" (SMTP 250 OK) bestätigt, kommt aber nicht beim Empfänger an (Spam-Filter, ungültige Mailbox) — Das System wertet SMTP 250 als Erfolg (`status: sent`). Bounce-Handling liegt ausserhalb des MVP-Scopes. Retry wird nicht ausgelöst.

- **EC-08:** Zwei Statusübergänge derselben Order werden in schneller Folge ausgelöst (z.B. `submitted` und unmittelbar danach `failed` durch Validierungsfehler im Dispatcher) — Beide Ereignisse erzeugen unabhängige `NotificationRecord`-Einträge. Es gibt keine Deduplizierung oder Zusammenfassung.

- **EC-09:** Der Template-Render-Prozess schlägt fehl (z.B. fehlende Platzhaltervariable im Template) — Der `NotificationRecord` wird mit `status: failed` und der Render-Fehlermeldung im `error_message`-Feld gespeichert. Der Retry-Mechanismus wird nicht gestartet, da es sich um einen Konfigurationsfehler handelt, der durch Wiederholung nicht behoben wird. Ein Admin-Alert wird erzeugt.

- **EC-10:** Der User hat keine E-Mail-Adresse im AD-Profil hinterlegt — Analog VAL-10: `NotificationRecord` mit `status: failed`, kein Retry. Im Audit-Log wird `action: notification_failed` mit dem Grund `missing_recipient_email` protokolliert.

---

## Feature 6.2: Zugangsdaten-Lieferung

**User Story:**
Als Requester möchte ich nach der erfolgreichen Provisionierung einer Datenbank die initialen Zugangsdaten sicher und einmalig abrufen können, damit keine Passwörter dauerhaft im Portal gespeichert werden und die Übergabe nachvollziehbar ist.

---

> **Abgrenzung zu Feature 4.5:** Feature 4.5 (provisioning-engine.md) spezifiziert die Erzeugung
> des Passworts, den Tofu-Output und den grundlegenden Mechanismus (REQ-77–REQ-81, Endpoint 31).
> Dieses Feature spezifiziert das vollständige Lifecycle-Management des `CredentialToken`,
> inklusive Token-Erzeugung, Brute-Force-Schutz, Admin-Re-Issue und Audit-Integration.
> Endpoint 31 aus provisioning-engine.md (GET /api/v1/credentials/{token}) bleibt der einzige
> Abruf-Endpoint für die Zugangsdaten selbst.

---

### Requirements

- **REQ-22:** Nach dem Statusübergang eines Datenbank-OrderItems zu `active` (Feature 4.2, REQ-55) erzeugt das System automatisch einen `CredentialToken`-Datensatz mit `status: pending`. Der Token besteht aus mindestens 32 kryptographisch zufälligen Bytes, kodiert in URL-sicherem Base64url. Die Token-Länge in der URL beträgt damit mindestens 43 Zeichen.

- **REQ-23:** Der erzeugte Token wird nicht im Klartext in der Datenbank gespeichert. Es wird ausschliesslich ein sicherer Hash (SHA-256 oder stärker) des Tokens persistiert. Das System rekonstruiert den Klartext-Token für den Versand aus dem einmalig im Arbeitsspeicher gehaltenen Wert.

- **REQ-24:** Die TTL des Tokens beträgt 48 Stunden ab Erzeugungszeitpunkt (`created_at`). Der Ablaufzeitpunkt wird als `expires_at` im Datensatz gespeichert. Ein abgelaufener Token antwortet mit HTTP 410 (Gone).

- **REQ-25:** Ein Token kann exakt einmal abgerufen werden. Beim ersten erfolgreichen Abruf wird der Status atomar von `pending` auf `consumed` gesetzt, `consumed_at` und `consumed_ip` werden gesetzt. Alle nachfolgenden Abrufversuche desselben Tokens antworten mit HTTP 404 (nicht 410, um Consumed von Expired zu unterscheiden, ohne dem Angreifer Information zu geben — intern wird protokolliert).

- **REQ-26:** Der Secure-Link, der per E-Mail (Feature 6.1) und System-Notification versendet wird, hat das Format: `{portal_base_url}/credentials/{token}`. Der Link wird im E-Mail-Template als Variable `{{credential_link}}` übergeben und enthält kein Passwort. Das Passwort wird ausschliesslich beim Abruf des Tokens über Endpoint 31 (provisioning-engine.md) ausgeliefert.

- **REQ-27:** Brute-Force-Schutz: Abrufversuche auf `GET /api/v1/credentials/{token}` werden pro Quell-IP-Adresse gezählt. Überschreiten die Fehlversuche (HTTP 404 oder 410) 10 Versuche innerhalb von 5 Minuten, wird die IP-Adresse für 30 Minuten gesperrt. Gesperrte IPs erhalten HTTP 429 mit `Retry-After`-Header. Die Ratenlimit-Zähler werden serverseitig im Arbeitsspeicher (oder Cache) geführt, nicht in der primären Datenbank.

- **REQ-28:** Ein Admin kann für eine Datenbank-Ressource manuell einen neuen `CredentialToken` ausstellen, wenn der ursprüngliche Token `consumed` oder `expired` ist. Ein neuer Token kann nur ausgestellt werden, wenn das Passwort noch im internen Secret-Store verfügbar ist. Ist das Passwort nicht mehr verfügbar, antwortet das System mit einem entsprechenden Fehler und verweist auf den Passwort-Reset-Flow (ausserhalb MVP).

- **REQ-29:** Beim manuellen Re-Issue durch einen Admin wird der vorherige Token (falls noch `pending`) auf `revoked` gesetzt. Es kann immer nur ein Token pro `order_item_id` im Status `pending` existieren.

- **REQ-30:** Jede Token-Erzeugung, jeder erfolgreiche Abruf, jeder fehlgeschlagene Abruf (inkl. IP) und jeder Admin-Re-Issue erzeugt einen Audit-Log-Eintrag (Feature 7.2).

- **REQ-31:** Das System führt einen täglichen Hintergrundprozess (Scheduled Job, Laufzeit konfigurierbar, Default: 03:00 Uhr Server-Zeit) aus, der alle `CredentialToken` mit `status: pending` und überschrittenem `expires_at` auf `expired` setzt. Dieser Prozess ändert keine `consumed`- oder `revoked`-Token.

---

### Validation Rules

- **VAL-11:** Token-Format bei Abruf — Muss dem URL-sicheren Base64url-Zeichensatz entsprechen (`[A-Za-z0-9_-]+`) und mindestens 43 Zeichen lang sein — HTTP 404 (kein spezifischer Fehlertext, um keine Informationen preiszugeben)

- **VAL-12:** Admin-Re-Issue: `order_item_id` — Muss eine valide UUID sein und zu einem OrderItem vom `service_type: database` gehören — `"Der angegebene order_item_id ist ungültig oder gehört nicht zu einer Datenbank-Bestellung."`

- **VAL-13:** Admin-Re-Issue: Ressourcen-Status — Das OrderItem muss den Status `active` haben — `"Zugangsdaten können nur für aktive Ressourcen neu ausgestellt werden (aktueller Status: {status})."`

- **VAL-14:** Admin-Re-Issue: Vorhandener Token — Darf nur ausgeführt werden, wenn kein Token mit `status: pending` für diese `order_item_id` existiert, oder wenn der bestehende `pending`-Token explizit durch das System widerrufen wird (REQ-29) — systemseitig geprüft, kein Anwender-Fehler.

---

### API Contract

**Endpoint 7: Get credential token status for a resource (requester/admin)**
```
GET /api/v1/resources/{resource_id}/credential-status
```
Authorization: Requester nur für eigene Ressourcen. Admin für alle.

Response 200:
```json
{
  "resource_id": "uuid",
  "order_item_id": "uuid",
  "credential_status": "available | consumed | expired | none",
  "expires_at": "ISO8601 datetime | null",
  "consumed_at": "ISO8601 datetime | null"
}
```
Hinweis: `token` und `consumed_ip` werden in dieser Response niemals zurückgeliefert.
Response 401: Nicht authentifiziert
Response 403: Ressource gehört nicht dem User
Response 404: Ressource nicht gefunden oder kein Credential-Token vorhanden (`credential_status: none`)

---

**Endpoint 8: Issue new credential token for a resource (admin)**
```
POST /api/v1/admin/resources/{resource_id}/credential-token
```
Response 201:
```json
{
  "credential_token_id": "uuid",
  "order_item_id": "uuid",
  "expires_at": "ISO8601 datetime",
  "credential_link": "string (vollständige URL mit Token)",
  "issued_by": "string (admin user_id)",
  "issued_at": "ISO8601 datetime",
  "previous_token_revoked": "boolean"
}
```
Response 400: Kein Passwort im Secret-Store verfügbar
Response 403: Nur Admin
Response 404: Ressource nicht gefunden
Response 409: Vorhandener `pending`-Token existiert (darf laut REQ-29 nicht passieren — Systemfehler)
Response 422: Ressource ist nicht `active` (VAL-13) oder kein `database`-Typ (VAL-12)

---

### Edge Cases

- **EC-11:** E-Mail-Scanner (z.B. Microsoft Safe Links, Proofpoint) ruft den Credential-Link automatisch vor dem User ab — Der erste Abruf (durch den Scanner) konsumiert den Token (REQ-25). Der User erhält beim manuellen Klick HTTP 404. Der Audit-Log-Eintrag enthält die IP des Scanners als `consumed_ip`. Der Admin kann einen neuen Token ausstellen (REQ-28). Dieser Fall ist in EC-51 der provisioning-engine.md referenziert und wird hier vollständig gehandhabt.

- **EC-12:** Ein Angreifer versucht, Token durch sequentielle Anfragen zu erraten (Brute Force) — REQ-27 sperrt die IP nach 10 Fehlversuchen in 5 Minuten für 30 Minuten (HTTP 429). Da Token mindestens 32 Byte Entropie haben, ist die Wahrscheinlichkeit eines zufälligen Treffers kryptographisch vernachlässigbar.

- **EC-13:** Der Admin-Re-Issue-Prozess wird aufgerufen, während der ursprüngliche Token gerade konsumiert wird (Race Condition) — Das atomare Setzen auf `consumed` (REQ-25) verhindert ein gleichzeitiges `revoke`. Der Re-Issue-Endpoint prüft den Status nach dem pessimistischen Lock. Ist der Token bereits `consumed`, antwortet er mit HTTP 409 und dem Hinweis, dass der Token bereits abgerufen wurde.

- **EC-14:** Der Scheduled Job (REQ-31) läuft nicht (z.B. Server-Neustart genau zur Laufzeit) — Abgelaufene Tokens bleiben im Status `pending`. Der Abruf-Endpoint (Endpoint 31, provisioning-engine.md) prüft `expires_at` unabhängig vom Token-Status und antwortet mit HTTP 410, sofern `expires_at` in der Vergangenheit liegt. Der Scheduled Job holt die Aktualisierung beim nächsten Lauf nach.

- **EC-15:** Das Passwort ist im Secret-Store nicht mehr verfügbar (z.B. Secret-Store-Migration, Datenverlust) — Admin-Re-Issue antwortet mit HTTP 400 und einem klaren Fehlertext: `"Das initiale Passwort für diese Ressource ist nicht mehr im Secret-Store verfügbar. Ein Re-Issue ist nicht möglich. Bitte führen Sie einen Passwort-Reset direkt auf dem Datenbanksystem durch."` Der Fehlergrund wird im Audit-Log protokolliert.

---

## Gruppe 7: Administration & Governance

---

## Feature 7.1: Admin-Dashboard

**User Story:**
Als Admin möchte ich eine konsolidierte Übersicht aller Orders, provisionierten Ressourcen, Service-Account-Zustände und ausstehenden manuellen Bereinigungen sehen, damit ich den Betriebszustand des Portals beurteilen und auf Probleme reagieren kann.

---

### Requirements

- **REQ-32:** Das Admin-Dashboard ist ausschliesslich für Benutzer mit der Rolle `admin` zugänglich. Jeder Zugriff auf Admin-Dashboard-Endpoints ohne Admin-Rolle antwortet mit HTTP 403.

- **REQ-33:** Das Dashboard liefert eine Übersicht aller Orders des gesamten Systems (alle User), unabhängig vom Requester. Die Liste ist filterbar nach: `status` (Enum-Mehrfachwahl: draft | validated | submitted | provisioning | done | failed), `requester_id` (UUID), `service_type` (Enum-Mehrfachwahl), Datumsbereich (`submitted_from`, `submitted_to`, ISO-8601 date).

- **REQ-34:** Die Order-Übersicht ist paginiert (Standardseitengrösse: 50, Maximum: 200). Die Antwort enthält Statusverteilungs-Zähler: `status_counts` (Objekt mit Count pro Status-Wert) zusätzlich zur paginierten Liste.

- **REQ-35:** Das Dashboard liefert eine Übersicht aller provisionierten Ressourcen des Systems (alle User). Filter: `service_type` (Mehrfachwahl), `status` (Mehrfachwahl), `requester_id`. Paginierung analog zur Order-Übersicht.

- **REQ-36:** Das Dashboard enthält einen Health-Status-Block für alle konfigurierten Service-Accounts (aus Feature 1.3, identity-access.md). Pro Service-Account wird zurückgeliefert: Name, Typ (ad | ipam | gitlab | opentofu), `health_status` (Enum: healthy | degraded | unreachable | unknown), letzter Prüfzeitpunkt (`last_checked_at`), Fehlermeldung bei nicht-healthy.

- **REQ-37:** Der Health-Status der Service-Accounts wird nicht bei jedem Dashboard-Abruf live geprüft. Stattdessen liefert das Dashboard den zuletzt gecachten Zustand, der durch einen konfigurierbaren Hintergrundprozess aktualisiert wird (Default-Intervall: alle 5 Minuten). Das Dashboard-Response enthält `health_last_refreshed_at`.

- **REQ-38:** Das Dashboard enthält eine Liste aller ausstehenden manuellen Bereinigungen ("Pending Manual Cleanups") aus Feature 4.6 (REQ-86, Endpoint 35 provisioning-engine.md). Pro Eintrag: `order_id`, `order_number`, `step` (tofu_destroy | ad_delete | ipam_release), `resource_reference`, `instructions`, `created_at`. Die Liste ist nicht paginiert, da maximal O(10) gleichzeitige Einträge erwartet werden. Überschreitet die Liste 50 Einträge, liefert das System eine Warnung im Response.

- **REQ-39:** Das Dashboard enthält eine Übersicht fehlgeschlagener Benachrichtigungen mit Status `retry_exhausted` (aus Feature 6.1). Pro Eintrag: `notification_id`, `order_id`, `order_number`, `event_type`, `recipient_email`, `last_attempt_at`, `error_message`. Die Liste liefert maximal die 20 neuesten Einträge; für vollständige Abfragen steht Endpoint 3 zur Verfügung.

- **REQ-40:** Alle Datenquellen des Dashboards (Orders, Ressourcen, Service-Account-Health, Pending Cleanups, fehlgeschlagene Benachrichtigungen) werden in einer einzigen API-Anfrage zurückgeliefert. Die Antwortzeit der Dashboard-API darf unter Normalbetrieb 2 Sekunden nicht überschreiten. Paginierte Teilabfragen nutzen dedizierte Endpoints (REQ-33 bis REQ-35).

- **REQ-41:** Das Dashboard enthält zusammenfassende Kennzahlen (`summary`): Gesamtanzahl Orders, Gesamtanzahl aktiver Ressourcen, Anzahl Orders im Status `provisioning`, Anzahl Orders im Status `failed` (letzten 7 Tage), Anzahl `retry_exhausted`-Benachrichtigungen, Anzahl Pending Manual Cleanups.

---

### Validation Rules

- **VAL-15:** Query-Parameter `submitted_from` und `submitted_to` — Müssen valide ISO-8601-Datumsangaben sein (Format YYYY-MM-DD) — `"submitted_from / submitted_to muss ein valides Datum im Format YYYY-MM-DD sein."`

- **VAL-16:** Query-Parameter `submitted_from` / `submitted_to` — `submitted_from` darf nicht nach `submitted_to` liegen — `"submitted_from darf nicht nach submitted_to liegen."`

- **VAL-17:** Query-Parameter `page_size` (Order- und Ressourcen-Listen) — Muss zwischen 1 und 200 liegen — `"page_size muss zwischen 1 und 200 liegen."`

---

### API Contract

**Endpoint 9: Get admin dashboard summary (admin)**
```
GET /api/v1/admin/dashboard
```
Response 200:
```json
{
  "summary": {
    "total_orders": "integer",
    "active_resources": "integer",
    "orders_provisioning": "integer",
    "orders_failed_last_7d": "integer",
    "notifications_retry_exhausted": "integer",
    "pending_manual_cleanups": "integer"
  },
  "service_account_health": {
    "health_last_refreshed_at": "ISO8601 datetime",
    "accounts": [
      {
        "id": "uuid",
        "name": "string",
        "type": "ad | ipam | gitlab | opentofu",
        "health_status": "healthy | degraded | unreachable | unknown",
        "last_checked_at": "ISO8601 datetime | null",
        "error_message": "string | null"
      }
    ]
  },
  "pending_manual_cleanups": {
    "count": "integer",
    "warning": "string | null",
    "items": [
      {
        "order_id": "uuid",
        "order_number": "string",
        "step": "tofu_destroy | ad_delete | ipam_release",
        "resource_reference": "string",
        "instructions": "string",
        "created_at": "ISO8601 datetime"
      }
    ]
  },
  "notifications_failed": {
    "count_retry_exhausted": "integer",
    "items": [
      {
        "notification_id": "uuid",
        "order_id": "uuid",
        "order_number": "string",
        "event_type": "string",
        "recipient_email": "string",
        "last_attempt_at": "ISO8601 datetime | null",
        "error_message": "string | null"
      }
    ]
  }
}
```
Response 403: Nur Admin

---

**Endpoint 10: List all orders (admin)**
```
GET /api/v1/admin/orders
```
Query Parameters:
```
status          string   optional  Kommaseparierte Werte (draft|validated|submitted|provisioning|done|failed)
requester_id    uuid     optional
service_type    string   optional  Kommaseparierte Werte (vm|database|container)
submitted_from  date     optional  YYYY-MM-DD
submitted_to    date     optional  YYYY-MM-DD
page            integer  optional  default: 1
page_size       integer  optional  default: 50, max: 200
```
Response 200:
```json
{
  "status_counts": {
    "draft": "integer",
    "validated": "integer",
    "submitted": "integer",
    "provisioning": "integer",
    "done": "integer",
    "failed": "integer"
  },
  "data": [
    {
      "id": "uuid",
      "order_number": "string",
      "requester_id": "uuid",
      "requester_name": "string",
      "status": "string",
      "title": "string",
      "item_count": "integer",
      "service_types": ["vm", "database"],
      "submitted_at": "ISO8601 datetime | null",
      "updated_at": "ISO8601 datetime"
    }
  ],
  "pagination": {
    "total_count": "integer",
    "page": "integer",
    "page_size": "integer",
    "has_next_page": "boolean"
  }
}
```
Response 400: Ungültige Query-Parameter (VAL-15 bis VAL-17)
Response 403: Nur Admin

---

**Endpoint 11: List all provisioned resources (admin)**
```
GET /api/v1/admin/resources
```
Query Parameters:
```
service_type    string   optional  Kommaseparierte Werte
status          string   optional  Kommaseparierte Werte
requester_id    uuid     optional
page            integer  optional  default: 1
page_size       integer  optional  default: 50, max: 200
```
Response 200: Analog zu Endpoint 1 (GET /api/v1/resources), jedoch mit zusätzlichem Feld `requester_name: string` pro Ressource und ohne Beschränkung auf eigene Ressourcen.
Response 400: Ungültige Query-Parameter
Response 403: Nur Admin

---

### Edge Cases

- **EC-16:** Das System hat tausende Orders (z.B. nach 2 Jahren Betrieb). Der Dashboard-Summary-Endpoint (Endpoint 9) berechnet `total_orders` und `active_resources` — Diese Aggregationen müssen über Datenbank-Indizes effizient ausführbar sein. Vollständige Table-Scans sind nicht akzeptabel. Die Implementierung muss sicherstellen, dass geeignete Indizes auf `status`, `requester_id` und `submitted_at` existieren.

- **EC-17:** Alle konfigurierten Service-Accounts sind `unreachable` (z.B. Netzwerkausfall) — Das Dashboard liefert trotzdem HTTP 200 mit dem letzten gecachten Zustand. Die `health_last_refreshed_at` zeigt das letzte erfolgreiche Update. Das Frontend muss den veralteten Zustand für den Benutzer erkennbar machen.

- **EC-18:** Die Pending-Manual-Cleanup-Liste überschreitet 50 Einträge — REQ-38: Die Response enthält `warning: "Es existieren mehr als 50 ausstehende manuelle Bereinigungen. Bitte prüfen Sie die Rollback-Prozesse."`. Alle Einträge werden trotzdem zurückgeliefert.

- **EC-19:** Ein Admin ruft Endpoint 10 mit einem Datumsfilter ab, der weit in der Vergangenheit liegt und potenziell hunderttausende Orders betrifft — Paginierung ist Pflicht (REQ-34). Der Endpoint liefert niemals eine ungepaginierte Vollliste, unabhängig von den Filterparametern.

- **EC-20:** Service-Account-Health-Check-Hintergrundprozess hängt (z.B. durch einen blockierenden LDAP-Call) — Der Health-Check-Prozess muss mit einem konfigurierbaren Timeout pro Service-Account (Default: 10 Sekunden) ausgestattet sein. Nach Timeout wird der Status auf `unreachable` gesetzt. Der Prozess darf den Haupt-Request-Thread nicht blockieren.

---

## Feature 7.2: Audit-Log

**User Story:**
Als Admin möchte ich ein vollständiges, unveränderliches Protokoll aller systemrelevanten Aktionen einsehen, filtern und exportieren können, damit Sicherheitsvorfälle nachvollziehbar sind und Compliance-Anforderungen erfüllt werden.

---

### Requirements

- **REQ-42:** Das Audit-Log ist append-only. Kein `AuditLogEntry` darf nach der Erstellung verändert oder gelöscht werden — weder über die API noch über direkte Datenbankzugriffe (soweit technisch durchsetzbar). Die Implementierung muss sicherstellen, dass kein UPDATE- oder DELETE-Befehl auf der Audit-Log-Tabelle ausgeführt werden kann (z.B. via DB-Grants oder Row-Level-Security).

- **REQ-43:** Das System schreibt automatisch einen `AuditLogEntry` für alle folgenden Aktionskategorien:
  - **Order-Events:** `order_created`, `order_updated`, `order_submitted`, `order_status_changed`, `order_deleted`
  - **Provisioning-Events:** `provisioning_started`, `provisioning_succeeded`, `provisioning_failed`, `rollback_triggered`, `rollback_step_completed`, `rollback_step_failed`
  - **Credential-Events:** `credential_token_issued`, `credential_token_consumed`, `credential_token_expired`, `credential_token_revoked`, `credential_access_failed`
  - **Benachrichtigungs-Events:** `notification_sent`, `notification_failed`, `notification_retried`
  - **Admin-Aktionen:** `admin_config_changed`, `admin_rollback_triggered`, `admin_credential_reissued`, `admin_notification_retried`
  - **User-Events:** `user_login`, `user_logout`, `user_login_failed`
  - **Approval-Events:** `approval_requested` (ApprovalRequest wurde erstellt, Approver wurden benachrichtigt), `approval_approved` (Order wurde von einem Approver genehmigt — `actor_id` = Approver-ID), `approval_rejected` (Order wurde von einem Approver abgelehnt — `actor_id` = Approver-ID, `details` enthält Ablehnungsgrund), `approval_timeout` (Order wurde automatisch wegen Fristablauf abgelehnt — `actor_id` = System), `approval_deadline_extended` (Admin hat Approval-Deadline verlängert — `actor_id` = Admin-ID, `details` enthält alte und neue Deadline), `approval_rule_created` (neue Approval-Regel wurde erstellt — `actor_id` = Admin-ID), `approval_rule_updated` (bestehende Approval-Regel wurde geändert — `actor_id` = Admin-ID, `details` enthält geänderte Felder), `approval_rule_deleted` (Approval-Regel wurde gelöscht — `actor_id` = Admin-ID, `details` enthält Snapshot der gelöschten Regel)
  - **Service-Account-Events:** `service_account_created`, `service_account_rotated`, `service_account_disabled`
  - **Template-Events:** `template_created`, `template_deprecated`, `template_disabled`

- **REQ-44:** Jeder `AuditLogEntry` enthält die in `AuditLogEntry` (Datenmodell oben) definierten Pflichtfelder. Das Feld `detail` darf niemals Passwörter, Tokens im Klartext, SMTP-Credentials oder sonstige Secrets enthalten. Eine Prüfung auf bekannte Secret-Felder (`password`, `token`, `secret`, `credential`) erfolgt vor dem Schreiben; entsprechende Felder werden durch `"[REDACTED]"` ersetzt.

- **REQ-45:** Das Schreiben eines Audit-Log-Eintrags darf die primäre Geschäftsoperation nicht blockieren. Schlägt das Schreiben des Audit-Log-Eintrags fehl, wird dies im Server-Log protokolliert und ein System-Alert erzeugt. Die primäre Operation wird trotzdem als erfolgreich betrachtet und abgeschlossen.

- **REQ-46:** Das Audit-Log ist über die API durchsuchbar und filterbar nach: `actor_id` (UUID), `actor_type` (user | system | service_account), `action` (Enum aus REQ-43), `resource_type` (Enum), `resource_id` (UUID), Datumsbereich (`from`, `to`, ISO-8601 datetime). Alle Filter sind kombinierbar. Ohne Filter werden die neuesten 100 Einträge zurückgeliefert.

- **REQ-47:** Die Audit-Log-Liste ist paginiert (Standardseitengrösse: 100, Maximum: 500). Die Sortierung ist immer `timestamp` absteigend. Eine abweichende Sortierung ist nicht konfigurierbar, um die Integrität des zeitlichen Nachvollzugs sicherzustellen.

- **REQ-48:** Das Audit-Log kann exportiert werden. Unterstützte Formate: CSV und JSON (newline-delimited). Der Export-Endpoint akzeptiert dieselben Filter-Parameter wie der Such-Endpoint, liefert jedoch alle Treffer ohne Paginierung (als Stream oder Datei-Download). Der Export ist auf 100.000 Einträge pro Anfrage begrenzt; grössere Exporte erfordern mehrere Anfragen mit Datumsbereichs-Filterung.

- **REQ-49:** Die Aufbewahrungsfrist ist per Admin-Konfiguration pflegbar (Default: 365 Tage). Ein Hintergrundprozess (Default: täglich um 02:00 Uhr Server-Zeit) löscht Einträge, deren `timestamp` älter als die konfigurierte Aufbewahrungsfrist ist. Das Löschen durch diesen Prozess ist die einzige zulässige DELETE-Operation auf der Audit-Log-Tabelle. Der Prozess selbst erzeugt einen Audit-Log-Eintrag: `action: audit_log_purged`, `detail: { "deleted_count": integer, "older_than": "ISO8601 datetime" }`.

- **REQ-50:** Die konfigurierte Aufbewahrungsfrist darf nicht unter 30 Tage gesetzt werden. Änderungen an der Aufbewahrungsfrist erzeugen einen Audit-Log-Eintrag `action: admin_config_changed`.

- **REQ-51:** Zugriff auf das Audit-Log (Lesen und Exportieren) ist ausschliesslich für Benutzer mit der Rolle `admin` möglich.

- **REQ-52:** Das Audit-Log enthält keine Benachrichtigungs-E-Mail-Inhalte (Template-Render-Ergebnis). Im `detail`-Feld von `notification_sent` wird ausschliesslich `{ "template_key": "string", "recipient_email": "string", "event_type": "string" }` gespeichert.

---

### Validation Rules

- **VAL-18:** Query-Parameter `from` und `to` (Datumsbereich) — Müssen valide ISO-8601-Datetime-Werte (mit Zeitzonen-Offset oder UTC-Z) sein — `"Der Parameter 'from'/'to' muss ein valides ISO-8601-Datum mit Zeitzone sein (z.B. 2026-01-01T00:00:00Z)."`

- **VAL-19:** Query-Parameter `from` / `to` — `from` darf nicht nach `to` liegen — `"'from' darf nicht nach 'to' liegen."`

- **VAL-20:** Query-Parameter `action` — Muss einem der in REQ-43 definierten Enum-Werte entsprechen — `"Unbekannte Aktion '{value}'. Erlaubte Werte: [Liste aus REQ-43]."`

- **VAL-21:** Query-Parameter `resource_type` — Muss einem der definierten Enum-Werte entsprechen: `order`, `order_item`, `resource`, `credential_token`, `user`, `service_template`, `system_config`, `audit_log` — `"Unbekannter resource_type '{value}'."`

- **VAL-22:** Query-Parameter `page_size` — Muss zwischen 1 und 500 liegen — `"page_size muss zwischen 1 und 500 liegen."`

- **VAL-23:** Export-Limit — Würde der gefilterte Export mehr als 100.000 Einträge umfassen, antwortet das System mit HTTP 422 und der Meldung: `"Der Export umfasst mehr als 100.000 Einträge. Bitte schränken Sie den Datumsbereich ein."` Der tatsächliche Umfang wird im Fehler-Response mitgeteilt: `"estimated_count": integer`.

- **VAL-24:** Aufbewahrungsfrist (Konfiguration) — Muss eine positive Ganzzahl >= 30 sein (Einheit: Tage) — `"Die Aufbewahrungsfrist muss mindestens 30 Tage betragen."`

- **VAL-25:** Export-Format — Muss `csv` oder `json` sein — `"Ungültiges Export-Format '{value}'. Erlaubte Werte: csv, json."`

---

### API Contract

**Endpoint 12: Search audit log (admin)**
```
GET /api/v1/admin/audit-log
```
Query Parameters:
```
actor_id        uuid      optional
actor_type      string    optional  user | system | service_account
action          string    optional  Enum aus REQ-43
resource_type   string    optional  Enum aus VAL-21
resource_id     uuid      optional
from            datetime  optional  ISO8601 mit Timezone
to              datetime  optional  ISO8601 mit Timezone
page            integer   optional  default: 1
page_size       integer   optional  default: 100, max: 500
```
Response 200:
```json
{
  "data": [
    {
      "id": "uuid",
      "timestamp": "ISO8601 datetime",
      "actor_type": "user | system | service_account",
      "actor_id": "string",
      "actor_name": "string",
      "action": "string",
      "resource_type": "string",
      "resource_id": "string | null",
      "resource_ref": "string | null",
      "result": "success | failure | partial",
      "detail": "object | null",
      "ip_address": "string | null"
    }
  ],
  "pagination": {
    "total_count": "integer",
    "page": "integer",
    "page_size": "integer",
    "has_next_page": "boolean"
  }
}
```
Response 400: Ungültige Query-Parameter (VAL-18 bis VAL-22)
Response 403: Nur Admin

---

**Endpoint 13: Export audit log (admin)**
```
GET /api/v1/admin/audit-log/export
```
Query Parameters: Identisch zu Endpoint 12 (ohne `page` und `page_size`). Zusätzlich:
```
format  string  required  csv | json
```
Response 200:
```
Content-Type: text/csv           (format=csv)
Content-Type: application/x-ndjson  (format=json, newline-delimited JSON)
Content-Disposition: attachment; filename="audit-log-{from}-{to}.{format}"
```
Body: Stream der gefilterten Audit-Log-Einträge in gewähltem Format. CSV enthält Header-Zeile.
Response 400: Ungültige Query-Parameter (VAL-18 bis VAL-25)
Response 403: Nur Admin
Response 422: Export überschreitet 100.000 Einträge (VAL-23)

---

**Endpoint 14: Get audit log entry detail (admin)**
```
GET /api/v1/admin/audit-log/{entry_id}
```
Response 200: Vollständiger `AuditLogEntry` (identische Felder wie in Endpoint 12)
Response 403: Nur Admin
Response 404: Eintrag nicht gefunden

---

**Endpoint 15: Get audit log configuration (admin)**
```
GET /api/v1/admin/config/audit-log
```
Response 200:
```json
{
  "retention_days": "integer",
  "purge_schedule_cron": "string",
  "last_purge_at": "ISO8601 datetime | null",
  "last_purge_deleted_count": "integer | null"
}
```
Response 403: Nur Admin

---

**Endpoint 16: Update audit log configuration (admin)**
```
PUT /api/v1/admin/config/audit-log
```
Request Body:
```json
{
  "retention_days": "integer (min: 30)"
}
```
Response 200: Aktualisierte Konfiguration (wie Endpoint 15)
Response 400: Validierungsfehler (VAL-24)
Response 403: Nur Admin

---

### Edge Cases

- **EC-21:** Ein Angreifer mit Admin-Zugang versucht, Audit-Log-Einträge zu löschen oder zu modifizieren — REQ-42 fordert, dass UPDATE und DELETE auf der Audit-Log-Tabelle auf Datenbankebene unterbunden werden (DB-Grants / Row-Level-Security). Ein Versuch über die API antwortet mit HTTP 405 (Method Not Allowed). Der Versuch selbst wird im Server-Log protokolliert.

- **EC-22:** Das Audit-Log wächst sehr stark (z.B. durch sehr häufige automatische Provisioning-Events) — REQ-49 stellt durch die konfigurierbare Aufbewahrungsfrist sicher, dass alte Daten bereinigt werden. Die Implementierung muss geeignete Indizes auf `timestamp`, `actor_id`, `action` und `resource_id` voraussetzen, um performante Filter-Abfragen zu gewährleisten.

- **EC-23:** Ein Export-Request für einen sehr grossen Datumsbereich wird gestellt (z.B. das gesamte letzte Jahr) — VAL-23 begrenzt auf 100.000 Einträge pro Export. Der Streaming-Export verhindert Memory-Probleme auf dem Server, da die Einträge nicht vollständig in den Arbeitsspeicher geladen werden dürfen.

- **EC-24:** Das Schreiben eines Audit-Log-Eintrags schlägt fehl (z.B. Disk voll, DB-Verbindung unterbrochen) — REQ-45: Die primäre Operation wird trotzdem abgeschlossen. Der Fehler wird im Server-Log mit dem vollständigen Inhalt des nicht geschriebenen Eintrags protokolliert, damit er bei Bedarf manuell nachgetragen werden kann.

- **EC-25:** Ein Audit-Log-Eintrag wird für eine systemseitige Aktion (actor_type: system) geschrieben, es gibt aber keinen zugehörigen User — `actor_id` wird auf den fixen Wert `"system"` gesetzt, `actor_name` auf `"System"`. `ip_address` bleibt `null`.

- **EC-26:** Der Purge-Hintergrundprozess läuft, während gleichzeitig viele neue Einträge geschrieben werden — Der Purge-Prozess darf nur Einträge löschen, deren `timestamp` zum Starttzeitpunkt des Prozesslaufs ausserhalb der Aufbewahrungsfrist lag. Einträge, die während des Prozesslaufs neu geschrieben werden, sind nicht betroffen.

- **EC-27:** Admin ändert die Aufbewahrungsfrist von 365 Tagen auf 30 Tage — Der nächste Purge-Job bereinigt alle Einträge älter als 30 Tage in einem Lauf. Vor dem Lauf erscheint keine Warnung. Die Konfigurationsänderung selbst wird im Audit-Log protokolliert. Es liegt in der Verantwortung des Admins, den Datenverlust zu beurteilen.

---

## Querschnittliche Edge Cases (gruppenübergreifend)

- **EC-28:** Ein Requester-Account wird deaktiviert (via AD, Feature 1.1), während seine Ressourcen noch aktiv sind — Die `ProvisionedResource`-Datensätze bleiben erhalten. Der deaktivierte User kann sich nicht mehr einloggen und hat keinen Zugriff mehr. Ein Admin kann die Ressourcen über Endpoint 11 einsehen. Ressourcen werden nicht automatisch dekommissioniert.

- **EC-29:** Eine Order wechselt während eines laufenden Dashboard-Abrufs (Endpoint 9) von `provisioning` zu `done` — Die Summary-Zähler können für diesen einen Request inkonsistent sein (z.B. `orders_provisioning` ist noch 1 zu hoch). Diese transiente Inkonsistenz ist akzeptabel; das Dashboard ist kein Echtzeit-Transaktionssystem.

- **EC-30:** Das Audit-Log und die Benachrichtigungs-E-Mail müssen für dieselbe Aktion gleichzeitig geschrieben werden (z.B. Provisioning-Done) — Beide Prozesse sind unabhängig voneinander (Fire-and-Forget für E-Mail, REQ-11; asynchrones Schreiben für Audit-Log, REQ-45). Ein Fehlschlag eines Prozesses beeinflusst den anderen nicht.

---

## Abhängigkeitsmatrix

Die folgende Matrix beschreibt, welche Features dieser Spec von welchen externen Specs abhängen und was sie umgekehrt bereitstellen.

### Abhängigkeiten nach innen (diese Spec konsumiert)

| Feature dieser Spec | Abhängigkeit | Quelle | Konkrete Referenz |
|---|---|---|---|
| 5.1 Ressourcen-Übersicht | `ProvisionedResource`-Datensätze | Gruppe 4, Feature 4.2 | REQ-55: Schreiben bei `active`-Übergang |
| 5.1 Ressourcen-Übersicht | Order-Daten (order_number, order_id) | Gruppe 3, Feature 3.1 | Order-Datenmodell |
| 5.1 Ressourcen-Übersicht | User-Authentifizierung + Rollen | Gruppe 1, Feature 1.1/1.2 | JWT, requester_id, admin-Rolle |
| 6.1 E-Mail-Benachrichtigungen | Statusübergang `submitted` | Gruppe 3, Feature 3.3 | REQ-131 (order_submitted-Event) |
| 6.1 E-Mail-Benachrichtigungen | Statusübergang `done` / `failed` | Gruppe 4, Feature 4.2 / 4.6 | REQ-54 (Statusübergang), REQ-87 |
| 6.1 E-Mail-Benachrichtigungen | User-E-Mail-Adresse | Gruppe 1, Feature 1.1 | LDAP-Attribut aus AD |
| 6.2 Zugangsdaten-Lieferung | Token-Abruf-Endpoint | Gruppe 4, Feature 4.5 | Endpoint 31 (GET /api/v1/credentials/{token}) |
| 6.2 Zugangsdaten-Lieferung | Passwort im Secret-Store | Gruppe 4, Feature 4.5 | REQ-77 (Passwort-Erzeugung), REQ-80 |
| 6.2 Zugangsdaten-Lieferung | Statusübergang zu `active` (DB) | Gruppe 4, Feature 4.5 | REQ-80: Trigger für Token-Erzeugung |
| 7.1 Admin-Dashboard | Service-Account-Health | Gruppe 1, Feature 1.3 | Health-Status-Zustände |
| 7.1 Admin-Dashboard | Pending Manual Cleanups | Gruppe 4, Feature 4.6 | REQ-86, Endpoint 35 |
| 7.1 Admin-Dashboard | Order-Daten (alle User) | Gruppe 3, Feature 3.1–3.3 | Order-Statusmaschine |
| 7.1 Admin-Dashboard | Fehlgeschlagene Benachrichtigungen | Feature 6.1 (diese Spec) | NotificationRecord, status: retry_exhausted |
| 7.2 Audit-Log | Alle Statusübergänge aller Features | Gruppen 1–6 | Jede schreibende Operation |

---

### Abhängigkeiten nach aussen (diese Spec stellt bereit)

| Feature dieser Spec | Stellt bereit für | Konsumierendes Feature |
|---|---|---|
| 6.2 Zugangsdaten-Lieferung | Vollständiges CredentialToken-Lifecycle | Feature 4.5 referenziert Endpoint 31 und REQ-80/81, die Implementierung der Token-Erzeugung und des Admin-Re-Issue liegt in dieser Spec |
| 7.2 Audit-Log | Audit-Eintrag-Erzeugung | Alle Features schreiben Audit-Einträge gemäss REQ-43; die Tabellen- und API-Spezifikation liegt hier |
| 6.1 E-Mail | E-Mail-Versand für Credential-Link | Feature 6.2 nutzt Feature 6.1 als Versandkanal (REQ-26) |

---

### Kritische Schnittstellen-Hinweise

1. **Feature 4.5 / Feature 6.2 (Credential-Token-Erzeugung):** REQ-80 in provisioning-engine.md beschreibt den Trigger (nach `active`-Übergang). Die vollständige `CredentialToken`-Spezifikation (Erzeugung, Hash-Speicherung, Lifecycle, Admin-Re-Issue) liegt in Feature 6.2 dieser Spec. Endpoint 31 (GET /api/v1/credentials/{token}) verbleibt in provisioning-engine.md als der einzige Abruf-Endpoint.

2. **Feature 4.6 / Feature 7.1 (Pending Manual Cleanups):** Die Daten werden durch Feature 4.6 erzeugt (REQ-86). Feature 7.1 (REQ-38) liest sie über Endpoint 35 der provisioning-engine.md. Keine eigene Tabelle in dieser Spec.

3. **Feature 1.3 / Feature 7.1 (Service-Account-Health):** Feature 7.1 zeigt gecachte Health-Daten aus Feature 1.3. Die Health-Check-Logik selbst ist nicht Teil dieser Spec.

4. **Audit-Log-Erzeugung:** Jede schreibende Operation in Gruppen 1–6 muss einen Audit-Log-Eintrag erzeugen. Die Implementierung dieser Querschnittsfunktion muss sicherstellen, dass die Erzeugung asynchron und nicht-blockierend erfolgt (REQ-45).
