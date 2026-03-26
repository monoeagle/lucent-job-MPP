# tests/integration/test_catalog_validation_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def val_app():
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
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu_cores", "label": "CPU-Kerne", "type": "integer",
             "required": True, "tofu_variable_name": "cpu_cores",
             "display_order": 1, "constraints": {"min": 1, "max": 64},
             "depends_on": [], "affects_options_of": []},
            {"key": "os_type", "label": "OS", "type": "enum",
             "required": True, "tofu_variable_name": "os_type",
             "display_order": 2, "constraints": {"options": [
                 {"value": "ubuntu", "label": "Ubuntu", "enabled": True},
                 {"value": "rhel", "label": "RHEL", "enabled": True},
             ]}, "depends_on": [], "affects_options_of": ["disk_type"]},
            {"key": "disk_type", "label": "Disk", "type": "enum",
             "required": True, "tofu_variable_name": "disk_type",
             "display_order": 3, "constraints": {"options": [
                 {"value": "ext4", "label": "ext4", "enabled": True},
                 {"value": "xfs", "label": "XFS", "enabled": True},
             ]},
             "depends_on": [{"parameter_key": "os_type", "operator": "neq",
                             "value": None, "effect": "visible"}],
             "affects_options_of": []},
        ],
    })
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def val_client(val_app):
    app, _ = val_app
    return app.test_client()


@pytest.fixture
def auth(val_client):
    resp = val_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


class TestValidateEndpoint:
    def test_valid_params(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/validate",
                                json={"parameters": {"cpu_cores": 4, "os_type": "ubuntu", "disk_type": "ext4"}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valid"] is True
        assert data["violations"] == []

    def test_invalid_params(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/validate",
                                json={"parameters": {"cpu_cores": 128, "os_type": "ubuntu"}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valid"] is False
        assert len(data["violations"]) >= 1

    def test_template_not_found(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/nonexistent/validate",
                                json={"parameters": {}}, headers=auth)
        assert resp.status_code == 404


class TestResolveOptionsEndpoint:
    def test_resolve_visible(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/resolve-options",
                                json={"parameter_key": "disk_type",
                                      "current_values": {"os_type": "ubuntu"}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_visible"] is True
        assert data["parameter_key"] == "disk_type"

    def test_resolve_not_visible(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/resolve-options",
                                json={"parameter_key": "disk_type",
                                      "current_values": {}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_visible"] is False

    def test_unknown_parameter(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/resolve-options",
                                json={"parameter_key": "nonexistent",
                                      "current_values": {}},
                                headers=auth)
        assert resp.status_code == 400
