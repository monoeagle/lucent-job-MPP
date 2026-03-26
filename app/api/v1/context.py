from dataclasses import asdict

from flask import Blueprint, jsonify, request, current_app, g

from app.core.auth import login_required, role_required
from app.data.repositories.context_rule_repository import ContextRuleRepository
from app.data.repositories.tenant_repository import TenantRepository
from app.services.context_service import ContextService

bp = Blueprint("context", __name__, url_prefix="/api/v1/context")
admin_bp = Blueprint("context_admin", __name__, url_prefix="/api/v1/admin/context")


def _service():
    tenant_repo = TenantRepository(g.db_session)
    return ContextService(current_app.cmdb_client, tenant_repo=tenant_repo)


def _rule_repo():
    return ContextRuleRepository(g.db_session)


def _tenant_repo():
    return TenantRepository(g.db_session)


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


@bp.route("/check-availability", methods=["POST"])
@login_required
def check_availability():
    body = request.get_json(silent=True) or {}
    template_slug = body.get("template_slug")
    context = body.get("context", {})

    if not template_slug:
        return jsonify({"error": "template_slug is required"}), 400

    repo = _rule_repo()
    result = repo.check_availability(template_slug, context)
    return jsonify(result), 200


@bp.route("/resolve-parameters", methods=["POST"])
@login_required
def resolve_parameters():
    body = request.get_json(silent=True) or {}
    template_slug = body.get("template_slug")
    parameter_key = body.get("parameter_key")
    context = body.get("context", {})

    if not template_slug or not parameter_key:
        return jsonify({"error": "template_slug and parameter_key are required"}), 400

    repo = _rule_repo()
    restrictions = repo.get_restrictions_for_context(template_slug, parameter_key, context)

    # Merge effects by priority (highest first, already sorted)
    effective_constraints = {}
    for r in restrictions:
        for key, value in r.effect.items():
            if key not in effective_constraints:
                effective_constraints[key] = value

    return jsonify({
        "parameter_key": parameter_key,
        "restrictions": [ContextRuleRepository._restriction_to_dict(r) for r in restrictions],
        "effective_constraints": effective_constraints,
    }), 200


# --- Admin: Availability Rules ---

def _rule_to_dict(rule):
    return {
        "id": rule.id,
        "name": rule.name,
        "template_slug": rule.template_slug,
        "rule_type": rule.rule_type,
        "conditions": rule.conditions,
        "priority": rule.priority,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def _restriction_to_dict(restriction):
    return {
        "id": restriction.id,
        "name": restriction.name,
        "template_slug": restriction.template_slug,
        "parameter_key": restriction.parameter_key,
        "restriction_type": restriction.restriction_type,
        "conditions": restriction.conditions,
        "effect": restriction.effect,
        "priority": restriction.priority,
        "is_active": restriction.is_active,
        "created_at": restriction.created_at.isoformat() if restriction.created_at else None,
        "updated_at": restriction.updated_at.isoformat() if restriction.updated_at else None,
    }


def _assignment_to_dict(assignment):
    return {
        "id": assignment.id,
        "user_id": assignment.user_id,
        "tenant_id": assignment.tenant_id,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
    }


@admin_bp.route("/availability-rules", methods=["POST"])
@role_required("admin")
def create_availability_rule():
    data = request.get_json()
    repo = _rule_repo()
    rule = repo.create_availability_rule(
        name=data["name"],
        template_slug=data["template_slug"],
        rule_type=data["rule_type"],
        conditions=data["conditions"],
        priority=data.get("priority", 0),
    )
    return jsonify(_rule_to_dict(rule)), 201


@admin_bp.route("/availability-rules", methods=["GET"])
@role_required("admin")
def list_availability_rules():
    repo = _rule_repo()
    template_slug = request.args.get("template_slug")
    rules = repo.list_availability_rules(template_slug=template_slug)
    return jsonify([_rule_to_dict(r) for r in rules]), 200


@admin_bp.route("/availability-rules/<rule_id>", methods=["PATCH"])
@role_required("admin")
def update_availability_rule(rule_id):
    data = request.get_json()
    repo = _rule_repo()
    rule = repo.update_availability_rule(rule_id, **data)
    if rule is None:
        return jsonify({"error": "Rule not found"}), 404
    return jsonify(_rule_to_dict(rule)), 200


@admin_bp.route("/availability-rules/<rule_id>", methods=["DELETE"])
@role_required("admin")
def delete_availability_rule(rule_id):
    repo = _rule_repo()
    if not repo.delete_availability_rule(rule_id):
        return jsonify({"error": "Rule not found"}), 404
    return "", 204


# --- Admin: Context Restrictions ---

@admin_bp.route("/restrictions", methods=["POST"])
@role_required("admin")
def create_restriction():
    data = request.get_json()
    repo = _rule_repo()
    restriction = repo.create_restriction(
        name=data["name"],
        template_slug=data.get("template_slug"),
        parameter_key=data["parameter_key"],
        restriction_type=data["restriction_type"],
        conditions=data["conditions"],
        effect=data["effect"],
        priority=data.get("priority", 0),
    )
    return jsonify(_restriction_to_dict(restriction)), 201


@admin_bp.route("/restrictions", methods=["GET"])
@role_required("admin")
def list_restrictions():
    repo = _rule_repo()
    template_slug = request.args.get("template_slug")
    restrictions = repo.list_restrictions(template_slug=template_slug)
    return jsonify([_restriction_to_dict(r) for r in restrictions]), 200


@admin_bp.route("/restrictions/<restriction_id>", methods=["DELETE"])
@role_required("admin")
def delete_restriction(restriction_id):
    repo = _rule_repo()
    if not repo.delete_restriction(restriction_id):
        return jsonify({"error": "Restriction not found"}), 404
    return "", 204


# --- Admin: Tenant Assignments ---

@admin_bp.route("/tenant-assignments", methods=["POST"])
@role_required("admin")
def create_tenant_assignment():
    data = request.get_json()
    repo = _tenant_repo()
    try:
        assignment = repo.assign_tenant(
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
        )
    except TenantRepository.DuplicateAssignmentError as e:
        return jsonify({"error": str(e)}), 409
    return jsonify(_assignment_to_dict(assignment)), 201


@admin_bp.route("/tenant-assignments", methods=["GET"])
@role_required("admin")
def list_tenant_assignments():
    repo = _tenant_repo()
    user_id = request.args.get("user_id")
    assignments = repo.list_assignments(user_id=user_id)
    return jsonify([_assignment_to_dict(a) for a in assignments]), 200


@admin_bp.route("/tenant-assignments/<assignment_id>", methods=["DELETE"])
@role_required("admin")
def delete_tenant_assignment(assignment_id):
    repo = _tenant_repo()
    if not repo.delete_assignment(assignment_id):
        return jsonify({"error": "Assignment not found"}), 404
    return "", 204
