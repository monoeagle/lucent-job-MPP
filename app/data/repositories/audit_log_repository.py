import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.data.db.models.audit_log import AuditLogModel


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_entry(self, actor_id: str | None, actor_type: str,
                     action: str, entity_type: str,
                     entity_id: str | None = None,
                     details: dict | None = None,
                     request_id: str | None = None) -> AuditLogModel:
        entry = AuditLogModel(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            request_id=request_id,
        )
        self.session.add(entry)
        self.session.commit()
        return entry

    def list_entries(self, actor_id: str | None = None,
                     action: str | None = None,
                     entity_type: str | None = None,
                     from_date: datetime | None = None,
                     to_date: datetime | None = None,
                     limit: int = 50, offset: int = 0) -> dict:
        q = self.session.query(AuditLogModel)
        q = self._apply_filters(q, actor_id, action, entity_type, from_date, to_date)
        total = q.count()
        items = q.order_by(AuditLogModel.timestamp.desc()).offset(offset).limit(limit).all()
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def count_entries(self, actor_id: str | None = None,
                      action: str | None = None,
                      entity_type: str | None = None,
                      from_date: datetime | None = None,
                      to_date: datetime | None = None) -> int:
        q = self.session.query(AuditLogModel)
        q = self._apply_filters(q, actor_id, action, entity_type, from_date, to_date)
        return q.count()

    def list_all_entries(self, actor_id: str | None = None,
                         action: str | None = None,
                         entity_type: str | None = None,
                         from_date: datetime | None = None,
                         to_date: datetime | None = None) -> list[AuditLogModel]:
        q = self.session.query(AuditLogModel)
        q = self._apply_filters(q, actor_id, action, entity_type, from_date, to_date)
        return q.order_by(AuditLogModel.timestamp.desc()).all()

    @staticmethod
    def _apply_filters(q, actor_id, action, entity_type, from_date, to_date):
        if actor_id is not None:
            q = q.filter(AuditLogModel.actor_id == actor_id)
        if action is not None:
            q = q.filter(AuditLogModel.action == action)
        if entity_type is not None:
            q = q.filter(AuditLogModel.entity_type == entity_type)
        if from_date is not None:
            q = q.filter(AuditLogModel.timestamp >= from_date)
        if to_date is not None:
            q = q.filter(AuditLogModel.timestamp <= to_date)
        return q
