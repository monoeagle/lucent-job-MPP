from flask import Blueprint, jsonify, g

from app.core.auth import login_required
from app.services.dashboard_service import DashboardService

bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


@bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    service = DashboardService(g.db_session)
    stats = service.get_stats(g.current_user.username, g.current_user.is_admin)
    return jsonify(stats), 200
