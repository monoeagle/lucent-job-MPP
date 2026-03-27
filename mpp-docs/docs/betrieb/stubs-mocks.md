# Stubs & Mocks

MPP verwendet in der Entwicklung drei Stub/Mock-Systeme als Ersatz fuer Produktionsdienste. Alle sind ueber Environment-Variablen konfigurierbar.

---

## Auth-Stub

**Problem:** Kein Active Directory / LDAP in der Entwicklungsumgebung.

**Loesung:** Konfigurierbarer Auth-Modus mit 4 vordefinierten Dummy-Benutzern.

### Konfiguration

```bash
AUTH_MODE=stub        # Aktiviert den Stub-Modus
ENV=development       # Muss != production sein
```

### Benutzer

| Benutzername     | Rollen              | E-Mail                |
|------------------|---------------------|-----------------------|
| test-requester   | requester           | requester@test.local  |
| test-approver    | approver            | approver@test.local   |
| test-admin       | admin               | admin@test.local      |
| test-multi       | requester, approver | multi@test.local      |

### Funktionsweise

- Login ohne Passwort (oder mit `stub-password`)
- JWT-Tokens werden identisch zum Produktionsmodus generiert
- Token-TTL konfigurierbar ueber `STUB_TOKEN_TTL_SECONDS` (Default: 86400)
- Fallback-JWT-Secret: `stub-jwt-secret-dev-only`

### Sicherheitsmechanismus

Stub-Modus wird bei `ENV=production` mit `RuntimeError` blockiert. Das verhindert versehentliches Deployment mit Dummy-Benutzern.

### Dateien

- `app/core/config.py` — Auth-Mode-Validierung
- `app/services/auth_service.py` — Stub-Login und Token-Generierung
- `app/core/auth.py` — Middleware (identisch fuer beide Modi)

---

## CMDB-Stub

**Problem:** Die Unternehmens-CMDB ist nicht von ausserhalb des Produktionsnetzwerks erreichbar.

**Loesung:** CMDB-Stub mit statischen YAML-Testdaten.

### Konfiguration

```bash
CMDB_MODE=stub                    # Aktiviert den Stub-Modus
CMDB_STUB_DATA_PATH=./stubs/cmdb/ # Pfad zu den YAML-Dateien
```

### Testdaten

| Datei                   | Inhalt                                        |
|-------------------------|-----------------------------------------------|
| `locations.yaml`        | 3 Standorte (DC-Frankfurt, DC-Munich, DC-Berlin) |
| `networks.yaml`         | 6 Netzwerke (je 2 pro Standort)               |
| `tenants.yaml`          | 3 Mandanten                                   |
| `security_zones.yaml`   | 3 Sicherheitszonen (prod, staging, dev)        |

### Funktionsweise

- `CmdbStubClient` implementiert dasselbe Interface wie der zukuenftige Live-Client
- Alle CMDB-API-Endpoints (`/api/v1/cmdb/*`) funktionieren identisch
- Daten werden beim Start aus YAML-Dateien geladen
- Filterung und Suche funktionieren wie bei der echten CMDB

### Dateien

- `app/data/clients/cmdb_client.py` — CmdbStubClient
- `stubs/cmdb/*.yaml` — Testdaten

---

## GitLab-Mock

**Problem:** Die GitLab-Instanz fuer Provisioning-Pipelines ist nicht verfuegbar.

**Loesung:** Separate Flask-App simuliert GitLab-Pipeline-API.

### Starten

```bash
python3 stubs/gitlab_mock.py
# Laeuft auf Port 8088
```

### Konfiguration

```bash
GITLAB_URL=http://localhost:8088   # URL des Mocks
GITLAB_TOKEN=any-token             # Wird nicht validiert
GITLAB_PROJECT_ID=1                # Projekt-ID
```

### Unterstuetzte Endpunkte

- **Pipeline-Triggering** (POST) — Erstellt eine simulierte Pipeline
- **Pipeline-Status-Abfrage** (GET) — Gibt aktuellen Status zurueck
- **Webhook-Simulation** — Sendet Callbacks mit konfigurierbarer Verzoegerung

### Pipeline-Simulation

Pipelines durchlaufen simulierte Status:

```
pending → running → success (oder failed)
```

### Funktionsweise

- GitLab-Client (`app/data/clients/gitlab_client.py`) kann gegen Mock oder echtes GitLab sprechen
- Derselbe Client-Code wird in beiden Modi verwendet
- Webhooks werden automatisch an das Backend zurueckgesendet

### Dateien

- `stubs/gitlab_mock.py` — Mock-Server
- `app/data/clients/gitlab_client.py` — Client (identisch fuer Mock und Produktion)

---

## Zusammenfassung Environment-Variablen

| Variable             | Wert fuer Entwicklung        | Wert fuer Produktion          |
|----------------------|------------------------------|-------------------------------|
| `AUTH_MODE`          | `stub`                       | `ldap`                        |
| `ENV`                | `development`                | `production`                  |
| `CMDB_MODE`         | `stub`                       | `live`                        |
| `GITLAB_URL`         | `http://localhost:8088`      | `https://gitlab.example.com`  |
