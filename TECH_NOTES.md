# Technische Notizen — Marketplace Portal (MPP)

Gesammelte Erkenntnisse und Designentscheidungen aus der Entwicklung.

---

## SQLAlchemy JSONB fuer flexible Parameter-Speicherung

### Problem
Service-Templates haben unterschiedliche Parameter-Sets. Eine relationale Modellierung (eine Tabelle pro Parameter-Typ) waere extrem aufwendig und unflexibel bei Aenderungen.

### Loesung
JSONB-Spalten in PostgreSQL mit SQLAlchemy:

```python
from sqlalchemy.dialects.postgresql import JSONB

parameters = Column(JSONB, nullable=False, default=list)
cross_parameter_rules = Column(JSONB, nullable=False, default=list)
```

### Vorteile
- Schema-Evolution ohne Migrationen (neue Parameter-Typen = neuer JSON-Key)
- PostgreSQL indiziert JSONB und ermoeglicht performante Queries
- Python-Dicts und -Listen werden transparent serialisiert

### Fallstricke
- Immer `default=list` oder `default=dict` setzen (nicht `default=[]` — mutable default!)
- JSONB-Tiefenabfragen in SQLAlchemy erfordern spezielle Syntax
- Keine referenzielle Integritaet innerhalb von JSONB — Validierung im Application-Layer noetig

---

## JWT-Auth mit Stub-Mode-Switching

### Design
Ein einziger `AuthService` mit zwei Pfaden:

```python
def login(self, username, password):
    if self.auth_mode == "stub":
        return self._stub_login(username)
    raise NotImplementedError("LDAP auth not implemented yet")
```

### Kernidee
- JWT-Token-Format ist identisch in beiden Modi
- Middleware (`login_required`, `role_required`) ist mode-agnostisch
- Stub-Benutzer sind als Python-Konstanten definiert (kein DB-Zugriff noetig)
- Sicherheitssperre: `AUTH_MODE=stub` + `ENV=production` → `RuntimeError`

### Lehre
Durch identische Token-Formate koennen alle Features vollstaendig mit Stub-Auth entwickelt und getestet werden. Der Umstieg auf LDAP erfordert nur die Implementierung von `_ldap_login()`.

---

## tanstack-query fuer Server State Management

### Problem
React-State-Management fuer Server-Daten (Caching, Invalidierung, Polling, Error-Handling) ist manuell fehleranfaellig und repetitiv.

### Loesung
tanstack-query (ehemals react-query) uebernimmt:

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})
```

### Muster im Projekt
- **useCatalog:** Templates laden, Kategorien cachen
- **useOrders:** CRUD-Mutations mit automatischer Invalidierung
- **useOrderStatus:** Polling mit `refetchInterval` fuer aktive Bestellungen

### Vorteile
- Automatisches Caching (30s staleTime) reduziert API-Calls
- Mutations invalidieren betroffene Queries automatisch
- Loading/Error-States kommen "gratis"
- Kein manueller State fuer Server-Daten noetig

### Abgrenzung zu zustand
zustand wird nur fuer Client-State verwendet (Auth-Token, User-Daten). Server-Daten gehoeren ausschliesslich in tanstack-query.

---

## Dynamisches Form-Rendering aus Template-Schemas

### Problem
Jedes Service-Template hat unterschiedliche Parameter mit verschiedenen Typen, Constraints und Abhaengigkeiten. Statische Formulare sind nicht wartbar.

### Loesung
Parameter-Definitionen als JSON-Schema im Template:

```json
{
  "key": "cpu_cores",
  "label": "CPU-Kerne",
  "type": "integer",
  "required": true,
  "group": "Compute",
  "display_order": 1,
  "constraints": {"min": 1, "max": 64, "step": 1, "unit": "Kerne"},
  "depends_on": [],
  "affects_options_of": ["disk_type"]
}
```

Frontend-ParameterForm rendert pro Typ die passende Komponente:

```
type: "integer"    → IntegerField (Slider/Input mit Min/Max/Step)
type: "string"     → StringField (Input mit Pattern-Validierung)
type: "boolean"    → BooleanField (Toggle)
type: "enum"       → EnumField (Dropdown mit aktivierbaren Optionen)
type: "size_bytes" → SizeBytesField (Groessen-Input mit Einheiten)
```

### depends_on-Mechanismus
- Feld A deklariert `affects_options_of: ["B"]`
- Feld B deklariert `depends_on: [{"parameter_key": "A", ...}]`
- Aenderung von A triggert Backend-Call (`resolve-options`) fuer neue Constraints von B
- Frontend aktualisiert Feld B dynamisch

### Lehre
Der Schema-basierte Ansatz erfordert initiale Komplexitaet, aber jedes neue Service-Template erfordert nur neue JSON-Daten — keinen neuen Code.

---

## Alembic-Migrationen mit JSONB-Spalten

### Problem
JSONB-Spalten erfordern PostgreSQL-spezifische Typen in Alembic-Migrationen.

### Loesung
Import des PostgreSQL-Dialekts in Migrationen:

```python
from sqlalchemy.dialects.postgresql import JSONB

