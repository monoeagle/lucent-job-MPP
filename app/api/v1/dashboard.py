from flask import Blueprint, jsonify, g
from sqlalchemy import func

from app.core.auth import login_required
from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.service_template import ServiceTemplateModel

bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


@bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    session = g.db_session
    user = g.current_user

    # Orders by status
    q = session.query(OrderModel.status, func.count(OrderModel.id))
    if not user.is_admin:
        q = q.filter(OrderModel.requester_id == user.username)
    rows = q.group_by(OrderModel.status).all()
    orders_by_status = {status: count for status, count in rows}

    # Orders by month (last 6)
    q = session.query(
        func.to_char(OrderModel.created_at, 'YYYY-MM').label('month'),
        func.count(OrderModel.id),
    )
    if not user.is_admin:
        q = q.filter(OrderModel.requester_id == user.username)
    rows = q.group_by('month').order_by('month').limit(6).all()
    orders_by_month = [{"month": m, "count": c} for m, c in rows]

    # Total templates
    total_templates = session.query(func.count(ServiceTemplateModel.id)).scalar() or 0

    # Active resources
    rq = session.query(func.count(OrderItemModel.id)).join(
        OrderModel, OrderItemModel.order_id == OrderModel.id
    ).filter(OrderModel.status == "done")
    if not user.is_admin:
        rq = rq.filter(OrderModel.requester_id == user.username)
    active_resources = rq.scalar() or 0

    # Pending approvals
    from app.data.db.models.approval import ApprovalRequestModel
    pq = session.query(func.count(ApprovalRequestModel.id)).filter(
        ApprovalRequestModel.status == "pending"
    )
    pending_approvals = pq.scalar() or 0

    # Popular templates (top 5)
    pop = session.query(
        OrderItemModel.template_slug,
        func.count(OrderItemModel.id).label('cnt'),
    ).group_by(OrderItemModel.template_slug).order_by(func.count(OrderItemModel.id).desc()).limit(5).all()

    popular_templates = []
    for slug, cnt in pop:
        tmpl = session.query(ServiceTemplateModel).filter_by(slug=slug).first()
        popular_templates.append({
            "slug": slug,
            "display_name": tmpl.display_name if tmpl else slug,
            "category": tmpl.category if tmpl else "",
            "order_count": cnt,
        })

    return jsonify({
        "orders_by_status": orders_by_status,
        "orders_by_month": orders_by_month,
        "total_templates": total_templates,
        "active_resources": active_resources,
        "pending_approvals": pending_approvals,
        "popular_templates": popular_templates,
    }), 200
