import logging

from sqlalchemy import func

from app.data.db.models.approval import ApprovalRequestModel
from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.service_template import ServiceTemplateModel

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, session):
        self.session = session

    def get_stats(self, user_id: str, is_admin: bool) -> dict:
        return {
            "orders_by_status": self._orders_by_status(user_id, is_admin),
            "orders_by_month": self._orders_by_month(user_id, is_admin),
            "total_templates": self._total_templates(),
            "active_resources": self._active_resources(user_id, is_admin),
            "pending_approvals": self._pending_approvals(),
            "popular_templates": self._popular_templates(),
        }

    def _orders_by_status(self, user_id: str, is_admin: bool) -> dict:
        q = self.session.query(OrderModel.status, func.count(OrderModel.id))
        if not is_admin:
            q = q.filter(OrderModel.requester_id == user_id)
        rows = q.group_by(OrderModel.status).all()
        return {status: count for status, count in rows}

    def _orders_by_month(self, user_id: str, is_admin: bool) -> list[dict]:
        q = self.session.query(
            func.to_char(OrderModel.created_at, 'YYYY-MM').label('month'),
            func.count(OrderModel.id),
        )
        if not is_admin:
            q = q.filter(OrderModel.requester_id == user_id)
        rows = q.group_by('month').order_by('month').limit(6).all()
        return [{"month": m, "count": c} for m, c in rows]

    def _total_templates(self) -> int:
        return self.session.query(func.count(ServiceTemplateModel.id)).scalar() or 0

    def _active_resources(self, user_id: str, is_admin: bool) -> int:
        q = self.session.query(func.count(OrderItemModel.id)).join(
            OrderModel, OrderItemModel.order_id == OrderModel.id
        ).filter(OrderModel.status == "done")
        if not is_admin:
            q = q.filter(OrderModel.requester_id == user_id)
        return q.scalar() or 0

    def _pending_approvals(self) -> int:
        q = self.session.query(func.count(ApprovalRequestModel.id)).filter(
            ApprovalRequestModel.status == "pending"
        )
        return q.scalar() or 0

    def _popular_templates(self) -> list[dict]:
        pop = self.session.query(
            OrderItemModel.template_slug,
            func.count(OrderItemModel.id).label('cnt'),
        ).group_by(OrderItemModel.template_slug).order_by(
            func.count(OrderItemModel.id).desc()
        ).limit(5).all()

        result = []
        for slug, cnt in pop:
            tmpl = self.session.query(ServiceTemplateModel).filter_by(slug=slug).first()
            result.append({
                "slug": slug,
                "display_name": tmpl.display_name if tmpl else slug,
                "category": tmpl.category if tmpl else "",
                "order_count": cnt,
            })
        return result
