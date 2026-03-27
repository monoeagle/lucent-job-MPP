# Frontend

React 19 + TypeScript 5.7 + Vite 6 + TailwindCSS 4 + tanstack-query 5 + zustand 5

---

## Seiten (11 Seiten)

| #  | Seite           | Pfad                      | Rolle      | Beschreibung                                        |
|----|-----------------|---------------------------|------------|-----------------------------------------------------|
| 1  | Login           | `/login`                  | —          | Anmeldung mit Benutzer-Auswahl (Stub-Mode)          |
| 2  | Catalog         | `/catalog`                | login      | Servicekatalog mit Filter, Suche und Detail-Drawer   |
| 3  | OrderList       | `/orders`                 | login      | Bestellungsuebersicht mit Status-Filter              |
| 4  | OrderNew        | `/orders/new`             | login      | Neue Bestellung erstellen mit Service-Auswahl        |
| 5  | OrderDetail     | `/orders/:orderId`        | login      | Bestelldetail mit Items, Validierung und Submit      |
| 6  | OrderExport     | `/orders/:orderId/export` | login      | OpenTofu-Export-Ansicht                              |
| 7  | Approvals       | `/approvals`              | approver   | Offene Genehmigungsanfragen bearbeiten               |
| 8  | Resources       | `/resources`              | login      | Uebersicht provisionierter Ressourcen                |
| 9  | AdminDashboard  | `/admin`                  | admin      | Admin-Dashboard mit Statistiken und Health           |
| 10 | Rules           | `/admin/rules`            | admin      | Approval-Regeln verwalten                            |
| 11 | AuditLog        | `/admin/audit-log`        | admin      | Audit-Log einsehen und filtern                       |

---

## Schluessel-Komponenten

### ParameterForm (`components/ParameterForm/`)

Dynamisches Formular-Rendering basierend auf Template-Parameterdefinitionen.

**Feld-Komponenten:**

- `StringField` — Texteingabe mit optionalem Regex-Pattern
- `IntegerField` — Zahleneingabe mit Min/Max/Step und Unit
- `BooleanField` — Toggle/Checkbox
- `EnumField` — Dropdown-Auswahl mit aktivierbaren Optionen
- `SizeBytesField` — Speichergroessen-Eingabe mit Einheiten

**Features:**

- Gruppierung nach `group`-Feld
- Sortierung nach `display_order`
- `depends_on`-Evaluation fuer abhaengige Felder
- Live-Validierung gegen Constraints

### Drawer (`components/Drawer.tsx`)

Wiederverwendbare Slide-In-Komponente (von rechts). Wird im Catalog fuer Template-Details verwendet.

### ContextSelector (`components/orders/ContextSelector.tsx`)

Kontextauswahl-Formular mit kaskadierenden Dropdowns:

1. Standort (Location) → laedt verfuegbare Netzwerke
2. Tenant → gefiltert nach Benutzer-Zuweisungen
3. Sicherheitszone → laedt passende Netzwerke
4. Netzwerk → gefiltert nach Location + Security Zone

### OrderItemCard (`components/orders/OrderItemCard.tsx`)

Karte fuer ein einzelnes Item in einer Bestellung. Zeigt Template-Info, Parameter und Validierungsstatus.

### StatusBadge (`components/StatusBadge.tsx`)

Farbige Badges fuer Order-Status (draft=grau, validated=blau, done=gruen, failed=rot, ...).

---

## Routing-Struktur

```
/login                          → Login (oeffentlich)
/                               → Redirect → /orders
├── /catalog                    → Catalog
├── /orders                     → OrderList
├── /orders/new                 → OrderNew
├── /orders/:orderId            → OrderDetail
├── /orders/:orderId/export     → OrderExport
├── /resources                  → Resources
├── /approvals                  → Approvals (approver/admin)
├── /admin                      → AdminDashboard (admin)
├── /admin/rules                → Rules (admin)
└── /admin/audit-log            → AuditLog (admin)
```

Alle Routen ausser `/login` sind durch `ProtectedRoute` geschuetzt.
Admin- und Approver-Routen erfordern zusaetzlich `requiredRoles`.

---

## Rollenbasierte Navigation

| Element         | requester | approver | admin |
|-----------------|-----------|----------|-------|
| Catalog         | ja        | ja       | ja    |
| Orders          | ja        | ja       | ja    |
| Resources       | ja        | ja       | ja    |
| Approvals       | —         | ja       | ja    |
| Admin Dashboard | —         | —        | ja    |
| Admin Rules     | —         | —        | ja    |
| Admin Audit Log | —         | —        | ja    |

---

## State Management

### Auth Store (`store/authStore.ts`)

zustand-Store mit localStorage-Persistierung:

- `user` — aktueller Benutzer
- `token` — JWT-Token
- `login(username)` — Login-Aktion
- `logout()` — Token und User loeschen
- `restoreSession()` — Session aus localStorage wiederherstellen

### Server State (tanstack-query)

Alle Server-Daten werden ueber tanstack-query verwaltet:

- `useCatalog` — Templates, Kategorien, Versionen
- `useOrders` — Bestellungen CRUD, Items, Validierung, Submit
- `useOrderStatus` — Status-Polling fuer aktive Bestellungen
- `useAuth` — Auth-bezogene Queries

**Default-Konfiguration:**

- `retry: 1`
- `staleTime: 30_000` (30 Sekunden)

---

## API-Module

| Modul               | Datei                 | Endpunkte                              |
|----------------------|-----------------------|----------------------------------------|
| Client               | `api/client.ts`      | Basis-HTTP-Client mit Auth-Headers     |
| Catalog              | `api/catalog.ts`     | Templates, Kategorien, Validierung     |
| Orders               | `api/orders.ts`      | Bestellungen CRUD, Items, Submit       |
| Approvals            | `api/approvals.ts`   | Genehmigungen auflisten und bearbeiten |
| Context              | `api/context.ts`     | CMDB-Daten und Kontext-Aufloesung      |
| Resources            | `api/resources.ts`   | Provisionierte Ressourcen              |
| Admin                | `api/admin.ts`       | Dashboard, Audit, Regeln               |
