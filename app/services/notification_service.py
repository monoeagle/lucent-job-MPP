import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.data.db.models.notification import NotificationModel


class NotificationService:
    def __init__(self, session: Session):
        self.session = session

    def send(self, event_type: str, recipient_email: str,
             recipient_id: str | None, subject: str, body: str) -> NotificationModel:
        now = datetime.now(timezone.utc)
        notification = NotificationModel(
            id=str(uuid.uuid4()),
            event_type=event_type,
            recipient_email=recipient_email,
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            status="sent",
            attempts=0,
            created_at=now,
            sent_at=now,
        )
        self.session.add(notification)
        self.session.commit()
        return notification

    def list_notifications(self, recipient_id: str | None = None,
                           status: str | None = None,
                           limit: int = 50, offset: int = 0) -> dict:
        q = self.session.query(NotificationModel)
        if recipient_id is not None:
            q = q.filter(NotificationModel.recipient_id == recipient_id)
        if status is not None:
            q = q.filter(NotificationModel.status == status)
        total = q.count()
        items = q.order_by(NotificationModel.created_at.desc()).offset(offset).limit(limit).all()
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_notification(self, notification_id: str) -> NotificationModel | None:
        return self.session.query(NotificationModel).filter_by(id=notification_id).first()

    def mark_read(self, notification_id: str, user_id: str) -> NotificationModel:
        notification = self.get_notification(notification_id)
        if notification is None:
            raise KeyError(f"Notification {notification_id} not found")
        if notification.recipient_id != user_id:
            raise PermissionError("Not allowed to mark another user's notification as read")
        if notification.read_at is None:
            notification.read_at = datetime.now(timezone.utc)
            self.session.commit()
        return notification

    def mark_all_read(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        result = self.session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.recipient_id == user_id,
                NotificationModel.read_at.is_(None),
            )
            .values(read_at=now)
        )
        self.session.commit()
        return result.rowcount

    def unread_count(self, user_id: str) -> int:
        return (
            self.session.query(NotificationModel)
            .filter(
                NotificationModel.recipient_id == user_id,
                NotificationModel.read_at.is_(None),
            )
            .count()
        )
