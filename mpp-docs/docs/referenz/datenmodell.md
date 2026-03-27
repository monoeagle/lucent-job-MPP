# Datenmodell

PostgreSQL mit SQLAlchemy 2.0 ORM. 9 Alembic-Migrationen. JSONB fuer flexible Parameter-Speicherung.

---

## Tabellen-Uebersicht

| Tabelle                    | Beschreibung                                    |
|----------------------------|-------------------------------------------------|
| `service_templates`        | Servicekatalog-Eintraege mit Parameterdefinitionen |
| `orders`                   | Bestellungen (Kopfdaten)                        |
| `order_items`              | Einzelne Services innerhalb einer Bestellung    |
| `approval_rules`           | Regeln fuer automatische Genehmigungspflicht    |
| `approval_requests`        | Konkrete Genehmigungsanfragen pro Bestellung    |
| `availability_rules`       | Verfuegbarkeitsregeln pro Template/Kontext      |
| `context_restrictions`     | Kontext-abhaengige Parameterbeschraenkungen     |
| `user_tenant_assignments`  | Zuordnung Benutzer zu Mandanten                 |
| `dispatch_logs`            | Protokoll der Provisioning-Aufrufe              |
| `audit_logs`               | Audit-Trail aller relevanten Aktionen           |
| `notifications`            | E-Mail-Benachrichtigungen (Queue)               |
| `credential_links`         | Einmal-Links fuer Zugangsdaten-Abruf            |

---

## Detailmodelle

### service_templates

| Spalte                        | Typ              | Beschreibung                              |
|-------------------------------|------------------|-------------------------------------------|
| `id`                          | String(36) PK    | UUID                                      |
| `slug`                        | String(64)       | Technischer Identifier                    |
| `version`                     | String(32)       | Semantische Version                       |
| `type`                        | String(32)       | Servicetyp (vm, database, container)      |
| `display_name`                | String(100)      | Anzeigename                               |
| `description`                 | Text             | Beschreibung                              |
| `category`                    | String(64)       | Kategorie (Compute, Database, ...)        |
| `icon_identifier`             | String(100)      | Icon-Referenz                             |
| `tofu_module_source`          | String(500)      | Git-URL des OpenTofu-Moduls               |
| `parameters`                  | JSONB            | Array der Parameterdefinitionen            |
| `cross_parameter_rules`       | JSONB            | Cross-Parameter-Validierungsregeln        |
| `status`                      | String(20)       | active / deprecated / disabled            |
| `estimated_cost_eur_per_month`| Numeric(10,2)    | Geschaetzte Monatskosten                  |
| `approval_always_required`    | Boolean          | Erzwingt immer Genehmigung                |
| `metadata`                    | JSONB            | Zusaetzliche Metadaten                    |
| `created_at`                  | DateTime(tz)     | Erstellungszeitpunkt                      |
| `deprecated_at`               | DateTime(tz)     | Zeitpunkt der Deprecation                 |
| `deprecated_by`               | String(36)       | ID des Nachfolger-Templates               |

**Unique-Constraint:** `(slug, version)`
**Indices:** `slug`, `type`, `category`, `status`, `(slug, status)`

### orders

| Spalte            | Typ           | Beschreibung                      |
|-------------------|---------------|-----------------------------------|
| `id`              | String(36) PK | UUID                              |
| `order_number`    | String(20) UQ | Lesbare Bestellnummer             |
| `requester_id`    | String(100)   | Benutzername des Bestellers       |
| `status`          | String(20)    | Aktueller Status (siehe Lifecycle)|
| `title`           | String(100)   | Titel der Bestellung              |
| `business_reason` | Text          | Geschaeftliche Begruendung        |
| `desired_date`    | String(10)    | Wunsch-Bereitstellungsdatum       |
| `context`         | JSONB         | Kontext (Location, Tenant, ...)   |
| `metadata`        | JSONB         | Zusaetzliche Metadaten            |
| `created_at`      | DateTime(tz)  | Erstellungszeitpunkt              |
| `updated_at`      | DateTime(tz)  | Letzte Aenderung                  |
| `submitted_at`    | DateTime(tz)  | Zeitpunkt der Einreichung         |

### order_items

