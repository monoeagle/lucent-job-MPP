# app/api/v1/approvals.py
from flask import Blueprint, jsonify, request, g, current_app

from app.core.auth import login_required, role_required
from app.core.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError
from app.data.repositories.approval_repository import ApprovalRepository
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository
from app.services.approval_service import ApprovalService

admin_bp = Blueprint("approval_admin", __name__, url_prefix="/api/v1")
approvals_bp = Blueprint("approvals", __name__, url_prefix="/api/v1")


def _get_approval_repo():
    return ApprovalRepository(g.db_session)


def _get_order_repo():
    return OrderRepository(g.db_session)


def _get_template_repo():
    return TemplateRepository(g.db_session)


def _get_approval_service():
    return ApprovalService(
        approval_repo=_get_approval_repo(),
        order_repo=_get_order_repo(),
        template_repo=_get_template_repo(),
        allow_self_approval=current_app.config.get("APPROVAL_ALLOW_SELF_APPROVAL", False),
        default_deadline_hours=current_app.config.get("APPROVAL_DEFAULT_DEADLINE_HOURS", 48),
    )


def _serialize_rule(rule):
    return {
        "id": rule.id,
        "name": rule.name,
        "rule_type": rule.rule_type,
        "threshold_eur": float(rule.threshold_eur) if rule.threshold_eur is not None else None,
        "service_type_slug": rule.service_type_slug,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def _serialize_request(req):
    return {
        "id": req.id,
        "order_id": req.order_id,
        "status": req.status,
        "approval_rule_ids": req.approval_rule_ids,
        "requested_at": req.requested_at.isoformat() if req.requested_at else None,
        "deadline_at": req.deadline_at.isoformat() if req.deadline_at else None,
        "decided_by": req.decided_by,
        "decided_at": req.decided_at.isoformat() if req.decided_at else None,
        "decision_reason": req.decision_reason,
    }


# ── Admin: Approval Rules ────────────────────────────────────────


@admin_bp.route("/admin/approval-rules", methods=["POST"])
@role_required("admin")
def create_rule():
    data = request.get_json() or {}
    repo = _get_approval_repo()
    rule = repo.create_rule(
        name=data.get("name", ""),
        rule_type=data.get("rule_type", ""),
        threshold_eur=data.get("threshold_eur"),
        service_type_slug=data.get("service_type_slug"),
        is_active=data.get("is_active", True),
    )
    return jsonify(_serialize_rule(rule)), 201


@admin_bp.route("/admin/approval-rules", methods=["GET"])
@role_required("admin")
def list_rules():
    repo = _get_approval_repo()
    rules = repo.list_rules()
    return jsonify([_serialize_rule(r) for r in rules]), 200


@admin_bp.route("/admin/approval-rules/<rule_id>", methods=["PATCH"])
@role_required("admin")
def update_rule(rule_id):
    repo = _get_approval_repo()
    rule = repo.get_rule(rule_id)
    if rule is None:
        raise NotFoundError("Approval rule not found.")

    data = request.get_json() or {}
    fields = {}
    for key in ("name", "rule_type", "threshold_eur", "service_type_slug", "is_active"):
        if key in data:
            fields[key] = data[key]

    updated = repo.update_rule(rule_id, **fields)
    return jsonify(_serialize_rule(updated)), 200


@admin_bp.route("/admin/approval-rules/<rule_id>", methods=["DELETE"])
@role_required("admin")
def delete_rule(rule_id):
    repo = _get_approval_repo()
    try:
        repo.delete_rule(rule_id)
    except repo.RuleInUseError:
        raise ConflictError("Cannot delete rule: referenced by pending approval requests.")
    return "", 204


# ── Admin: Approval Settings ─────────────────────────────────────


@admin_bp.route("/admin/approval-settings", methods=["GET"])
@role_required("admin")
def get_settings():
    return jsonify({
        "default_deadline_hours": current_app.config.get("APPROVAL_DEFAULT_DEADLINE_HOURS", 48),
        "allow_self_approval": current_app.config.get("APPROVAL_ALLOW_SELF_APPROVAL", False),
    }), 200


@admin_bp.route("/admin/approval-settings", methods=["PUT"])
@role_required("admin")
def update_settings():
    data = request.get_json() or {}
    if "default_deadline_hours" in data:
        current_app.config["APPROVAL_DEFAULT_DEADLINE_HOURS"] = int(data["default_deadline_hours"])
    if "allow_self_approval" in data:
        current_app.config["APPROVAL_ALLOW_SELF_APPROVAL"] = bool(data["allow_self_approval"])

    return jsonify({
        "default_deadline_hours": current_app.config.get("APPROVAL_DEFAULT_DEADLINE_HOURS", 48),
        "allow_self_approval": current_app.config.get("APPROVAL_ALLOW_SELF_APPROVAL", False),
    }), 200


# ── Workflow: Approval Requests ──────────────────────────────────


@approvals_bp.route("/approvals", methods=["GET"])
@login_required
def list_approvals():
    repo = _get_approval_repo()
    order_repo = _get_order_repo()
    user = g.current_user

    pending = repo.list_pending_requests()

    results = []
    for req in pending:
        order = order_repo.get_by_id(req.order_id)
        if order is None:
            continue

        # Approver/admin see all; requester sees only own orders
        if user.has_role("approver") or user.is_admin:
            pass
        elif order.requester_id == user.username:
            pass
        else:
            continue

        item = _serialize_request(req)
        item["requester_id"] = order.requester_id
        results.append(item)

    return jsonify(results), 200


@approvals_bp.route("/approvals/<approval_id>", methods=["GET"])
@login_required
def get_approval(approval_id):
    repo = _get_approval_repo()
    order_repo = _get_order_repo()
    user = g.current_user

    req = repo.get_request(approval_id)
    if req is None:
        raise NotFoundError("Approval request not found.")

    order = order_repo.get_by_id(req.order_id)

    # Access: approver, admin, or order owner
    if not (user.has_role("approver") or user.is_admin or
            (order and order.requester_id == user.username)):
        raise ForbiddenError("Keine Berechtigung.")

    result = _serialize_request(req)
    if order:
        result["requester_id"] = order.requester_id
    return jsonify(result), 200


@approvals_bp.route("/approvals/<approval_id>/approve", methods=["POST"])
@login_required
def approve_request(approval_id):
    user = g.current_user

    # Only approver or admin can approve
    if not (user.has_role("approver") or user.is_admin):
        raise ForbiddenError("Keine Berechtigung.")

    data = request.get_json() or {}
    service = _get_approval_service()

    try:
        result = service.approve(approval_id, user.username, reason=data.get("reason"))
    except ApprovalService.SelfApprovalError:
        raise ForbiddenError("Cannot approve your own order.")
    except ApprovalService.ConflictError as e:
        raise ConflictError(str(e))

    # Transition order to approved
    order_repo = _get_order_repo()
    order_repo.update_order_status(result.order_id, "approved")

    return jsonify(_serialize_request(result)), 200


@approvals_bp.route("/approvals/<approval_id>/reject", methods=["POST"])
@login_required
def reject_request(approval_id):
    user = g.current_user

    if not (user.has_role("approver") or user.is_admin):
        raise ForbiddenError("Keine Berechtigung.")

    data = request.get_json() or {}
    reason = data.get("reason", "")

    service = _get_approval_service()
    try:
        result = service.reject(approval_id, user.username, reason)
    except ValueError:
        raise ValidationError("A reason is required to reject an approval request.")
    except ApprovalService.ConflictError as e:
        raise ConflictError(str(e))

    # Transition order to rejected
    order_repo = _get_order_repo()
    order_repo.update_order_status(result.order_id, "rejected")

    return jsonify(_serialize_request(result)), 200
