from flask import Blueprint, jsonify, request, current_app

from app.core.auth import login_required

bp = Blueprint("cmdb", __name__, url_prefix="/api/v1/cmdb")


def _client():
    return current_app.cmdb_client


@bp.route("/locations", methods=["GET"])
@login_required
def list_locations():
    return jsonify(_client().get_locations())


@bp.route("/locations/<location_id>", methods=["GET"])
@login_required
def get_location(location_id):
    item = _client().get_location(location_id)
    if item is None:
        return jsonify({"error": "Location not found"}), 404
    return jsonify(item)


@bp.route("/networks", methods=["GET"])
@login_required
def list_networks():
    location_id = request.args.get("location_id")
    security_zone_id = request.args.get("security_zone_id")
    return jsonify(_client().get_networks(
        location_id=location_id,
        security_zone_id=security_zone_id,
    ))


@bp.route("/networks/<network_id>", methods=["GET"])
@login_required
def get_network(network_id):
    item = _client().get_network(network_id)
    if item is None:
        return jsonify({"error": "Network not found"}), 404
    return jsonify(item)


@bp.route("/tenants", methods=["GET"])
@login_required
def list_tenants():
    return jsonify(_client().get_tenants())


@bp.route("/tenants/<tenant_id>", methods=["GET"])
@login_required
def get_tenant(tenant_id):
    item = _client().get_tenant(tenant_id)
    if item is None:
        return jsonify({"error": "Tenant not found"}), 404
    return jsonify(item)


@bp.route("/security-zones", methods=["GET"])
@login_required
def list_security_zones():
    return jsonify(_client().get_security_zones())


@bp.route("/security-zones/<zone_id>", methods=["GET"])
@login_required
def get_security_zone(zone_id):
    item = _client().get_security_zone(zone_id)
    if item is None:
        return jsonify({"error": "Security zone not found"}), 404
    return jsonify(item)


@bp.route("/health", methods=["GET"])
@login_required
def health():
    c = _client()
    return jsonify({
        "status": "ok" if c.health() else "error",
        "mode": current_app.config.get("CMDB_MODE", "stub"),
        "entities": {
            "locations": len(c.get_locations()),
            "networks": len(c.get_networks()),
            "tenants": len(c.get_tenants()),
            "security_zones": len(c.get_security_zones()),
        },
    })
