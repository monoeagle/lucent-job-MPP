from flask import Blueprint, jsonify, request, g
from app.core.auth import login_required
from app.data.db.models.order import OrderModel
from app.data.db.models.service_template import ServiceTemplateModel

bp = Blueprint("search", __name__, url_prefix="/api/v1")


@bp.route("/search", methods=["GET"])
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 5, type=int)

    if len(q) < 1:
        return jsonify({"query": q, "orders": [], "templates": [], "resources": []}), 200

    session = g.db_session
    user = g.current_user
    pattern = f"%{q}%"

    # Search orders
    oq = session.query(OrderModel).filter(
        (OrderModel.title.ilike(pattern)) | (OrderModel.order_number.ilike(pattern))
    )
    if not user.is_admin:
        oq = oq.filter(OrderModel.requester_id == user.username)
    orders = oq.order_by(OrderModel.created_at.desc()).limit(limit).all()

    # Search templates (active + deprecated only)
    tq = session.query(ServiceTemplateModel).filter(
        (ServiceTemplateModel.display_name.ilike(pattern)) | (ServiceTemplateModel.slug.ilike(pattern))
    ).filter(ServiceTemplateModel.status.in_(["active", "deprecated"]))
    templates = tq.limit(limit).all()

    return jsonify({
        "query": q,
        "orders": [
            {"id": o.id, "order_number": o.order_number, "title": o.title, "status": o.status}
            for o in orders
        ],
        "templates": [
            {"slug": t.slug, "display_name": t.display_name, "category": t.category, "status": t.status}
            for t in templates
        ],
        "resources": [],
    }), 200
