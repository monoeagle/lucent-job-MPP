# Sidebar + Navigation Redesign

**Ziel:** Bestehende flache Sidebar-Navigation in eine collapsible, strukturierte Navigation umbauen mit neuer Menustruktur, Role-based Sections und persistiertem Collapse-State.

**Scope:** Nur Sidebar, Navigation und Routing. Keine neuen Backend-Features, keine inhaltlichen Seitenumbauten.

---

## Sidebar-Struktur

```
┌─────────────────────┐
│  MPP          [«]   │  Logo/Titel + Collapse-Toggle
├─────────────────────┤
│  Dashboard          │  /dashboard (Startseite)
│  Shop               │  /shop (war: /catalog)
│  My Services        │  /my-services (war: /resources)
│  Notifications      │  /notifications (Platzhalter)
│  Review Requests    │  /reviews (war: /approvals, approver/admin)
│  Subscriptions      │  disabled, grau, Tooltip "Kommt bald"
├─────────────────────┤  Trennlinie, nur fuer admin sichtbar
│  Admin Dashboard    │  /admin
│  Rules              │  /admin/rules
│  Audit Log          │  /admin/audit-log
├─────────────────────┤
│  User / Logout      │  fixiert am unteren Rand
└─────────────────────┘
```

## Collapsible-Verhalten

- **Expanded:** ~240px Breite, Icons + Labels sichtbar
- **Collapsed:** ~64px Breite, nur Icons sichtbar, Labels als Tooltip bei Hover
- **Toggle:** Button im Sidebar-Header (Chevron-Icon)
- **Persistenz:** Collapse-Zustand in `localStorage` unter Key `mpp-sidebar-collapsed`
- **Uebergang:** CSS transition fuer smooth collapse/expand (~200ms)
- **Content-Area:** Passt sich dynamisch an die Sidebar-Breite an

## Role-based Visibility

| Menuepunkt | Sichtbar fuer |
|---|---|
| Dashboard, Shop, My Services, Notifications, Subscriptions | alle eingeloggten User |
| Review Requests | approver, admin |
| Admin Dashboard, Rules, Audit Log | admin |

## Routing-Aenderungen

| Alter Pfad | Neuer Pfad | Redirect |
|---|---|---|
| `/catalog` | `/shop` | `/catalog` → `/shop` (301) |
| `/resources` | `/my-services` | `/resources` → `/my-services` (301) |
| `/approvals` | `/reviews` | `/approvals` → `/reviews` (301) |
| `/` | `/dashboard` | Default-Route auf `/dashboard` |
| `/orders` | `/orders` | unveraendert (via Shop-Flow erreichbar) |
| — | `/notifications` | neue Route, Platzhalter-Seite |

## User/Logout in Sidebar

- Verschieben von Header in Sidebar-Footer
- Anzeige: Avatar/Icon + Username (collapsed: nur Icon)
- Logout-Button darunter
- Header.tsx wird vereinfacht (kein User-Bereich mehr)

## Neue Seiten

### Notifications (Platzhalter)
- Titel "Benachrichtigungen"
- Leer-State: "Keine Benachrichtigungen vorhanden"
- Vorbereitet fuer spaetere Integration mit Backend

### Dashboard (ueberarbeitet)
- Bestehende Dashboard-Seite als Startseite unter `/dashboard`
- Inhaltliche Aenderungen (Widgets, Suche) sind NICHT Teil dieser Spec

## Betroffene Dateien

### Aendern
- `frontend/src/components/Layout/Sidebar.tsx` — Kompletter Umbau: Collapsible, neue Menustruktur, Admin-Sektion, User-Footer
- `frontend/src/components/Layout/AppLayout.tsx` — Variable Sidebar-Breite, dynamisches Layout
- `frontend/src/components/Layout/Header.tsx` — User/Logout entfernen, vereinfachen
- `frontend/src/App.tsx` — Neue Routes, Redirects, Default-Route auf /dashboard

### Neu erstellen
- `frontend/src/pages/Notifications.tsx` — Platzhalter-Seite

### Nicht aendern
- Backend — keine Aenderungen
- Bestehende Seiteninhalte — nur Routing-Pfade aendern
- API-Module — unveraendert
- Types — unveraendert

## Abgrenzung (NICHT in Scope)

- Dashboard-Inhalte (Widgets, Suche, Warenkorb)
- Shop-Wizard / Bestell-Flow
- Subscriptions-Backend und -Frontend
- Notifications-Backend
- Mobile/Responsive Design