op.add_column('orders', sa.Column('context', JSONB(), nullable=True))
```

### Tipps
- JSONB-Default-Werte als Server-Default setzen: `server_default='{}'`
- Bei Aenderungen an JSONB-Struktur: Keine Migration noetig (Schema-frei)
- Indices auf JSONB-Pfade: `Index('ix_name', model.column['key'].astext)`

### Migrationsreihenfolge im Projekt
1. `service_templates` — Template-Katalog
2. `orders` + `order_items` — Bestellungen
3. `context_rules` + `tenant_assignments` — Kontext
4. `context` auf orders — Order-Kontext-Spalte
5. `provisioning_status` + `dispatch_logs` — Provisioning
6. `approval_rules` + `approval_requests` — Genehmigungen
7. `audit_logs` — Audit
8. `notifications` — Benachrichtigungen
9. `credential_links` — Zugangsdaten

---

## Order-Status-Machine

### Design
Status-Transitions als explizite Whitelist im Domain-Modell:

```python
_TRANSITIONS = {
    "draft": {"validated"},
    "validated": {"submitted", "draft"},
    "submitted": {"provisioning", "pending_approval"},
    "pending_approval": {"approved", "rejected"},
    "approved": {"provisioning"},
    "provisioning": {"done", "failed"},
    "done": set(),
    "failed": set(),
    "rejected": set(),
}
```

### Vorteile
- Alle erlaubten Transitions auf einen Blick
- `can_transition()` ist eine einfache Set-Lookup-Operation
- Terminal-Status (`done`, `failed`, `rejected`) haben leere Transition-Sets
- Keine Framework-Abhaengigkeit (reines Python)

### Lehre
Eine explizite Status-Machine im Domain-Layer verhindert ungueltige Transitions zuverlaessiger als Business-Logic-Checks in Services.

---

## CMDB-Stub-Architektur

### Design
Der CMDB-Stub implementiert dasselbe Interface wie der zukuenftige Live-Client:

```python
class CmdbStubClient:
    def get_locations(self): ...
    def get_networks(self, location_id=None, security_zone_id=None): ...
    def get_tenants(self): ...
    def get_security_zones(self): ...
    def health(self): ...
```

Daten werden aus YAML-Dateien geladen und im Speicher gehalten.

### Austausch-Strategie
1. `CmdbLiveClient` mit demselben Interface implementieren
2. In `app/__init__.py` den Client basierend auf `CMDB_MODE` waehlen
3. Kein Code ausserhalb von `data/clients/` muss geaendert werden

### Lehre
Durch konsequente Interface-Trennung (Dependency Inversion) ist der Stub-zu-Live-Wechsel eine Ein-Zeilen-Aenderung in der App-Factory.
