import os


def resolve_database_url(fallback: str | None) -> str:
    """Bevorzugt die Umgebungsvariable DATABASE_URL vor dem übergebenen Fallback.

    Wird von Alembic (`migrations/env.py`) genutzt, damit Migrationen dieselbe DB
    treffen wie die App, statt die hartkodierte `sqlalchemy.url` aus `alembic.ini`.
    """
    return os.environ.get("DATABASE_URL") or fallback or ""
