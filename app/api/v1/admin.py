from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, g

from app.core.auth import role_required
from app.data.repositories.audit_log_repository import AuditLogRepository
from app.services.audit_service import AuditService

bp = Blueprint("admin_audit", __name__, url_prefix="/api/v1")


def _get_audit_service() -> AuditService:
    repo = AuditLogRepository(g.db_session)
    return AuditService(repo)


def _parse_filters() -> dict:
    filters = {}
    for key in ("actor_id", "action", "entity_type"):
        val = request.args.get(key)
        if val:
            filters[key] = val
    from_date = request.args.get("from_date")
    if from_date:
        filters["from_date"] = datetime.fromisoformat(from_date.replace(" ", "+"))
    to_date = request.args.get("to_date")
    if to_date:
        filters["to_date"] = datetime.fromisoformat(to_date.replace(" ", "+"))
    return filters


def _serialize_entry(entry) -> dict:
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "actor_id": entry.actor_id,
        "actor_type": entry.actor_type,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "details": entry.details,
        "request_id": entry.request_id,
    }


@bp.route("/admin/audit-log", methods=["GET"])
@role_required("admin")
def list_audit_log():
    filters = _parse_filters()
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    service = _get_audit_service()
    result = service.get_entries(filters, limit=limit, offset=offset)

    return jsonify({
        "items": [_serialize_entry(e) for e in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200


@bp.route("/admin/audit-log/export", methods=["GET"])
@role_required("admin")
def export_audit_log():
    filters = _parse_filters()
    service = _get_audit_service()
    entries = service.export_entries(filters)
    return jsonify([_serialize_entry(e) for e in entries]), 200
