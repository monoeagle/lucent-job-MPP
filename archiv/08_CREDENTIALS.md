# Zugangsdaten — Marketplace Portal (MPP)

> **WARNUNG: NUR FUER ENTWICKLUNG — NIEMALS IN PRODUKTION VERWENDEN!**

---

## Auth-Stub-Benutzer

| Benutzername     | Passwort         | Rollen              | E-Mail                |
|------------------|------------------|---------------------|-----------------------|
| test-requester   | (keins / stub-password) | requester      | requester@test.local  |
| test-approver    | (keins / stub-password) | approver       | approver@test.local   |
| test-admin       | (keins / stub-password) | admin          | admin@test.local      |
| test-multi       | (keins / stub-password) | requester, approver | multi@test.local |

**Hinweis:** Im Stub-Modus ist kein Passwort erforderlich. Falls angegeben, wird es ignoriert (aber `stub-password` ist der dokumentierte Wert).

---

## PostgreSQL

| Parameter    | Wert                                          |
|-------------|-----------------------------------------------|
| Host        | `localhost`                                    |
| Port        | `5432`                                         |
| Datenbank   | `mpp_dev` (Entwicklung), `mpp_test` (Tests)   |
| Benutzer    | `mpp`                                          |
| Passwort    | `mpp`                                          |
| URL (Dev)   | `postgresql://mpp:mpp@localhost:5432/mpp_dev`  |
| URL (Test)  | `postgresql://mpp:mpp@localhost:5432/mpp_test` |

### Datenbank erstellen

```bash
sudo -u postgres createuser -P mpp          # Passwort: mpp
sudo -u postgres createdb -O mpp mpp_dev
sudo -u postgres createdb -O mpp mpp_test
```

---

## JWT

| Parameter       | Wert                              |
|-----------------|-----------------------------------|
| Secret (Stub)   | `stub-jwt-secret-dev-only`        |
| Algorithmus     | HS256                             |
| Token-TTL       | 86400 Sekunden (24 Stunden)       |

**Hinweis:** Das Fallback-Secret wird automatisch gesetzt, wenn `AUTH_MODE=stub` und kein `JWT_SECRET` konfiguriert ist. In Produktion muss ein sicheres Secret gesetzt werden.

---

## Environment-Variablen

| Variable                        | Default                                     | Beschreibung                       |
|---------------------------------|---------------------------------------------|------------------------------------|
| `AUTH_MODE`                     | `ldap`                                      | Auth-Modus (`stub` oder `ldap`)    |
| `ENV`                           | `development`                               | Umgebung                           |
| `JWT_SECRET`                    | (leer, Fallback in Stub)                    | JWT-Signaturschluessel             |
| `STUB_TOKEN_TTL_SECONDS`       | `86400`                                     | Token-Lebensdauer (Sekunden)       |
| `DATABASE_URL`                  | `postgresql://mpp:mpp@localhost:5432/mpp_dev` | Datenbank-URL                    |
| `CMDB_MODE`                    | `stub`                                      | CMDB-Modus (`stub` oder `live`)    |
| `CMDB_STUB_DATA_PATH`         | `./stubs/cmdb/`                             | Pfad zu CMDB-Stub-Daten           |
| `GITLAB_URL`                    | (leer)                                      | GitLab-URL                         |
| `GITLAB_TOKEN`                  | (leer)                                      | GitLab-API-Token                   |
| `GITLAB_PROJECT_ID`            | `1`                                         | GitLab-Projekt-ID                  |
| `APPROVAL_DEFAULT_DEADLINE_HOURS` | `48`                                     | Standard-Approval-Frist (Stunden)  |
| `APPROVAL_ALLOW_SELF_APPROVAL` | `false`                                     | Selbst-Genehmigung erlaubt?        |

---

## GitLab-Mock

| Parameter    | Wert                                   |
|-------------|----------------------------------------|
| URL          | `http://localhost:8088` (wenn gestartet)|
| Token        | (beliebig, wird nicht validiert)       |
| Projekt-ID   | `1`                                    |

---

## Ports

| Dienst           | Port  | Beschreibung                |
|------------------|-------|-----------------------------|
| Backend (Flask)  | 5000  | API-Server                  |
| Frontend (Vite)  | 3000  | Dev-Server                  |
| GitLab-Mock      | 8088  | Pipeline-Simulation         |
| PostgreSQL       | 5432  | Datenbank                   |
