# Audit HIGH-Findings Fixes — Design Spec

**Ziel:** Strukturelle Verbesserungen basierend auf dem 3-Way-Audit. Keine Verhaltensaenderungen, keine neuen Features. Bestehende Tests muessen gruen bleiben.

---

## Fix 1: orders.py aufteilen (679 → 4 Dateien)

Aufteilen nach Verantwortung:
- `orders.py` (~120 Zeilen) — Order CRUD, list, shared helpers (_serialize_order, _serialize_item, _serialize_group, _check_owner, _get_service, _get_repo)
- `order_items.py` (~100 Zeilen) — add_item, update_item, remove_item, reorder_items
- `order_groups.py` (~100 Zeilen) — create_group, update_group, delete_group, reorder_groups
- `order_actions.py` (~150 Zeilen) — validate_order, submit_order, get_order_status, export_order_tofu, export_item_tofu

Alle Dateien nutzen denselben Blueprint `bp` (definiert in orders.py, importiert in den anderen). Shared helpers werden aus orders.py importiert. Blueprint-Registrierung in `__init__.py` bleibt unveraendert (nur `orders.bp`).

## Fix 2: submit_order Orchestration → Service

Die submit_order Funktion in order_actions.py (nach Fix 1) wird vereinfacht. Post-Submit-Orchestration (Approval-Check, Dispatch, Notification, Subscription) wird in `OrderService.post_submit(order)` verschoben. Der API-Handler ruft nur noch `service.submit_order()` und `service.post_submit()` auf.

## Fix 3: Error-Format konsistent

In `catalog.py` und `context.py` werden manuelle `jsonify({"error": "..."})` Returns durch `raise NotFoundError(...)`, `raise ValidationError(...)` etc. ersetzt. Nutzt die bestehenden AppError-Klassen aus `app.core.errors`.

## Fix 4: Pagination-Cap

Neuer Helper `cap_limit(limit, max_limit=200)` in `app/core/helpers.py`. Wird in allen paginierten Endpoints aufgerufen um den `limit`-Parameter auf maximal 200 zu begrenzen.

## Fix 5: Services fuer dashboard/search/resources

Neue Service-Klassen die die raw SQLAlchemy-Queries aus den API-Handlern uebernehmen:
- `DashboardService` — Aggregations-Queries fuer Stats
- `SearchService` — ILIKE-Suche ueber Orders + Templates
- `ResourceService` — Resource-Listing mit Joins

API-Handler importieren dann nur noch aus `app.services`, nicht aus `app.data.db.models`.

---

## Betroffene Dateien

### Neu
- `app/api/v1/order_items.py`
- `app/api/v1/order_groups.py`
- `app/api/v1/order_actions.py`
- `app/core/helpers.py`
- `app/services/dashboard_service.py`
- `app/services/search_service.py`
- `app/services/resource_service.py`

### Aendern
- `app/api/v1/orders.py` — Stark verkleinern
- `app/api/v1/catalog.py` — Error-Format
- `app/api/v1/context.py` — Error-Format
- `app/api/v1/dashboard.py` — Service nutzen statt raw queries
- `app/api/v1/search.py` — Service nutzen statt raw queries
- `app/api/v1/resources.py` — Service nutzen statt raw queries
- `app/services/order_service.py` — post_submit() Methode
- Alle paginierten Endpoints — cap_limit()

### Nicht aendern
- Tests (muessen weiter gruen sein)
- Frontend
- Datenbank-Schema

## Abgrenzung
- Nicht alle 28 API→data Imports werden gefixt (nur die schlimmsten: dashboard, search, resources)
- Kein neues Feature, keine API-Aenderung
- Keine Test-Aenderungen (rein strukturelles Refactoring)
