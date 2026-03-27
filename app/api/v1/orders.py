from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, g, current_app

from app.core.auth import login_required
from app.core.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.tenant_repository import TenantRepository
from app.services.catalog_service import CatalogService
from app.services.context_service import ContextService
from app.services.order_service import OrderService
from app.data.repositories.dispatch_log_repository import DispatchLogRepository
from app.services.provisioning_service import ProvisioningService

bp = Blueprint("orders", __name__, url_prefix="/api/v1")


def _get_context_service():
    cmdb_client = getattr(current_app, "cmdb_client", None)
    if cmdb_client is None:
        return None
    tenant_repo = TenantRepository(g.db_session)
    return ContextService(cmdb_client, tenant_repo=tenant_repo)


def _get_service() -> OrderService:
    repo = OrderRepository(g.db_session)
    template_repo = TemplateRepository(g.db_session)
    catalog_service = CatalogService(template_repo)
    context_service = _get_context_service()
    return OrderService(repo, template_repo, catalog_service, context_service)


def _get_repo() -> OrderRepository:
    return OrderRepository(g.db_session)


def _serialize_order(order) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "requester_id": order.requester_id,
        "status": order.status,
        "title": order.title,
        "business_reason": order.business_reason,
        "desired_date": order.desired_date,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        "context": order.context,
        "items": [_serialize_item(i) for i in order.items],
    }


def _serialize_item(item) -> dict:
    return {
        "id": item.id,
        "order_id": item.order_id,
        "template_slug": item.template_slug,
        "template_version": item.template_version,
        "display_name": item.display_name,
        "parameters": item.parameters,
        "position": item.position,
        "validation_state": item.validation_state,
        "validation_errors": item.validation_errors,
    }


def _check_owner(order):
    """Raise 403 if current user is not the owner and not admin."""
    user = g.current_user
    if order.requester_id != user.username and not user.is_admin:
        raise ForbiddenError("Keine Berechtigung.")


@bp.route("/orders", methods=["POST"])
@login_required
def create_order():
    data = request.get_json() or {}
    title = data.get("title", "")
    business_reason = data.get("business_reason")
    desired_date = data.get("desired_date")
    context = data.get("context")

    service = _get_service()
    try:
        result = service.create_order(
            requester_id=g.current_user.username,
            title=title,
            business_reason=business_reason,
            desired_date=desired_date,
            context=context,
        )
    except ContextService.ContextValidationError as e:
        return jsonify({
            "error_code": "CONTEXT_VALIDATION_FAILED",
            "message": "Context validation failed.",
            "violations": e.violations,
        }), 400
    except ContextService.CmdbUnavailableError:
        return jsonify({
            "error_code": "CMDB_UNAVAILABLE",
            "message": "CMDB service is unavailable.",
        }), 503
    except ValueError as e:
        raise ValidationError(str(e))

    return jsonify(_serialize_order(result["order"])), 201


@bp.route("/orders/<order_id>", methods=["GET"])
@login_required
def get_order(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)
    return jsonify(_serialize_order(order)), 200


@bp.route("/orders", methods=["GET"])
@login_required
def list_orders():
    repo = _get_repo()
    status = request.args.get("status")
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    user = g.current_user
    requester_id = None if user.is_admin else user.username

    result = repo.list_orders(
        requester_id=requester_id,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return jsonify({
        "items": [_serialize_order(o) for o in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200


@bp.route("/orders/<order_id>", methods=["PATCH"])
@login_required
def update_order(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    if order.status != "draft":
        raise ConflictError("Order must be in draft status to update.")

    data = request.get_json() or {}
    fields = {}
    for key in ("title", "business_reason", "desired_date"):
        if key in data:
            fields[key] = data[key]

    updated = repo.update_order(order_id, **fields)
    return jsonify(_serialize_order(updated)), 200


@bp.route("/orders/<order_id>", methods=["DELETE"])
@login_required
def delete_order(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    if order.status != "draft":
        raise ConflictError("Order must be in draft status to delete.")

    repo.delete_order(order_id)
    return "", 204


# ── Item management endpoints ────────────────────────────────


@bp.route("/orders/<order_id>/items", methods=["POST"])
@login_required
def add_item(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    data = request.get_json() or {}
    service = _get_service()
    try:
        result = service.add_item(
            order_id=order_id,
            requester_id=g.current_user.username,
            template_slug=data.get("template_slug", ""),
            template_version=data.get("template_version", ""),
            parameters=data.get("parameters", {}),
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg or "disabled" in msg:
            raise ValidationError(msg)
        raise ConflictError(msg)

    body = {"item": _serialize_item(result["item"]), "warning": result.get("warning")}
    return jsonify(body), 201


@bp.route("/orders/<order_id>/items/<item_id>", methods=["PATCH"])
@login_required
def update_item(order_id, item_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    data = request.get_json() or {}
    service = _get_service()
    try:
        result = service.update_item(
            order_id=order_id,
            item_id=item_id,
            requester_id=g.current_user.username,
            parameters=data.get("parameters", {}),
        )
    except ValueError as e:
        raise ConflictError(str(e))

    return jsonify({"item": _serialize_item(result["item"])}), 200


@bp.route("/orders/<order_id>/items/<item_id>", methods=["DELETE"])
@login_required
def remove_item(order_id, item_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    if order.status != "draft":
        raise ConflictError("Order must be in draft status to remove items.")

    service = _get_service()
    service.remove_item(order_id, item_id, g.current_user.username)
    return "", 204


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
        # No approval needed — trigger dispatch if GitLab client is configured
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
                pass  # Dispatch failure should not block submit

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


@bp.route("/orders/<order_id>/items/positions", methods=["PUT"])
@login_required
def reorder_items(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    if order.status != "draft":
        raise ConflictError("Order must be in draft status to reorder items.")

    data = request.get_json() or {}
    positions = data.get("positions", [])
    repo.reorder_items(order_id, positions)

    # Re-fetch order to get updated positions
    order = repo.get_by_id(order_id)
    return jsonify(_serialize_order(order)), 200


# ── Export endpoints ─────────────────────────────────────────

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

    items = []
    for item, export_data in zip(order.items, result["items"]):
        items.append(_build_export_item(item, export_data))

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
