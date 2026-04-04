---
description: Test-Richtlinien fuer MPP
globs: "test_*.py,*.test.ts,*.test.tsx"
---
- TDD ist PFLICHT — 862 Tests als Baseline
- pytest (Backend) + Vitest/Jest (Frontend)
- @pytest.mark.e2e fuer End-to-End
- Externe Abhaengigkeiten mocken
- Kleine, fokussierte Tests
