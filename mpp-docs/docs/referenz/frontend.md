# Frontend

React 19 + TypeScript 5.7 + Vite 6 + TailwindCSS 4 + tanstack-query 5 + zustand 5

---

## Seiten (17 Seiten)

| #  | Seite           | Pfad                      | Rolle      | Beschreibung                                        |
|----|-----------------|---------------------------|------------|-----------------------------------------------------|
| 1  | Login           | `/login`                  | —          | Anmeldung mit Benutzer-Auswahl (Stub-Mode)          |
| 2  | Dashboard       | `/dashboard`              | login      | Dashboard mit Stats, Recharts-Charts und Suche       |
| 3  | Catalog (Shop)  | `/catalog`                | login      | Servicekatalog mit Wizard/Formular-Toggle            |
| 4  | Workspace       | `/orders`                 | login      | Alle/Meine Bestellungen Tabs                         |
| 5  | OrderNew        | `/orders/new`             | login      | Neue Bestellung mit Shop Wizard oder Formular        |
| 6  | OrderDetail     | `/orders/:orderId`        | login      | Bestelldetail mit Items, Validierung und Submit      |
| 7  | OrderExport     | `/orders/:orderId/export` | login      | OpenTofu-Export-Ansicht                              |
| 8  | Approvals       | `/approvals`              | approver   | Offene Genehmigungsanfragen bearbeiten               |
| 9  | Resources       | `/resources`              | login      | Uebersicht provisionierter Ressourcen                |
| 10 | Subscriptions   | `/subscriptions`          | login      | Aktive Subscriptions verwalten                       |
| 11 | Notifications   | `/notifications`          | login      | Benachrichtigungen mit Read/Unread-Status            |
| 12 | AdminDashboard  | `/admin`                  | admin      | Admin-Dashboard mit Statistiken und Health           |
| 13 | Rules           | `/admin/rules`            | admin      | Approval-Regeln verwalten                            |
| 14 | AuditLog        | `/admin/audit-log`        | admin      | Audit-Log einsehen und filtern                       |
| 15 | DSGVO           | `/admin/dsgvo`            | superadmin | DSGVO-Anonymisierung und Datenschutz-Verwaltung      |
| 16 | ReviewRequests  | `/review-requests`        | approver   | Genehmigungsanfragen pruefen                         |
| 17 | FormView        | (Inline)                  | login      | Split-Layout: Formular links, Sticky Summary rechts  |

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

### StepIndicator (`components/StepIndicator.tsx`)

Fortschrittsanzeige fuer den Shop Wizard mit Schritt-Visualisierung.

### WizardView (`components/WizardView.tsx`)

Mehrstufiger Wizard fuer die Service-Bestellung mit wizard_config und T-Shirt-Sizes.

### FormView (`components/FormView.tsx`)

Split-Layout-Ansicht: Formular links, Sticky Request-Summary rechts. Alternatives Layout zum Wizard.

### RequestSummary (`components/RequestSummary.tsx`)

Zusammenfassung der aktuellen Bestellung (Items, Kosten, Kontext). Wird in FormView als Sticky-Sidebar verwendet.

### GlobalSearch (`components/GlobalSearch.tsx`)

Globale Suche im Header ueber alle Entitaeten (Orders, Templates, Ressourcen).

### StatCard (`components/StatCard.tsx`)

Statistik-Karte fuer Dashboard mit Zahl, Label und optionalem Trend-Indikator.

---

## Sidebar (fest)

Die Sidebar ist fixiert und zeigt folgende Navigationspunkte:

- Dashboard
- Shop (Katalog)
- Bestellungen (Workspace)
- Notifications
- Review Requests (nur approver/admin)

---

## Routing-Struktur

```
/login                          → Login (oeffentlich)
/                               → Redirect → /dashboard
├── /dashboard                  → Dashboard
├── /catalog                    → Catalog (Shop)
├── /orders                     → Workspace (Alle/Meine Bestellungen)
├── /orders/new                 → OrderNew (Wizard oder Formular)
├── /orders/:orderId            → OrderDetail
├── /orders/:orderId/export     → OrderExport
├── /resources                  → Resources
├── /subscriptions              → Subscriptions
├── /notifications              → Notifications
├── /approvals                  → Approvals (approver/admin)
├── /review-requests            → ReviewRequests (approver/admin)
├── /admin                      → AdminDashboard (admin)
├── /admin/rules                → Rules (admin)
├── /admin/audit-log            → AuditLog (admin)
└── /admin/dsgvo                → DSGVO (superadmin)
```

Alle Routen ausser `/login` sind durch `ProtectedRoute` geschuetzt.
Admin- und Approver-Routen erfordern zusaetzlich `requiredRoles`.

---

## Rollenbasierte Navigation

| Element         | requester | approver | admin | superadmin |
|-----------------|-----------|----------|-------|------------|
| Dashboard       | ja        | ja       | ja    | ja         |
| Catalog (Shop)  | ja        | ja       | ja    | ja         |
| Workspace       | ja        | ja       | ja    | ja         |
| Resources       | ja        | ja       | ja    | ja         |
| Subscriptions   | ja        | ja       | ja    | ja         |
| Notifications   | ja        | ja       | ja    | ja         |
| Review Requests | —         | ja       | ja    | ja         |
| Approvals       | —         | ja       | ja    | ja         |
| Admin Dashboard | —         | —        | ja    | ja         |
| Admin Rules     | —         | —        | ja    | ja         |
| Admin Audit Log | —         | —        | ja    | ja         |
| Admin DSGVO     | —         | —        | —     | ja         |

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
- `useSubscriptions` — Subscriptions auflisten, Change, Cancel
- `useNotifications` — Benachrichtigungen, Read/Unread
- `useDashboard` — Dashboard-Statistiken und Charts

**Default-Konfiguration:**

- `retry: 1`
- `staleTime: 30_000` (30 Sekunden)

---

## API-Module

| Modul               | Datei                      | Endpunkte                              |
|----------------------|----------------------------|----------------------------------------|
| Client               | `api/client.ts`           | Basis-HTTP-Client mit Auth-Headers     |
| Catalog              | `api/catalog.ts`          | Templates, Kategorien, Validierung     |
| Orders               | `api/orders.ts`           | Bestellungen CRUD, Items, Submit       |
| Approvals            | `api/approvals.ts`        | Genehmigungen auflisten und bearbeiten |
| Context              | `api/context.ts`          | CMDB-Daten und Kontext-Aufloesung      |
| Resources            | `api/resources.ts`        | Provisionierte Ressourcen              |
| Admin                | `api/admin.ts`            | Dashboard, Audit, Regeln               |
| Subscriptions        | `api/subscriptions.ts`    | Subscriptions, Change, Cancel          |
| Notifications        | `api/notifications.ts`    | Benachrichtigungen, Read-Status        |
| Search               | `api/search.ts`           | Globale Suche                          |
