# tests/integration/test_catalog_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def db_session(app):
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seeded_db(db_session):
    repo = TemplateRepository(db_session)
    repo.create({
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "description": "A standard Linux virtual machine",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu", "label": "CPU Cores", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {"min": 1, "max": 64}, "depends_on": []}
        ],
    })
    repo.create({
        "slug": "db-postgres",
        "version": "1.0.0",
        "type": "database",
        "display_name": "PostgreSQL DB",
        "description": "Managed PostgreSQL database",
        "category": "Database",
        "tofu_module_source": "git::https://gitlab.internal/tofu/db.git",
        "parameters": [
            {"key": "storage_gb", "label": "Storage", "type": "integer", "required": True,
             "tofu_variable_name": "storage_gb", "display_order": 1,
             "constraints": {"min": 10, "max": 1000}, "depends_on": []}
        ],
    })
    return repo


class TestListTemplates:
    def test_unauthenticated_returns_401(self, client, seeded_db):
        resp = client.get("/api/v1/catalog/templates")
        assert resp.status_code == 401

    def test_list_all_templates(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 2
        assert len(body["data"]) == 2
        assert "limit" in body
        assert "offset" in body

    def test_filter_by_type(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates?type=vm", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["data"][0]["slug"] == "vm-linux"

    def test_filter_by_category(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates?category=Database", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["data"][0]["slug"] == "db-postgres"

    def test_search_by_query(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates?q=linux", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["data"][0]["slug"] == "vm-linux"

    def test_pagination(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates?limit=1&offset=0", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 1
        assert body["total"] == 2
        assert body["limit"] == 1
        assert body["offset"] == 0

    def test_filter_by_status(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates?status=active", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 2


class TestGetTemplateDetail:
    def test_get_existing_template(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates/vm-linux", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["slug"] == "vm-linux"
        assert body["display_name"] == "Linux VM"
        assert "parameters" in body

    def test_get_template_with_version(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates/vm-linux?version=1.0.0",
                          headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["version"] == "1.0.0"

    def test_template_not_found(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/templates/nonexistent", headers=requester_headers)
        assert resp.status_code == 404

    def test_all_versions_disabled_returns_410(self, client, db_session, requester_headers):
        repo = TemplateRepository(db_session)
        t = repo.create({
            "slug": "vm-disabled",
            "version": "1.0.0",
            "type": "vm",
            "display_name": "Disabled VM",
            "description": "A disabled template",
            "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [],
        })
        repo.update_status(t.id, "disabled")
        resp = client.get("/api/v1/catalog/templates/vm-disabled", headers=requester_headers)
        assert resp.status_code == 410

    def test_unauthenticated_returns_401(self, client, seeded_db):
        resp = client.get("/api/v1/catalog/templates/vm-linux")
        assert resp.status_code == 401


class TestListVersions:
    def test_list_versions(self, client, db_session, requester_headers):
        repo = TemplateRepository(db_session)
        repo.create({
            "slug": "vm-linux",
            "version": "1.0.0",
            "type": "vm",
            "display_name": "Linux VM",
            "description": "v1",
            "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [],
        })
        repo.create({
            "slug": "vm-linux",
            "version": "2.0.0",
            "type": "vm",
            "display_name": "Linux VM v2",
            "description": "v2",
            "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [],
        })
        resp = client.get("/api/v1/catalog/templates/vm-linux/versions",
                          headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body) == 2
        versions = [v["version"] for v in body]
        assert "1.0.0" in versions
        assert "2.0.0" in versions

    def test_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/v1/catalog/templates/vm-linux/versions")
        assert resp.status_code == 401


class TestListCategories:
    def test_list_categories(self, client, seeded_db, requester_headers):
        resp = client.get("/api/v1/catalog/categories", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body) == 2
        names = [c["name"] for c in body]
        assert "Compute" in names
        assert "Database" in names
        for cat in body:
            assert "template_count" in cat
            assert cat["template_count"] >= 1

    def test_unauthenticated_returns_401(self, client, seeded_db):
        resp = client.get("/api/v1/catalog/categories")
        assert resp.status_code == 401
