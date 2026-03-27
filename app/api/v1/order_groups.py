"""Order group management endpoints (create, update, delete, reorder)."""

import logging

from flask import jsonify, request, g

from app.core.auth import login_required
from app.core.errors import NotFoundError, ConflictError, ValidationError
from app.data.repositories.order_repository import DuplicateGroupError, GroupNotEmptyError
from app.api.v1.orders import bp, _get_service, _get_repo, _serialize_group, _check_owner

logger = logging.getLogger(__name__)


@bp.route("/orders/<order_id>/groups", methods=["POST"])
@login_required
def create_group(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    data = request.get_json() or {}
    service = _get_service()
    try:
        result = service.create_group(
            order_id=order_id,
            requester_id=g.current_user.username,
            name=data.get("name", ""),
            description=data.get("description"),
        )
    except DuplicateGroupError as e:
        raise ConflictError(str(e))
    except ValueError as e:
        msg = str(e)
        if "draft" in msg.lower():
            raise ConflictError(msg)
        raise ValidationError(msg)

    return jsonify({"group": _serialize_group(result["group"])}), 201


@bp.route("/orders/<order_id>/groups/<group_id>", methods=["PATCH"])
@login_required
def update_group(order_id, group_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    data = request.get_json() or {}
    service = _get_service()
    fields = {}
    for key in ("name", "description"):
        if key in data:
            fields[key] = data[key]

    try:
        result = service.update_group(
            order_id=order_id,
            group_id=group_id,
            requester_id=g.current_user.username,
            **fields,
        )
    except ValueError as e:
        raise ConflictError(str(e))

    return jsonify({"group": _serialize_group(result["group"])}), 200


@bp.route("/orders/<order_id>/groups/<group_id>", methods=["DELETE"])
@login_required
def delete_group(order_id, group_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    service = _get_service()
    try:
        service.delete_group(
            order_id=order_id,
            group_id=group_id,
            requester_id=g.current_user.username,
        )
    except GroupNotEmptyError as e:
        raise ConflictError(str(e))
    except ValueError as e:
        raise ConflictError(str(e))

    return "", 204


@bp.route("/orders/<order_id>/groups/reorder", methods=["PUT"])
@login_required
def reorder_groups(order_id):
    repo = _get_repo()
    order = repo.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found.")
    _check_owner(order)

    if order.status != "draft":
        raise ConflictError("Order must be in draft status to reorder groups.")

    data = request.get_json() or {}
    positions = data.get("positions", [])
    repo.reorder_groups(order_id, positions)

    groups = repo.list_groups(order_id)
    return jsonify({"groups": [_serialize_group(g_) for g_ in groups]}), 200
