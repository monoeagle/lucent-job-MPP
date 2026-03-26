from decimal import Decimal

from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required, role_required
from app.data.repositories.template_repository import TemplateRepository
from app.domain.catalog import TemplateStatus
from app.services.catalog_service import CatalogService
from app.services.template_validator import TemplateValidator

bp = Blueprint("catalog", __name__, url_prefix="/api/v1/catalog")
admin_bp = Blueprint("catalog_admin", __name__, url_prefix="/api/v1/admin/catalog")


def _get_repo() -> TemplateRepository:
    return TemplateRepository(g.db_session)


def _template_to_dict(t) -> dict:
    return {
        "id": t.id,
        "slug": t.slug,
        "version": t.version,
        "type": t.type,
        "display_name": t.display_name,
        "description": t.description,
        "category": t.category,
        "icon_identifier": t.icon_identifier,
        "tofu_module_source": t.tofu_module_source,
        "parameters": t.parameters,
        "cross_parameter_rules": t.cross_parameter_rules,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "deprecated_at": t.deprecated_at.isoformat() if t.deprecated_at else None,
        "deprecated_by": t.deprecated_by,
        "estimated_cost_eur_per_month": (
            float(t.estimated_cost_eur_per_month)
            if t.estimated_cost_eur_per_month is not None else None
        ),
        "approval_always_required": t.approval_always_required,
        "metadata": t.metadata_,
    }


@bp.route("/templates", methods=["GET"])
@login_required
def list_templates():
    repo = _get_repo()
    status = request.args.get("status", "active")
    type_filter = request.args.get("type")
    category = request.args.get("category")
    search = request.args.get("q")
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    result = repo.list_templates(
        status_filter=status,
        type_filter=type_filter,
        category_filter=category,
        search=search,
        limit=limit,
        offset=offset,
    )
    return jsonify({
        "data": [_template_to_dict(t) for t in result["data"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    })


@bp.route("/templates/<slug>", methods=["GET"])
@login_required
def get_template(slug):
    repo = _get_repo()
    version = request.args.get("version")

    if version:
        template = repo.get_by_slug_and_version(slug, version)
    else:
        template = repo.get_by_slug(slug, status="all")

    if template is None:
        # Check if any versions exist but are all disabled
        all_versions = repo.list_versions(slug, status_filter="all")
        if all_versions and all(v.status == "disabled" for v in all_versions):
            return jsonify({"error": "Template is disabled", "slug": slug}), 410
        return jsonify({"error": "Template not found"}), 404

    if template.status == "disabled":
        all_versions = repo.list_versions(slug, status_filter="all")
        if all(v.status == "disabled" for v in all_versions):
            return jsonify({"error": "Template is disabled", "slug": slug}), 410

    return jsonify(_template_to_dict(template))


@bp.route("/templates/<slug>/versions", methods=["GET"])
@login_required
def list_versions(slug):
    repo = _get_repo()
    versions = repo.list_versions(slug, status_filter="all")
    return jsonify([_template_to_dict(v) for v in versions])


@bp.route("/categories", methods=["GET"])
@login_required
def list_categories():
    repo = _get_repo()
    categories = repo.get_categories()
    return jsonify(categories)


@bp.route("/templates/<slug>/validate", methods=["POST"])
@login_required
def validate_template_params(slug):
    repo = _get_repo()
    template = repo.get_by_slug(slug, status="all")
    if template is None:
        return jsonify({"error": "Template not found"}), 404

    data = request.get_json()
    parameters = data.get("parameters", {})

    service = CatalogService(repo)
    violations = service.validate_parameters(
        template.parameters, parameters, template.cross_parameter_rules or [],
    )
    return jsonify({
        "valid": len(violations) == 0,
        "violations": violations,
        "warnings": [],
    }), 200


@bp.route("/templates/<slug>/diff", methods=["GET"])
@role_required("approver", "admin")
def diff_template_versions(slug):
    from_version = request.args.get("from_version")
    to_version = request.args.get("to_version")

    if not from_version or not to_version:
        return jsonify({"error": "from_version and to_version are required"}), 400

    repo = _get_repo()
    from_tmpl = repo.get_by_slug_and_version(slug, from_version)
    to_tmpl = repo.get_by_slug_and_version(slug, to_version)

    if from_tmpl is None or to_tmpl is None:
        return jsonify({"error": "Version not found"}), 404

    service = CatalogService(repo)
    changes = service.compute_diff(from_tmpl, to_tmpl)

    return jsonify({
        "slug": slug,
        "from_version": from_version,
        "to_version": to_version,
        "changes": changes,
    }), 200


@bp.route("/templates/<slug>/resolve-options", methods=["POST"])
@login_required
def resolve_options(slug):
    repo = _get_repo()
    template = repo.get_by_slug(slug, status="all")
    if template is None:
        return jsonify({"error": "Template not found"}), 404

    data = request.get_json()
    parameter_key = data.get("parameter_key")
    current_values = data.get("current_values", {})

    # Find the parameter definition
    param_def = None
    for p in template.parameters:
        if p["key"] == parameter_key:
            param_def = p
            break

    if param_def is None:
        return jsonify({"error": f"Parameter '{parameter_key}' not found"}), 400

    service = CatalogService(repo)
    state = service.resolve_dependency_state(
        param_def.get("depends_on", []), current_values,
    )
    state["parameter_key"] = parameter_key
    return jsonify(state), 200


# --- Admin endpoints ---

@admin_bp.route("/templates", methods=["POST"])
@role_required("admin")
def register_template():
    data = request.get_json()
    validator = TemplateValidator()
    errors = validator.validate_template(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    repo = _get_repo()
    try:
        template = repo.create(data)
    except TemplateRepository.DuplicateTemplateError as e:
        return jsonify({"error": str(e)}), 409

    return jsonify(_template_to_dict(template)), 201


@admin_bp.route("/templates/<template_id>/status", methods=["PATCH"])
@role_required("admin")
def update_template_status(template_id):
    data = request.get_json()
    new_status = data.get("status")

    repo = _get_repo()
    template = repo.get_by_id(template_id)
    if template is None:
        return jsonify({"error": "Template not found"}), 404

    if not TemplateStatus.can_transition(template.status, new_status):
        return jsonify({"error": f"Cannot transition from '{template.status}' to '{new_status}'"}), 409

    deprecated_by = data.get("deprecated_by")
    if new_status == "deprecated" and deprecated_by:
        replacement = repo.get_by_id(deprecated_by)
        if replacement is None or replacement.status != "active":
            return jsonify({"error": "deprecated_by must reference an active template"}), 400

    template = repo.update_status(template_id, new_status, deprecated_by=deprecated_by)
    return jsonify(_template_to_dict(template)), 200
