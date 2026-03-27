from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required
from app.core.errors import NotFoundError, ForbiddenError
from app.data.repositories.order_repository import OrderRepository
from app.data.db.models.order import OrderModel, OrderItemModel

bp = Blueprint("resources", __name__, url_prefix="/api/v1")


def _serialize_resource(item, order):
    return {
        "item_id": item.id,
        "template_slug": item.template_slug,
        "template_version": item.template_version,
        "display_name": item.display_name,
        "parameters": item.parameters,
        "order_id": order.id,
        "order_number": order.order_number,
        "provisioned_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@bp.route("/resources", methods=["GET"])
@login_required
def list_resources():
    session = g.db_session
    user = g.current_user

    q = (
        session.query(OrderItemModel, OrderModel)
        .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
        .filter(
            OrderModel.status == "done",
            OrderItemModel.provisioning_status == "done",
        )
    )

    if not user.is_admin:
        q = q.filter(OrderModel.requester_id == user.username)

    service_type = request.args.get("service_type")
    if service_type:
        from app.data.db.models.service_template import ServiceTemplateModel
        q = q.join(
            ServiceTemplateModel,
            (ServiceTemplateModel.slug == OrderItemModel.template_slug)
            & (ServiceTemplateModel.version == OrderItemModel.template_version),
        ).filter(ServiceTemplateModel.type == service_type)

    results = q.all()
    items = [_serialize_resource(item, order) for item, order in results]

    return jsonify({"items": items}), 200


@bp.route("/resources/<item_id>", methods=["GET"])
@login_required
def get_resource(item_id):
    session = g.db_session
    user = g.current_user

    result = (
        session.query(OrderItemModel, OrderModel)
        .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
        .filter(
            OrderItemModel.id == item_id,
            OrderModel.status == "done",
            OrderItemModel.provisioning_status == "done",
        )
        .first()
    )

    if result is None:
        raise NotFoundError("Resource not found.")

    item, order = result

    if not user.is_admin and order.requester_id != user.username:
        raise ForbiddenError("Keine Berechtigung.")

    return jsonify(_serialize_resource(item, order)), 200
