from dataclasses import asdict

from flask import Blueprint, jsonify, request, current_app, g

from app.core.auth import login_required
from app.services.context_service import ContextService

bp = Blueprint("context", __name__, url_prefix="/api/v1/context")


def _service():
    return ContextService(current_app.cmdb_client)


@bp.route("/resolve", methods=["POST"])
@login_required
def resolve_context():
    body = request.get_json(silent=True) or {}

    location_id = body.get("location_id")
    tenant_id = body.get("tenant_id")
    security_zone_id = body.get("security_zone_id")
    network_id = body.get("network_id")

    if not location_id or not tenant_id or not security_zone_id:
        return jsonify({
            "error_code": "VALIDATION_FAILED",
            "message": "location_id, tenant_id, and security_zone_id are required.",
        }), 400

    svc = _service()
    try:
        resolved = svc.resolve_context(
            location_id=location_id,
            tenant_id=tenant_id,
            security_zone_id=security_zone_id,
            network_id=network_id,
            user_id=g.current_user.username,
        )
    except ContextService.ContextValidationError as e:
        return jsonify({
            "error_code": "CONTEXT_VALIDATION_FAILED",
            "violations": e.violations,
        }), 400
    except ContextService.CmdbUnavailableError:
        return jsonify({
            "error_code": "CMDB_UNAVAILABLE",
            "message": "CMDB service is unavailable.",
        }), 503

    return jsonify(asdict(resolved)), 200


@bp.route("/locations", methods=["GET"])
@login_required
def list_locations():
    return jsonify(current_app.cmdb_client.get_locations())


@bp.route("/tenants", methods=["GET"])
@login_required
def list_tenants():
    svc = _service()
    tenants = svc.get_allowed_tenants(g.current_user.username)
    return jsonify(tenants)


@bp.route("/security-zones", methods=["GET"])
@login_required
def list_security_zones():
    return jsonify(current_app.cmdb_client.get_security_zones())


@bp.route("/networks", methods=["GET"])
@login_required
def list_networks():
    location_id = request.args.get("location_id")
    security_zone_id = request.args.get("security_zone_id")
    return jsonify(current_app.cmdb_client.get_networks(
        location_id=location_id,
        security_zone_id=security_zone_id,
    ))
