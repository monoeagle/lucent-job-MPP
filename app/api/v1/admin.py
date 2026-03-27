from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, g, current_app
from sqlalchemy import func

from app.core.auth import role_required
from app.core.helpers import cap_limit
from app.data.repositories.audit_log_repository import AuditLogRepository
from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.approval import ApprovalRequestModel
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
@role_required("superadmin")
def list_audit_log():
    filters = _parse_filters()
    limit = cap_limit(request.args.get("limit", 50, type=int))
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
@role_required("admin", "superadmin")
def export_audit_log():
    filters = _parse_filters()
    service = _get_audit_service()
    entries = service.export_entries(filters)
    return jsonify([_serialize_entry(e) for e in entries]), 200


@bp.route("/admin/dashboard", methods=["GET"])
@role_required("admin", "superadmin")
def admin_dashboard():
    session = g.db_session

    # Order counts by status
    all_statuses = ["draft", "validated", "submitted", "pending_approval",
                    "approved", "provisioning", "done", "cancelled", "rejected", "failed"]
    rows = (
        session.query(OrderModel.status, func.count(OrderModel.id))
        .group_by(OrderModel.status)
        .all()
    )
    counts_map = dict(rows)
    order_counts = {s: counts_map.get(s, 0) for s in all_statuses}

    # Pending approvals
    pending_approvals = (
        session.query(func.count(ApprovalRequestModel.id))
        .filter(ApprovalRequestModel.status == "pending")
        .scalar()
    )

    # Active resources (done items in done orders)
    active_resources = (
        session.query(func.count(OrderItemModel.id))
        .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
        .filter(
            OrderModel.status == "done",
            OrderItemModel.provisioning_status == "done",
        )
        .scalar()
    )

    # Recent orders (last 10)
    recent = (
        session.query(OrderModel)
        .order_by(OrderModel.created_at.desc())
        .limit(10)
        .all()
    )
    recent_orders = [
        {
            "order_id": o.id,
            "order_number": o.order_number,
            "title": o.title,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in recent
    ]

    # System health
    db_status = "ok"
    try:
        session.execute(func.now())
    except Exception:
        db_status = "unavailable"

    cmdb_status = "ok" if hasattr(current_app, "cmdb_client") else "unavailable"

    return jsonify({
        "order_counts": order_counts,
        "pending_approvals": pending_approvals,
        "active_resources": active_resources,
        "recent_orders": recent_orders,
        "system_health": {
            "database": db_status,
            "cmdb": cmdb_status,
        },
    }), 200


@bp.route("/admin/config", methods=["GET"])
@role_required("admin", "superadmin")
def get_system_config():
    cfg = current_app.config

    # DB connection check
    db_status = "ok"
    try:
        g.db_session.execute(func.now())
    except Exception:
        db_status = "error"

    db_url = cfg.get("DATABASE_URL", "")
    # mask password
    if "@" in db_url:
        before_at = db_url.split("@")[0]
        after_at = db_url.split("@")[1]
        user_part = before_at.rsplit(":", 1)[0] if ":" in before_at else before_at
        db_url = f"{user_part}:***@{after_at}"

    return jsonify({
        "auth": {
            "mode": cfg.get("AUTH_MODE", "unknown"),
            "status": "ok",
            "description": "Stub-Modus (lokale Testbenutzer)" if cfg.get("AUTH_MODE") == "stub" else "LDAP/AD-Anbindung",
        },
        "cmdb": {
            "mode": cfg.get("CMDB_MODE", "unknown"),
            "status": "ok",
            "stub_data_path": cfg.get("CMDB_STUB_DATA_PATH", ""),
            "description": "Stub-Modus (YAML-Dateien)" if cfg.get("CMDB_MODE") == "stub" else "Live-CMDB-Anbindung",
        },
        "database": {
            "url": db_url,
            "status": db_status,
        },
        "gitlab": {
            "url": cfg.get("GITLAB_URL", "") or "(nicht konfiguriert)",
            "project_id": cfg.get("GITLAB_PROJECT_ID", ""),
            "status": "ok" if cfg.get("GITLAB_URL") else "nicht konfiguriert",
        },
        "email": {
            "status": "nicht konfiguriert",
            "description": "SMTP nicht konfiguriert — Benachrichtigungen nur In-App",
        },
        "dsgvo": {
            "anonymize": cfg.get("DSGVO_ANONYMIZE", False),
        },
        "approvals": {
            "default_deadline_hours": cfg.get("APPROVAL_DEFAULT_DEADLINE_HOURS", 48),
            "allow_self_approval": cfg.get("APPROVAL_ALLOW_SELF_APPROVAL", False),
        },
    }), 200


@bp.route("/admin/dsgvo", methods=["GET"])
@role_required("superadmin")
def get_dsgvo_status():
    enabled = current_app.config.get("DSGVO_ANONYMIZE", False)
    return jsonify({"dsgvo_anonymize": enabled}), 200


@bp.route("/admin/dsgvo", methods=["PUT"])
@role_required("superadmin")
def set_dsgvo_status():
    data = request.get_json() or {}
    enabled = data.get("dsgvo_anonymize", False)
    current_app.config["DSGVO_ANONYMIZE"] = bool(enabled)
    return jsonify({"dsgvo_anonymize": bool(enabled), "message": "DSGVO-Modus aktualisiert."}), 200
