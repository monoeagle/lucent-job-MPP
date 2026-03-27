# Architektur

MPP folgt **Clean Architecture** auf beiden Seiten (Backend und Frontend) mit strikter Dependency-Richtung.

---

## Prinzip

Abhaengigkeiten zeigen immer nach innen — von der Infrastruktur zum Domaenkern. Die aeusseren Schichten kennen die inneren, aber nicht umgekehrt.

---

## Backend-Architektur

```
┌─────────────────────────────────────────────────────┐
│  API (Presentation)                                  │
│  app/api/v1/  — Flask-Blueprints, REST-Endpoints     │
├─────────────────────────────────────────────────────┤
│  Services (Use Cases)                                │
│  app/services/  — Business-Logik, Orchestrierung     │
├─────────────────────────────────────────────────────┤
│  Domain (Entities)                                   │
│  app/domain/  — Reine Datenklassen, Value Objects    │
├─────────────────────────────────────────────────────┤
│  Data (Repositories + Clients)                       │
│  app/data/  — DB-Modelle, Repositories, API-Clients  │
└─────────────────────────────────────────────────────┘
```

### Dependency-Flow

```
api/ → services/ → domain/ ← data/
```

- `api/` darf `services/` und `core/` aufrufen
- `services/` darf `domain/` und `data/repositories/` aufrufen
- `data/` darf `domain/` aufrufen
- `domain/` hat keine Abhaengigkeiten

### Verboten

- `api/` → `data/` (nur ueber Services)
- `domain/` → `data/`, `services/`, `api/`
- `services/` → `api/`

---

## Frontend-Architektur

```
┌─────────────────────────────────────────────────────┐
│  Pages (Presentation)                                │
│  src/pages/  — React-Seiten, UI-Logik                │
├─────────────────────────────────────────────────────┤
│  Hooks (Use Cases)                                   │
│  src/hooks/  — tanstack-query Hooks, Mutations       │
├─────────────────────────────────────────────────────┤
│  API (Data)                                          │
│  src/api/  — HTTP-Client, Endpoint-Module            │
├─────────────────────────────────────────────────────┤
│  Types (Domain)                                      │
│  src/types/  — TypeScript-Typen, Interfaces          │
└─────────────────────────────────────────────────────┘
```

### Dependency-Flow

```
pages/ → hooks/ → api/ ← types/
```

---

## Schichtenmodell (Gesamt)

```
┌──────────┐     HTTP/JSON     ┌──────────┐
│ Frontend │ ←──────────────→  │ Backend  │
│ React    │     REST API      │ Flask    │
└──────────┘                   └──────────┘
                                    │
                               ┌────┴────┐
                               │ PostgreSQL│
                               └──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
              │ Auth-Stub │  │ CMDB-Stub │  │ GitLab-   │
              │ (oder AD) │  │ (oder API)│  │ Mock/Live │
              └───────────┘  └───────────┘  └───────────┘
```

---

## Externe Systeme

| System   | Produktion        | Entwicklung               |
|----------|-------------------|---------------------------|
| Auth     | LDAP/AD           | Auth-Stub (5 Dummy-User)  |
| CMDB     | Unternehmens-CMDB | CMDB-Stub (YAML-Daten)    |
| GitLab   | GitLab CI/CD      | GitLab-Mock (Simulation)  |

Alle externen Systeme sind ueber konfigurierbare Modi austauschbar. Details unter [Stubs & Mocks](../betrieb/stubs-mocks.md).

---

## Rollen

| Rolle       | Beschreibung                                                        |
|-------------|---------------------------------------------------------------------|
| requester   | Standard-Benutzer, bestellt Services                                |
| approver    | Genehmigt/lehnt Bestellungen ab                                     |
| admin       | Verwaltung von Regeln, Templates, Audit-Log, Dashboard              |
| superadmin  | Erweiterte Admin-Rechte: DSGVO-Anonymisierung, Rules, Audit-Zugang |

---

## Subscriptions-Layer

Subscriptions erweitern den Order-Lifecycle um Change- und Cancel-Operationen. Aenderungen an bestehenden Bestellungen durchlaufen denselben Approval-Workflow wie Neubestellungen.

---

## DSGVO-Anonymisierungs-Middleware

Backend-Middleware fuer datenschutzkonforme Anonymisierung personenbezogener Daten. Per Admin-Toggle aktivierbar. Anonymisiert Benutzer-IDs, E-Mail-Adressen und Namen in API-Responses und Datenbank-Eintraegen.

---

## Ports

| Dienst           | Port  |
|------------------|-------|
| Backend (Flask)  | 5000  |
| Frontend (Vite)  | 3000  |
| GitLab-Mock      | 8088  |
| PostgreSQL       | 5432  |
