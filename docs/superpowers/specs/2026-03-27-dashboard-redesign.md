# Dashboard Redesign — Design Spec

**Ziel:** Rollenabhaengiges Dashboard mit Stat-Kacheln, Listen, Charts (recharts) und globaler Suche. Ersetzt die aktuelle Platzhalter-Seite. Zwei neue Backend-Endpoints (Search + Stats).

---

## Layout

Obere Zeile: Titel + globale Suche. Darunter Stat-Kacheln (4er Grid). Darunter 2-spaltig: Listen links, Charts rechts. Rollen-spezifische Widgets am Ende.

## Widgets nach Rolle

### Alle User

**Stat-Kacheln (4er Grid):**
- Offene Orders (Status draft + submitted)
- Pending Approvals (eigene, awaiting decision)
- Aktive Services (Resources mit Status active)
- Templates gesamt

**Letzte Bestellungen (Liste):**
- 5 neueste Orders mit Order-Nummer, Titel, Status-Badge, Datum
- Link "Alle anzeigen" → /orders

**Orders nach Status (Donut-Chart):**
- recharts PieChart mit Status-Verteilung (draft, submitted, pending_approval, provisioning, done, failed)
- Farben: draft=gray, submitted=blue, pending_approval=yellow, provisioning=purple, done=green, failed=red

**Orders ueber Zeit (Line-Chart):**
- recharts LineChart, letzte 6 Monate, Anzahl Orders pro Monat
- X-Achse: Monat (Jan, Feb...), Y-Achse: Anzahl

**Beliebte Services (Liste):**
- Top 5 Templates nach Bestellhaeufigkeit
- Template-Name + Kategorie-Badge + "Bestellen"-Link (→ /shop/{slug}/request)
- Link "Zum Shop" → /shop

### Approver/Admin zusaetzlich

**Ausstehende Genehmigungen (Liste):**
- Pending Approvals mit Order-Referenz, Requester, Deadline
- Link zur Approval-Detail-Seite
- Nur sichtbar wenn Rolle approver oder admin

### Admin zusaetzlich

- Stat-Kachel "Templates gesamt" zeigt bei Admin die Anzahl aller Templates (inkl. disabled/deprecated)

## Globale Suche

**Frontend:** Suchfeld oben rechts im Dashboard-Header. Bei Eingabe (min. 2 Zeichen, 300ms Debounce) oeffnet sich ein Dropdown mit gruppierten Ergebnissen.

**Ergebnis-Dropdown:**
```
┌────────────────────────────┐
│ Orders                     │
│   ORD-2026-00042 - My VM   │
│   ORD-2026-00041 - DB      │
│ Services                   │
│   Linux VM (Compute)       │
│   PostgreSQL DB (Database)  │
│ Resources                  │
│   web-01 (vm-linux)        │
└────────────────────────────┘
```

Klick navigiert zur Detail-Seite:
- Order → /orders/{id}
- Template → /shop/{slug}/request
- Resource → /my-services (mit Fokus, falls spaeter Detail-Seite existiert)

Escape oder Klick ausserhalb schliesst das Dropdown. Leeres Suchfeld schliesst ebenfalls.

## Backend: Search-Endpoint

```
GET /api/v1/search?q=linux&limit=5
```

Response:
```json
{
  "query": "linux",
  "orders": [
    { "id": "...", "order_number": "ORD-2026-00042", "title": "Linux VM Bestellung", "status": "draft" }
  ],
  "templates": [
    { "slug": "vm-linux", "display_name": "Linux VM", "category": "Compute", "status": "active" }
  ],
  "resources": []
}
```

Implementierung: ILIKE-Suche in bestehenden Repositories. Orders: Titel + Order-Nummer. Templates: display_name + slug. Resources: display_name. Limit pro Kategorie (Default 5). Login erforderlich. User sieht nur eigene Orders/Resources (ausser Admin).

## Backend: Dashboard-Stats Endpoint

```
GET /api/v1/dashboard/stats
```

Response:
```json
{
  "orders_by_status": { "draft": 3, "submitted": 1, "done": 7, "failed": 0 },
  "orders_by_month": [
    { "month": "2026-01", "count": 5 },
    { "month": "2026-02", "count": 8 }
  ],
  "total_templates": 12,
  "active_resources": 7,
  "pending_approvals": 2,
  "popular_templates": [
    { "slug": "vm-linux", "display_name": "Linux VM", "category": "Compute", "order_count": 15 },
    { "slug": "db-postgres", "display_name": "PostgreSQL DB", "category": "Database", "order_count": 8 }
  ]
}
```

Implementierung: Aggregations-Queries auf bestehende Tabellen. orders_by_month: GROUP BY date_trunc('month', created_at) letzte 6 Monate. popular_templates: GROUP BY template_slug auf order_items, COUNT, ORDER BY count DESC LIMIT 5. Login erforderlich. User sieht nur eigene Daten (ausser Admin sieht alles).

## Betroffene Dateien

### Backend — Neu
- `app/api/v1/search.py` — Search-Blueprint mit GET /api/v1/search
- `app/api/v1/dashboard.py` — Dashboard-Blueprint mit GET /api/v1/dashboard/stats
- `tests/integration/test_search_api.py`
- `tests/integration/test_dashboard_api.py`

### Backend — Aendern
- `app/__init__.py` — Blueprints registrieren (search, dashboard)

### Frontend — Neu
- `frontend/src/components/dashboard/StatCard.tsx` — Einzelne Zahlen-Kachel
- `frontend/src/components/dashboard/RecentOrders.tsx` — Letzte 5 Orders
- `frontend/src/components/dashboard/OrderStatusChart.tsx` — Donut (recharts PieChart)
- `frontend/src/components/dashboard/OrderTimelineChart.tsx` — Line (recharts LineChart)
- `frontend/src/components/dashboard/PopularServices.tsx` — Top 5 Templates
- `frontend/src/components/dashboard/PendingApprovals.tsx` — Ausstehende Genehmigungen
- `frontend/src/components/dashboard/GlobalSearch.tsx` — Suchfeld + Ergebnis-Dropdown
- `frontend/src/api/dashboard.ts` — API-Client fuer search + stats
- `frontend/src/hooks/useDashboard.ts` — Query-Hooks (useStats, useSearch)

### Frontend — Aendern
- `frontend/src/pages/Dashboard.tsx` — Komplett ueberarbeiten
- `frontend/package.json` — recharts Dependency hinzufuegen

### Nicht aendern
- Bestehende API-Endpoints
- Bestehende Komponenten
- Datenbank-Schema

## Abgrenzung

- Kein Warenkorb
- Keine Echtzeit-Updates (SSE) fuer Dashboard
- Keine konfigurierbaren/verschiebbaren Widgets
- Keine Admin-System-Metriken (CPU, Memory)
- Keine Suchhistorie oder Suchvorschlaege
