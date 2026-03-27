import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.data.db.models.notification import NotificationModel


class NotificationService:
    EVENT_TEMPLATES = {
        "order_submitted": {
            "subject": "Bestellung {order_number} eingereicht",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde erfolgreich eingereicht.",
        },
        "order_approved": {
            "subject": "Bestellung {order_number} genehmigt",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde genehmigt.",
        },
        "order_rejected": {
            "subject": "Bestellung {order_number} abgelehnt",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde abgelehnt. Grund: {reason}",
        },
        "order_provisioned": {
            "subject": "Bestellung {order_number} bereitgestellt",
            "body": "Ihre Bestellung '{title}' ({order_number}) wurde erfolgreich bereitgestellt.",
        },
        "order_failed": {
            "subject": "Bestellung {order_number} fehlgeschlagen",
            "body": "Bei der Bereitstellung von '{title}' ({order_number}) ist ein Fehler aufgetreten.",
        },
        "approval_requested": {
            "subject": "Genehmigung erforderlich: {order_number}",
            "body": "Bestellung {order_number} von {requester} erfordert Ihre Genehmigung.",
        },
        "approval_decided": {
            "subject": "Genehmigung entschieden: {order_number}",
            "body": "Die Genehmigung fuer Bestellung {order_number} wurde entschieden.",
        },
        "template_deprecated": {
            "subject": "Service-Template veraltet: {template_name}",
            "body": "Das Template '{template_name}' wurde als veraltet markiert.",
        },
        "system_maintenance": {
            "subject": "Wartungshinweis: {title}",
            "body": "{message}",
        },
    }

    def __init__(self, session: Session, email_sender=None):
        self.session = session
        self.email_sender = email_sender

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

    def create_event_notification(self, event_type: str, recipient_id: str,
                                   recipient_email: str, context: dict) -> NotificationModel:
        defaults = {"reason": "", "message": "", "title": "", "template_name": "",
                     "order_number": "", "requester": ""}
        ctx = {**defaults, **context}
        tmpl = self.EVENT_TEMPLATES.get(event_type, {
            "subject": event_type,
            "body": str(context),
        })
        subject = tmpl["subject"].format_map(ctx)
        body = tmpl["body"].format_map(ctx)

        notification = self.send(event_type, recipient_email, recipient_id, subject, body)

        if self.email_sender:
            self.email_sender.send(recipient_email, subject, body)

        return notification
