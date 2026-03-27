---
name: Marketplace Portal - Projektkontext
description: IT-Services Marketplace für automatisierte Provisionierung (VMs, DBs, Container) mit Rollen, Umsystemen und Feature-Gruppen
type: project
---

Wir bauen ein Marketplace Portal für automatisierte IT-Services (VMs, Datenbanken, Container).

**Rollen:** requester, approver, admin

**Umsysteme:** Active Directory, IPAM, Datenbanken, Backup, Gitlab, OpenTofu

**Schnittstelle zu Feature 4.1:** Nach Approval löst die Bestellung einen OpenTofu Job-Dispatcher aus. Das ist die explizite Schnittstelle zwischen Feature 3.3/3.4 und Feature 4.1.

**SSE-Anforderung:** Bestellstatus-Updates müssen über Server-Sent Events (SSE) ans Frontend geliefert werden — kein Polling.

**MVP Feature-Gruppen (bekannt):**
- Gruppe 3 "Bestellprozess & Workflow":
  - 3.1 Order CRUD (Draft-basiert, Multi-Service)
  - 3.2 Order Validation
  - 3.3 Order Submit + Status-Machine
  - 3.4 JSON Export für GitLab / OpenTofu
  - 3.5 Approval-Workflow (als Feature-Gruppe 8 eigenständig spezifiziert)
  - Spec: docs/specs/order-lifecycle.md (ERSETZT order-process.md)
  - ACHTUNG: order-process.md ist veraltet und NICHT mehr gültig
- Gruppe 8 "Approval-Workflow":
  - 8.1 Approval-Regeln & Schwellwerte
  - 8.2 Approval-Workflow (1-stufig)
  - 8.3 Automatische Ablehnung bei Timeout
  - Spec: docs/specs/approval-workflow.md
- Gruppe 4 "Provisioning-Engine":
  - 4.1 OpenTofu Job-Dispatcher
  - 4.2 Provisioning-Status-Sync
  - 4.3 AD-Integration: Computer-Objekt
  - 4.4 IPAM-Integration: IP-Reservierung
  - 4.5 Datenbank-Provisioning
  - 4.6 Fehlerbehandlung & Rollback
  - 4.7 Idempotenz-Schutz
  - Spec: docs/specs/provisioning-engine.md

**Orchestrierungsreihenfolge (VM/Container):** IPAM → AD → Tofu Apply → Status-Sync → (Credentials nur DB)
**Orchestrierungsreihenfolge (Datenbank):** IPAM (optional) → Tofu Apply → Status-Sync → Credential-Delivery

**MVP Feature-Gruppen (bekannt, Gruppe 2):**
- Gruppe 2 "Service Catalog & Template-Modell":
  - 2.1 Service Catalog & Template-Modell
  - Spec: docs/specs/service-catalog.md

**Datenmodell-Kernkonzepte (Feature 2.1):**
- ServiceTemplate: id, slug, version (SemVer), type (Enum), parameters[], status (active/deprecated/disabled), tofu_module_source
- ParameterDefinition: key, label, type (Enum: string/integer/float/boolean/enum/range_integer/range_float/size_bytes), required, tofu_variable_name, depends_on[], affects_options_of[]
- Templates sind nach Erstellung unveränderlich (neue Version = neuer Record)
- JSON-Export: tofu_variable_name → OpenTofu-Variable (nur Parameter mit erfüllten depends_on)
- Endpoint 41 löst dynamische Optionen auf (z.B. OS bestimmt verfügbare Disk-Typen)
- Endpoint 43 validiert Order-Parameter gegen Template (immer HTTP 200, Violations im Body)

**MVP Feature-Gruppen (bekannt, Gruppe 1):**
- Gruppe 1 "Identity & Access":
  - 1.1 User Authentication (SSO/LDAP gegen AD, JWT, Logout)
  - 1.2 Rollen & Berechtigungen (requester/approver/admin aus AD-Gruppen)
  - 1.3 Service-Accounts für Umsysteme (AD, IPAM, GitLab, OpenTofu)
  - Spec: docs/specs/identity-access.md

**Nummerierungskonvention:** Jede Feature-Gruppe hat eine EIGENE, neu beginnende Nummerierung (REQ-01 ff., VAL-01 ff., EC-01 ff., Endpoint 1 ff.). KEINE gruppenübergreifende Durchnummerierung.

