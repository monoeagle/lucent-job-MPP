# Testing

MPP wurde vollstaendig mit **Test-Driven Development (TDD)** entwickelt. 771 Backend-Tests + 106 Frontend-Tests = **877 Tests** insgesamt.

> **Stand 2026-06-27:** Ein voller Backend-Lauf (`tests/`, inkl. e2e) zeigt **739 gruen / 32 rot** (771 gesamt). Die 32 sind **pre-existing Baseline-Drift** (`test_approval_rules_api` 9, `test_audit_log_api` 6, `test_dsgvo_api` 4, `test_approval_submit_integration` 2, `test_auth_stub_users`/`test_auth_service`/`test_auth_roles` u. a.) — diese Session hat **keinen** App-/Test-Code geaendert (reine Delivery/Doku-Session), Triage offen. Frontend (106) diese Session nicht erneut ausgefuehrt.

---

## Uebersicht

| Bereich      | Framework         | Anzahl | Verzeichnis          |
|--------------|-------------------|--------|----------------------|
| Backend Unit | pytest            | ~500   | `tests/unit/`        |
| Backend Int. | pytest            | ~230   | `tests/integration/` |
| Backend E2E  | pytest            | ~26    | `tests/e2e/`         |
| Frontend     | vitest + RTL      | 106    | `frontend/tests/`    |
| **Gesamt**   |                   | **877**|                      |

---

## TDD-Workflow

Jedes Feature wurde im Red-Green-Refactor-Zyklus entwickelt:

1. **Red** — Test schreiben, der fehlschlaegt
2. **Green** — Minimale Implementierung, damit der Test besteht
3. **Refactor** — Code verbessern, ohne das Verhalten zu aendern
4. **Commit** — Aenderungen sichern

---

## Tests ausfuehren

### Backend-Tests

```bash
# Alle Tests
pytest

# Nur Unit-Tests
pytest tests/unit/

# Nur Integration-Tests
pytest tests/integration/

# Nur E2E-Tests
pytest tests/e2e/

# Mit Ausgabe
pytest -v

# Bestimmtes Test-Modul
pytest tests/unit/test_auth_service.py
```

### Frontend-Tests

```bash
cd frontend

# Alle Tests
npx vitest run

# Watch-Modus
npx vitest

# Mit Coverage
npx vitest run --coverage
```

### Ueber den Dev-Launcher

```bash
./scripts/mpp.sh
# Waehle Option [4] Tests ausfuehren
```

---

## Backend-Teststruktur

### Unit-Tests (`tests/unit/`)

Testen einzelne Services und Repositories isoliert. Externe Abhaengigkeiten werden gemockt.

**Beispiel-Kategorien:**

- `test_auth_service.py` — Login, Token-Generierung, Stub-Modi
- `test_catalog_service.py` — Parameter-Validierung, Cross-Rules, Diff
- `test_order_service.py` — Order-Lifecycle, Item-Management
- `test_approval_service.py` — Regel-Evaluation, Approve/Reject
- `test_context_service.py` — CMDB-Resolution, Tenant-Pruefung
- `test_template_validator.py` — Template-Registrierungs-Validierung
- `test_subscription_service.py` — Subscription-Lifecycle, Change, Cancel
- `test_dashboard_service.py` — Dashboard-Statistiken und Aggregation
- `test_search_service.py` — Globale Suche, Relevanz-Ranking
- `test_dsgvo.py` — DSGVO-Anonymisierung, Datenschutz-Middleware

### Integration-Tests (`tests/integration/`)

Testen Services mit echter Datenbankinteraktion. Verwenden eine separate Test-Datenbank (`mpp_test`).

**Besonderheiten:**

- Jeder Test verwendet eine eigene Session mit Rollback
- Gemeinsame Fixtures in `tests/conftest.py`
- Alembic-Migrationen werden vor dem Test-Lauf ausgefuehrt

### E2E-Tests (`tests/e2e/`)

Testen komplette Flows ueber die API-Schicht:

- Kompletter Bestell-Flow (Create → Add Items → Validate → Submit → Provision)
- Approval-Flow (Submit → Pending → Approve/Reject)
- CMDB-Integration (Kontext-Aufloesung mit Verfuegbarkeitspruefung)
- Subscription-Flow (Order → Done → Subscription → Change/Cancel)
- Post-Submit-Flow (Genehmigung → Provisionierung → Credential-Link)

---

## Frontend-Teststruktur

### Komponenten-Tests

Tests mit `@testing-library/react`:

- Rendering-Tests (Komponente wird korrekt angezeigt)
- Interaktions-Tests (Klick, Eingabe, Navigation)
- State-Tests (Daten werden korrekt geladen und angezeigt)

### Mocking

- API-Module werden komplett gemockt (kein Backend-Zugriff)
- Auth-Store wird fuer Tests vorkonfiguriert
- tanstack-query-Provider wird in Test-Wrapper bereitgestellt

---

## Test-Datenbank

| Parameter | Wert                                          |
|-----------|-----------------------------------------------|
| Name      | `mpp_test`                                     |
| URL       | `postgresql://mpp:mpp@localhost:5432/mpp_test` |
| Isolation | Session-Rollback nach jedem Test               |

```bash
# Test-Datenbank erstellen
sudo -u postgres createdb -O mpp mpp_test
```

---

## Conventions

- Teste Verhalten, nicht Implementierungsdetails
- Decke Edge Cases ab
- Mocke externe Abhaengigkeiten
- Bevorzuge kleine, fokussierte Tests
- Namenskonvention: `test_<feature>_<scenario>.py`
