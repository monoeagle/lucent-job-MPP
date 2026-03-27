# API-Referenz

Basis-Prefix: `/api/v1` — 76 Endpoints insgesamt.

---

## Auth-Level-Legende

| Level      | Beschreibung                                         |
|------------|------------------------------------------------------|
| —          | Kein Token erforderlich                              |
| login      | Gueltiger JWT-Token (beliebige Rolle)                |
| approver   | Rolle `approver` oder `admin`                        |
| admin      | Rolle `admin`                                        |

---

## Health

| # | Method | Path                    | Auth     | Beschreibung                     |
|---|--------|-------------------------|----------|----------------------------------|
| 1 | GET    | `/health`               | —        | Health-Check (inkl. Auth-Mode)   |
| 2 | GET    | `/admin/health`         | admin    | Admin-Health-Check               |

---

## Auth

| #  | Method | Path                     | Auth     | Beschreibung                     |
|----|--------|--------------------------|----------|----------------------------------|
| 3  | POST   | `/auth/login`            | —        | Login (Username + Passwort)      |
| 4  | GET    | `/auth/me`               | login    | Aktueller Benutzer               |
| 5  | GET    | `/dev/auth/stub-users`   | —        | Stub-Benutzer auflisten (nur Stub-Mode) |

---

## Catalog

| #  | Method | Path                                      | Auth     | Beschreibung                         |
|----|--------|-------------------------------------------|----------|--------------------------------------|
| 6  | GET    | `/catalog/templates`                      | login    | Templates auflisten (Filter, Suche, Paginierung) |
| 7  | GET    | `/catalog/templates/<slug>`               | login    | Template nach Slug abrufen           |
| 8  | GET    | `/catalog/templates/<slug>/versions`      | login    | Alle Versionen eines Templates       |
| 9  | GET    | `/catalog/categories`                     | login    | Kategorien auflisten                 |
| 10 | POST   | `/catalog/templates/<slug>/validate`      | login    | Parameter gegen Template validieren  |
| 11 | GET    | `/catalog/templates/<slug>/diff`          | approver | Version-Diff vergleichen             |
| 12 | POST   | `/catalog/templates/<slug>/resolve-options`| login   | Abhaengige Optionen aufloesen        |

### Catalog Admin

| #  | Method | Path                                         | Auth  | Beschreibung                    |
|----|--------|----------------------------------------------|-------|---------------------------------|
| 13 | POST   | `/admin/catalog/templates`                   | admin | Neues Template registrieren     |
| 14 | PATCH  | `/admin/catalog/templates/<id>/status`       | admin | Template-Status aendern         |

---

## Orders

| #  | Method | Path                                            | Auth  | Beschreibung                           |
|----|--------|-------------------------------------------------|-------|----------------------------------------|
| 15 | POST   | `/orders`                                       | login | Neue Bestellung erstellen              |
| 16 | GET    | `/orders`                                       | login | Bestellungen auflisten                 |
| 17 | GET    | `/orders/<id>`                                  | login | Bestellung abrufen                     |
| 18 | PATCH  | `/orders/<id>`                                  | login | Bestellung aktualisieren (nur Draft)   |
| 19 | DELETE | `/orders/<id>`                                  | login | Bestellung loeschen (nur Draft)        |
| 20 | GET    | `/orders/<id>/status`                           | login | Bestell-Status mit Item-Status         |
| 21 | POST   | `/orders/<id>/items`                            | login | Item zur Bestellung hinzufuegen        |
| 22 | PATCH  | `/orders/<id>/items/<item_id>`                  | login | Item-Parameter aktualisieren           |
| 23 | DELETE | `/orders/<id>/items/<item_id>`                  | login | Item entfernen                         |
| 24 | PUT    | `/orders/<id>/items/positions`                  | login | Item-Reihenfolge aendern               |
| 25 | POST   | `/orders/<id>/validate`                         | login | Bestellung validieren                  |
| 26 | POST   | `/orders/<id>/submit`                           | login | Bestellung einreichen                  |
| 27 | GET    | `/orders/<id>/export/tofu`                      | login | OpenTofu-Export (alle Items)           |
| 28 | GET    | `/orders/<id>/items/<item_id>/export/tofu`      | login | OpenTofu-Export (einzelnes Item)       |

---

## Context / CMDB

| #  | Method | Path                                 | Auth  | Beschreibung                              |
|----|--------|--------------------------------------|-------|-------------------------------------------|
| 29 | POST   | `/context/resolve`                   | login | Kontext aufloesen und validieren          |
| 30 | GET    | `/context/locations`                 | login | Standorte auflisten                       |
| 31 | GET    | `/context/tenants`                   | login | Erlaubte Tenants des Benutzers            |
| 32 | GET    | `/context/security-zones`            | login | Sicherheitszonen auflisten                |
| 33 | GET    | `/context/networks`                  | login | Netzwerke auflisten (Filter)              |
| 34 | POST   | `/context/check-availability`        | login | Verfuegbarkeit pruefen                    |
| 35 | POST   | `/context/resolve-parameters`        | login | Kontext-abhaengige Parameter aufloesen    |

### CMDB Direct Access

