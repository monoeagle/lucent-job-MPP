import logging

from flask import Blueprint, jsonify, request, g, current_app

logger = logging.getLogger(__name__)

from app.core.auth import login_required
from app.core.helpers import cap_limit
from app.core.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.tenant_repository import TenantRepository
from app.services.catalog_service import CatalogService
from app.services.context_service import ContextService
from app.services.order_service import OrderService

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
    repo = OrderRepository(g.db_session)
    groups = repo.list_groups(order.id)
    grouped_item_ids = set()
    serialized_groups = []
    for grp in groups:
        serialized_groups.append(_serialize_group(grp))
        for item in grp.items:
            grouped_item_ids.add(item.id)

    ungrouped = [_serialize_item(i) for i in order.items if i.id not in grouped_item_ids]

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
        "groups": serialized_groups,
        "ungrouped_items": ungrouped,
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
        "group_id": item.group_id,
        "quantity": item.quantity,
        "instance_parameters": item.instance_parameters,
    }


def _serialize_group(group) -> dict:
    return {
        "id": group.id,
        "order_id": group.order_id,
        "name": group.name,
        "description": group.description,
        "position": group.position,
        "items": [_serialize_item(i) for i in group.items],
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
    limit = cap_limit(request.args.get("limit", 20, type=int))
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


# Import submodules to register their routes on bp
from app.api.v1 import order_items  # noqa: F401, E402
from app.api.v1 import order_groups  # noqa: F401, E402
from app.api.v1 import order_actions  # noqa: F401, E402
