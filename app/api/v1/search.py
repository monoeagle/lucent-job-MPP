from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required
from app.core.helpers import cap_limit
from app.services.search_service import SearchService

bp = Blueprint("search", __name__, url_prefix="/api/v1")


@bp.route("/search", methods=["GET"])
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    limit = cap_limit(request.args.get("limit", 5, type=int))

    if len(q) < 1:
        return jsonify({"query": q, "orders": [], "templates": [], "resources": []}), 200

    service = SearchService(g.db_session)
    result = service.search(q, g.current_user.username, g.current_user.is_admin, limit)
    return jsonify(result), 200