| Spalte               | Typ           | Beschreibung                       |
|----------------------|---------------|------------------------------------|
| `id`                 | String(36) PK | UUID                               |
| `order_id`           | String(36) FK | Referenz auf orders.id             |
| `template_slug`      | String(64)    | Slug des Service-Templates         |
| `template_version`   | String(32)    | Version des Templates              |
| `display_name`       | String(100)   | Anzeigename des Items              |
| `parameters`         | JSONB         | Konfigurierte Parameter            |
| `position`           | Integer       | Reihenfolge innerhalb der Order    |
| `validation_state`   | String(20)    | unchecked / valid / invalid        |
| `validation_errors`  | JSONB         | Array der Validierungsfehler       |
| `provisioning_status`| String(20)    | not_started / running / done / failed |
| `job_id`             | String(100)   | GitLab-Pipeline-Job-ID             |
| `created_at`         | DateTime(tz)  | Erstellungszeitpunkt               |
| `updated_at`         | DateTime(tz)  | Letzte Aenderung                   |

**Beziehung:** `order_items.order_id → orders.id` (CASCADE DELETE)

### approval_rules

| Spalte              | Typ           | Beschreibung                          |
|---------------------|---------------|---------------------------------------|
| `id`                | String(36) PK | UUID                                  |
| `name`              | String(100)   | Regelname                             |
| `rule_type`         | String(20)    | cost_threshold / service_type / always|
| `threshold_eur`     | Numeric(10,2) | Kostenschwelle (bei cost_threshold)   |
| `service_type_slug` | String(64)    | Template-Slug (bei service_type)      |
| `is_active`         | Boolean       | Regel aktiv?                          |
| `created_at`        | DateTime(tz)  | Erstellungszeitpunkt                  |
| `updated_at`        | DateTime(tz)  | Letzte Aenderung                      |

### approval_requests

| Spalte              | Typ           | Beschreibung                          |
|---------------------|---------------|---------------------------------------|
| `id`                | String(36) PK | UUID                                  |
| `order_id`          | String(36) FK | Referenz auf orders.id                |
| `status`            | String(20)    | pending / approved / rejected         |
| `approval_rule_ids` | JSONB         | IDs der ausloesenden Regeln           |
| `requested_at`      | DateTime(tz)  | Zeitpunkt der Anfrage                 |
| `deadline_at`       | DateTime(tz)  | Deadline fuer Entscheidung            |
| `decided_by`        | String(100)   | Benutzername des Entscheiders         |
| `decided_at`        | DateTime(tz)  | Zeitpunkt der Entscheidung            |
| `decision_reason`   | Text          | Begruendung                           |

**Unique-Constraint:** `(order_id)` — max. 1 Request pro Order

### availability_rules

| Spalte          | Typ           | Beschreibung                          |
|-----------------|---------------|---------------------------------------|
| `id`            | String(36) PK | UUID                                  |
| `name`          | String(100)   | Regelname                             |
| `template_slug` | String(64)    | Betroffenes Template                  |
| `rule_type`     | String(10)    | allow / deny                          |
| `conditions`    | JSONB         | Kontext-Bedingungen                   |
| `priority`      | Integer       | Prioritaet (hoeher = wichtiger)       |
| `is_active`     | Boolean       | Regel aktiv?                          |
| `created_at`    | DateTime(tz)  | Erstellungszeitpunkt                  |
| `updated_at`    | DateTime(tz)  | Letzte Aenderung                      |

### context_restrictions

| Spalte             | Typ           | Beschreibung                       |
|--------------------|---------------|------------------------------------|
| `id`               | String(36) PK | UUID                               |
| `name`             | String(100)   | Regelname                          |
| `template_slug`    | String(64)    | Betroffenes Template (optional)    |
| `parameter_key`    | String(64)    | Betroffener Parameter              |
| `restriction_type` | String(20)    | Typ der Einschraenkung             |
| `conditions`       | JSONB         | Kontext-Bedingungen                |
| `effect`           | JSONB         | Auswirkung (z.B. max-Wert-Aenderung)|
| `priority`         | Integer       | Prioritaet                         |
| `is_active`        | Boolean       | Regel aktiv?                       |
| `created_at`       | DateTime(tz)  | Erstellungszeitpunkt               |
| `updated_at`       | DateTime(tz)  | Letzte Aenderung                   |

### user_tenant_assignments

| Spalte      | Typ           | Beschreibung                          |
|-------------|---------------|---------------------------------------|
| `id`        | String(36) PK | UUID                                  |
| `user_id`   | String(100)   | Benutzername                          |
| `tenant_id` | String(64)    | Mandanten-ID                          |
| `created_at`| DateTime(tz)  | Erstellungszeitpunkt                  |

**Unique-Constraint:** `(user_id, tenant_id)`

