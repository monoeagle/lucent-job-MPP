from decimal import Decimal

from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required
from app.data.repositories.template_repository import TemplateRepository

bp = Blueprint("catalog", __name__, url_prefix="/api/v1/catalog")


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
