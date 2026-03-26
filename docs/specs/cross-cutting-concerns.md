# Querschnittsthemen — Cross-Cutting Concerns

> **Status:** Draft v1.0
> **Erstellt:** 2026-03-26
> **Umfang:** 3 Themen (Idempotenz-Patterns, Error-Handling-Patterns, Permissions-Matrix)
> **Nummerierungsraum:** REQ-CCC-01 ff., VAL-CCC-01 ff., EC-CCC-01 ff. (eigenes Präfix, keine Überschneidung mit Feature-Gruppen-Nummern)
> **Hinweis:** Dieses Dokument definiert keine neuen Features, sondern konsolidiert Querschnittsregeln, die über alle Feature-Gruppen 1–8 hinweg gelten. Bei Widersprüchen zu Einzelspecs gilt das spezifischere Dokument; diese Spec schärft, was offen geblieben ist.

---

## Inhaltsverzeichnis

- [Thema 1: Idempotenz-Patterns](#thema-1-idempotenz-patterns)
- [Thema 2: Error-Handling-Patterns](#thema-2-error-handling-patterns)
- [Thema 3: Permissions-Matrix](#thema-3-permissions-matrix)

---

## Thema 1: Idempotenz-Patterns

### Übersicht

Idempotenz ist kein einzelnes Feature, sondern eine systemweite Eigenschaft. Die folgende Tabelle gibt einen Überblick, wo im System Idempotenz gilt und welches Muster dort angewendet wird. Jeder Bereich wird danach detailliert beschrieben.

| Bereich | Endpoint / Aktion | Idempotenz-Muster | Reaktion auf Duplikat |
|---------|-------------------|-------------------|-----------------------|
| Order Submit | `POST /api/v1/orders/{order_id}/submit` | Status-Guard + optionaler `Idempotency-Key`-Header | HTTP 409 oder gecachte Response |
| Approval Decision | `POST /api/v1/approval-requests/{id}/approve` und `/reject` | Atomisches `UPDATE WHERE status = 'pending'` (CAS) | HTTP 409 |
| Approval Timeout-Job | Cron-Job (intern) | Atomisches `UPDATE WHERE status = 'pending' AND deadline_at < now()` | Silent Skip |
| Provisioning Dispatch | `POST /api/v1/admin/orders/{order_id}/items/{item_id}/dispatch` + automatischer Dispatcher | Atomisches `UPDATE WHERE provisioning_status = 'pending' AND job_id IS NULL` (CAS) | HTTP 409 (manuell) / interner Abbruch (automatisch) |
| E-Mail-Benachrichtigungen | Internes Notification-System (Fire-and-Forget) | `NotificationRecord` mit Status-Guard; Admin-Retry erzeugt neuen Record | Kein Retry auf bereits `sent`-Records; separater Record für manuellen Retry |

---

### Requirements

- **REQ-CCC-01:** Alle idempotenzgeschützten Operationen im System verwenden ausschliesslich datenbankbasierte Mechanismen als Source of Truth. Es gibt keine externe Idempotenz-Infrastruktur (Redis, Message-Broker-Deduplication etc.) als harte Systemanforderung. Die Datenbank-Transaktion ist der einzige verbindliche Idempotenz-Anker.

- **REQ-CCC-02:** Ein Idempotenz-Konflikt wird nie silent ignoriert, wenn er eine externe Aktion betrifft (z.B. Provisioning-Auslösung, Approval-Entscheidung). Stattdessen wird der Konflikt protokolliert und — bei manuellen API-Aufrufen — als HTTP 409 zurückgemeldet.

- **REQ-CCC-03:** Interne, systemgesteuerte Prozesse (Cron-Jobs, Event-Queue-Consumer) dürfen Duplikat-Ereignisse silent droppen, wenn der Datenbankzustand eindeutig belegt, dass die Aktion bereits abgeschlossen ist. Ein Log-Eintrag ist Pflicht.

---

### 1.1 Order Submit

**Wo:** `POST /api/v1/orders/{order_id}/submit`

**Wie:** Zweistufiger Schutz:

1. **Status-Guard (synchron):** Der Submit-Endpoint prüft den aktuellen `order_status` in einer atomaren DB-Transaktion. Ist der Status nicht `validated`, antwortet das System mit HTTP 409 (VAL-93 aus order-lifecycle.md: bereits `submitted`, `provisioning`, `done`, `failed`). Der Statusübergang `validated` → `submitted` erfolgt nur einmalig.

2. **`Idempotency-Key`-Header (optional, für Client-Retries):** Der Client kann eine UUID v4 im `Idempotency-Key`-Header mitsenden. Wird derselbe Key innerhalb von 24 Stunden erneut übermittelt, gibt das System die gecachte HTTP-200-Response zurück, ohne den Submit erneut auszulösen. Fehlerhafte Responses (HTTP 4xx/5xx) werden nicht gecacht — ein Retry mit demselben Key löst einen neuen Versuch aus.

**Requirements:**

- **REQ-CCC-04:** Der Statusübergang `validated` → `submitted` wird als einzige atomare DB-Operation durchgeführt. Ein paralleler zweiter Submit-Request erhält eine leere affected-rows-Menge zurück und antwortet mit HTTP 409.

- **REQ-CCC-05:** `Idempotency-Key`-Cache-Einträge werden serverseitig für genau 24 Stunden vorgehalten. Nach Ablauf der 24 Stunden ist eine erneute Ausführung mit demselben Key möglich (neuer Submit-Versuch).

- **REQ-CCC-06:** Der `Idempotency-Key`-Cache wird nicht für die primäre Idempotenz genutzt — er ist eine zusätzliche Schutzschicht für netzwerkbedingte Client-Retries. Die primäre Absicherung liegt auf dem `order_status`.

**Validierung:**

- **VAL-CCC-01:** `Idempotency-Key`-Header — Wenn angegeben, muss er eine gültige UUID v4 sein (Format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`) — `"Der Idempotency-Key muss eine gültige UUID (Version 4) sein."`

**Edge Cases:**

- **EC-CCC-01:** Client sendet Submit + parallel einen zweiten Submit (Race Condition, netzwerkbedingte Doppelübertragung ohne `Idempotency-Key`) → Atomischer DB-Update entscheidet. Erster Request gewinnt (HTTP 200), zweiter erhält HTTP 409.

- **EC-CCC-02:** Client sendet Submit mit `Idempotency-Key`, erster Request schlägt mit HTTP 500 fehl → Die gecachte Response enthält ausschliesslich erfolgreiche Antworten. Der Retry mit gleichem Key löst einen neuen Versuch aus (kein Cache-Hit).

- **EC-CCC-03:** `Idempotency-Key`-Cache-Eintrag läuft während eines Retries genau ab (Timing) → Das System behandelt einen abgelaufenen Cache-Eintrag wie einen fehlenden Entry: neuer Submit-Versuch wird ausgeführt. Status-Guard verhindert Doppel-Provisioning, sofern Order bereits `submitted` ist.

---

### 1.2 Approval Decision

**Wo:** `POST /api/v1/approval-requests/{approval_request_id}/approve` und `POST /api/v1/approval-requests/{approval_request_id}/reject`

**Wie:** Compare-and-Swap (CAS) auf Datenbankebene.

Das System führt das Statusupdate als atomisches `UPDATE approval_requests SET status = 'approved'|'rejected' WHERE id = ? AND status = 'pending'` aus. Sind keine Zeilen betroffen (affected rows = 0), ist die Anfrage bereits entschieden. Jeder zweite Approver oder jeder parallele Request erhält HTTP 409.

Zusätzlicher Race-Case: Timeout-Job vs. Approver laufen gleichzeitig. Beide verwenden dieselbe CAS-Bedingung (`status = 'pending'`). Wer zuerst committed, gewinnt. Der andere erhält affected rows = 0 und handelt entsprechend (HTTP 409 für Approver; Silent Skip für Timeout-Job).

**Requirements:**

- **REQ-CCC-07:** Der `approve`- und der `reject`-Endpoint verwenden kein Pre-Select-Check + separates Update (Two-Step), sondern ausschliesslich den Single-Statement-CAS-Ansatz. Dies verhindert TOCTOU-Fehler (Time-of-Check/Time-of-Use).

- **REQ-CCC-08:** Gewinnt der Timeout-Job den CAS-Wettbewerb gegen einen Approver, antwortet das System dem Approver mit HTTP 409 und dem spezifischen Fehlercode `APPROVAL_REQUEST_EXPIRED` (Unterscheidung zu `APPROVAL_REQUEST_ALREADY_DECIDED` für den Fall, dass ein anderer Approver bereits entschieden hat).

- **REQ-CCC-09:** Gewinnt ein Approver den CAS-Wettbewerb gegen den Timeout-Job, findet der Timeout-Job keinen `pending`-Record mehr. Er überspringt den Record still (kein Fehler, kein Statusübergang), erstellt jedoch einen Log-Eintrag.

**Edge Cases:**

- **EC-CCC-04:** Beide Approver in einem Multi-Approver-Szenario (zukünftige Erweiterung) treffen gleichzeitig eine Entscheidung → CAS stellt sicher, dass nur einer gewinnt. Da im MVP ein 1-stufiger Workflow ohne parallele Approver-Anforderung vorgesehen ist, ist dieser Fall aktuell theoretisch. Die CAS-Implementierung muss diesen Fall dennoch korrekt handhaben.

- **EC-CCC-05:** Cron-Job für Timeout läuft zweimal in schneller Folge (z.B. nach Server-Neustart) → Beide Läufe verwenden `UPDATE WHERE status = 'pending' AND deadline_at < now()`. Der zweite Lauf findet den Record bereits in `status = 'rejected'` vor und überspringt ihn. Keine doppelten Benachrichtigungen entstehen.

---

### 1.3 Provisioning Dispatch

**Wo:** Automatischer Dispatcher (intern) + `POST /api/v1/admin/orders/{order_id}/items/{item_id}/dispatch` (manuell)

**Wie:** CAS auf `provisioning_status` per OrderItem.

Das System führt pro OrderItem ein atomisches `UPDATE order_items SET provisioning_status = 'provisioning', job_id = NULL WHERE id = ? AND provisioning_status = 'pending' AND job_id IS NULL` aus. Sind keine Zeilen betroffen (affected rows = 0), ist das Item bereits in Verarbeitung oder abgeschlossen.

**Requirements:**

- **REQ-CCC-10:** Der Idempotenz-Check ist per OrderItem atomar, nicht per Order. Mehrere Items derselben Order können gleichzeitig den Übergang `pending` → `provisioning` durchlaufen, da jedes Item seinen eigenen unabhängigen CAS-Check hat.

- **REQ-CCC-11:** Wird ein OrderItem-Event aus der internen Job-Queue empfangen, dessen Item bereits `provisioning_status` `provisioning`, `done` oder `failed` hat, wird das Event silent gedroppt. Ein Log-Eintrag (Level INFO) mit `order_item_id` und aktuellem Status ist Pflicht.

- **REQ-CCC-12:** Beim Serverstart prüft der Dispatcher alle OrderItems mit `provisioning_status = 'pending'` und einem Alter über 5 Minuten (d.h. `created_at < now() - 5min`), die noch keine `job_id` haben. Dieser Startup-Check läuft zusätzlich alle 10 Minuten als zyklischer Hintergrund-Job.

- **REQ-CCC-13:** Für verwaiste OrderItems aus REQ-CCC-12 führt der Dispatcher einen Deduplication-Check gegen GitLab aus: Existiert ein Job, der in den letzten 10 Minuten mit dieser `order_item_id` als Pipeline-Variable gestartet wurde? Ja → `job_id` nachtragen, `provisioning_status` auf `provisioning` setzen, Feature 4.2 (Status-Sync) starten. Nein → Item erneut dispatchen.

**Edge Cases:**

- **EC-CCC-06:** Admin löst manuellen Dispatch aus, während der automatische Dispatcher dasselbe Item zeitgleich verarbeitet → CAS-Check entscheidet. Erster gewinnt. Admin erhält HTTP 409 (falls manuell als zweiter). Automatischer Dispatcher bricht intern ab (affected rows = 0), keine Fehlermeldung nach aussen.

- **EC-CCC-07:** Dispatcher stürzt nach GitLab-Call, aber vor dem DB-Update ab (job_id noch nicht persistiert) → Startup-Check (REQ-CCC-12) greift: Item ist älter als 5 Minuten, `provisioning_status = 'pending'`, keine `job_id`. Deduplication-Check gegen GitLab findet den Job und trägt die `job_id` nach.

---

### 1.4 E-Mail-Benachrichtigungen

**Wo:** Internes Notification-System (Fire-and-Forget, wird durch Statusübergänge ausgelöst)

**Wie:** `NotificationRecord`-basierter Status-Guard.

Vor jedem Sendeversuch legt das System einen `NotificationRecord` mit `status = 'pending'` an. Jeder `NotificationRecord` ist an eine spezifische Kombination aus `order_id` + `event_type` + `triggered_at` gebunden. Das System sendet niemals erneut gegen einen `NotificationRecord` mit `status = 'sent'`. Wiederholungsversuche laufen nur gegen Records mit `status = 'pending'` oder `'failed'` (mit verbleibendem `attempt_count`).

**Requirements:**

- **REQ-CCC-14:** Ein automatisches Retry darf nur für `NotificationRecord`-Einträge mit `status = 'failed'` und `attempt_count < 3` ausgelöst werden. Einträge mit `status = 'sent'` oder `status = 'retry_exhausted'` erhalten keine weiteren automatischen Sendeversuche.

- **REQ-CCC-15:** Der manuelle Admin-Retry (`POST /api/v1/admin/notifications/{notification_id}/retry`) erzeugt immer einen neuen `NotificationRecord` mit `attempt_count = 0`. Der ursprüngliche Record wird nicht modifiziert und verbleibt in seinem aktuellen Status. Dies verhindert Statusinkonsistenzen bei gleichzeitigen Retry-Versuchen.

- **REQ-CCC-16:** Löst ein Statusübergang (z.B. `done`) eine Benachrichtigung aus, während zeitgleich derselbe Statusübergang ein zweites Mal signalisiert wird (z.B. durch doppelte Queue-Delivery), prüft das System vor dem Anlegen eines neuen `NotificationRecord`, ob für dieselbe `order_id` + `event_type`-Kombination bereits ein `NotificationRecord` mit `status` `pending`, `sent` oder `failed` innerhalb der letzten 60 Sekunden existiert. Ist dies der Fall, wird kein zweiter Record angelegt (silent skip + Log-Eintrag).

**Validation Rules:**

- **VAL-CCC-02:** Admin-Retry-Request — `notification_id` muss existieren — `"Die Benachrichtigung wurde nicht gefunden."` (HTTP 404)
- **VAL-CCC-03:** Admin-Retry auf einen Record mit `status = 'sent'` — `"Diese Benachrichtigung wurde bereits erfolgreich gesendet. Ein erneuter Versuch ist nicht notwendig."` (HTTP 400)
- **VAL-CCC-04:** Admin-Retry auf einen Record mit `status = 'pending'` — `"Für diese Benachrichtigung läuft bereits ein Sendeversuch."` (HTTP 400)

**Edge Cases:**

- **EC-CCC-08:** SMTP-Server antwortet mit HTTP 250 OK (Senden erfolgreich), aber die E-Mail kommt beim Empfänger nicht an (Spam-Filter, Bounce) → Das System wertet SMTP 250 als Erfolg (`status: sent`). Bounce-Handling liegt ausserhalb des MVP-Scopes. Kein automatischer Retry.

- **EC-CCC-09:** Template-Render schlägt fehl (fehlende Platzhaltervariable) → `NotificationRecord` wird mit `status = 'failed'` angelegt. Automatischer Retry wird nicht gestartet (Konfigurationsfehler, keine transiente Ursache). Admin-Alert wird erzeugt (Log-Level ERROR).

---

## Thema 2: Error-Handling-Patterns

### Übersicht

Dieses Kapitel definiert systemweite, verbindliche Patterns für Fehlermeldungen, HTTP-Statuscodes, Retry-Strategien, Circuit Breaker und Logging. Alle Feature-Gruppen müssen diese Patterns einhalten.

---

### 2.1 Standard-Fehler-Response-Format

Alle API-Fehlerantworten (HTTP 4xx und 5xx) verwenden exakt folgendes JSON-Format:

```json
{
  "error_code": "SCREAMING_SNAKE_CASE string — maschinenlesbarer Fehlercode",
  "message": "string — human-readable Fehlermeldung auf Deutsch (für UI-Anzeige)",
  "details": "object | null — optionale strukturierte Zusatzinformationen",
  "request_id": "UUID — serverseitig generiert, in jedem Response-Header X-Request-ID und im Response-Body"
}
```

**Beispiele:**

```json
{
  "error_code": "ORDER_NOT_FOUND",
  "message": "Die angeforderte Bestellung wurde nicht gefunden.",
  "details": { "order_id": "550e8400-e29b-41d4-a716-446655440000" },
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Die Eingabe enthält ungültige Werte.",
  "details": {
    "fields": [
      { "field": "cpu_cores", "error": "Muss zwischen 1 und 64 liegen." },
      { "field": "memory_gb", "error": "Pflichtfeld fehlt." }
    ]
  },
  "request_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

**Requirements:**

- **REQ-CCC-17:** Jede API-Response (auch Erfolgsresponses) enthält den Header `X-Request-ID: <UUID>`. Die UUID wird pro Request vom Server generiert und identifiziert den Request eindeutig in Logs und Error-Responses.

- **REQ-CCC-18:** Das Feld `error_code` ist ein enum-artiger String in SCREAMING_SNAKE_CASE. Neue `error_code`-Werte müssen projektintern dokumentiert sein. Unbekannte Fehler aus Drittsystemen werden in `EXTERNAL_SYSTEM_ERROR` übersetzt; der technische Originalfehler erscheint ausschliesslich im Log, nicht in der API-Response.

- **REQ-CCC-19:** Das Feld `message` ist immer auf Deutsch und für die Anzeige in der Benutzeroberfläche geeignet. Technische Stack-Traces, SQL-Fehlermeldungen, interne Pfade oder Secrets dürfen in keinem `message`- oder `details`-Feld erscheinen.

- **REQ-CCC-20:** Das Feld `details` ist `null`, wenn keine strukturierten Zusatzinformationen vorliegen. Bei Validierungsfehlern enthält es ein `fields`-Array mit den fehlerhaften Feldern (Name + Fehlermeldung). Bei Ressourcenfehlern enthält es die betreffende `resource_id`.

---

### 2.2 HTTP-Statuscodes und ihre Semantik

| Code | Bedeutung im Projekt | Verwendungsbeispiele |
|------|----------------------|---------------------|
| 200 | Erfolgreiche Operation (Daten zurückgegeben oder Aktion abgeschlossen) | GET, PATCH, POST bei Aktionen ohne Erstellung |
| 201 | Ressource erfolgreich erstellt | POST Orders, POST Service-Accounts, POST Approval-Rules |
| 204 | Erfolgreiche Operation ohne Response-Body | DELETE-Operationen |
| 400 | Client-seitiger Fehler — ungültige Eingabe, Validierungsfehler, fehlerhafter Zustand | Validation-Fehler, ungültiger Statusübergang für die aktuelle Lage |
| 401 | Nicht authentifiziert — fehlendes, abgelaufenes oder ungültiges JWT | Token fehlt, Token abgelaufen, Signatur ungültig |
| 403 | Authentifiziert, aber nicht berechtigt — Rolle oder Ownership unzureichend | Requester greift auf fremde Order zu; Requester ruft Admin-Endpoint auf |
| 404 | Ressource nicht gefunden (nur wenn kein Informations-Leakage möglich) | Template nicht gefunden; eigene Order nicht gefunden |
| 409 | Konflikt — Idempotenz-Verletzung, unzulässiger Statusübergang, Ressource bereits in Zielzustand | Doppelter Submit; bereits entschiedener Approval; Service-Account in Benutzung |
| 410 | Ressource permanent entfernt (bekannte, aber nicht mehr verfügbare Ressource) | Abgelaufener Credential-Token |
| 422 | Semantisch ungültige Anfrage — syntaktisch korrekt, aber fachlich nicht ausführbar | Parameter-Abhängigkeitsregel verletzt; Template in Status `disabled` |
| 429 | Rate-Limit überschritten — zu viele Anfragen | Login-Rate-Limit; Credential-Brute-Force-Schutz |
| 500 | Unerwarteter Serverfehler — Bug oder nicht behebbare Ausnahme | Unbehandelte Exception; DB-Verbindungsfehler ohne Retry-Option |
| 503 | Externer Dienst nicht erreichbar — Umsystem ausgefallen | AD nicht erreichbar; GitLab-API down; SMTP-Server offline |

**Requirements:**

- **REQ-CCC-21:** HTTP 403 wird für alle Berechtigungsfehler verwendet, unabhängig davon, ob die Ressource existiert oder nicht (kein Information-Leakage). Ausnahme: Eigene Ressourcen eines Requesters liefern 404, wenn sie nicht existieren.

- **REQ-CCC-22:** HTTP 400 und HTTP 422 sind klar voneinander getrennt. 400 gilt für technisch ungültige Eingaben (fehlende Pflichtfelder, falsches Format). 422 gilt für fachlich ungültige Aktionen, die syntaktisch korrekt sind, aber gegen Geschäftsregeln verstossen.

- **REQ-CCC-23:** HTTP 500 darf niemals technische Details (Stack-Traces, SQL-Fehlermeldungen, interne Pfade) in der API-Response enthalten. Der Fehler wird vollständig nur im Server-Log (Level ERROR) protokolliert.

- **REQ-CCC-24:** HTTP 503 wird ausschliesslich für nicht erreichbare externe Systeme verwendet. Ist das externe System erreichbar, aber antwortet mit einem Fehler, wird der Fehler in einen geeigneten 4xx-Code übersetzt oder als 500 behandelt, je nach Ursache.

---

### 2.3 Retry-Strategien für Umsystem-Aufrufe

Umsysteme sind: Active Directory (LDAP), IPAM (HTTP), GitLab (HTTP), SMTP.

**Fehlerkategorisierung:**

| Kategorie | Beschreibung | Verhalten |
|-----------|-------------|-----------|
| Transient | Netzwerk-Timeout, Verbindungsfehler, HTTP 429 (Rate-Limit), HTTP 503 | Automatischer Retry mit exponentiellem Backoff |
| Permanent | HTTP 400, HTTP 401, HTTP 403, HTTP 404 vom Umsystem; fachlich falsche Konfiguration | Sofortiger Fehlschlag, kein Retry |
| Unbekannt | Unerwartete HTTP-Codes (z.B. HTTP 502, HTTP 500 vom Umsystem) | Einmaliger Retry; bei erneutem Fehler: Permanent behandeln |

**Requirements:**

- **REQ-CCC-25:** Transiente Fehler bei Umsystem-Aufrufen lösen automatisches Retry mit exponentiellem Backoff aus. Die Basis-Wartezeit beträgt 1 Sekunde; der Multiplikator ist 2; maximale Wartezeit beträgt 32 Sekunden. Maximale Anzahl Versuche: 4 (inklusive Erstversuch). Die Wartezeitformel lautet: `min(2^(n-1) * 1s, 32s)` für Versuch n.

| Versuch | Wartezeit vor Versuch |
|---------|----------------------|
| 1 (Erstversuch) | — |
| 2 | 1 Sekunde |
| 3 | 2 Sekunden |
| 4 | 4 Sekunden |
| (danach: Fehler permanent) | — |

- **REQ-CCC-26:** Permanente Fehler werden nicht wiederholt. Der Fehler wird sofort als `permanent_failure` klassifiziert, geloggt (Level ERROR) und in den Provisionierungs-Fehlerstatus übertragen (Feature 4.6).

- **REQ-CCC-27:** Bei E-Mail-Benachrichtigungen gilt ein abweichender Retry-Plan mit längeren Intervallen (da kein realtime-kritischer Pfad): Wartezeiten 1 Minute, 5 Minuten; maximal 3 Versuche. Dies ist in Feature 6.1 (REQ-16) spezifiziert und gilt prioritär gegenüber REQ-CCC-25.

- **REQ-CCC-28:** Retry-Versuche werden immer vollständig im Audit-Log protokolliert: `system` (ad | ipam | gitlab | smtp), `attempt_number`, `error_message`, `next_retry_at`. Der letzte fehlgeschlagene Versuch trägt `final_failure: true`.

---

### 2.4 Circuit-Breaker-Pattern

Circuit Breaker werden für die drei kritischen synchronen Umsystem-Integrationen implementiert: Active Directory, IPAM und GitLab.

**Zustandsmodell:**

```
CLOSED → (Fehlerschwelle überschritten) → OPEN → (Wartezeit abgelaufen) → HALF_OPEN → (Probe erfolgreich) → CLOSED
                                                                                      → (Probe fehlgeschlagen) → OPEN
```

**Requirements:**

- **REQ-CCC-29:** Jedes der drei Umsysteme (AD, IPAM, GitLab) hat einen unabhängigen Circuit Breaker. Ein offener Circuit Breaker bei AD beeinflusst nicht den Circuit Breaker für GitLab.

- **REQ-CCC-30:** Ein Circuit Breaker öffnet (Zustand `OPEN`), wenn innerhalb eines gleitenden 60-Sekunden-Fensters mindestens 5 Fehler aufgetreten sind, von denen mindestens 50 % der letzten 10 Anfragen Fehler waren. Im Zustand `OPEN` werden keine Anfragen an das Umsystem weitergeleitet; alle Anfragen schlagen sofort mit `CIRCUIT_OPEN` fehl (kein Netzwerk-Call).

- **REQ-CCC-31:** Die Wartezeit im Zustand `OPEN` beträgt 30 Sekunden. Danach wechselt der Circuit Breaker in `HALF_OPEN`. Im Zustand `HALF_OPEN` wird genau eine Probe-Anfrage an das Umsystem gesendet. Ist sie erfolgreich, wechselt der Breaker zu `CLOSED`. Schlägt sie fehl, wechselt er zurück zu `OPEN` mit zurückgesetzter Wartezeit.

- **REQ-CCC-32:** Provisioning-Jobs, die versuchen, ein Umsystem mit offenem Circuit Breaker aufzurufen, schlagen sofort mit `provisioning_status = 'failed'` und `failure_reason = 'SERVICE_UNAVAILABLE_CIRCUIT_OPEN'` fehl. Der Admin erhält eine Benachrichtigung (Feature 7.1).

- **REQ-CCC-33:** Der Admin kann den Zustand aller Circuit Breaker über das Admin-Dashboard (Feature 7.1) einsehen. Das Dashboard zeigt pro Umsystem: aktuellen Zustand, Fehlerrate, letzte Fehlerzeit, Zeit bis zum nächsten `HALF_OPEN`-Versuch.

- **REQ-CCC-34:** Circuit Breaker für SMTP (E-Mail) sind nicht im MVP vorgesehen, da E-Mail-Versand als Fire-and-Forget mit eigenem Retry-Mechanismus (Feature 6.1, REQ-16) abgehandelt wird und kein synchroner Kritikpfad ist.

**API Contract:**

- Endpoint: `GET /api/v1/admin/circuit-breaker/status`
- Authorization: Bearer token (role: admin required)
- Response 200:
```json
{
  "circuit_breakers": [
    {
      "system": "ad | ipam | gitlab",
      "state": "CLOSED | OPEN | HALF_OPEN",
      "error_count_last_60s": "integer",
      "error_rate_last_10_requests": "float (0.0–1.0)",
      "last_failure_at": "ISO-8601 datetime | null",
      "opens_at": "ISO-8601 datetime | null",
      "half_open_at": "ISO-8601 datetime | null"
    }
  ]
}
```
- Response 401: `{ "error_code": "UNAUTHORIZED", "message": "Authentifizierung erforderlich.", "details": null, "request_id": "uuid" }`
- Response 403: `{ "error_code": "FORBIDDEN", "message": "Nur Administratoren können diesen Endpoint aufrufen.", "details": null, "request_id": "uuid" }`

---

### 2.5 Logging-Standards

**Requirements:**

- **REQ-CCC-35:** Das System verwendet vier Log-Level mit folgender Semantik:

| Level | Verwendung |
|-------|------------|
| ERROR | Unerwartete Fehler, die manuelle Intervention erfordern oder den Service beeinträchtigen: nicht behandelte Exceptions, geschlossene Umsystem-Verbindungen nach Retry-Erschöpfung, Circuit-Breaker-Öffnung, Provisioning-Fehlschläge, fehlende Konfiguration beim Start. |
| WARN | Erwartbare Ausnahmezustände, die nicht sofort kritisch sind, aber überwacht werden müssen: fehlgeschlagene Health-Checks, abgelaufene Approval-Requests, wiederholte Idempotenz-Konflikte, Rate-Limit-Auslösungen. |
| INFO | Normale Systemereignisse: Statusübergänge von Orders und OrderItems, erfolgreiche Logins/Logouts, Admin-Aktionen, abgeschlossene Provisioning-Jobs, gesendete Benachrichtigungen. |
| DEBUG | Diagnose-Informationen für Entwickler und Debugging: eingehende Request-Parameter (ohne Credentials), Datenbankabfragen, Cache-Treffer/-Misses, Retry-Versuche. DEBUG ist in Produktion standardmässig deaktiviert. |

- **REQ-CCC-36:** Jeder Log-Eintrag enthält mindestens: `timestamp` (ISO-8601 mit Millisekunden), `level`, `request_id` (wenn im Request-Kontext), `user_id` (wenn authentifiziert), `message`, und ein strukturiertes `context`-Objekt mit relevanten Feldern.

- **REQ-CCC-37:** Folgende Daten dürfen unter keinen Umständen in Logs erscheinen, unabhängig vom Log-Level: Passwörter, JWT-Token-Inhalte, Service-Account-Credentials, Credential-Token-Werte (Zugangsdaten-Links), LDAP-Bind-Passwörter. Felder dieser Art müssen vor dem Logging explizit mit `***` maskiert oder vollständig entfernt werden.

- **REQ-CCC-38:** Autorisierungsfehler (HTTP 403) werden auf Level INFO geloggt mit `user_id`, angefragtem Endpoint, HTTP-Methode, Zeitstempel und der `request_id`. Kein Stack-Trace.

- **REQ-CCC-39:** Unerwartete Exceptions (HTTP 500) werden auf Level ERROR geloggt mit vollständigem Stack-Trace, `request_id`, `user_id` (falls vorhanden) und Request-Kontext (Methode, Pfad, Query-Parameter ohne Credentials).

---

### Edge Cases (Error-Handling)

- **EC-CCC-10:** Ein Umsystem antwortet mit einem unerwarteten HTTP-Code (z.B. HTTP 418 oder HTTP 507) → Das System behandelt alle nicht explizit kategorisierten 4xx-Codes als permanent, alle nicht explizit kategorisierten 5xx-Codes als transient (ein Retry). Der Fehlercode in der Response ist `EXTERNAL_SYSTEM_ERROR`.

- **EC-CCC-11:** Der Datenbankserver ist beim Start des Portals nicht erreichbar → Der Server startet nicht. Ein ERROR-Log-Eintrag wird in stderr ausgegeben (kein DB-Zugriff möglich). Nach manuellem Neustart wird ein normaler Startup-Check ausgeführt.

- **EC-CCC-12:** Ein Request-Body ist kein valides JSON → HTTP 400, `error_code: INVALID_JSON`, `message: "Der Anfrage-Body enthält kein gültiges JSON-Format."`. Stack-Trace wird nicht in der Response ausgegeben.

- **EC-CCC-13:** Ein API-Call enthält korrekte Syntax, aber ein `order_id`-Feld ist keine gültige UUID → HTTP 400, `error_code: INVALID_PARAMETER_FORMAT`, `details.field: "order_id"`, `details.expected: "UUID v4"`.

---

## Thema 3: Permissions-Matrix

### Rollen-Hierarchie (Referenz)

```
admin      ⊇ approver ⊇ requester
```

`admin` besitzt alle Berechtigungen von `approver` und `requester`.
`approver` besitzt alle Berechtigungen von `requester`.

Legende für die Matrix:

| Symbol | Bedeutung |
|--------|-----------|
| Ja | Rolle darf diesen Endpoint aufrufen |
| Nein | Rolle darf diesen Endpoint nicht aufrufen (HTTP 403) |
| — | Kein JWT erforderlich (öffentlicher Endpoint) |
| (eigene) | Nur auf eigene Ressourcen (Ownership-Check erforderlich) |
| (zugewiesen) | Nur auf zugewiesene Ressourcen (z.B. eigene Approval-Requests) |

---

### Gruppe 1: Identity & Access

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 1 | Login | POST | `/api/v1/auth/login` | — | — | — | Kein JWT, öffentlich |
| 2 | Logout | POST | `/api/v1/auth/logout` | Ja | Ja | Ja | Eigenes Token |
| 3 | Eigenes Profil abrufen | GET | `/api/v1/auth/me` | Ja | Ja | Ja | Eigenes Token |
| 4 | Berechtigungsmatrix abrufen | GET | `/api/v1/auth/permissions` | Nein | Nein | Ja | — |
| 5 | Service-Accounts auflisten | GET | `/api/v1/service-accounts` | Nein | Nein | Ja | — |
| 6 | Service-Account abrufen | GET | `/api/v1/service-accounts/{id}` | Nein | Nein | Ja | — |
| 7 | Service-Account erstellen | POST | `/api/v1/service-accounts` | Nein | Nein | Ja | — |
| 8 | Service-Account aktualisieren | PATCH | `/api/v1/service-accounts/{id}` | Nein | Nein | Ja | — |
| 9 | Service-Account löschen | DELETE | `/api/v1/service-accounts/{id}` | Nein | Nein | Ja | Nur wenn kein aktiver Job |
| 10 | Health-Check auslösen | POST | `/api/v1/service-accounts/{id}/health-check` | Nein | Nein | Ja | — |
| 11 | Health-Status aller Accounts | GET | `/api/v1/service-accounts/health` | Nein | Nein | Ja | — |

---

### Gruppe 2: Service Catalog

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 12 | Templates auflisten | GET | `/api/v1/catalog/templates` | Ja | Ja | Ja | Nur `active` und `deprecated` Templates für requester/approver; admin sieht alle inkl. `disabled` |
| 13 | Template abrufen | GET | `/api/v1/catalog/templates/{slug}` | Ja | Ja | Ja | Nur `active` und `deprecated` für requester/approver |
| 14 | Template-Versionen auflisten | GET | `/api/v1/catalog/templates/{slug}/versions` | Ja | Ja | Ja | — |
| 15 | Template-Diff abrufen | GET | `/api/v1/catalog/templates/{slug}/diff` | Ja | Ja | Ja | — |
| 16 | Parameter-Optionen auflösen | POST | `/api/v1/catalog/templates/{slug}/resolve-options` | Ja | Ja | Ja | — |
| 17 | Kategorien abrufen | GET | `/api/v1/catalog/categories` | Ja | Ja | Ja | — |
| 18 | Template-Parameter validieren | POST | `/api/v1/catalog/templates/{slug}/validate` | Ja | Ja | Ja | — |
| 19 | Template erstellen | POST | `/api/v1/admin/catalog/templates` | Nein | Nein | Ja | — |
| 20 | Template-Status ändern | PATCH | `/api/v1/admin/catalog/templates/{id}/status` | Nein | Nein | Ja | — |

---

### Gruppe 3: Order Lifecycle

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 21 | Draft-Order erstellen | POST | `/api/v1/orders` | Ja | Ja | Ja | — |
| 22 | Order abrufen | GET | `/api/v1/orders/{order_id}` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders; HTTP 403 auf fremde |
| 23 | Orders auflisten | GET | `/api/v1/orders` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders gefiltert; approver + admin: alle |
| 24 | Order-Metadaten aktualisieren | PATCH | `/api/v1/orders/{order_id}` | Ja (eigene, draft) | Ja (eigene, draft) | Ja | Nur im Status `draft`; Ownership-Check für requester und approver |
| 25 | Draft-Order löschen | DELETE | `/api/v1/orders/{order_id}` | Ja (eigene, draft) | Ja (eigene, draft) | Ja | Nur im Status `draft`; Ownership-Check für requester und approver |
| 26 | Item hinzufügen | POST | `/api/v1/orders/{order_id}/items` | Ja (eigene, draft) | Ja (eigene, draft) | Ja | Nur im Status `draft`; Ownership-Check |
| 27 | Item aktualisieren | PATCH | `/api/v1/orders/{order_id}/items/{item_id}` | Ja (eigene, draft) | Ja (eigene, draft) | Ja | Nur im Status `draft`; Ownership-Check |
| 28 | Item entfernen | DELETE | `/api/v1/orders/{order_id}/items/{item_id}` | Ja (eigene, draft) | Ja (eigene, draft) | Ja | Nur im Status `draft`; Ownership-Check |
| 29 | Item-Reihenfolge ändern | PUT | `/api/v1/orders/{order_id}/items/positions` | Ja (eigene, draft) | Ja (eigene, draft) | Ja | Nur im Status `draft`; Ownership-Check |
| 30 | Validierung auslösen | POST | `/api/v1/orders/{order_id}/validate` | Ja (eigene) | Ja (eigene) | Ja | Order muss in `draft` oder `validated` sein; Ownership-Check |
| 31 | Order einreichen (Submit) | POST | `/api/v1/orders/{order_id}/submit` | Ja (eigene, validated) | Ja (eigene, validated) | Ja | Nur im Status `validated`; Ownership-Check |
| 32 | Order-Status abrufen (Polling) | GET | `/api/v1/orders/{order_id}/status` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders |
| 33 | Order-Status SSE-Stream | GET | `/api/v1/orders/{order_id}/events` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders |
| 34 | Order als OpenTofu-JSON exportieren | GET | `/api/v1/orders/{order_id}/export/tofu` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders |
| 35 | Order-Item als OpenTofu-JSON exportieren | GET | `/api/v1/orders/{order_id}/items/{item_id}/export/tofu` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders |

---

### Gruppe 4: Provisioning Engine

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 36 | Dispatcher-Konfiguration abrufen | GET | `/api/v1/admin/dispatcher/config` | Nein | Nein | Ja | — |
| 37 | Dispatch-Log einer Order abrufen | GET | `/api/v1/admin/orders/{order_id}/dispatch-log` | Nein | Nein | Ja | — |
| 38 | Manuellen Dispatch auslösen | POST | `/api/v1/admin/orders/{order_id}/items/{item_id}/dispatch` | Nein | Nein | Ja | OrderItem muss `provisioning_status = pending` haben |
| 39 | Webhook-Empfänger (GitLab/Tofu) | POST | `/api/v1/internal/provisioning/webhook` | — | — | — | Kein JWT; Authentifizierung via Webhook-Secret-Header |
| 40 | Provisioning-Status einer Order abrufen | GET | `/api/v1/orders/{order_id}/provisioning-status` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders |
| 41 | Sync-Konfiguration abrufen | GET | `/api/v1/admin/provisioning/sync-config` | Nein | Nein | Ja | — |
| 42 | Sync-Konfiguration aktualisieren | PUT | `/api/v1/admin/provisioning/sync-config` | Nein | Nein | Ja | — |
| 43 | AD-Connector-Konfiguration abrufen | GET | `/api/v1/admin/ad-connector/config` | Nein | Nein | Ja | — |
| 44 | AD-Connector-Konfiguration aktualisieren | PUT | `/api/v1/admin/ad-connector/config` | Nein | Nein | Ja | — |
| 45 | AD-Connector-Konnektivität testen | POST | `/api/v1/admin/ad-connector/test` | Nein | Nein | Ja | — |
| 46 | IPAM-Konfiguration abrufen | GET | `/api/v1/admin/ipam/config` | Nein | Nein | Ja | — |
| 47 | IPAM-Konfiguration aktualisieren | PUT | `/api/v1/admin/ipam/config` | Nein | Nein | Ja | — |
| 48 | IP-Reservierung einer Order abrufen | GET | `/api/v1/admin/orders/{order_id}/ip-reservation` | Nein | Nein | Ja | — |
| 49 | Zugangsdaten via Token abrufen | GET | `/api/v1/credentials/{token}` | — | — | — | Kein JWT; authentifizierung via Token-Wert; Rate-Limit pro IP |
| 50 | Datenbank-Server-Konfigurationen auflisten | GET | `/api/v1/admin/db-servers` | Nein | Nein | Ja | — |
| 51 | Datenbank-Server-Konfiguration hinzufügen/aktualisieren | PUT | `/api/v1/admin/db-servers/{server_id}` | Nein | Nein | Ja | — |
| 52 | Manuellen Rollback auslösen | POST | `/api/v1/admin/orders/{order_id}/rollback` | Nein | Nein | Ja | — |
| 53 | Rollback-Status abrufen | GET | `/api/v1/admin/orders/{order_id}/rollback-status` | Nein | Nein | Ja | — |
| 54 | Idempotenz-Status einer Order abrufen | GET | `/api/v1/admin/orders/{order_id}/idempotency-status` | Nein | Nein | Ja | — |

---

### Gruppe 5–7: Ressourcen, Benachrichtigungen, Administration

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 55 | Eigene Ressourcen auflisten | GET | `/api/v1/resources` | Ja (eigene) | Ja (eigene) | Ja | requester + approver: nur eigene Ressourcen; admin: alle |
| 56 | Ressource abrufen | GET | `/api/v1/resources/{resource_id}` | Ja (eigene) | Ja (eigene) | Ja | requester + approver: nur eigene; HTTP 403 (nicht 404) auf fremde |
| 57 | Benachrichtigungen einer Order abrufen | GET | `/api/v1/orders/{order_id}/notifications` | Ja (eigene) | Ja | Ja | requester: nur eigene Orders |
| 58 | Fehlgeschlagene Benachrichtigung erneut senden | POST | `/api/v1/admin/notifications/{notification_id}/retry` | Nein | Nein | Ja | Nur für `status = retry_exhausted` |
| 59 | SMTP-Konfiguration abrufen | GET | `/api/v1/admin/config/smtp` | Nein | Nein | Ja | — |
| 60 | SMTP-Konfiguration aktualisieren | PUT | `/api/v1/admin/config/smtp` | Nein | Nein | Ja | — |
| 61 | Credential-Token-Status abrufen | GET | `/api/v1/resources/{resource_id}/credential-status` | Ja (eigene) | Ja (eigene) | Ja | requester + approver: nur eigene Ressourcen |
| 62 | Neuen Credential-Token ausstellen | POST | `/api/v1/admin/resources/{resource_id}/credential-token` | Nein | Nein | Ja | — |
| 63 | Admin-Dashboard abrufen | GET | `/api/v1/admin/dashboard` | Nein | Nein | Ja | — |
| 64 | Alle Orders auflisten (Admin) | GET | `/api/v1/admin/orders` | Nein | Nein | Ja | Adminansicht aller Orders, paginiert |
| 65 | Alle Ressourcen auflisten (Admin) | GET | `/api/v1/admin/resources` | Nein | Nein | Ja | Adminansicht inkl. `requester_name` |
| 66 | Audit-Log durchsuchen | GET | `/api/v1/admin/audit-log` | Nein | Nein | Ja | — |
| 67 | Audit-Log exportieren | GET | `/api/v1/admin/audit-log/export` | Nein | Nein | Ja | — |
| 68 | Audit-Log-Eintrag abrufen | GET | `/api/v1/admin/audit-log/{entry_id}` | Nein | Nein | Ja | — |
| 69 | Audit-Log-Konfiguration abrufen | GET | `/api/v1/admin/config/audit-log` | Nein | Nein | Ja | — |
| 70 | Audit-Log-Konfiguration aktualisieren | PUT | `/api/v1/admin/config/audit-log` | Nein | Nein | Ja | — |

---

### Gruppe 8: Approval Workflow

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 71 | Approval-Regeln auflisten | GET | `/api/v1/approval-rules` | Nein | Ja | Ja | — |
| 72 | Approval-Regel erstellen | POST | `/api/v1/approval-rules` | Nein | Nein | Ja | — |
| 73 | Approval-Regel aktualisieren | PATCH | `/api/v1/approval-rules/{rule_id}` | Nein | Nein | Ja | — |
| 74 | Approval-Regel löschen | DELETE | `/api/v1/approval-rules/{rule_id}` | Nein | Nein | Ja | Nur wenn keine aktiven Requests auf dieser Regel |
| 75 | Approval-Regeln evaluieren (Dry Run) | POST | `/api/v1/approval-rules/evaluate` | Nein | Ja | Ja | — |
| 76 | Approval-Requests auflisten | GET | `/api/v1/approval-requests` | Nein | Ja (zugewiesen) | Ja | approver: sieht nur Requests, die an ihn oder seine Gruppe gehen; admin: alle |
| 77 | Approval-Request abrufen | GET | `/api/v1/approval-requests/{approval_request_id}` | Nein | Ja (zugewiesen) | Ja | approver: nur zugewiesene Requests |
| 78 | Approval-Request genehmigen | POST | `/api/v1/approval-requests/{approval_request_id}/approve` | Nein | Ja (zugewiesen) | Ja | approver: nur zugewiesene, offene (status = pending) Requests |
| 79 | Approval-Request ablehnen | POST | `/api/v1/approval-requests/{approval_request_id}/reject` | Nein | Ja (zugewiesen) | Ja | approver: nur zugewiesene, offene (status = pending) Requests |
| 80 | Order-Details für Approval abrufen | GET | `/api/v1/approval-requests/{approval_request_id}/order-details` | Nein | Ja (zugewiesen) | Ja | approver: nur zugewiesene Requests |
| 81 | Deadline eines Approval-Requests verlängern | PATCH | `/api/v1/approval-requests/{approval_request_id}/deadline` | Nein | Nein | Ja | — |
| 82 | Ablaufende Approval-Requests auflisten | GET | `/api/v1/approval-requests/expiring` | Nein | Nein | Ja | — |
| 83 | Approval-Systemkonfiguration abrufen | GET | `/api/v1/approval-config` | Nein | Nein | Ja | — |
| 84 | Approval-Systemkonfiguration aktualisieren | PATCH | `/api/v1/approval-config` | Nein | Nein | Ja | — |

---

### Querschnittsthemen-spezifische Endpoints (diese Spec)

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 85 | Circuit-Breaker-Status abrufen | GET | `/api/v1/admin/circuit-breaker/status` | Nein | Nein | Ja | — |

---

### Health-Check (öffentlich)

| Nr. | Endpoint | Methode | Pfad | requester | approver | admin | Zusatzbedingung |
|-----|----------|---------|------|-----------|----------|-------|-----------------|
| 86 | Health-Check | GET | `/api/v1/health` | — | — | — | Kein JWT, öffentlich; nur interner Systemstatus |

---

### Permissions-Matrix: Zusammenfassung nach Rollen

| Rolle | Erlaubte Endpoint-Nummern | Gesamtanzahl |
|-------|--------------------------|--------------|
| requester | 1–3, 12–18, 21–35 (eigene), 40 (eigene), 49, 55–57 (eigene), 61 (eigene) | ~32 |
| approver | wie requester + 4 entfällt + 23 (alle), 32 (alle), 33 (alle), 34 (alle), 35 (alle), 40 (alle), 55 (eigene), 56 (eigene), 57 (alle), 61 (eigene), 71, 75–80 | ~42 |
| admin | Alle Endpoints (1–86) | 86 |

> Hinweis: "eigene" bedeutet, der Ownership-Check (`requester_id = user_id aus JWT`) wird erzwungen. Scheitert der Ownership-Check, antwortet das System mit HTTP 403 (nicht HTTP 404).

---

### Requirements (Permissions-Matrix)

- **REQ-CCC-40:** Jeder Endpoint implementiert die in der Matrix definierten Rollenpflichten serverseitig. Eine clientseitige Rolle reicht nicht aus; der Server prüft den JWT-`roles`-Claim bei jedem Request.

- **REQ-CCC-41:** Ownership-Checks (Spalte "Zusatzbedingung: eigene") werden zusätzlich zur Rollen-Prüfung durchgeführt. Ein Requester mit gültigem JWT, der auf eine fremde Order zugreift, erhält HTTP 403, unabhängig davon, dass die Ressource existiert.

- **REQ-CCC-42:** Der interne Webhook-Endpoint (`POST /api/v1/internal/provisioning/webhook`, Nr. 39) und der öffentliche Credential-Endpoint (`GET /api/v1/credentials/{token}`, Nr. 49) verwenden keine JWT-Authentifizierung. Stattdessen gelten spezifische Authentifizierungsverfahren: Webhook-Secret-Header für Nr. 39, Token-in-Pfad für Nr. 49. Diese Endpoints sind keine Ausnahmen von der Sicherheitsanforderung, sondern nutzen einen anderen, gleichwertigen Authentifizierungsmechanismus.

- **REQ-CCC-43:** Der Health-Check-Endpoint (`GET /api/v1/health`, Nr. 86) ist vollständig öffentlich und gibt ausschliesslich den Betriebszustand des Portals selbst zurück (HTTP 200 = betriebsbereit, HTTP 503 = nicht betriebsbereit). Keine Systemdetails, Versionsnummern oder interne Konfiguration.

---

## Abhängigkeitsmatrix

| Diese Spec | Abhängigkeit von | Beschreibung |
|------------|-----------------|--------------|
| Idempotenz-Patterns (1.1) | order-lifecycle.md REQ-150, REQ-159, VAL-93/94 | Submit-Idempotenz; Spec konkretisiert das Caching-Verhalten |
| Idempotenz-Patterns (1.2) | approval-workflow.md REQ-40, EC-07, EC-16 | CAS-Mechanismus; Spec fasst es systemweit zusammen |
| Idempotenz-Patterns (1.3) | provisioning-engine.md REQ-93–99, Feature 4.7 | Dispatch-Idempotenz; Spec ergänzt Startup-Check-Details |
| Idempotenz-Patterns (1.4) | resources-notifications-admin.md REQ-15–17 | Notification-Deduplication; REQ-CCC-16 ergänzt 60s-Fenster-Regel |
| Error-Handling (2.1–2.4) | Alle Feature-Gruppen | Verbindlich für alle API-Responses; überschreibt keine bestehenden Fehlercodes |
| Circuit-Breaker (2.4) | provisioning-engine.md Feature 4.1–4.5 | Circuit Breaker für AD, IPAM, GitLab; Neuer Admin-Endpoint Nr. 85 |
| Permissions-Matrix (3) | identity-access.md REQ-19, REQ-20 | Vollständige Ausformulierung der High-Level-Matrix aus REQ-19 |
