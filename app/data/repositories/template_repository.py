import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.db.models.service_template import ServiceTemplateModel


class TemplateRepository:
    class DuplicateTemplateError(Exception):
        pass

    class TemplateNotFoundError(Exception):
        pass

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: dict) -> ServiceTemplateModel:
        template = ServiceTemplateModel(
            id=str(uuid.uuid4()),
            slug=data["slug"],
            version=data["version"],
            type=data["type"],
            display_name=data["display_name"],
            description=data.get("description"),
            category=data["category"],
            icon_identifier=data.get("icon_identifier"),
            tofu_module_source=data["tofu_module_source"],
            parameters=data.get("parameters", []),
            cross_parameter_rules=data.get("cross_parameter_rules", []),
            status="active",
            estimated_cost_eur_per_month=data.get("estimated_cost_eur_per_month"),
            approval_always_required=data.get("approval_always_required", False),
            metadata_=data.get("metadata", {}),
        )
        self.session.add(template)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise self.DuplicateTemplateError(
                f"A template with slug '{data['slug']}' and version '{data['version']}' already exists."
            )
        return template

    def get_by_id(self, template_id: str) -> ServiceTemplateModel | None:
        return self.session.query(ServiceTemplateModel).filter_by(id=template_id).first()

    def get_by_slug(self, slug: str, status: str = "active") -> ServiceTemplateModel | None:
        q = (
            self.session.query(ServiceTemplateModel)
            .filter_by(slug=slug)
        )
        if status != "all":
            q = q.filter_by(status=status)
        q = q.order_by(ServiceTemplateModel.created_at.desc())
        result = q.first()
        if result is None and status == "active":
            return self.get_by_slug(slug, status="deprecated")
        return result

    def get_by_slug_and_version(self, slug: str, version: str) -> ServiceTemplateModel | None:
        return (
            self.session.query(ServiceTemplateModel)
            .filter_by(slug=slug, version=version)
            .first()
        )

    def list_templates(self, status_filter: str = "active", type_filter: str | None = None,
                       category_filter: str | None = None, search: str | None = None,
                       limit: int = 20, offset: int = 0) -> dict:
        q = self.session.query(ServiceTemplateModel)
        if status_filter and status_filter != "all":
            q = q.filter_by(status=status_filter)
        if type_filter:
            q = q.filter_by(type=type_filter)
        if category_filter:
            q = q.filter(func.lower(ServiceTemplateModel.category) == category_filter.lower())
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            q = q.filter(
                or_(
                    func.lower(ServiceTemplateModel.display_name).like(term),
                    func.lower(ServiceTemplateModel.description).like(term),
                )
            )
        total = q.count()
        data = q.order_by(ServiceTemplateModel.created_at.desc()).offset(offset).limit(limit).all()
        return {"data": data, "total": total, "limit": limit, "offset": offset}

    def list_versions(self, slug: str, status_filter: str | None = None) -> list[ServiceTemplateModel]:
        q = self.session.query(ServiceTemplateModel).filter_by(slug=slug)
        if status_filter and status_filter != "all":
            q = q.filter_by(status=status_filter)
        return q.order_by(ServiceTemplateModel.created_at.desc()).all()

    def update_status(self, template_id: str, new_status: str,
                      deprecated_by: str | None = None) -> ServiceTemplateModel:
        template = self.get_by_id(template_id)
        if template is None:
            raise self.TemplateNotFoundError(f"Template '{template_id}' not found.")
        template.status = new_status
        if new_status == "deprecated":
            template.deprecated_at = datetime.now(timezone.utc)
            template.deprecated_by = deprecated_by
        self.session.commit()
        return template

    def get_categories(self) -> list[dict]:
        results = (
            self.session.query(
                ServiceTemplateModel.category,
                func.count(ServiceTemplateModel.id),
            )
            .filter(ServiceTemplateModel.status.in_(["active", "deprecated"]))
            .group_by(ServiceTemplateModel.category)
            .all()
        )
        return [{"name": name, "template_count": count} for name, count in results]
