---
description: Python/Flask Konventionen fuer MPP
globs: "*.py"
---
- Architektur: api/ (Blueprints) → services/ (Business) → domain/ (Entities) ← data/ (SQLAlchemy)
- services/ KEINE Flask-Imports (kein request, kein current_app)
- Alembic fuer DB-Migrationen
- CMDB-Stub: YAML-basiert, kein echtes CMDB
- DSGVO-Anonymisierungs-Middleware aktiv
- Type Hints fuer alle Public Functions
