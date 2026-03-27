# tests/integration/test_per_instance_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
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
def seed_template_per_instance(db_session):
    """Template with shared + per_instance + auto params."""
    repo = TemplateRepository(db_session)
    return repo.create({
        "slug": "vm-cluster",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Cluster VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm-cluster.git",
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
            {
                "key": "hostname", "label": "Hostname", "type": "string",
                "required": True, "tofu_variable_name": "hostname",
                "display_order": 2, "per_instance": "auto",
            },
            {
                "key": "custom_tag", "label": "Tag", "type": "string",
                "required": True, "tofu_variable_name": "custom_tag",
                "display_order": 3, "per_instance": True,
            },
        ],
    })


@pytest.fixture
def seed_order(db_session):
    repo = OrderRepository(db_session)
    return repo.create_order("test-requester", "Per-Instance Test", "Need VMs", "2026-06-01")


# ── GET template shows per_instance field ────────────────────


class TestTemplateShowsPerInstance:
    def test_get_template_includes_per_instance(
        self, client, db_session, seed_template_per_instance, requester_headers,
    ):
        resp = client.get(
            "/api/v1/catalog/templates/vm-cluster",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        params_by_key = {p["key"]: p for p in data["parameters"]}
        assert params_by_key["cpu_cores"].get("per_instance", False) is False
        assert params_by_key["hostname"]["per_instance"] == "auto"
        assert params_by_key["custom_tag"]["per_instance"] is True


# ── Parameter Layout endpoint ────────────────────────────────


class TestParameterLayout:
    def test_parameter_layout_quantity_3(
        self, client, db_session, seed_template_per_instance, requester_headers,
    ):
        resp = client.get(
            "/api/v1/catalog/templates/vm-cluster/parameter-layout?quantity=3",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "shared_parameters" in data
        assert "per_instance_parameters" in data
        assert "auto_parameters" in data

        shared_keys = [p["key"] for p in data["shared_parameters"]]
        per_instance_keys = [p["key"] for p in data["per_instance_parameters"]]
        auto_keys = [p["key"] for p in data["auto_parameters"]]

        assert "cpu_cores" in shared_keys
        assert "custom_tag" in per_instance_keys
        assert "hostname" in auto_keys
        assert data["quantity"] == 3

    def test_parameter_layout_quantity_1_all_shared(
        self, client, db_session, seed_template_per_instance, requester_headers,
    ):
        resp = client.get(
            "/api/v1/catalog/templates/vm-cluster/parameter-layout?quantity=1",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # With quantity=1, all params are shared (no per-instance split needed)
        shared_keys = [p["key"] for p in data["shared_parameters"]]
        assert "cpu_cores" in shared_keys
        assert "hostname" in shared_keys
        assert "custom_tag" in shared_keys
        assert data["per_instance_parameters"] == []
        assert data["auto_parameters"] == []

    def test_parameter_layout_template_not_found(
        self, client, db_session, requester_headers,
    ):
        resp = client.get(
            "/api/v1/catalog/templates/nonexistent/parameter-layout?quantity=1",
            headers=requester_headers,
        )
        assert resp.status_code == 404


# ── Validate with missing per-instance params ────────────────


class TestValidatePerInstanceParams:
    def test_validate_missing_instance_param_produces_violation(
        self, client, db_session, seed_order, seed_template_per_instance,
        requester_headers,
    ):
        # Add item with quantity=2 but only 1 instance_parameters set
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-cluster",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
                "quantity": 2,
                "instance_parameters": [
                    {"custom_tag": "web-01"},
                    # second instance missing custom_tag
                    {},
                ],
            },
        )

        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["all_valid"] is False

    def test_validate_all_instance_params_present_is_valid(
        self, client, db_session, seed_order, seed_template_per_instance,
        requester_headers,
    ):
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-cluster",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
                "quantity": 2,
                "instance_parameters": [
                    {"custom_tag": "web-01"},
                    {"custom_tag": "web-02"},
                ],
            },
        )

        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["all_valid"] is True


# ── Register template with per_instance params (admin) ───────


class TestRegisterTemplateWithPerInstance:
    def test_register_template_per_instance_accepted(
        self, client, db_session, admin_headers,
    ):
        resp = client.post(
            "/api/v1/admin/catalog/templates",
            headers=admin_headers,
            json={
                "slug": "vm-per-inst",
                "version": "1.0.0",
                "type": "vm",
                "display_name": "Per Instance VM",
                "category": "Compute",
                "tofu_module_source": "git::https://gitlab.internal/tofu/vm-pi.git",
                "parameters": [
                    {
                        "key": "cpu", "label": "CPU", "type": "integer",
                        "required": True, "tofu_variable_name": "cpu_cores",
                        "display_order": 1, "constraints": {"min": 1, "max": 64},
                    },
                    {
                        "key": "tag", "label": "Tag", "type": "string",
                        "required": True, "tofu_variable_name": "tag",
                        "display_order": 2, "per_instance": True,
                    },
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        params_by_key = {p["key"]: p for p in data["parameters"]}
        assert params_by_key["tag"]["per_instance"] is True

    def test_register_template_auto_only_for_string(
        self, client, db_session, admin_headers,
    ):
        resp = client.post(
            "/api/v1/admin/catalog/templates",
            headers=admin_headers,
            json={
                "slug": "vm-bad-auto",
                "version": "1.0.0",
                "type": "vm",
                "display_name": "Bad Auto VM",
                "category": "Compute",
                "tofu_module_source": "git::https://gitlab.internal/tofu/vm-ba.git",
                "parameters": [
                    {
                        "key": "cpu", "label": "CPU", "type": "integer",
                        "required": True, "tofu_variable_name": "cpu_cores",
                        "display_order": 1, "per_instance": "auto",
                    },
                ],
            },
        )
        assert resp.status_code == 400
