import logging

from app.core.errors import NotFoundError, ForbiddenError
from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.service_template import ServiceTemplateModel

logger = logging.getLogger(__name__)


def _serialize_resource(item, order) -> dict:
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


class ResourceService:
    def __init__(self, session):
        self.session = session

    def list_resources(self, user_id: str, is_admin: bool, service_type: str | None = None) -> dict:
        q = (
            self.session.query(OrderItemModel, OrderModel)
            .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
            .filter(
                OrderModel.status == "done",
                OrderItemModel.provisioning_status == "done",
            )
        )

        if not is_admin:
            q = q.filter(OrderModel.requester_id == user_id)

        if service_type:
            q = q.join(
                ServiceTemplateModel,
                (ServiceTemplateModel.slug == OrderItemModel.template_slug)
                & (ServiceTemplateModel.version == OrderItemModel.template_version),
            ).filter(ServiceTemplateModel.type == service_type)

        results = q.all()
        items = [_serialize_resource(item, order) for item, order in results]
        return {"items": items}

    def get_resource(self, item_id: str, user_id: str, is_admin: bool) -> dict:
        result = (
            self.session.query(OrderItemModel, OrderModel)
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

        if not is_admin and order.requester_id != user_id:
            raise ForbiddenError("Keine Berechtigung.")

        return _serialize_resource(item, order)
