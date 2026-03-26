from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required
from app.core.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService

bp = Blueprint("orders", __name__, url_prefix="/api/v1")


def _get_service() -> OrderService:
    repo = OrderRepository(g.db_session)
    template_repo = TemplateRepository(g.db_session)
    catalog_service = CatalogService(template_repo)
    return OrderService(repo, template_repo, catalog_service)


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

    service = _get_service()
    try:
        result = service.create_order(
            requester_id=g.current_user.username,
            title=title,
            business_reason=business_reason,
            desired_date=desired_date,
        )
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
