from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required, role_required
from app.services.notification_service import NotificationService

admin_bp = Blueprint("admin_notifications", __name__, url_prefix="/api/v1")
bp = Blueprint("notifications", __name__, url_prefix="/api/v1")


def _get_service() -> NotificationService:
    return NotificationService(g.db_session)


def _serialize(notif) -> dict:
    return {
        "id": notif.id,
        "event_type": notif.event_type,
        "recipient_email": notif.recipient_email,
        "recipient_id": notif.recipient_id,
        "subject": notif.subject,
        "body": notif.body,
        "status": notif.status,
        "attempts": notif.attempts,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
        "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
        "error_message": notif.error_message,
    }


@admin_bp.route("/admin/notifications", methods=["GET"])
@role_required("admin")
def admin_list_notifications():
    service = _get_service()
    status = request.args.get("status")
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    result = service.list_notifications(status=status, limit=limit, offset=offset)
    return jsonify({
        "items": [_serialize(n) for n in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200


@bp.route("/notifications", methods=["GET"])
@login_required
def list_own_notifications():
    user = g.current_user
    service = _get_service()
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    result = service.list_notifications(
        recipient_id=user.username, limit=limit, offset=offset,
    )
    return jsonify({
        "items": [_serialize(n) for n in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200