### dispatch_logs

| Spalte            | Typ           | Beschreibung                      |
|-------------------|---------------|-----------------------------------|
| `id`              | String(36) PK | UUID                              |
| `order_id`        | String(36)    | Bestellungs-ID                    |
| `order_item_id`   | String(36)    | Item-ID                           |
| `job_id`          | String(100)   | GitLab-Pipeline-Job-ID            |
| `dispatch_method` | String(20)    | gitlab_pipeline                   |
| `dispatched_at`   | DateTime(tz)  | Zeitpunkt des Dispatch            |
| `attempt_count`   | Integer       | Versuch-Nummer                    |
| `status`          | String(20)    | dispatched / success / failed     |
| `error_message`   | Text          | Fehlermeldung (bei Fehler)        |

### audit_logs

| Spalte        | Typ           | Beschreibung                      |
|---------------|---------------|-----------------------------------|
| `id`          | String(36) PK | UUID                              |
| `timestamp`   | DateTime(tz)  | Zeitstempel                       |
| `actor_id`    | String(100)   | Ausfuehrender Benutzer            |
| `actor_type`  | String(20)    | user / system                     |
| `action`      | String(50)    | Aktion (z.B. order.created)       |
| `entity_type` | String(50)    | Entitaetstyp                      |
| `entity_id`   | String(36)    | Entitaets-ID                      |
| `details`     | JSONB         | Zusaetzliche Details              |
| `request_id`  | String(36)    | Request-Correlation-ID            |

### notifications

| Spalte            | Typ           | Beschreibung                      |
|-------------------|---------------|-----------------------------------|
| `id`              | String(36) PK | UUID                              |
| `event_type`      | String(50)    | Ereignistyp                       |
| `recipient_email` | String(200)   | Empfaenger-E-Mail                 |
| `recipient_id`    | String(100)   | Empfaenger-Benutzer-ID            |
| `subject`         | String(200)   | Betreff                           |
| `body`            | Text          | Nachrichtentext                   |
| `status`          | String(20)    | pending / sent / failed           |
| `attempts`        | Integer       | Anzahl Sendeversuche              |
| `created_at`      | DateTime(tz)  | Erstellungszeitpunkt              |
| `sent_at`         | DateTime(tz)  | Sendezeitpunkt                    |
| `error_message`   | Text          | Fehlermeldung                     |

### credential_links

| Spalte          | Typ           | Beschreibung                      |
|-----------------|---------------|-----------------------------------|
| `id`            | String(36) PK | UUID                              |
| `order_item_id` | String(36)    | Zugehoeriges OrderItem            |
| `token_hash`    | String(64) UQ | SHA-256-Hash des Tokens           |
| `credentials`   | JSONB         | Verschluesselte Zugangsdaten      |
| `expires_at`    | DateTime(tz)  | Ablaufzeitpunkt                   |
| `accessed_at`   | DateTime(tz)  | Letzter Zugriff                   |
| `is_consumed`   | Boolean       | Bereits abgerufen?                |

---

## Beziehungen

```
service_templates
    ↑ (slug + version)
order_items ──→ orders (FK: order_id, CASCADE)
    ↑
dispatch_logs (order_item_id)
credential_links (order_item_id)

approval_requests ──→ orders (FK: order_id)

availability_rules ──→ service_templates (template_slug, logisch)
context_restrictions ──→ service_templates (template_slug, logisch)
```

---

## JSONB-Felder (wichtigste)

| Tabelle            | Feld                   | Inhalt                                           |
|--------------------|------------------------|--------------------------------------------------|
| service_templates  | `parameters`           | Array von ParameterDefinitions (key, type, constraints, depends_on) |
| service_templates  | `cross_parameter_rules`| Regeln fuer parameteruebergreifende Validierung  |
| orders             | `context`              | Location, Tenant, Security Zone, Network         |
| order_items        | `parameters`           | Vom Benutzer konfigurierte Parameter-Werte       |
| order_items        | `validation_errors`    | Array der Validierungsfehler                     |
| approval_requests  | `approval_rule_ids`    | IDs der ausloesenden ApprovalRules               |
| availability_rules | `conditions`           | Kontext-Bedingungen fuer Verfuegbarkeit          |
| context_restrictions| `conditions` / `effect`| Bedingungen und Auswirkungen                    |
| audit_logs         | `details`              | Kontextinformationen zur Aktion                  |
| credential_links   | `credentials`          | Zugangsdaten (verschluesselt)                    |
