import logging

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, repo):
        self.repo = repo

    def log(self, actor_id: str | None, action: str, entity_type: str,
            entity_id: str | None = None, details: dict | None = None) -> None:
        """Fire-and-forget audit logging. Never raises."""
        try:
            actor_type = "system" if actor_id is None else "user"
            self.repo.create_entry(
                actor_id=actor_id,
                actor_type=actor_type,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
        except Exception:
            logger.exception("Failed to write audit log entry")

    def get_entries(self, filters: dict, limit: int = 50, offset: int = 0) -> dict:
        return self.repo.list_entries(
            actor_id=filters.get("actor_id"),
            action=filters.get("action"),
            entity_type=filters.get("entity_type"),
            from_date=filters.get("from_date"),
            to_date=filters.get("to_date"),
            limit=limit,
            offset=offset,
        )

    def export_entries(self, filters: dict) -> list:
        return self.repo.list_all_entries(
            actor_id=filters.get("actor_id"),
            action=filters.get("action"),
            entity_type=filters.get("entity_type"),
            from_date=filters.get("from_date"),
            to_date=filters.get("to_date"),
        )