**Nummerierungsstände je Gruppe:**
- Gruppe 1 (identity-access.md): REQ-01..43, VAL-01..16, EC-01..29, Endpoints 1..11
- Gruppe 2 (service-catalog.md): REQ-100..125 (historisch, kein Neustart), VAL-47..70, EC-66..80, Endpoints 37..44
- Gruppe 3 (order-lifecycle.md): REQ-126..191 (historisch), VAL-71..107, EC-81..128, Endpoints 45..67
- Gruppe 4 (provisioning-engine.md): REQ-44..103 (historisch), VAL-23..46, EC-30..72, Endpoints 18..34 (+ Rollback: 35, außerhalb Originalumfang)
- Gruppen 5–7 (resources-notifications-admin.md): REQ-01..67, VAL-01..29, EC-01..30, Endpoints 1..16 (Neustart gemäß Konvention)
- Gruppe 8 (approval-workflow.md): REQ-01..43, VAL-01..22, EC-01..20, Endpoints 1..14 (Neustart gemäß Konvention)

**Hinweis:** Die historischen Nummerierungen in Gruppe 2/3/4 sind nicht konsistent mit dem Neu-Start-Modell, wurden aber so festgelegt und sollen nicht nachträglich geändert werden.

**Bekannte Schnittstellenklärung (Gruppen 5–7):** CredentialToken-Lifecycle (Erzeugung, Hash-Speicherung, Admin-Re-Issue) liegt in Feature 6.2 (resources-notifications-admin.md). Der Abruf-Endpoint (GET /api/v1/credentials/{token}) verbleibt als Endpoint 31 in provisioning-engine.md. Feature 4.5 REQ-80 ist der Trigger für die Token-Erzeugung.

**Why:** MVP-Spezifikationen für Entwicklerteam, das ohne Rückfragen implementieren können soll.

**How to apply:** Neue Feature-Gruppen starten die Nummerierung bei REQ-01, VAL-01, EC-01, Endpoint 1. Innerhalb einer Gruppe fortlaufend nummerieren.

**Wichtige Schnittstellenänderung (order-lifecycle.md → provisioning-engine.md):** Das Dispatch-Event-Format hat sich geändert. REQ-44 und REQ-46 in provisioning-engine.md müssen aktualisiert werden: `service_id` → `template_slug` + `template_version`, `order_item_id` kommt neu hinzu.

**Approval-Workflow: Entscheidung zum Status-Flow (approval-workflow.md):** Bedingter Zweig nach `submitted` (Modell A). Orders ohne Approval-Regel laufen direkt zu `provisioning`. Orders mit mindestens einer greifenden Regel gehen zu `pending_approval`. Neue Status: `pending_approval`, `approved` (kurzlebig), `rejected` (Terminal). Feature 4.1 löst Dispatch NACH `approved` aus (nicht mehr nur nach `submitted`).

**Offene Nacharbeiten aus approval-workflow.md:**
- order-lifecycle.md: OrderStatus-Enum, REQ-154, REQ-157, Endpoints 46/47/56/57, Statusmaschinen-Diagramm
- service-catalog.md: ServiceTemplate um `estimated_cost_eur_per_month` und `approval_always_required` erweitern

**Querschnittsthemen (cross-cutting-concerns.md, v1.0, erstellt 2026-03-26):**
- Spec: docs/specs/cross-cutting-concerns.md
- Nummerierungsraum: REQ-CCC-01..43, VAL-CCC-01..04, EC-CCC-01..13 (Präfix CCC, kein Konflikt mit Feature-Gruppen)
- Enthält: Idempotenz-Patterns (Order Submit, Approval CAS, Provisioning Dispatch, E-Mail-Dedup), Error-Handling (Response-Format, HTTP-Codes, Retry-Backoff, Circuit Breaker, Logging), Permissions-Matrix (alle 86 Endpoints × 3 Rollen)
- Neuer Admin-Endpoint: GET /api/v1/admin/circuit-breaker/status (Endpoint Nr. 85 systemweit)
- REQ-CCC-16 ergänzt 60s-Dedup-Fenster für E-Mail-Notifications (war in resources-notifications-admin.md offen)