| #  | Method | Path                                 | Auth  | Beschreibung                              |
|----|--------|--------------------------------------|-------|-------------------------------------------|
| 36 | GET    | `/cmdb/locations`                    | login | Alle Standorte                            |
| 37 | GET    | `/cmdb/locations/<id>`               | login | Einzelner Standort                        |
| 38 | GET    | `/cmdb/networks`                     | login | Alle Netzwerke (Filter)                   |
| 39 | GET    | `/cmdb/networks/<id>`                | login | Einzelnes Netzwerk                        |
| 40 | GET    | `/cmdb/tenants`                      | login | Alle Tenants                              |
| 41 | GET    | `/cmdb/tenants/<id>`                 | login | Einzelner Tenant                          |
| 42 | GET    | `/cmdb/security-zones`               | login | Alle Sicherheitszonen                     |
| 43 | GET    | `/cmdb/security-zones/<id>`          | login | Einzelne Sicherheitszone                  |
| 44 | GET    | `/cmdb/health`                       | login | CMDB-Health-Check                         |

### Context Admin

| #  | Method | Path                                           | Auth  | Beschreibung                        |
|----|--------|-------------------------------------------------|-------|-------------------------------------|
| 45 | POST   | `/admin/context/availability-rules`             | admin | Verfuegbarkeitsregel erstellen      |
| 46 | GET    | `/admin/context/availability-rules`             | admin | Verfuegbarkeitsregeln auflisten     |
| 47 | PATCH  | `/admin/context/availability-rules/<id>`        | admin | Verfuegbarkeitsregel aktualisieren  |
| 48 | DELETE | `/admin/context/availability-rules/<id>`        | admin | Verfuegbarkeitsregel loeschen       |
| 49 | POST   | `/admin/context/restrictions`                   | admin | Kontext-Restriction erstellen       |
| 50 | GET    | `/admin/context/restrictions`                   | admin | Kontext-Restrictions auflisten      |
| 51 | DELETE | `/admin/context/restrictions/<id>`              | admin | Kontext-Restriction loeschen        |
| 52 | POST   | `/admin/context/tenant-assignments`             | admin | Tenant-Zuweisung erstellen          |
| 53 | GET    | `/admin/context/tenant-assignments`             | admin | Tenant-Zuweisungen auflisten        |
| 54 | DELETE | `/admin/context/tenant-assignments/<id>`        | admin | Tenant-Zuweisung loeschen           |

---

## Approvals

| #  | Method | Path                                     | Auth         | Beschreibung                      |
|----|--------|------------------------------------------|--------------|-----------------------------------|
| 55 | GET    | `/approvals`                             | login        | Offene Genehmigungen auflisten    |
| 56 | GET    | `/approvals/<id>`                        | login        | Einzelne Genehmigungsanfrage      |
| 57 | POST   | `/approvals/<id>/approve`                | approver     | Genehmigen                        |
| 58 | POST   | `/approvals/<id>/reject`                 | approver     | Ablehnen (Grund erforderlich)     |

### Approval Admin

| #  | Method | Path                                     | Auth  | Beschreibung                        |
|----|--------|------------------------------------------|-------|-------------------------------------|
| 59 | POST   | `/admin/approval-rules`                  | admin | Approval-Regel erstellen            |
| 60 | GET    | `/admin/approval-rules`                  | admin | Approval-Regeln auflisten           |
| 61 | PATCH  | `/admin/approval-rules/<id>`             | admin | Approval-Regel aktualisieren        |
| 62 | DELETE | `/admin/approval-rules/<id>`             | admin | Approval-Regel loeschen             |
| 63 | GET    | `/admin/approval-settings`               | admin | Approval-Einstellungen abrufen      |
| 64 | PUT    | `/admin/approval-settings`               | admin | Approval-Einstellungen aendern      |

---

## Provisioning

| #  | Method | Path                                                    | Auth  | Beschreibung                      |
|----|--------|---------------------------------------------------------|-------|-----------------------------------|
| 65 | POST   | `/webhooks/gitlab`                                      | —     | GitLab-Webhook (Pipeline-Status)  |
| 66 | GET    | `/credentials/<token>`                                  | —     | Einmal-Link Zugangsdaten abrufen  |

### Provisioning Admin

| #  | Method | Path                                                    | Auth  | Beschreibung                      |
|----|--------|---------------------------------------------------------|-------|-----------------------------------|
| 67 | GET    | `/admin/dispatcher/config`                              | admin | Dispatcher-Konfiguration          |
| 68 | GET    | `/admin/orders/<id>/dispatch-log`                       | admin | Dispatch-Log einer Bestellung     |
| 69 | POST   | `/admin/orders/<id>/items/<item_id>/dispatch`           | admin | Einzelnes Item dispatchen         |
| 70 | POST   | `/admin/orders/<id>/items/<item_id>/credentials`        | admin | Credential-Link erstellen         |

---

## Resources

| #  | Method | Path                       | Auth  | Beschreibung                              |
|----|--------|----------------------------|-------|-------------------------------------------|
| 71 | GET    | `/resources`               | login | Provisionierte Ressourcen auflisten       |
| 72 | GET    | `/resources/<item_id>`     | login | Einzelne Ressource abrufen                |

---

## Admin (Dashboard & Audit)

| #  | Method | Path                        | Auth  | Beschreibung                             |
|----|--------|-----------------------------|-------|------------------------------------------|
| 73 | GET    | `/admin/dashboard`          | admin | Admin-Dashboard (Statistiken, Health)    |
| 74 | GET    | `/admin/audit-log`          | admin | Audit-Log abfragen (Filter, Paginierung)|
| 75 | GET    | `/admin/audit-log/export`   | admin | Audit-Log exportieren                    |

---

## Notifications

| #  | Method | Path                          | Auth  | Beschreibung                          |
|----|--------|-------------------------------|-------|---------------------------------------|
| 76 | GET    | `/admin/notifications`        | admin | Alle Benachrichtigungen (Admin)       |
| 77 | GET    | `/notifications`              | login | Eigene Benachrichtigungen             |
