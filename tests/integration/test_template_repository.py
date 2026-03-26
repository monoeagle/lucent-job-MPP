# tests/integration/test_template_repository.py
import uuid
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def repo():
    engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield TemplateRepository(session)
    session.close()
    Base.metadata.drop_all(engine)


def _make_template(**overrides):
    defaults = {
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "description": "Test",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1, "constraints": {"min": 1, "max": 64}}
        ],
    }
    defaults.update(overrides)
    return defaults


class TestTemplateRepository:
    def test_create_and_get_by_slug(self, repo):
        data = _make_template()
        created = repo.create(data)
        assert created.slug == "vm-linux"
        assert created.id is not None

        loaded = repo.get_by_slug("vm-linux")
        assert loaded is not None
        assert loaded.version == "1.0.0"

    def test_get_by_slug_and_version(self, repo):
        repo.create(_make_template(version="1.0.0"))
        repo.create(_make_template(version="2.0.0"))

        v1 = repo.get_by_slug_and_version("vm-linux", "1.0.0")
        assert v1 is not None
        assert v1.version == "1.0.0"

    def test_get_by_slug_returns_latest_active(self, repo):
        repo.create(_make_template(version="1.0.0"))
        repo.create(_make_template(version="2.0.0"))

        latest = repo.get_by_slug("vm-linux")
        assert latest.version == "2.0.0"

    def test_list_with_filters(self, repo):
        repo.create(_make_template(slug="vm-linux", type="vm", category="Compute"))
        repo.create(_make_template(slug="db-postgres", type="database", category="Database",
                                    display_name="PostgreSQL DB",
                                    tofu_module_source="git::https://gitlab.internal/tofu/db.git"))

        result = repo.list_templates(type_filter="vm")
        assert len(result["data"]) == 1
        assert result["data"][0].slug == "vm-linux"

    def test_list_with_search(self, repo):
        repo.create(_make_template(slug="vm-linux", display_name="Linux Virtual Machine"))
        repo.create(_make_template(slug="db-postgres", display_name="PostgreSQL DB",
                                    type="database", category="Database",
                                    tofu_module_source="git::https://gitlab.internal/tofu/db.git"))

        result = repo.list_templates(search="linux")
        assert len(result["data"]) == 1

    def test_list_pagination(self, repo):
        for i in range(5):
            repo.create(_make_template(slug=f"vm-{i}", version="1.0.0"))
        result = repo.list_templates(limit=2, offset=0)
        assert len(result["data"]) == 2
        assert result["total"] == 5

    def test_list_versions(self, repo):
        repo.create(_make_template(version="1.0.0"))
        repo.create(_make_template(version="2.0.0"))
        versions = repo.list_versions("vm-linux")
        assert len(versions) == 2

    def test_update_status(self, repo):
        created = repo.create(_make_template())
        repo.update_status(created.id, "deprecated", deprecated_by="some-other-id")
        loaded = repo.get_by_id(created.id)
        assert loaded.status == "deprecated"

    def test_duplicate_slug_version_raises(self, repo):
        repo.create(_make_template())
        with pytest.raises(repo.DuplicateTemplateError):
            repo.create(_make_template())

    def test_get_categories(self, repo):
        repo.create(_make_template(slug="vm-1", category="Compute"))
        repo.create(_make_template(slug="db-1", type="database", category="Database",
                                    tofu_module_source="git::https://gitlab.internal/tofu/db.git"))
        categories = repo.get_categories()
        assert len(categories) == 2
        names = [c["name"] for c in categories]
        assert "Compute" in names
        assert "Database" in names
