# CLAUDE.md — MPP (Self-Service IT-Provisioning Portal)

**Stack:** Python 3.12 / Flask 3.1 + React 19 / TypeScript / Vite 6
**Ports:** Backend 5000, Frontend Dev 3000
**Autor:** Tobias Philipp / Lucent Trails

## Architektur

```
Backend:  api/ (Blueprints) → services/ (Business) → domain/ (Entities) ← data/ (SQLAlchemy)
Frontend: pages/ → hooks/ → api/ ← types/
```

api/ → data/ ist VERBOTEN. services/ hat KEINE Flask-Imports.

## Rollen & Stub-Benutzer

4 Rollen: Admin, Approver, Requester, Viewer (superadmin fuer DSGVO)
Stubs: `test-requester`, `test-approver`, `test-admin`, `test-multi`, `test-superadmin`

## Tests

862 Tests (756 Backend / 106 Frontend) — TDD ist PFLICHT, keine Ausnahmen.
pytest (Backend) + Vitest (Frontend). Neue Features nur nach gruenen Tests.

## Stubs & Mocks

- CMDB-Stub: YAML-Daten in `stubs/cmdb/`
- GitLab-Mock: Pipeline-Simulation in `stubs/gitlab_mock.py`
- AUTH_MODE=stub / CMDB_MODE=stub (nie in Produktion)

## Weiter lesen

- `docs/` — Architektur, Audit, Dependency-Matrix, Specs
- `.claude/rules/python.md` — Flask/Backend-Konventionen
- `.claude/rules/react-typescript.md` — Frontend-Konventionen
- `.claude/rules/testing.md` — Test-Richtlinien