**Entwicklungs- und Test-Infrastruktur (development-testing.md, v1.0, erstellt 2026-03-26):**
- Spec: docs/specs/development-testing.md
- Gruppe 9: Auth-Stub (9.1), GitLab-Mock (9.2), CMDB-Stub (9.3), Test-Fixtures (9.4)
- Nummerierungsstand Gruppe 9: REQ-01..50, VAL-01..17, EC-01..30, Endpoints 1..16
- Aktivierung: AUTH_MODE=stub, CMDB_MODE=stub, GitLab-Mock separater Prozess (Port 8929)
- Produktions-Safeguard: ENV=production + Stub-Mode → Start-Abbruch (FATAL)
- Fixture-IDs: Präfix `fix-` obligatorisch, stabile fixierte IDs
- Stub-User: test-requester, test-approver, test-admin, test-multi (alle mit Passwort `stub-password` oder ohne Passwort)
- GitLab-Mock simuliert: pending → running → success/failed, mit konfigurierbaren Delays und Fehlerrate
- CMDB-Stub: 3 Standorte (Berlin, Munich, Hamburg), 7 Netze, 2 Mandanten, 3 Sicherheitszonen

**Kontextabhängige Bestellkonfiguration (context-dependent-ordering.md, v1.0, erstellt 2026-03-26):**
- Spec: docs/specs/context-dependent-ordering.md
- Gruppe 10: Bestellkontext-Modell (10.1), Kontextabhängige Parameter-Einschränkungen (10.2), Kontextabhängige Service-Verfügbarkeit (10.3)
- Nummerierungsstand Gruppe 10: REQ-01..35, VAL-01..29, EC-01..22, Endpoints 1..21
- Kernkonzepte: OrderContext (location, tenant, security_zone, network), ContextRestriction (Regeln für Parameter-Limits), AvailabilityRule (deny/allow Whitelist-Logik)
- Kontext-Auswahlschritt vor Service-Auswahl (Schritt 0)
- Default-Allow-Modell für Verfügbarkeit; allow-Regeln aktivieren Whitelist-Semantik pro Template
- Prioritätsauflösung: limit_max/min → restriktivster Wert; filter_options → Schnittmenge; set_value/disable → höchste Priority (disable beats set_value)
- Pseudoparameter `__context_security_zone` für Tenant-Sicherheitsbereich-Sperren (Feature 10.2 REQ-19)
- Erweiterung von Endpoint 37 (service-catalog.md) um Kontext-Parameter (location_id, tenant_id, security_zone_id, hide_unavailable)
- Order speichert OrderContext unveränderlich nach Submit; Änderung im Draft invalidiert alle Order-Items

**OrderItemGroup, Quantity & Per-Instance-Parameter (order-groups-quantity.md, v1.0, erstellt 2026-03-26):**
- Spec: docs/specs/order-groups-quantity.md
- Gruppe 11: OrderItemGroup (11.1), Quantity-Skalierung (11.2), Per-Instance-Parameter (11.3)
- Nummerierungsstand Gruppe 11: REQ-01..49, VAL-01..31, EC-01..38, Endpoints 1..17
- Kernkonzepte: OrderItemGroup (logische UI-Einheit, nicht atomarer Dispatch-Block), quantity (1–50, N Dispatch-Events beim Submit), per_instance (false/true/"auto" am ParameterDefinition)
- Rollback-Entscheidung: Fehlschlag eines Items rollt nur dieses Item zurück, nicht die gesamte Gruppe
- Neuer Item-Status: `partial_failure` (einige Instanzen done, einige failed)
- Auto-Generierung: hostname_sequence (Prefix + laufende Nr., atomarer Batch) und ipam_reservation (N IPs via IPAM, Batch-Rollback bei Teilfehler)
- Dispatch-Event-Format erweitert um: instance_id, instance_index, group_id, group_name
- Kostenkalkulation für Approval: item_cost = estimated_cost_eur_per_month × quantity
- Erweiterungen: ParameterDefinition um per_instance, OrderItem um group_id/quantity/instance_parameters/generated_parameters, Order-Response um groups[]/ungrouped_items
- Rückwärtskompatibel: Items ohne group_id und quantity=1 verhalten sich wie bisher
