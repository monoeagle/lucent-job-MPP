"""Order item management endpoints (add, update, remove, reorder)."""

import logging

from flask import jsonify, request, g

from app.core.auth import login_required
from app.core.errors import NotFoundError, ConflictError
from app.api.v1.orders import bp, _get_service, _get_repo, _serialize_item, _serialize_order, _check_owner

logger = logging.getLogger(__name__)


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
            quantity=data.get("quantity", 1),
            instance_parameters=data.get("instance_parameters"),
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg or "disabled" in msg:
            from app.core.errors import ValidationError
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

    # Handle group_id assignment
    if "group_id" in data:
        try:
            service.assign_item_to_group(
                order_id=order_id,
                item_id=item_id,
                requester_id=g.current_user.username,
                group_id=data["group_id"],
            )
        except ValueError as e:
            raise ConflictError(str(e))

    if "parameters" in data:
        try:
            service.update_item(
                order_id=order_id,
                item_id=item_id,
                requester_id=g.current_user.username,
                parameters=data["parameters"],
            )
        except ValueError as e:
            raise ConflictError(str(e))

    # Re-fetch item for response
    repo = _get_repo()
    item = repo.get_item_by_id(item_id)
    return jsonify({"item": _serialize_item(item)}), 200


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
