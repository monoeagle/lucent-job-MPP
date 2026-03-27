# Konsolidierter Audit-Report — MPP 2026-03-27

**3 unabhaengige Reviews:** Security Engineer, Clean Architect, Quality Auditor

---

## Uebereinstimmung (3/3 oder 2/3 Agenten finden dasselbe)

### 🔴 CRITICAL (2 Findings — Security)

| # | Finding | Gefunden von |
|---|---------|-------------|
| C-1 | **Unauthenticated GitLab Webhook** — POST /api/v1/webhooks/gitlab hat keine Auth. Angreifer kann Order-Status manipulieren. | Security |
| C-2 | **Unauthenticated Credential Endpoint** — GET /api/v1/credentials/{token} hat kein @login_required. Token im URL = Log-Exposure. | Security |

### 🟠 HIGH (5 Findings — Konsens)

| # | Finding | Gefunden von |
|---|---------|-------------|
| H-1 | **Silent Exception Swallowing** (3x `except Exception: pass` in submit_order) | Security + Architect + Quality (3/3) |
| H-2 | **orders.py 679 Zeilen** — 3x ueber 200-Zeilen-Limit, mischt CRUD + Items + Groups + Export + Submit-Orchestration | Architect + Quality (2/3) |
| H-3 | **submit_order Orchestration in API-Layer** — 84 Zeilen, 4 Services + 5 Repos direkt instanziiert, gehoert in Service-Layer | Architect + Quality (2/3) |
| H-4 | **API -> data Layer-Verletzung** — 28 direkte Imports aus data/ in 11 API-Dateien | Architect |
| H-5 | **Hardcoded JWT Secret in Stub-Mode** + Stub-Auth ignoriert Passwort komplett | Security |

### 🟡 MEDIUM (Wichtigste, dedupliziert)

| # | Finding | Gefunden von |
|---|---------|-------------|
| M-1 | Kein Pagination-Cap (limit=999999 moeglich) | Security + Quality |
| M-2 | Kein Rate-Limiting auf Login | Security |
| M-3 | Kein CORS konfiguriert | Security |
| M-4 | Inkonsistente Error-Formate (catalog/context nutzen `{"error":...}` statt AppError) | Quality |
| M-5 | Approvals + Resources Endpoints ohne Pagination | Quality |
| M-6 | Dashboard pending_approvals zeigt globale Daten fuer alle User | Security |
| M-7 | Mass Assignment in context availability-rules (kein Field-Whitelist) | Security |
| M-8 | Fehlende Service-Layer fuer dashboard, search, resources | Architect |
| M-9 | Services importieren direkt Models statt Repositories (notification, credential) | Architect |
| M-10 | Frontend Pages importieren direkt API statt Hooks (5 Stellen) | Architect |

### 🟢 LOW (8 Findings)

- Health-Endpoint exposes auth_mode
- Stub-Users-Endpoint ohne Auth
- LIKE Wildcard-Injection in Search
- CMDB Health zeigt Entity-Counts
- GitLab-URL in Dispatcher-Config
- Grammar-Fehler in Validation-Message
- Unused Import (Decimal in catalog.py)
- provisioning_status hardcoded "not_started"

---

## Positive Beobachtungen (alle 3 Agenten)

- ✅ 742 Backend + 104 Frontend Tests, alle gruen
- ✅ TypeScript strict mode, 0 Errors, 0 `any` Types
- ✅ Kein TODO/FIXME/HACK im Code
- ✅ Domain-Layer hat 0 ausgehende Dependencies (sauber)
- ✅ Data-Layer importiert nie aus API/Services (sauber)
- ✅ Keine Circular Imports
- ✅ SQLAlchemy ORM verhindert SQL-Injection
- ✅ Ownership-Checks auf allen Order-Operationen
- ✅ UUID-basierte IDs verhindern Enumeration
- ✅ Credential-Links mit SHA-256 + One-Time-Consumption

---

## Priorisierte Fix-Liste

### Sofort (vor jeglichem Deployment)
1. Auth auf Webhook-Endpoint (X-Gitlab-Token Validation)
2. Auth auf Credential-Endpoint (oder Token-in-Body statt URL)
3. Silent Exceptions → logging.exception()

### Kurzfristig (naechste Phase)
4. orders.py aufteilen (679 → 4 Dateien)
5. submit_order Orchestration in Service-Layer verschieben
6. Pagination-Cap auf alle Endpoints (max 200)
7. Rate-Limiting auf Login-Endpoint
8. Error-Format konsistent machen (AppError ueberall)

### Mittelfristig
9. API → data Imports eliminieren (28 Stellen)
10. Fehlende Service-Layer erstellen (Dashboard, Search, Resources)
11. Frontend: Hooks statt direkte API-Imports
12. CORS konfigurieren

---

## Verdict

| Agent | Verdict |
|-------|---------|
| Security Engineer | **FAIL** (2 CRITICAL) |
| Clean Architect | **Strukturelle Probleme** (API→data Boundary nicht enforced) |
| Quality Auditor | **CONDITIONAL** (3 HIGH fixen → production-ready) |

**Gesamt: CONDITIONAL — 3 sofortige Fixes noetig, dann production-ready fuer Demo/Staging.**
