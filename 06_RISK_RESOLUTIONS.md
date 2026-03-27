# Risiko-Mitigationen — Marketplace Portal (MPP)

Dokumentation der technischen Risiken und gewaehlten Loesungsstrategien.

---

## R1: Kein Active Directory in der Entwicklung

**Risiko:** In der Entwicklungsumgebung steht kein AD/LDAP-Server zur Verfuegung. Ohne Auth-Loesung koennen keine rollenbasierten Features entwickelt oder getestet werden.

**Loesung: Auth-Stub**

- Konfigurierbarer Auth-Modus ueber `AUTH_MODE` Environment-Variable
- 4 vordefinierte Stub-Benutzer mit verschiedenen Rollen:
  - `test-requester` (requester)
  - `test-approver` (approver)
  - `test-admin` (admin)
  - `test-multi` (requester + approver)
- Login ohne Passwort (oder mit `stub-password`)
- JWT-Tokens werden identisch zum Produktionsmodus generiert
- **Sicherheitsmechanismus:** Stub-Modus wird bei `ENV=production` mit RuntimeError blockiert
- **Fallback-Secret:** In Stub-Modus wird ein Default-JWT-Secret verwendet, falls keines konfiguriert ist

**Dateien:**
- `app/core/config.py` — Auth-Mode-Validierung
- `app/services/auth_service.py` — Stub-Login und Token-Generierung
- `app/core/auth.py` — Middleware (identisch fuer beide Modi)

---

## R2: Kein CMDB in der Entwicklung

**Risiko:** Die Unternehmens-CMDB ist nicht von ausserhalb des Produktionsnetzwerks erreichbar. Kontext-abhaengige Features (Standort, Tenant, Netzwerk, Sicherheitszone) koennen nicht entwickelt werden.

**Loesung: CMDB-Stub mit YAML-Daten**

- Konfigurierbarer Modus ueber `CMDB_MODE` Environment-Variable
- Statische Testdaten in YAML-Dateien:
  - `stubs/cmdb/locations.yaml` — 3 Standorte (DC-Frankfurt, DC-Munich, DC-Berlin)
  - `stubs/cmdb/networks.yaml` — 6 Netzwerke (je 2 pro Standort)
  - `stubs/cmdb/tenants.yaml` — 3 Mandanten
  - `stubs/cmdb/security_zones.yaml` — 3 Sicherheitszonen (prod, staging, dev)
- CmdbStubClient implementiert dasselbe Interface wie der zukuenftige Live-Client
- Alle CMDB-API-Endpoints (`/api/v1/cmdb/*`) funktionieren identisch

**Dateien:**
- `app/data/clients/cmdb_client.py` — CmdbStubClient
- `stubs/cmdb/*.yaml` — Testdaten

---

## R3: Kein GitLab in der Entwicklung

**Risiko:** Die GitLab-Instanz fuer Provisioning-Pipelines ist nicht verfuegbar. Der gesamte Provisioning-Flow kann nicht end-to-end getestet werden.

**Loesung: GitLab-Mock**

- Separate Flask-App (`stubs/gitlab_mock.py`) simuliert GitLab-Pipeline-API
- Unterstuetzte Endpunkte:
  - Pipeline-Triggering (POST)
  - Pipeline-Status-Abfrage (GET)
  - Webhook-Simulation mit konfigurierbarer Verzoegerung
- Pipelines durchlaufen simulierte Status: `pending` → `running` → `success`/`failed`
- GitLab-Client (`app/data/clients/gitlab_client.py`) kann gegen Mock oder echtes GitLab sprechen

**Dateien:**
- `stubs/gitlab_mock.py` — Mock-Server
- `app/data/clients/gitlab_client.py` — Client (identisch fuer Mock und Produktion)

---

## R4: Dynamische Parameter-Formulare

**Risiko:** Service-Templates haben unterschiedliche Parameter-Sets mit verschiedenen Typen, Constraints und Abhaengigkeiten. Ein statisches Formular ist nicht moeglich.

**Loesung: ParameterForm mit Schema-basiertem Rendering**

- Template-Parameter sind in JSONB als Array von Definitionen gespeichert
- Jede Definition enthaelt: `key`, `type`, `label`, `constraints`, `depends_on`, `group`, `display_order`
- Frontend rendert dynamisch die passende Feld-Komponente pro Typ:
  - `string` → StringField
  - `integer` → IntegerField
  - `boolean` → BooleanField
  - `enum` → EnumField
  - `size_bytes` → SizeBytesField
- **depends_on-Evaluation:** Felder koennen von anderen Feldern abhaengen (z.B. Betriebssystem beeinflusst verfuegbare Disk-Typen)
- **Cross-Parameter-Rules:** Ausdruecke wie `ram_gb >= cpu_cores * 2` werden bei Validierung evaluiert

**Dateien:**
- `frontend/src/components/ParameterForm/` — alle Feld-Komponenten
- `app/services/catalog_service.py` — Backend-Validierung
- `app/api/v1/catalog.py` — Resolve-Options-Endpoint

---

## R5: Multi-Service-Bestellungen

**Risiko:** Benutzer bestellen haeufig mehrere zusammenhaengende Services gleichzeitig (z.B. VM + Datenbank). Einzelbestellungen wuerden den Workflow verkomplizieren.

**Loesung: OrderItem-Modell mit Per-Item-Validierung**

- Eine Order kann mehrere OrderItems enthalten
- Jedes Item referenziert ein Template (slug + version) und hat eigene Parameter
- Items koennen einzeln hinzugefuegt, aktualisiert und entfernt werden
- Validierung erfolgt pro Item (validation_state: unchecked/valid/invalid)
- Order-Validierung validiert alle Items auf einmal
- Reorder-Endpoint erlaubt Neuordnung der Items
- Pro Item wird separat provisioniert (eigene Pipeline, eigener DispatchLog)

**Dateien:**
- `app/data/db/models/order.py` — OrderModel + OrderItemModel
- `app/services/order_service.py` — Item-Management und Validierung

---

## R6: Kontext-abhaengige Bestellungen

**Risiko:** Services muessen in einem bestimmten Kontext (Standort, Tenant, Sicherheitszone, Netzwerk) provisioniert werden. Nicht jeder Service ist an jedem Standort verfuegbar.

**Loesung: CMDB + AvailabilityRules + ContextRestrictions**

- **AvailabilityRules:** Definieren, ob ein Template in einem bestimmten Kontext verfuegbar ist (allow/deny)
- **ContextRestrictions:** Aendern Parameter-Constraints basierend auf dem Kontext (z.B. max RAM in Dev-Zone = 32 GB)
- **UserTenantAssignments:** Schraenken ein, welche Tenants ein Benutzer waehlen darf
- **Resolution-Flow:**
  1. Benutzer waehlt Kontext (ContextSelector im Frontend)
  2. Backend validiert gegen CMDB und Tenant-Zuweisungen
  3. AvailabilityRules bestimmen sichtbare Templates
  4. ContextRestrictions modifizieren Parameter-Constraints
  5. Kontext wird in der Order gespeichert (JSONB)

**Dateien:**
- `app/data/db/models/context_rule.py` — AvailabilityRule, ContextRestriction, TenantAssignment
- `app/services/context_service.py` — Kontextaufloesung und Validierung
- `frontend/src/components/orders/ContextSelector.tsx` — UI-Komponente
