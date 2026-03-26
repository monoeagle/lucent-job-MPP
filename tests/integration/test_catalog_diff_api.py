# tests/integration/test_catalog_diff_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def diff_app():
    app = create_app({
        "AUTH_MODE": "stub", "ENV": "development", "TESTING": "True",
        "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_test",
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    repo = TemplateRepository(session)

    repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux VM", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git?ref=v1",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {"min": 1, "max": 32}},
            {"key": "legacy_bios", "label": "Legacy BIOS", "type": "boolean",
             "required": False, "tofu_variable_name": "legacy_bios", "display_order": 2,
             "constraints": {}},
        ],
    })
    repo.create({
        "slug": "vm-linux", "version": "2.0.0", "type": "vm",
        "display_name": "Linux VM v2", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git?ref=v2",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {"min": 1, "max": 64}},
            {"key": "backup", "label": "Backup", "type": "boolean", "required": False,
             "tofu_variable_name": "backup_enabled", "display_order": 2,
             "constraints": {}},
        ],
    })
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def diff_client(diff_app):
    app, _ = diff_app
    return app.test_client()


@pytest.fixture
def approver_auth(diff_client):
    resp = diff_client.post("/api/v1/auth/login", json={"username": "test-approver"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


class TestVersionDiff:
    def test_diff_shows_changes(self, diff_client, approver_auth):
        resp = diff_client.get(
            "/api/v1/catalog/templates/vm-linux/diff?from_version=1.0.0&to_version=2.0.0",
            headers=approver_auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["slug"] == "vm-linux"
        changes = data["changes"]
        assert len(changes["added_parameters"]) == 1
        assert changes["added_parameters"][0]["key"] == "backup"
        assert len(changes["removed_parameters"]) == 1
        assert changes["removed_parameters"][0]["key"] == "legacy_bios"
        assert len(changes["modified_parameters"]) >= 1

    def test_diff_missing_version(self, diff_client, approver_auth):
        resp = diff_client.get(
            "/api/v1/catalog/templates/vm-linux/diff?from_version=1.0.0&to_version=9.9.9",
            headers=approver_auth)
        assert resp.status_code == 404

    def test_diff_requires_approver_or_admin(self, diff_client):
        resp = diff_client.post("/api/v1/auth/login", json={"username": "test-requester"})
        token = resp.get_json()["token"]
        resp = diff_client.get(
            "/api/v1/catalog/templates/vm-linux/diff?from_version=1.0.0&to_version=2.0.0",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
