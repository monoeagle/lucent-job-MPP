# Business Logic — Marketplace Portal (MPP)

## Services-Uebersicht

| Service                | Modul                           | Verantwortung                                   |
|------------------------|---------------------------------|-------------------------------------------------|
| AuthService            | `services/auth_service.py`      | Login, JWT-Token-Erzeugung und -Verifikation    |
| CatalogService         | `services/catalog_service.py`   | Parameter-Validierung, Dependency-Resolution, Diff |
| OrderService           | `services/order_service.py`     | Order-Lifecycle, Item-Management, Tofu-Export   |
| ContextService         | `services/context_service.py`   | CMDB-Kontextaufloesung, Tenant-Pruefung         |
| ProvisioningService    | `services/provisioning_service.py` | Pipeline-Dispatch, Status-Sync, Webhooks     |
| ApprovalService        | `services/approval_service.py`  | Regel-Evaluation, Genehmigung/Ablehnung         |
| AuditService           | `services/audit_service.py`     | Audit-Log-Abfrage und -Export                   |
| NotificationService    | `services/notification_service.py` | Benachrichtigungserzeugung und -abfrage      |
| CredentialService      | `services/credential_service.py`| Einmal-Links fuer Zugangsdaten                  |
| TemplateValidator      | `services/template_validator.py`| Validierung neuer Templates bei Registrierung   |

---

## AuthService

**Operationen:**
- `login(username, password)` — Authentifiziert gegen Stub oder LDAP; erzeugt JWT-Token
- `verify_token(token)` — Dekodiert JWT und gibt User-Objekt zurueck
- `get_stub_users()` — Listet verfuegbare Stub-Benutzer auf

**Auth-Modi:**
- `stub`: 4 Dummy-Benutzer, kein Passwort noetig, JWT mit konfigurierbarer TTL
- `ldap`: Nicht implementiert (Platzhalter fuer Produktion)

**Sicherheitsregel:** Stub-Modus darf nicht in Produktion (`ENV=production`) aktiv sein.

---

## CatalogService

**Operationen:**
- `validate_parameters(definitions, values, cross_rules)` — Prueft einzelne Parameter und Cross-Parameter-Regeln
- `resolve_dependency_state(depends_on, current_values)` — Berechnet den Zustand abhaengiger Parameter
- `compute_diff(from_template, to_template)` — Vergleicht zwei Template-Versionen

**Parameter-Validierung:**
1. Pflichtfelder pruefen
2. Typspezifische Constraints (min/max, options, regex)
3. Cross-Parameter-Rules evaluieren (z.B. `ram_gb >= cpu_cores * 2`)

---

## OrderService

**Operationen:**
- `create_order(requester_id, title, ...)` — Neue Bestellung im Status `draft`
- `add_item(order_id, template_slug, version, parameters)` — Service zur Bestellung hinzufuegen
- `update_item(order_id, item_id, parameters)` — Item-Parameter aktualisieren
- `remove_item(order_id, item_id)` — Item entfernen
- `validate_order(order_id)` — Alle Items validieren, Status auf `validated` oder `draft`
- `submit_order(order_id)` — Bestellung einreichen (Transitions: validated → submitted)
- `export_tofu(order_id)` — OpenTofu-JSON-Export fuer alle Items

---

## Order-Lifecycle

```
draft ──→ validated ──→ submitted ──→ pending_approval ──→ approved ──→ provisioning ──→ done
  ↑           │                               │                              │
  └───────────┘                               ↓                              ↓
        (Re-Edit)                         rejected                        failed
```

### Status-Transitions

| Von                | Nach               | Ausloeser                           |
|--------------------|--------------------|-------------------------------------|
| `draft`            | `validated`        | Alle Items validiert                |
| `validated`        | `submitted`        | Benutzer reicht ein                 |
| `validated`        | `draft`            | Benutzer bearbeitet erneut          |
| `submitted`        | `pending_approval` | Approval-Regeln greifen             |
| `submitted`        | `provisioning`     | Keine Approval noetig, Dispatch     |
| `pending_approval` | `approved`         | Approver genehmigt                  |
| `pending_approval` | `rejected`         | Approver lehnt ab                   |
| `approved`         | `provisioning`     | Admin dispatcht manuell             |
| `provisioning`     | `done`             | Alle Pipelines erfolgreich          |
| `provisioning`     | `failed`           | Mindestens eine Pipeline fehlgeschlagen |

**Terminal-Status:** `done`, `failed`, `rejected` — keine weiteren Transitions moeglich.
**Editierbar:** Nur im Status `draft`.

---

## ApprovalService

**Operationen:**
- `evaluate_rules(order)` — Prueft alle aktiven ApprovalRules gegen die Bestellung
- `create_approval_request(order_id, matched_rules)` — Erzeugt ApprovalRequest mit Deadline
- `approve(request_id, decided_by, reason)` — Genehmigt Anfrage
- `reject(request_id, decided_by, reason)` — Lehnt Anfrage ab (Grund erforderlich)

### Regel-Evaluation

Beim Submit einer Bestellung werden alle aktiven ApprovalRules evaluiert:

1. **cost_threshold:** Geschaetzte Gesamtkosten > `threshold_eur`
2. **service_type:** Order enthaelt Items mit `service_type_slug`
3. **always:** Template hat `approval_always_required = True`

Wenn mindestens eine Regel greift → Status wechselt zu `pending_approval`.

**Self-Approval-Schutz:** Konfigurierbar ueber `APPROVAL_ALLOW_SELF_APPROVAL`. Default: verboten.

---

## ContextService

**Operationen:**
- `resolve_context(location_id, tenant_id, security_zone_id, network_id, user_id)` — Loeost Kontext aus CMDB auf und validiert
- `get_allowed_tenants(user_id)` — Gibt dem Benutzer zugewiesene Tenants zurueck

### Context-Resolution-Flow

1. Benutzer waehlt Location, Tenant, Security Zone (optional: Network)
2. System prueft: Existieren die Entitaeten in der CMDB?
3. System prueft: Ist der Benutzer dem Tenant zugewiesen?
4. System prueft: Ist das Network kompatibel mit Location + Security Zone?
5. Ergebnis: Aufgeloester Kontext mit vollstaendigen CMDB-Daten

---

## ProvisioningService

**Operationen:**
- `dispatch_order(order_id)` — Dispatcht alle Items einer Bestellung
- `dispatch_item(order_id, item_id)` — Dispatcht einzelnes Item
- `handle_webhook(pipeline_id, status)` — Verarbeitet GitLab-Webhook-Callbacks

### Dispatch-Flow

1. Fuer jedes OrderItem wird eine GitLab-Pipeline getriggert
2. Pipeline-Parameter: Template-Slug, Version, konfigurierte Parameter
3. DispatchLog wird erstellt (Status: `dispatched`)
4. GitLab-Webhook meldet Pipeline-Ergebnis zurueck
5. DispatchLog und OrderItem werden aktualisiert
