import logging

from app.data.db.models.order import OrderModel
from app.data.db.models.service_template import ServiceTemplateModel

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, session):
        self.session = session

    def search(self, query: str, user_id: str, is_admin: bool, limit: int = 5) -> dict:
        pattern = f"%{query}%"
        return {
            "query": query,
            "orders": self._search_orders(pattern, user_id, is_admin, limit),
            "templates": self._search_templates(pattern, limit),
            "resources": [],
        }

    def _search_orders(self, pattern: str, user_id: str, is_admin: bool, limit: int) -> list[dict]:
        q = self.session.query(OrderModel).filter(
            (OrderModel.title.ilike(pattern)) | (OrderModel.order_number.ilike(pattern))
        )
        if not is_admin:
            q = q.filter(OrderModel.requester_id == user_id)
        orders = q.order_by(OrderModel.created_at.desc()).limit(limit).all()
        return [
            {"id": o.id, "order_number": o.order_number, "title": o.title, "status": o.status}
            for o in orders
        ]

    def _search_templates(self, pattern: str, limit: int) -> list[dict]:
        templates = self.session.query(ServiceTemplateModel).filter(
            (ServiceTemplateModel.display_name.ilike(pattern)) | (ServiceTemplateModel.slug.ilike(pattern))
        ).filter(ServiceTemplateModel.status.in_(["active", "deprecated"])).limit(limit).all()
        return [
            {"slug": t.slug, "display_name": t.display_name, "category": t.category, "status": t.status}
            for t in templates
        ]
