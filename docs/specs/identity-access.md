# Feature-Gruppe 1: Identity & Access

> **Status:** Draft v1.0
> **Erstellt:** 2026-03-26
> **Umfang:** 3 Features, Requirements REQ-01–REQ-43, Validation Rules VAL-01–VAL-22, API Endpoints 1–17, Edge Cases EC-01–EC-29
> **Hinweis:** Nummerierung beginnt neu für diese Feature-Gruppe (Gruppe 1). Alle anderen Gruppen haben eigene Nummerierungsräume.

---

## Inhaltsverzeichnis

- [Feature 1.1: User Authentication](#feature-11-user-authentication)
- [Feature 1.2: Rollen & Berechtigungen](#feature-12-rollen--berechtigungen)
- [Feature 1.3: Service-Accounts für Umsysteme](#feature-13-service-accounts-für-umsysteme)
- [Logisches Datenmodell](#logisches-datenmodell)
- [Abhängigkeitsmatrix](#abhängigkeitsmatrix)

---

## Logisches Datenmodell

Das Datenmodell ist quellenagnostisch. Die API-Contracts definieren das Austauschformat; die interne Persistierung ist nicht Bestandteil dieser Spec.

### AuthenticatedUser (Session-Kontext)

```
AuthenticatedUser {
  user_id:      string          // unveränderlicher Bezeichner aus AD (z.B. objectGUID als UUID-String)
  username:     string          // sAMAccountName aus AD (Login-Name)
  display_name: string          // Anzeigename (CN aus AD)
  email:        string          // E-Mail-Adresse aus AD
  roles:        UserRole[]      // abgeleitete Rollen (requester | approver | admin) — zum Zeitpunkt der Token-Ausstellung
  ad_groups:    string[]        // rohe AD-Gruppen-Mitgliedschaften, die zur Rollen-Ableitung genutzt wurden
}
```

### UserRole (Enum)

```
requester   — Kann Orders erstellen, bearbeiten, einreichen und eigene Orders einsehen
approver    — Kann zugewiesene Orders genehmigen oder ablehnen; impliziert requester
admin       — Vollzugriff auf alle Ressourcen; kann Service-Accounts verwalten; impliziert approver + requester
```

### ServiceAccount

```
ServiceAccount {
  id:           string (UUID)        // interne ID, unveränderlich, serverseitig generiert
  name:         string               // eindeutiger technischer Name (z.B. "ad-connector", "ipam-client")
  system:       ServiceAccountSystem // ad | ipam | gitlab | opentofu
  description:  string (optional)    // Freitext-Beschreibung
  credentials:  object               // verschlüsselt gespeichert; Inhalt systemspezifisch (siehe REQ-38)
  status:       ServiceAccountStatus // active | disabled | error
  last_checked: ISO-8601 datetime (optional) // Zeitpunkt des letzten Health-Checks
  last_error:   string (optional)    // letzte Fehlermeldung aus Health-Check
  created_at:   ISO-8601 datetime
  updated_at:   ISO-8601 datetime
}
```

### ServiceAccountSystem (Enum)

```
ad        — Active Directory (LDAP)
ipam      — IP Address Management
gitlab    — GitLab (API-Token)
opentofu  — OpenTofu / Terraform (API-Token oder SSH-Key)
```

### ServiceAccountStatus (Enum)

```
active    — Account konfiguriert und zuletzt erfolgreich getestet
disabled  — Account manuell deaktiviert (kein Health-Check, nicht genutzt)
error     — Letzter Health-Check fehlgeschlagen
```

---

## Feature 1.1: User Authentication

### User Story

Als Mitarbeiter möchte ich mich mit meinen bestehenden Active-Directory-Zugangsdaten am Marketplace Portal anmelden, damit ich keinen separaten Account anlegen muss und die Authentifizierung durch die zentrale IT-Infrastruktur kontrolliert wird.

---

### Requirements

- **REQ-01:** Das System authentifiziert Benutzer ausschließlich gegen Active Directory via LDAP/LDAPS (oder SAML/OAuth2 SSO, wenn das AD als IdP konfiguriert ist). Ein eigenes User-Management oder lokale Passwort-Speicherung im Portal ist im MVP nicht vorgesehen.

- **REQ-02:** Nach erfolgreicher Authentifizierung stellt das System ein signiertes JWT (JSON Web Token) aus. Das Token enthält: `user_id`, `username`, `display_name`, `email`, `roles`, Ausstellungszeitpunkt (`iat`) und Ablaufzeitpunkt (`exp`).

- **REQ-03:** Die JWT-Gültigkeitsdauer beträgt 8 Stunden. Nach Ablauf ist das Token ungültig; der Client erhält HTTP 401 und muss den Benutzer zur erneuten Anmeldung auffordern.

- **REQ-04:** Das System unterstützt kein automatisches Token-Refresh im MVP. Ein abgelaufenes Token kann nicht verlängert werden; es ist eine vollständige Neuanmeldung erforderlich.

- **REQ-05:** Das JWT wird serverseitig mit einem konfigurierbaren Secret oder RSA-Schlüsselpaar signiert. Der Signing-Key wird nicht im Code oder in Versionskontrolle gespeichert; er wird über Umgebungsvariablen oder einen Secret-Manager bereitgestellt.

- **REQ-06:** Jeder API-Endpoint (außer `POST /api/v1/auth/login` und `GET /api/v1/health`) erfordert ein gültiges JWT im `Authorization`-Header (`Bearer <token>`). Fehlt das Token oder ist es ungültig/abgelaufen, antwortet das System mit HTTP 401.

- **REQ-07:** Das System validiert bei jeder Anfrage die Token-Signatur und den `exp`-Claim. Weitere Token-Blacklisting (z.B. bei Logout) ist im MVP nicht implementiert; der Logout ist clientseitig (Token-Löschung).

- **REQ-08:** Der Login-Endpoint nimmt `username` (sAMAccountName) und `password` entgegen. Das Passwort wird ausschließlich für die LDAP-Bind-Operation genutzt und danach nicht persistiert oder geloggt.

- **REQ-09:** Das System protokolliert erfolgreiche und fehlgeschlagene Login-Versuche mit Zeitstempel und `username`. Passwörter, Tokens und andere Credentials dürfen in keinem Log auftauchen.

- **REQ-10:** Nach 5 aufeinanderfolgenden fehlgeschlagenen Login-Versuchen für denselben `username` innerhalb von 10 Minuten sperrt das System weitere Login-Versuche für diesen `username` für 15 Minuten (Rate-Limiting). Die Sperre gilt unabhängig davon, ob der Account in AD existiert.

- **REQ-11:** Der Logout-Endpoint akzeptiert ein gültiges JWT und gibt HTTP 200 zurück. Da das System kein serverseitiges Token-Blacklisting betreibt, ist Logout im MVP eine clientseitige Operation; der Endpoint dient der einheitlichen API-Oberfläche und dem Audit-Log-Eintrag.

- **REQ-12:** Ist der Active-Directory-Server bei einem Login-Versuch nicht erreichbar, antwortet das System mit HTTP 503 und einer konfigurierbaren Fehlermeldung. Das System darf in diesem Fall keine Authentifizierung durchführen oder zulassen.

- **REQ-13:** Alle Kommunikation zwischen Portal-Backend und Active Directory erfolgt verschlüsselt (LDAPS auf Port 636 oder StartTLS auf Port 389). Unverschlüsselte LDAP-Verbindungen sind nicht zulässig.

---

### Validation Rules

- **VAL-01:** `username` beim Login — Pflichtfeld, 1–64 Zeichen, darf keine Steuerzeichen enthalten — `"Benutzername ist ein Pflichtfeld."`

- **VAL-02:** `password` beim Login — Pflichtfeld, 1–256 Zeichen — `"Passwort ist ein Pflichtfeld."`

- **VAL-03:** `Authorization`-Header bei geschützten Endpoints — Muss im Format `Bearer <token>` vorhanden sein — `"Authentifizierung erforderlich. Bitte melden Sie sich an."`

- **VAL-04:** JWT-Signatur — Muss mit dem konfigurierten Signing-Key validierbar sein — `"Ungültiges Authentifizierungstoken."`

- **VAL-05:** JWT `exp`-Claim — Muss in der Zukunft liegen — `"Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an."`

- **VAL-06:** Login-Rate-Limit — Nach 5 fehlgeschlagenen Versuchen innerhalb von 10 Minuten für denselben `username` — `"Zu viele fehlgeschlagene Anmeldeversuche. Bitte versuchen Sie es in 15 Minuten erneut."`

---

### API Contract

**Endpoint 1: Login**
```
POST /api/v1/auth/login
```
Request Body:
```json
{
  "username": "string (sAMAccountName, required)",
  "password": "string (required, never logged)"
}
```
Response 200:
```json
{
  "token": "string (signed JWT)",
  "expires_at": "2026-03-26T16:00:00Z",
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "jsmith",
    "display_name": "John Smith",
    "email": "jsmith@example.com",
    "roles": ["requester"]
  }
}
```
Response 401:
```json
{ "error": "INVALID_CREDENTIALS", "message": "Benutzername oder Passwort ist falsch." }
```
Response 429:
```json
{ "error": "RATE_LIMIT_EXCEEDED", "message": "Zu viele fehlgeschlagene Anmeldeversuche. Bitte versuchen Sie es in 15 Minuten erneut.", "retry_after_seconds": 900 }
```
Response 503:
```json
{ "error": "AUTH_SERVICE_UNAVAILABLE", "message": "Der Authentifizierungsdienst ist derzeit nicht erreichbar. Bitte versuchen Sie es später erneut." }
```

---

**Endpoint 2: Logout**
```
POST /api/v1/auth/logout
Authorization: Bearer <token>
```
Request Body: (leer)

Response 200:
```json
{ "message": "Erfolgreich abgemeldet." }
```
Response 401:
```json
{ "error": "UNAUTHORIZED", "message": "Authentifizierung erforderlich. Bitte melden Sie sich an." }
```

---

**Endpoint 3: Eigenes Profil abrufen**
```
GET /api/v1/auth/me
Authorization: Bearer <token>
```
Response 200:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith",
  "display_name": "John Smith",
  "email": "jsmith@example.com",
  "roles": ["requester"],
  "token_expires_at": "2026-03-26T16:00:00Z"
}
```
Response 401:
```json
{ "error": "UNAUTHORIZED", "message": "Authentifizierung erforderlich. Bitte melden Sie sich an." }
```

---

### Edge Cases

- **EC-01:** AD-Server antwortet mit Timeout (> konfiguriertes Limit) → HTTP 503, Login wird abgebrochen, Fehler wird geloggt (ohne Passwort). Das System führt keinen Fallback auf lokale Authentifizierung durch.

- **EC-02:** AD-Bind erfolgreich, aber das User-Objekt hat kein `mail`-Attribut gesetzt → Login wird abgebrochen, HTTP 500 mit internem Fehlercode `AD_ATTRIBUTE_MISSING`. Admin erhält Hinweis im Log. (Rationale: E-Mail wird für Benachrichtigungen in späteren Features benötigt und muss validierbar sein.)

- **EC-03:** User ist im AD als deaktiviert markiert (`userAccountControl`-Flag) → LDAP-Bind schlägt fehl oder das System erkennt den disabled-Zustand; HTTP 401 mit Meldung `"Ihr Konto ist deaktiviert. Bitte wenden Sie sich an den IT-Support."` Der Response-Code 401 (nicht 403) verhindert Enumeration.

- **EC-04:** JWT-Signing-Key fehlt oder ist ungültig beim Server-Start → Server startet nicht; Fehler wird im Startlog ausgegeben. Kein Betrieb ohne gültigen Signing-Key.

- **EC-05:** Client sendet ein JWT, das für eine andere Umgebung (anderer Signing-Key) ausgestellt wurde → Signaturvalidierung schlägt fehl → HTTP 401 `INVALID_TOKEN`.

- **EC-06:** Token läuft während einer laufenden API-Anfrage ab (zwischen Request-Eingang und Verarbeitung) → Die Anfrage wird mit dem zum Zeitpunkt des Request-Eingangs geprüften Token-Status verarbeitet. Die Prüfung erfolgt einmalig zu Beginn der Request-Verarbeitung.

- **EC-07:** Login-Rate-Limit: Angreifer nutzt verschiedene `username`-Werte, um Rate-Limit zu umgehen → Das Rate-Limiting greift pro `username` (nicht pro IP). IP-basiertes Rate-Limiting ist eine Infrastruktur-Maßnahme (z.B. Reverse Proxy) und liegt außerhalb dieser Spec.

---

## Feature 1.2: Rollen & Berechtigungen

### User Story

Als System möchte ich sicherstellen, dass jeder Benutzer nur die Aktionen ausführen kann, für die seine Rolle ihn berechtigt, damit unbefugte Zugriffe auf sensible Ressourcen und Operationen verhindert werden.

---

### Requirements

- **REQ-14:** Das System kennt genau drei Rollen: `requester`, `approver`, `admin`. Die Rollen sind hierarchisch: `admin` schließt alle Berechtigungen von `approver` ein, `approver` schließt alle Berechtigungen von `requester` ein.

- **REQ-15:** Rollen werden ausschließlich aus der AD-Gruppen-Mitgliedschaft des authentifizierten Benutzers abgeleitet. Die Zuordnung von AD-Gruppen zu Portal-Rollen ist serverseitig konfiguriert (nicht im Code hardcodiert) und wird über Umgebungsvariablen oder eine Konfigurationsdatei verwaltet.

- **REQ-16:** Gehört ein Benutzer keiner der konfigurierten AD-Gruppen an, erhält er implizit die Rolle `requester`. Ein Benutzer ohne jede Rolle (kein Portal-Zugang) ist im MVP nicht vorgesehen; jeder AD-User mit gültigem Login kann den Marketplace nutzen.

- **REQ-17:** Rollen werden zum Zeitpunkt der Token-Ausstellung in das JWT eingebettet. Ändert sich die AD-Gruppen-Mitgliedschaft eines Benutzers, wirkt sich dies erst nach der nächsten Anmeldung (neuem Token) aus. Bestehende Tokens bleiben für ihre Restlaufzeit gültig.

- **REQ-18:** Jeder API-Endpoint, der Daten verändert oder auf fremde Ressourcen zugreift, prüft die Rolle aus dem JWT gegen die erforderliche Mindest-Rolle. Bei unzureichender Berechtigung antwortet das System mit HTTP 403.

- **REQ-19:** Die Berechtigungsmatrix ist wie folgt definiert:

  | Aktion | requester | approver | admin |
  |--------|-----------|----------|-------|
  | Eigene Orders einsehen, erstellen, bearbeiten, einreichen | Ja | Ja | Ja |
  | Alle Orders systemweit einsehen | Nein | Ja | Ja |
  | Orders genehmigen / ablehnen | Nein | Ja | Ja |
  | Service-Catalog einsehen (aktive Templates) | Ja | Ja | Ja |
  | Service-Catalog verwalten (Templates anlegen, deaktivieren) | Nein | Nein | Ja |
  | Provisioning-Status einsehen (eigene Orders) | Ja | Ja | Ja |
  | Provisioning-Status einsehen (alle Orders) | Nein | Ja | Ja |
  | Provisioning manuell auslösen / abbrechen | Nein | Nein | Ja |
  | Service-Accounts verwalten | Nein | Nein | Ja |
  | Health-Checks für Service-Accounts auslösen | Nein | Nein | Ja |
  | Systemweite Konfiguration einsehen und ändern | Nein | Nein | Ja |

- **REQ-20:** Ressourcen-Zugriffskontrolle (Ownership): Ein `requester` kann nur auf seine eigenen Orders zugreifen. Ein `approver` kann Orders einsehen, die zur Genehmigung an ihn weitergeleitet wurden, sowie alle Orders (nur lesend). Ein `admin` kann auf alle Ressourcen zugreifen. Diese Regel gilt zusätzlich zur rollenbasierten Berechtigungsmatrix (REQ-19).

- **REQ-21:** HTTP 403-Responses dürfen keine Information darüber preisgeben, ob die angefragte Ressource existiert (keine Unterscheidung zwischen "nicht gefunden" und "keine Berechtigung" für Ressourcen anderer Benutzer). Für einen `requester` antworten Endpoints auf fremde Order-IDs mit HTTP 403, nicht HTTP 404.

- **REQ-22:** Das System muss alle Autorisierungsentscheidungen auditierbar machen: Jeder HTTP-403-Response wird intern geloggt mit `user_id`, angefragtem Endpoint, HTTP-Methode und Zeitstempel.

---

### Validation Rules

- **VAL-07:** Rollen-Prüfung bei schreibenden Operationen — Rolle aus JWT-Claim muss die Mindest-Rolle für die Operation erfüllen — `"Sie haben keine Berechtigung, diese Aktion auszuführen."`

- **VAL-08:** Ressourcen-Ownership-Prüfung — `requester_id` der Ressource muss mit `user_id` aus JWT übereinstimmen, außer Rolle ist `approver` oder `admin` — `"Sie haben keine Berechtigung, auf diese Ressource zuzugreifen."`

- **VAL-09:** Ungültige Rolle im JWT-Claim — JWT enthält einen `roles`-Wert, der nicht in `[requester, approver, admin]` enthalten ist — `"Ungültiges Authentifizierungstoken."` (HTTP 401, da Token manipuliert)

---

### API Contract

**Endpoint 4: Berechtigungsmatrix abrufen (Admin-Referenz)**
```
GET /api/v1/auth/permissions
Authorization: Bearer <token> (role: admin required)
```
Response 200:
```json
{
  "roles": ["requester", "approver", "admin"],
  "ad_group_mappings": {
    "requester": "CN=mp-requesters,OU=Groups,DC=example,DC=com",
    "approver": "CN=mp-approvers,OU=Groups,DC=example,DC=com",
    "admin": "CN=mp-admins,OU=Groups,DC=example,DC=com"
  }
}
```
Response 403:
```json
{ "error": "FORBIDDEN", "message": "Sie haben keine Berechtigung, diese Aktion auszuführen." }
```

---

### Edge Cases

- **EC-08:** Ein Benutzer wird während einer aktiven Session aus einer AD-Gruppe entfernt (z.B. Kündigung, Rollenwechsel) → Das bestehende JWT bleibt bis zu seinem `exp`-Zeitpunkt gültig. Das System kann keine laufenden Tokens invalidieren (kein Blacklisting im MVP). Mitigationsstrategie: kurze Token-Laufzeit (8h, REQ-03) und Prozess-seitige Maßnahmen (IT-Prozess zur Account-Sperrung direkt in AD).

- **EC-09:** Ein Benutzer wird in AD komplett deaktiviert, hat aber noch ein gültiges JWT → Token bleibt gültig bis `exp`. Mitigation: s. EC-08. Hinweis: Wenn der LDAP-Connector bei jeder Anfrage den AD-Status prüfen würde, würde das AD zum Single Point of Failure für alle API-Calls — dies ist eine bewusste MVP-Entscheidung gegen Live-Validierung.

- **EC-10:** JWT-Claim `roles` enthält `["admin", "requester"]` (mehrere Rollen) → Das System wertet die höchste Rolle aus der Liste aus. Für alle Berechtigungsprüfungen gilt die Hierarchie aus REQ-14.

- **EC-11:** AD-Gruppen-Konfiguration ist für eine Rolle nicht gesetzt (leerer Mapping-Eintrag) → Diese Rolle kann durch keinen Benutzer erworben werden. Das System loggt einen Konfigurationswarnung beim Start, startet aber dennoch. Betrifft nicht `requester` (Default-Rolle, REQ-16).

- **EC-12:** Requester versucht, die Order eines anderen Requesters aufzurufen (kennt die UUID z.B. durch Raten) → HTTP 403 (nicht HTTP 404), um keine Ressourcenexistenz zu bestätigen (REQ-21).

---

## Feature 1.3: Service-Accounts für Umsysteme

### User Story

Als Admin möchte ich die Zugangsdaten für technische Service-Accounts (AD, IPAM, GitLab, OpenTofu) zentral im Portal verwalten und deren Konnektivität testen, damit die Provisioning-Pipeline zuverlässig betrieben und Probleme frühzeitig erkannt werden.

---

### Requirements

- **REQ-23:** Das System verwaltet Service-Account-Konfigurationen für genau vier Zielsysteme: `ad` (Active Directory), `ipam`, `gitlab`, `opentofu`. Pro System kann genau ein aktiver Service-Account konfiguriert sein.

- **REQ-24:** Service-Account-Credentials werden niemals im Klartext persistiert. Die Verschlüsselung erfolgt mit einem serverseitigen Encryption-Key (AES-256 oder vergleichbar), der separat vom Application-Secret gespeichert wird und nicht in Versionskontrolle landet.

- **REQ-25:** Credentials erscheinen niemals in API-Responses. Die `GET`-Endpoints für Service-Accounts liefern alle Felder außer den eigentlichen Credential-Werten. Credential-Felder werden durch `"***"` oder einen leeren String ersetzt.

- **REQ-26:** Credentials erscheinen niemals in Logs. Das System muss sicherstellen, dass Credential-Felder beim Logging explizit maskiert werden, auch bei unerwarteten Exceptions (kein versehentliches Serialisieren des gesamten Request-Objekts).

- **REQ-27:** Nur Benutzer mit der Rolle `admin` können Service-Accounts erstellen, bearbeiten, löschen oder Health-Checks auslösen. Alle anderen Rollen erhalten HTTP 403.

- **REQ-28:** Das System stellt pro Service-Account einen Health-Check-Endpoint bereit. Der Health-Check prüft die tatsächliche Verbindung zum Zielsystem (nicht nur Konfigurationsvalidität):
  - `ad`: LDAP-Bind mit den hinterlegten Credentials
  - `ipam`: HTTP GET auf einen konfigurierten Ping-Endpoint der IPAM-API
  - `gitlab`: GitLab API-Call (`GET /api/v4/user` oder äquivalent) mit dem hinterlegten Token
  - `opentofu`: Verbindungstest zum OpenTofu-Backend (systemspezifisch, z.B. HTTP GET auf den Health-Endpoint)

- **REQ-29:** Nach einem Health-Check aktualisiert das System `last_checked`, `status` und `last_error` des Service-Accounts. Bei Erfolg: `status = active`, `last_error = null`. Bei Fehler: `status = error`, `last_error` enthält die Fehlermeldung (ohne Credentials in der Fehlermeldung).

- **REQ-30:** Das System führt automatische Health-Checks für alle aktiven Service-Accounts in einem konfigurierbaren Intervall durch (Standard: alle 5 Minuten). Schlägt ein Health-Check fehl, wird ein interner Alert geloggt. Push-Benachrichtigungen an Admins sind im MVP nicht enthalten.

- **REQ-31:** Ist ein Service-Account im Status `error` oder `disabled`, und ein Provisioning-Job benötigt diesen Account, schlägt der Job mit einem aussagekräftigen Fehler ab (`SERVICE_ACCOUNT_UNAVAILABLE`). Das System versucht keinen Fallback auf andere Accounts.

- **REQ-32:** Das Löschen eines Service-Accounts ist nur möglich, wenn kein aktiver Provisioning-Job diesen Account aktuell nutzt. Andernfalls HTTP 409 mit Hinweis auf laufende Jobs.

- **REQ-33:** Der `name` eines Service-Accounts muss systemweit eindeutig sein. Der `system`-Typ darf nur die Enum-Werte `ad | ipam | gitlab | opentofu` annehmen.

- **REQ-34:** Das Credential-Format ist pro System unterschiedlich und wird durch das Backend validiert:
  - `ad`: `{ "bind_dn": "CN=svc-mp,...", "password": "..." }`
  - `ipam`: `{ "base_url": "https://...", "api_key": "..." }`
  - `gitlab`: `{ "base_url": "https://...", "token": "..." }`
  - `opentofu`: `{ "backend_url": "https://...", "token": "..." }` (oder SSH-Key-Variante, falls konfiguriert)

- **REQ-35:** Wird ein Service-Account aktualisiert (PATCH), können Credentials teilweise übergeben werden. Felder, die nicht im Request-Body enthalten sind, behalten ihre bestehenden verschlüsselten Werte. Ein leerer String `""` für ein Credential-Feld ist nicht zulässig und wird abgelehnt.

- **REQ-36:** Das System stellt einen Übersichts-Endpoint bereit, der den Status aller konfigurierten Service-Accounts in einer Response zurückgibt (ohne Credentials). Dieser Endpoint ist ebenfalls nur für `admin` zugänglich.

---

### Validation Rules

- **VAL-10:** `name` bei Erstellung — Pflichtfeld, 3–64 Zeichen, nur Kleinbuchstaben, Ziffern und Bindestriche (`[a-z0-9-]+`) — `"Der Name darf nur Kleinbuchstaben, Ziffern und Bindestriche enthalten (3–64 Zeichen)."`

- **VAL-11:** `name` — Muss systemweit eindeutig sein — `"Ein Service-Account mit diesem Namen existiert bereits."`

- **VAL-12:** `system` — Pflichtfeld, muss einer der Werte `ad | ipam | gitlab | opentofu` sein — `"Ungültiger System-Typ. Erlaubte Werte: ad, ipam, gitlab, opentofu."`

- **VAL-13:** `credentials` bei Erstellung — Pflichtfeld, muss alle erforderlichen Felder für den jeweiligen `system`-Typ enthalten (REQ-34) — `"Die Zugangsdaten sind unvollständig für den gewählten System-Typ."`

- **VAL-14:** `credentials`-Felder beim Update — Leerer String `""` für ein Credential-Feld ist nicht zulässig — `"Credential-Felder dürfen nicht leer sein. Lassen Sie das Feld weg, um den bestehenden Wert zu behalten."`

- **VAL-15:** Löschen eines Service-Accounts — Kein aktiver Provisioning-Job darf diesen Account nutzen — `"Der Service-Account kann nicht gelöscht werden, da er von einem laufenden Provisioning-Job verwendet wird."`

- **VAL-16:** `status` beim manuellen Update — Nur `active` und `disabled` sind als direkt setzbare Werte erlaubt. `error` wird ausschließlich durch den Health-Check-Mechanismus gesetzt — `"Der Status 'error' kann nicht manuell gesetzt werden."`

---

### API Contract

**Endpoint 5: List all service accounts**
```
GET /api/v1/service-accounts
Authorization: Bearer <token> (role: admin required)
```
Response 200:
```json
{
  "service_accounts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "ad-connector",
      "system": "ad",
      "description": "LDAP-Bind-Account für AD-Integration",
      "status": "active",
      "last_checked": "2026-03-26T08:00:00Z",
      "last_error": null,
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-03-26T08:00:00Z"
    }
  ]
}
```
Response 403:
```json
{ "error": "FORBIDDEN", "message": "Sie haben keine Berechtigung, diese Aktion auszuführen." }
```

---

**Endpoint 6: Get a service account by ID**
```
GET /api/v1/service-accounts/{id}
Authorization: Bearer <token> (role: admin required)
```
Path Parameter: `id` — UUID des Service-Accounts

Response 200:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "ad-connector",
  "system": "ad",
  "description": "LDAP-Bind-Account für AD-Integration",
  "status": "active",
  "credentials": {
    "bind_dn": "CN=svc-mp,OU=ServiceAccounts,DC=example,DC=com",
    "password": "***"
  },
  "last_checked": "2026-03-26T08:00:00Z",
  "last_error": null,
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-03-26T08:00:00Z"
}
```
Response 403:
```json
{ "error": "FORBIDDEN", "message": "Sie haben keine Berechtigung, diese Aktion auszuführen." }
```
Response 404:
```json
{ "error": "NOT_FOUND", "message": "Service-Account nicht gefunden." }
```

---

**Endpoint 7: Create a service account**
```
POST /api/v1/service-accounts
Authorization: Bearer <token> (role: admin required)
```
Request Body:
```json
{
  "name": "gitlab-runner",
  "system": "gitlab",
  "description": "string (optional)",
  "credentials": {
    "base_url": "https://gitlab.example.com",
    "token": "glpat-xxxxxxxxxxxxxxxxxxxx"
  }
}
```
Response 201:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "gitlab-runner",
  "system": "gitlab",
  "description": null,
  "status": "active",
  "credentials": {
    "base_url": "https://gitlab.example.com",
    "token": "***"
  },
  "last_checked": null,
  "last_error": null,
  "created_at": "2026-03-26T09:00:00Z",
  "updated_at": "2026-03-26T09:00:00Z"
}
```
Response 400:
```json
{ "error": "VALIDATION_ERROR", "violations": [{ "field": "credentials.token", "message": "Die Zugangsdaten sind unvollständig für den gewählten System-Typ." }] }
```
Response 409:
```json
{ "error": "CONFLICT", "message": "Ein Service-Account mit diesem Namen existiert bereits." }
```

---

**Endpoint 8: Update a service account**
```
PATCH /api/v1/service-accounts/{id}
Authorization: Bearer <token> (role: admin required)
```
Request Body (alle Felder optional, nur geänderte Felder senden):
```json
{
  "description": "string (optional)",
  "status": "active | disabled (optional)",
  "credentials": {
    "token": "new-token-value (optional, partial update allowed)"
  }
}
```
Response 200: (gleiche Struktur wie Endpoint 6, Credentials maskiert)

Response 400:
```json
{ "error": "VALIDATION_ERROR", "violations": [{ "field": "status", "message": "Der Status 'error' kann nicht manuell gesetzt werden." }] }
```
Response 404:
```json
{ "error": "NOT_FOUND", "message": "Service-Account nicht gefunden." }
```

---

**Endpoint 9: Delete a service account**
```
DELETE /api/v1/service-accounts/{id}
Authorization: Bearer <token> (role: admin required)
```
Response 204: (kein Body)

Response 404:
```json
{ "error": "NOT_FOUND", "message": "Service-Account nicht gefunden." }
```
Response 409:
```json
{ "error": "CONFLICT", "message": "Der Service-Account kann nicht gelöscht werden, da er von einem laufenden Provisioning-Job verwendet wird.", "blocking_job_count": 2 }
```

---

**Endpoint 10: Trigger health check for a service account**
```
POST /api/v1/service-accounts/{id}/health-check
Authorization: Bearer <token> (role: admin required)
```
Response 200 (Health-Check erfolgreich):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "active",
  "last_checked": "2026-03-26T09:15:00Z",
  "last_error": null,
  "check_duration_ms": 142
}
```
Response 200 (Health-Check fehlgeschlagen — kein 4xx, da die Anfrage selbst gültig war):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "error",
  "last_checked": "2026-03-26T09:15:00Z",
  "last_error": "LDAP-Verbindung abgelehnt: ungültige Credentials (Code 49).",
  "check_duration_ms": 3021
}
```
Response 404:
```json
{ "error": "NOT_FOUND", "message": "Service-Account nicht gefunden." }
```

---

**Endpoint 11: Get health status of all service accounts**
```
GET /api/v1/service-accounts/health
Authorization: Bearer <token> (role: admin required)
```
Response 200:
```json
{
  "checked_at": "2026-03-26T09:00:00Z",
  "summary": {
    "total": 4,
    "active": 3,
    "error": 1,
    "disabled": 0
  },
  "accounts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "ad-connector",
      "system": "ad",
      "status": "active",
      "last_checked": "2026-03-26T09:00:00Z",
      "last_error": null
    }
  ]
}
```

---

### Edge Cases

- **EC-13:** Health-Check für `ad`-Account schlägt mit LDAP-Fehlercode 49 fehl (ungültige Credentials) → `status = error`, `last_error` enthält die LDAP-Fehlermeldung ohne Klartext-Credentials. Das Passwort selbst erscheint nicht in `last_error`.

- **EC-14:** Health-Check für `gitlab`-Account: GitLab antwortet mit HTTP 401 (Token abgelaufen oder widerrufen) → `status = error`, `last_error = "GitLab-Token ungültig oder abgelaufen (HTTP 401)."` Admin muss Token manuell erneuern.

- **EC-15:** Automatischer Health-Check (REQ-30) läuft genau dann, wenn ein Admin manuell einen Health-Check auslöst → Beide Checks laufen durch; das Ergebnis des zuletzt abgeschlossenen Checks überschreibt `last_checked` und `status`. Es gibt kein Locking für Health-Checks.

- **EC-16:** Ein Admin versucht, den einzigen `ad`-Service-Account zu löschen, während ein Provisioning-Job läuft, der AD-Objekte anlegt → HTTP 409 (REQ-32, VAL-15). Der Löschvorgang wird vollständig abgelehnt; der Account bleibt intakt.

- **EC-17:** Encryption-Key für Credentials wird nach dem Speichern eines Accounts rotiert → Bestehende verschlüsselte Werte können nicht mehr entschlüsselt werden; Verbindungsversuche schlagen fehl. Dieses Szenario erfordert einen definierten Key-Rotation-Prozess (außerhalb MVP-Scope; Admin muss Credentials neu eingeben). Das System erkennt Entschlüsselungsfehler und setzt `status = error` mit `last_error = "Credentials-Entschlüsselung fehlgeschlagen."`.

- **EC-18:** PATCH-Request enthält Credential-Feld mit Wert `null` (explizit) → Das System behandelt `null` identisch zu einem fehlenden Feld (behält bestehenden Wert). Nur `""` (leerer String) wird mit VAL-14 abgelehnt.

- **EC-19:** Automatischer Health-Check-Job schlägt für alle 4 Service-Accounts gleichzeitig fehl (z.B. Netzwerkausfall) → Alle vier Accounts erhalten `status = error`. Das System loggt jeden Fehler einzeln. Laufende Provisioning-Jobs erhalten beim nächsten Umsystem-Aufruf den Fehler `SERVICE_ACCOUNT_UNAVAILABLE` (REQ-31).

- **EC-20:** Admin erstellt Service-Account mit `system: ad`, obwohl bereits ein Account mit `system: ad` und `status: active` existiert → Kein Constraint auf Eindeutigkeit des `system`-Typs (nur `name` ist unique, REQ-33). Mehrere Accounts pro System sind technisch zulässig; welcher genutzt wird, entscheidet die Provisioning-Engine (außerhalb dieser Spec).

---

## Übergreifende Edge Cases (Feature-Gruppe 1)

- **EC-21:** Zwei simultane Login-Requests für denselben `username` (z.B. Browser-Tab-Doppelklick) → Beide Requests werden unabhängig verarbeitet. Beide erhalten gültige Tokens (kein Single-Session-Constraint im MVP). Das ist akzeptiert.

- **EC-22:** JWT enthält Rolle `admin`, aber der AD-Benutzer wurde inzwischen aus der Admin-Gruppe entfernt → Token bleibt gültig bis `exp` (EC-08). Alle Admin-Operationen sind bis Token-Ablauf möglich. Mitigationsstrategie: IT-Prozess, nicht technisch im MVP.

- **EC-23:** Der Portal-Server verliert die Verbindung zum AD während des Starts (kein Login möglich, Service-Account-Health-Checks schlagen fehl) → Server startet, ist aber funktional eingeschränkt. Login-Endpoint antwortet mit HTTP 503 (REQ-12). Bestehende gültige Tokens werden weiterhin akzeptiert (JWT-Prüfung ist lokal, kein AD-Lookup nötig).

- **EC-24:** Malformed JWT (z.B. Base64-Fehler, fehlende Segmente) → HTTP 401 `INVALID_TOKEN`. Keine Unterscheidung zwischen "abgelaufen" und "manipuliert" in der öffentlichen Fehlermeldung.

- **EC-25:** Concurrent PATCH auf denselben Service-Account (zwei Admin-Sessions gleichzeitig) → Das System nutzt optimistisches Locking oder Last-Write-Wins. Kein explizites Concurrency-Control im MVP; der letzte Write gewinnt. Admins werden nicht über konkurrierende Änderungen informiert.

- **EC-26:** Login-Anfrage enthält SQL-Injection oder LDAP-Injection in `username` → Das System escaped alle LDAP-Queries korrekt (LDAP-Injection-Prevention ist nicht optional; es ist eine Sicherheitsanforderung). SQL-Injection ist durch parametrisierte Queries im Backend abgedeckt.

- **EC-27:** Token wird vom Client in einem Cookie statt im `Authorization`-Header gesendet → Das System akzeptiert ausschließlich den `Authorization: Bearer`-Header. Cookie-basierte Auth ist im MVP nicht unterstützt; HTTP 401.

- **EC-28:** Admin-Benutzer löscht sich selbst (seinen eigenen AD-Account wird aus der Admin-Gruppe entfernt, aber sein Token ist noch gültig) → Token bleibt valide bis `exp`. Es gibt keinen Self-Revoke-Mechanismus.

- **EC-29:** Health-Check-Endpoint für einen `disabled` Service-Account wird aufgerufen → Der Health-Check wird trotzdem ausgeführt (Admin-Entscheidung, den Account zu testen), aber der `status` bleibt nach dem Check `disabled`, nicht `active`. Nur wenn der Admin explizit `status: active` per PATCH setzt, wird der Account reaktiviert.

---

## Statusmaschinen-Übersicht

### Service-Account-Status

```
[Erstellung] → active
active        → disabled  (Admin: PATCH status=disabled)
active        → error     (System: Health-Check fehlgeschlagen)
disabled      → active    (Admin: PATCH status=active)
error         → active    (System: nächster Health-Check erfolgreich)
error         → disabled  (Admin: PATCH status=disabled)
```

---

## Abhängigkeitsmatrix

### Eingehende Abhängigkeiten (andere Gruppen nutzen Feature-Gruppe 1)

| Feature | Abhängigkeit von Gruppe 1 | Details |
|---------|--------------------------|---------|
| Feature 2.1 (Service Catalog) | Auth + RBAC | Alle Catalog-Endpoints erfordern gültiges JWT (REQ-06). Template-Verwaltung erfordert Rolle `admin` (REQ-19). Catalog-Lesen erfordert mindestens `requester`. |
| Feature 3.1 (Order CRUD) | Auth + RBAC + user_id | `requester_id` einer Order entspricht dem `user_id` aus dem JWT (REQ-20). Zugriffskontrolle auf Orders basiert auf Feature 1.2. |
| Feature 3.2 (Order Validation) | Auth | Validation-Endpoint erfordert JWT; `user_id` wird für Audit-Log genutzt. |
| Feature 3.3 (Order Submit) | Auth + RBAC | Submit erfordert `requester`-Rolle. Status-SSE-Stream erfordert gültiges JWT. |
| Feature 3.4 (JSON Export) | Auth + RBAC | Export-Endpoint erfordert `admin`-Rolle oder Ownership. |
| Feature 4.1 (OpenTofu Job-Dispatcher) | Service-Account (gitlab, opentofu) | Dispatcher nutzt `gitlab`- und `opentofu`-Service-Accounts (Feature 1.3). Bei `SERVICE_ACCOUNT_UNAVAILABLE` bricht der Job ab (REQ-31). |
| Feature 4.3 (AD-Integration) | Service-Account (ad) | AD-Computer-Objekt-Anlage nutzt `ad`-Service-Account. |
| Feature 4.4 (IPAM-Integration) | Service-Account (ipam) | IP-Reservierung nutzt `ipam`-Service-Account. |
| Feature 4.5 (Datenbank-Provisioning) | Service-Account (opentofu) | DB-Provisioning-Job nutzt `opentofu`-Service-Account. |
| Feature 4.6 (Fehlerbehandlung & Rollback) | Service-Account | Rollback-Operationen nutzen denselben Service-Account wie der ursprüngliche Job. Bei `error`-Status des Accounts kann auch Rollback fehlschlagen (EC-19). |

### Ausgehende Abhängigkeiten (Gruppe 1 nutzt andere Gruppen)

| Feature | Abhängigkeit |
|---------|-------------|
| Keine | Feature-Gruppe 1 hat keine fachlichen Abhängigkeiten zu anderen Feature-Gruppen. Sie ist die Basis-Schicht, auf der alle anderen Gruppen aufbauen. |

### Querschnittsanforderungen

| Anforderung | Gilt für |
|-------------|---------|
| Alle API-Endpoints außer `/auth/login` und `/health` erfordern `Authorization: Bearer <token>` | Alle Endpoints in Feature-Gruppen 2, 3, 4 |
| HTTP 401 bei fehlendem/ungültigem/abgelaufenem Token | Alle geschützten Endpoints systemweit |
| HTTP 403 bei unzureichender Rolle | Alle rollengeschützten Endpoints systemweit |
| `user_id` aus JWT ist die kanonische Benutzer-ID in allen anderen Features | Feature 3.1 (`requester_id`), Feature 3.3 (Audit), Feature 4.x (Job-Initiator) |
| Credentials und Tokens dürfen in keinen Logs erscheinen | Systemweit, alle Feature-Gruppen |
