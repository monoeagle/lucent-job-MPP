# Marketplace Portal Frontend — Design Spec

> **Erstellt:** 2026-03-26
> **Status:** Approved
> **Tech-Stack:** React 19 + TypeScript, Vite, TailwindCSS, tanstack-query, react-hook-form, zod, react-router

---

## Kontext

Frontend für das Marketplace Portal Backend (Flask, 76 API-Endpoints, PostgreSQL). User bestellen IT-Services (VMs, Datenbanken, Container) über eine Web-Oberfläche. Das Backend ist vollständig implementiert (489 Tests, Phasen 0-7).

---

## Entscheidungen

| Entscheidung | Wert | Begründung |
|-------------|------|------------|
| Framework | React 19 + TypeScript | Bestes Ökosystem für dynamische Formulare |
| Styling | TailwindCSS | Utility-first, schnell, keine eigene Design-Library nötig |
| Layout | Sidebar + Content | Mehrere gleichwertige Bereiche brauchen permanente Navigation |
| Bestellprozess | Order-Detail als Hub | Draft-basiertes Modell, flexibel, kein starrer Wizard |
| Item-Konfiguration | Slide-in Drawer | Kontext bleibt sichtbar, genug Platz für Parameter |
| Status-Updates | Polling jetzt, SSE-ready | Backend SSE ist Stub, Polling funktioniert sofort |
| Server-State | tanstack-query | Caching, Refetching, Optimistic Updates |
| Forms | react-hook-form + zod | Dynamische Validierung, Performance |
| Client-State | zustand (minimal) | Auth-Token, UI-Preferences |

---

## Seitenstruktur

| Route | Seite | Rollen |
|-------|-------|--------|
| `/login` | Login | alle |
| `/catalog` | Service Catalog (Template-Karten, Filter, Suche) | alle auth |
| `/orders` | Order-Liste (eigene, Filter, Pagination) | alle auth |
| `/orders/new` | Neue Order (Kontext setzen → Redirect zu Detail) | requester+ |
| `/orders/:id` | **Order-Detail Hub** (Items, Validierung, Submit) | owner/admin |
| `/orders/:id/export` | JSON-Export Ansicht (readonly) | owner/admin |
| `/resources` | Meine Ressourcen (provisionierte Items) | alle auth |
| `/approvals` | Pending Approvals (Approve/Reject) | approver/admin |
| `/admin/dashboard` | Admin Dashboard (Counts, Health, Recent Orders) | admin |
| `/admin/rules` | Regelverwaltung (Approval, Availability, Restrictions, Tenants) | admin |
| `/admin/audit` | Audit Log (Filter, Export) | admin |

---

## Kern-UI: Order-Detail als Hub

```
┌─────────────────────────────────────────────────┐
│ Order: ORD-2026-00042          Status: [draft]  │
│ "Web-Cluster Q2"                                │
├─────────────────────────────────────────────────┤
│ Kontext: Berlin HQ | Corporate IT | MEDIUM      │
│ [Kontext ändern]  (nur im Draft)                │
├─────────────────────────────────────────────────┤
│ Items:                                          │
│ ┌─ 1. Linux VM (vm-linux v2.0.0) ─── [✓ valid] │
│ │   CPU: 4 | RAM: 16 GB | OS: Ubuntu           │
│ │   [Bearbeiten] [Entfernen]                    │
│ ├─ 2. PostgreSQL DB (db-pg v1.0.0) ── [⚠ invalid]│
│ │   Version: 16 | Storage: 100 GB              │
│ │   ❌ RAM muss min. 4 GB sein                  │
│ │   [Bearbeiten] [Entfernen]                    │
│ └───────────────────────────────────────────────│
│ [+ Service hinzufügen]                          │
├─────────────────────────────────────────────────┤
│ Begründung: "Neues Web-Cluster für Q2-Launch"   │
│ Wunschtermin: 2026-04-15                        │
├─────────────────────────────────────────────────┤
│ [Validieren]  [Absenden]  [JSON-Export]  [🗑]   │
└─────────────────────────────────────────────────┘
```

- **"+ Service hinzufügen"** öffnet Drawer rechts
- **"Bearbeiten"** öffnet Drawer mit vorausgefüllten Werten
- **Validierungsfehler** inline pro Item
- **Submit** nur aktiv wenn Status = validated
- **Status-Badge** pollt bei submitted/provisioning

---

## Drawer: Service konfigurieren

```
┌──────────────── Service konfigurieren ──┐
│                                          │
│ Template: [vm-linux v2.0.0 ▼]           │
│                                          │
│ ── Compute ──────────────────────────── │
│ CPU-Kerne:  [4 ▼]  (1-64)              │
│ RAM (GB):   [16 ▼]  (2-256)            │
│                                          │
│ ── System ───────────────────────────── │
│ Betriebssystem: [Ubuntu 22.04 ▼]       │
│                                          │
│ ── Storage ──────────────────────────── │
│ Disk-Typ: [ext4 ▼]    ← dynamisch      │
│ Disk-Größe: [100] GB                    │
│                                          │
│ ⚠ Template deprecated. Neuere Version   │
│   vm-linux v3.0.0 verfügbar.            │
│                                          │
│        [Abbrechen]  [Hinzufügen]        │
└──────────────────────────────────────────┘
```

---

## Projektstruktur

