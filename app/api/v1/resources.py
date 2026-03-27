from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required
from app.services.resource_service import ResourceService

bp = Blueprint("resources", __name__, url_prefix="/api/v1")


@bp.route("/resources", methods=["GET"])
@login_required
def list_resources():
    service = ResourceService(g.db_session)
    service_type = request.args.get("service_type")
    result = service.list_resources(
        g.current_user.username, g.current_user.is_admin, service_type
    )
    return jsonify(result), 200


@bp.route("/resources/<item_id>", methods=["GET"])
@login_required
def get_resource(item_id):
    service = ResourceService(g.db_session)
    result = service.get_resource(item_id, g.current_user.username, g.current_user.is_admin)
    return jsonify(result), 200
