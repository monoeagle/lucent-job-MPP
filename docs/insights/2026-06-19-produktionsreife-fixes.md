# Insight — VM-Install-Guide + Produktionsreife-Fixes (2026-06-19)

Nicht-offensichtliche Erkenntnisse dieser Session. Code-Struktur steht im Repo; hier nur, was in
einer frischen Session **überraschen** würde.

## 1. Die „862 Tests grün"-Baseline ist FALSCH — 23 Backend-Tests sind aktuell rot
`CLAUDE.md` und die Doku behaupten „862 Tests (756 Backend / 106 Frontend), alle grün". Ein voller
`tests/unit + tests/integration`-Lauf ergab aber **23 failed, 642 passed**. Per `git stash` (meine
Änderungen weg) verifiziert: die 23 fallen **identisch ohne** meine Arbeit → **pre-existing**, keine
Regression. Themen: Stub-User-Count (`assert 5 == 4` — `test-superadmin` kam dazu), Auth-403s,
DSGVO, Audit-Log, Approval-Rules. **Lehre:** vor „TDD-Baseline grün"-Annahmen erst real `pytest`
laufen lassen; die Zahl in den Docs ist ein *Count*, kein *grün-Beweis*.

## 2. Das Projektverzeichnis ist ein Symlink
pytest-Tracebacks zeigen Pfade unter `/home/meagle/Dokumente/CLAUDE/lucent-hub-apps/lucent-app-mpp-
TDD/…`, obwohl ich in `_Projects/lucent-job-MPP/` arbeite. Beide zeigen auf denselben Ort. Nur
relevant, wenn man sich über „fremde" Pfade in der Ausgabe wundert.

## 3. `venv/bin/pytest` ist kaputt (Shebang) — `venv/bin/python -m pytest` nutzen
Direktaufruf scheitert mit „Kann nicht ausführen. Datei nicht gefunden" (Shebang zeigt auf einen
nicht mehr passenden Python-Pfad, vermutlich AppImage-Bundle-Artefakt). Immer als Modul starten.

## 4. Der Flask-VM-Guide ist NICHT 1:1 das Django-Pendant — die App ist nicht produktionsreif
Recherche (Explore-Subagent) ergab harte Lücken ggü. dem produktionsreifen Django-Projekt:
**kein gunicorn** in `requirements.txt`, **kein lauffähiger Prod-Auth** (`AUTH_MODE=ldap` →
`NotImplementedError`, und `ENV=production`+`stub` ist per Guard verboten → niemand kann sich
einloggen), **`CMDB_MODE=live` nicht implementiert**, **keine User-Tabelle/-Verwaltung**, kein
Redis/Celery. Der Guide (`docs/deployment/vm-installation.md`) beschreibt daher das **Zielbild**
mit ehrlichen „⚠ Lücke"-Boxen statt „produktionssicher" zu behaupten.

## 5. ProxyFix lässt sich nicht über `test_request_context` testen
ProxyFix ist WSGI-Middleware (`app.wsgi_app`). `test_request_context` baut den Request-Context
**direkt** aus dem Environ und umgeht die wsgi_app-Kette → die `X-Forwarded-*`-Auswertung greift
dort nie. Behavior-Test bräuchte eine echte Route, die `request.scheme` ausgibt (gibt's nicht) →
pragmatisch strukturell getestet: `assert isinstance(app.wsgi_app, ProxyFix)`.

## 6. gunicorn-Entrypoint ist der Factory-Aufruf `app:create_app()`
Es gibt **kein** Modul-Level-`app` und **keine** `wsgi.py` — nur die Factory `create_app` in
`app/__init__.py`. gunicorn startet daher als `gunicorn "app:create_app()"` (Smoke-Test grün:
`/health` 200, `/ready` 200). `WorkingDirectory` muss das Repo-Root sein, sonst wird das Package
`app` nicht gefunden.

## 7. `alembic.ini` ignorierte `DATABASE_URL` — jetzt über `app/core/db_url.py` behoben
`migrations/env.py` las `config.get_main_option("sqlalchemy.url")` (hartkodiert `mpp_dev`). Neu:
`resolve_database_url()` bevorzugt die Env-Variable. Funktional bewiesen: mit `DATABASE_URL=bogus`
zielt `alembic current` auf genau diese DB statt auf `mpp_dev`.

## 8. `/health` bleibt Liveness — DB-Check kam als separater `/ready` dazu (nicht-brechend)
Den bestehenden `/api/v1/health` NICHT um einen DB-Check erweitern (bestehende Tests erwarten immer
200) → neuer `/api/v1/ready` mit `SELECT 1` (503 bei DB-Ausfall). Saubere Trennung Liveness vs.
Readiness, keine Regression an bestehenden Health-Tests.

## Offen / nächste sinnvolle Schritte
- **LDAP/OIDC-Auth** implementieren (echter Prod-Blocker) — braucht Design/Brainstorming.
- Die **23 pre-existing Test-Failures** triagieren (Seed-/Rollen-Drift) — eigene Session wert.
- `CMDB_MODE=live`, User-Verwaltung, HSTS-Konfiguration, DSGVO-Flag verdrahten.