```
frontend/
├── src/
│   ├── api/                    # API Client (fetch wrapper, auth header)
│   │   ├── client.ts           # Base client with auth, error handling
│   │   ├── catalog.ts          # Catalog API calls
│   │   ├── orders.ts           # Order API calls
│   │   ├── context.ts          # Context/CMDB API calls
│   │   ├── approvals.ts        # Approval API calls
│   │   └── admin.ts            # Admin API calls
│   ├── hooks/                  # Custom React hooks
│   │   ├── useAuth.ts          # Auth state + login/logout
│   │   ├── useOrderStatus.ts   # Polling (SSE-ready abstraction)
│   │   └── useCatalog.ts       # Catalog queries with tanstack-query
│   ├── components/             # Shared UI components
│   │   ├── Layout/             # Sidebar, Header, Content wrapper
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── AppLayout.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── ErrorDisplay.tsx
│   │   ├── ConfirmDialog.tsx
│   │   ├── Drawer.tsx
│   │   └── ParameterForm/      # Dynamic form renderer
│   │       ├── ParameterForm.tsx    # Main: renders fields from schema
│   │       ├── IntegerField.tsx
│   │       ├── FloatField.tsx
│   │       ├── EnumField.tsx
│   │       ├── BooleanField.tsx
│   │       ├── StringField.tsx
│   │       ├── SizeBytesField.tsx
│   │       └── FieldGroup.tsx       # Groups parameters by group name
│   ├── pages/                  # Route-level components
│   │   ├── Login.tsx
│   │   ├── Catalog.tsx
│   │   ├── OrderList.tsx
│   │   ├── OrderDetail.tsx     # The Hub
│   │   ├── OrderNew.tsx        # Context selection → redirect
│   │   ├── OrderExport.tsx
│   │   ├── Resources.tsx
│   │   ├── Approvals.tsx
│   │   └── admin/
│   │       ├── Dashboard.tsx
│   │       ├── Rules.tsx
│   │       └── AuditLog.tsx
│   ├── store/                  # Minimal client state
│   │   └── authStore.ts        # zustand: token, user, login/logout
│   ├── types/                  # TypeScript types matching API contracts
│   │   ├── catalog.ts
│   │   ├── order.ts
│   │   ├── context.ts
│   │   ├── approval.ts
│   │   └── common.ts           # ErrorResponse, Pagination, etc.
│   └── App.tsx                 # Router + Layout + QueryProvider
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

---

## Kernkomponente: ParameterForm

Die wichtigste Komponente — rendert dynamisch aus dem Template-Schema:

1. Liest `parameters` Array aus dem Template
2. Sortiert nach `display_order`, gruppiert nach `group`
3. Pro Parameter: wählt den richtigen Field-Typ (IntegerField, EnumField, etc.)
4. Wendet `constraints` als Validierungsregeln an (zod-Schema wird dynamisch aus Template generiert)
5. Evaluiert `depends_on` client-seitig: blendet Felder ein/aus
6. Bei `affects_options_of`: ruft `POST /resolve-options` auf und aktualisiert Enum-Optionen
7. Zeigt `cross_parameter_rules` Violations an (nach Server-Validierung)

### Field-Typ-Mapping

| ParameterType | Component | Input-Typ |
|---------------|-----------|-----------|
| integer | IntegerField | Number input mit min/max/step |
| float | FloatField | Number input mit step |
| string | StringField | Text input mit pattern/length |
| boolean | BooleanField | Toggle/Checkbox |
| enum | EnumField | Select dropdown |
| range_integer | IntegerField | Slider oder Number input |
| range_float | FloatField | Slider oder Number input |
| size_bytes | SizeBytesField | Number input mit Unit-Selector (MB/GB/TB) |

---

## Datenfluss

```
User Action → React Component → tanstack-query mutation → Flask API → Response
                                                                        ↓
                                                              tanstack-query cache invalidation
                                                                        ↓
                                                              React re-render
```

- **Server-State** (Orders, Catalog, Resources): tanstack-query (caching, background refetch)
- **Client-State** (Auth-Token, Sidebar-Toggle): zustand
- **Form-State**: react-hook-form (lokal im Drawer/Page, nicht global)

---

## Error-Handling

| Szenario | UI-Verhalten |
|----------|-------------|
| API-Fehler (4xx/5xx) | Toast-Notification mit `message` aus Response |
| Validierungsfehler (400 mit fields) | Inline-Fehler pro Feld im Formular |
| 401 Unauthorized | Redirect zu `/login`, Token löschen |
| 503 CMDB Unavailable | Banner oben: "CMDB nicht erreichbar. Bestellung temporär nicht möglich." |
| Netzwerk-Fehler | Toast: "Verbindung zum Server unterbrochen." |
| Provisioning-Timeout | Status-Badge zeigt "Provisioning..." mit Ladeindikator |

---

## Status-Updates (Polling → SSE)

```typescript
// hooks/useOrderStatus.ts
function useOrderStatus(orderId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['order-status', orderId],
    queryFn: () => api.orders.getStatus(orderId),
    refetchInterval: enabled ? 10_000 : false, // 10s polling
    // Later: replace with SSE EventSource
  });
}
```

Polling aktiv wenn Order-Status in: `submitted`, `pending_approval`, `provisioning`.
Stoppt automatisch bei Terminal-Status (`done`, `failed`, `rejected`).

---

## Rollenbasierte UI

| Element | requester | approver | admin |
|---------|-----------|----------|-------|
| Catalog | sichtbar | sichtbar | sichtbar |
| My Orders | eigene | eigene | alle |
| Resources | eigene | eigene | alle |
| Approvals (Sidebar) | versteckt | sichtbar | sichtbar |
| Admin (Sidebar) | versteckt | versteckt | sichtbar |
| Order Submit | ja | ja | ja |
| Approve/Reject | nein | ja | ja |

---

## Abhängigkeiten (npm)

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.0.0",
    "react-hook-form": "^7.54.0",
    "@hookform/resolvers": "^3.9.0",
    "zod": "^3.24.0",
    "zustand": "^5.0.0",
    "tailwindcss": "^4.0.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.0.0"
  }
}
```
