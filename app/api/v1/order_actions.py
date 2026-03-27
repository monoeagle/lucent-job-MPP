"""Order action endpoints (validate, submit, status, export)."""

import logging
from datetime import datetime, timezone

from flask import jsonify, g, current_app

from app.core.auth import login_required
from app.core.errors import NotFoundError, ConflictError
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.dispatch_log_repository import DispatchLogRepository
from app.services.provisioning_service import ProvisioningService
from app.api.v1.orders import bp, _get_service, _get_repo, _serialize_item, _check_owner

logger = logging.getLogger(__name__)

_READONLY_STATUSES = {"provisioning", "done", "failed"}


def _build_export_item(item, export_data):
    """Build a single export item dict from order item + service export data."""
    return {
        "order_item_id": item.id,
        "template_slug": item.template_slug,
        "template_version": item.template_version,
        "position": item.position,
        "module_source": export_data["module_source"],
        "variables": export_data["variables"],
        "error": export_data.get("error"),
    }


@bp.route("/orders/<order_id>/validate", methods=["POST"])
@login_required
def validate_order(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    service = _get_service()
    try:
        result = service.validate_order(order_id, g.current_user.username)
    except ValueError as e:
        raise ConflictError(str(e))

    # Enrich item_results with item details
    items_by_id = {i.id: i for i in order.items}
    item_results = []
    for r in result["items"]:
        item = items_by_id.get(r["item_id"])
        item_results.append({
            "item_id": r["item_id"],
            "template_slug": item.template_slug if item else None,
            "template_version": item.template_version if item else None,
            "position": item.position if item else None,
            "validation_state": r["validation_state"],
            "violations": r["violations"],
        })

    all_valid = result["status"] == "validated"
    return jsonify({
        "order_id": order_id,
        "order_status": result["status"],
        "all_valid": all_valid,
        "item_results": item_results,
    }), 200


@bp.route("/orders/<order_id>/submit", methods=["POST"])
@login_required
def submit_order(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    service = _get_service()
    try:
        result = service.submit_order(order_id, g.current_user.username)
    except ValueError as e:
        raise ConflictError(str(e))

    submitted = result["order"]

    # Check if approval is needed
    from app.data.repositories.approval_repository import ApprovalRepository
    from app.services.approval_service import ApprovalService
    approval_repo = ApprovalRepository(g.db_session)
    order_repo = OrderRepository(g.db_session)
    template_repo = TemplateRepository(g.db_session)
    approval_service = ApprovalService(
        approval_repo=approval_repo,
        order_repo=order_repo,
        template_repo=template_repo,
        allow_self_approval=current_app.config.get("APPROVAL_ALLOW_SELF_APPROVAL", False),
        default_deadline_hours=current_app.config.get("APPROVAL_DEFAULT_DEADLINE_HOURS", 48),
    )

    matched_rules = approval_service.evaluate_rules(submitted)
    if matched_rules:
        approval_service.create_approval_request(submitted.id, matched_rules)
        order_repo.update_order_status(submitted.id, "pending_approval")
        submitted = order_repo.get_by_id(submitted.id)
    else:
        # No approval needed -- trigger dispatch if GitLab client is configured
        gitlab_client = getattr(current_app, "gitlab_client", None)
        if gitlab_client is not None:
            try:
                dispatch_log_repo = DispatchLogRepository(g.db_session)
                prov_service = ProvisioningService(
                    order_repo, dispatch_log_repo, gitlab_client,
                )
                prov_service.dispatch_order(order_id)
                submitted = order_repo.get_by_id(order_id)
            except Exception:
                logger.exception("Dispatch failed for order %s", order_id)

    # Send notification
    from app.services.notification_service import NotificationService
    try:
        notif_service = NotificationService(g.db_session)
        notif_service.create_event_notification(
            event_type="order_submitted",
            recipient_id=submitted.requester_id,
            recipient_email=f"{submitted.requester_id}@marketplace.local",
            context={
                "order_number": submitted.order_number,
                "title": submitted.title or "",
            },
        )
    except Exception:
        logger.exception("Notification failed for order %s", submitted.order_number)

    # Create subscriptions
    from app.data.repositories.subscription_repository import SubscriptionRepository
    from app.services.subscription_service import SubscriptionService
    try:
        sub_repo = SubscriptionRepository(g.db_session)
        sub_service = SubscriptionService(sub_repo)
        sub_service.create_from_order(submitted, template_costs={})
    except Exception:
        logger.exception("Subscription creation failed for order %s", submitted.order_number)

    return jsonify({
        "order_id": submitted.id,
        "order_number": submitted.order_number,
        "status": submitted.status,
        "item_count": len(submitted.items),
        "submitted_at": submitted.submitted_at.isoformat() if submitted.submitted_at else None,
        "message": "Ihre Bestellung wurde erfolgreich eingereicht.",
    }), 200


@bp.route("/orders/<order_id>/status", methods=["GET"])
@login_required
def get_order_status(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    item_statuses = []
    for item in order.items:
        item_statuses.append({
            "item_id": item.id,
            "position": item.position,
            "template_slug": item.template_slug,
            "provisioning_status": "not_started",
            "job_id": None,
        })

    return jsonify({
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "item_statuses": item_statuses,
        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }), 200


@bp.route("/orders/<order_id>/export/tofu", methods=["GET"])
@login_required
def export_order_tofu(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    if order.status == "draft":
        raise ConflictError("Cannot export a draft order.")

    service = _get_service()
    result = service.export_tofu(order_id, g.current_user.username)

    readonly_notice = None
    if order.status in _READONLY_STATUSES:
        readonly_notice = f"Order is {order.status}. Export is read-only."

    # Build lookup for order_item_id and position by slug+version
    item_lookup = {}
    for item in order.items:
        key = (item.template_slug, item.template_version)
        if key not in item_lookup:
            item_lookup[key] = item

    items = []
    for export_data in result["items"]:
        key = (export_data["template_slug"], export_data["template_version"])
        source_item = item_lookup.get(key)
        items.append({
            "order_item_id": source_item.id if source_item else None,
            "template_slug": export_data["template_slug"],
            "template_version": export_data["template_version"],
            "position": source_item.position if source_item else None,
            "module_source": export_data["module_source"],
            "variables": export_data["variables"],
            "error": export_data.get("error"),
        })

    return jsonify({
        "order_id": order.id,
        "order_number": order.order_number,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "readonly_notice": readonly_notice,
        "items": items,
    }), 200


@bp.route("/orders/<order_id>/items/<item_id>/export/tofu", methods=["GET"])
@login_required
def export_item_tofu(order_id, item_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    if order.status == "draft":
        raise ConflictError("Cannot export a draft order.")

    item = next((i for i in order.items if i.id == item_id), None)
    if item is None:
        raise NotFoundError("Item not found.")

    service = _get_service()
    result = service.export_tofu(order_id, g.current_user.username)

    export_data = next(
        (e for e in result["items"] if e["template_slug"] == item.template_slug
         and e["template_version"] == item.template_version),
        None,
    )
    if export_data is None:
        raise NotFoundError("Export data not found for item.")

    return jsonify(_build_export_item(item, export_data)), 200
