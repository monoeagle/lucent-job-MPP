# tests/integration/test_approval_submit_integration.py
import os
import pytest

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.approval_repository import ApprovalRepository


@pytest.fixture
def integ_app():
    app = create_app({
        "AUTH_MODE": "stub",
        "ENV": "development",
        "TESTING": "True",
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://mpp:mpp@localhost:5432/mpp_test",
        ),
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def integ_client(integ_app):
    app, _ = integ_app
    return app.test_client()


@pytest.fixture
def integ_session(integ_app):
    app, _ = integ_app
    session = app.session_factory()
    yield session
    session.close()


@pytest.fixture
def seed_template(integ_session):
    repo = TemplateRepository(integ_session)
    return repo.create({
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "estimated_cost_eur_per_month": 100.00,
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
        ],
    })


@pytest.fixture
def seed_expensive_template(integ_session):
    repo = TemplateRepository(integ_session)
    return repo.create({
        "slug": "vm-expensive",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Expensive VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "estimated_cost_eur_per_month": 6000.00,
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
        ],
    })


@pytest.fixture
def seed_approval_required_template(integ_session):
    repo = TemplateRepository(integ_session)
    return repo.create({
        "slug": "vm-approval-required",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Approval Required VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "approval_always_required": True,
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
        ],
    })


def _auth_header(client, username):
    resp = client.post("/api/v1/auth/login", json={"username": username})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


def _create_validated_order(client, headers, template_slug="vm-linux"):
    """Create order, add item, validate, return order_id."""
    resp = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"title": "Approval Test Order", "business_reason": "Testing approvals"},
    )
    order_id = resp.get_json()["id"]

    client.post(
        f"/api/v1/orders/{order_id}/items",
        headers=headers,
        json={
            "template_slug": template_slug,
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 4},
        },
    )

    client.post(f"/api/v1/orders/{order_id}/validate", headers=headers)
    return order_id


class TestSubmitWithNoRules:
    def test_submit_without_rules_goes_to_submitted(
        self, integ_client, integ_session, seed_template,
    ):
        """When no approval rules exist, submit goes straight to 'submitted'."""
        headers = _auth_header(integ_client, "test-requester")
        order_id = _create_validated_order(integ_client, headers)

        resp = integ_client.post(
            f"/api/v1/orders/{order_id}/submit", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "submitted"


class TestSubmitWithCostThresholdRule:
    def test_expensive_order_gets_pending_approval(
        self, integ_app, integ_client, integ_session,
        seed_expensive_template,
    ):
        """Order exceeding cost threshold triggers approval."""
        # Create cost_threshold rule via admin API
        admin_header = _auth_header(integ_client, "test-admin")
        resp = integ_client.post(
            "/api/v1/admin/approval-rules",
            json={
                "name": "Cost Gate",
                "rule_type": "cost_threshold",
                "threshold_eur": 5000.00,
            },
            headers=admin_header,
        )
        assert resp.status_code == 201

        # Submit expensive order as requester
        requester_header = _auth_header(integ_client, "test-requester")
        order_id = _create_validated_order(
            integ_client, requester_header, template_slug="vm-expensive",
        )

        resp = integ_client.post(
            f"/api/v1/orders/{order_id}/submit", headers=requester_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "pending_approval"

    def test_cheap_order_not_blocked(
        self, integ_client, integ_session, seed_template,
    ):
        """Order below threshold still submits normally."""
        admin_header = _auth_header(integ_client, "test-admin")
        integ_client.post(
            "/api/v1/admin/approval-rules",
            json={
                "name": "Cost Gate",
                "rule_type": "cost_threshold",
                "threshold_eur": 5000.00,
            },
            headers=admin_header,
        )

        requester_header = _auth_header(integ_client, "test-requester")
        order_id = _create_validated_order(integ_client, requester_header)

        resp = integ_client.post(
            f"/api/v1/orders/{order_id}/submit", headers=requester_header,
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "submitted"


class TestApproveTriggersProvisioning:
    def test_approve_transitions_to_approved(
        self, integ_app, integ_client, integ_session,
        seed_expensive_template,
    ):
        """After approval, order status transitions to 'approved'."""
        admin_header = _auth_header(integ_client, "test-admin")
        integ_client.post(
            "/api/v1/admin/approval-rules",
            json={
                "name": "Cost Gate",
                "rule_type": "cost_threshold",
                "threshold_eur": 5000.00,
            },
            headers=admin_header,
        )

        requester_header = _auth_header(integ_client, "test-requester")
        order_id = _create_validated_order(
            integ_client, requester_header, template_slug="vm-expensive",
        )

        resp = integ_client.post(
            f"/api/v1/orders/{order_id}/submit", headers=requester_header,
        )
        assert resp.get_json()["status"] == "pending_approval"

        # Find the approval request
        approver_header = _auth_header(integ_client, "test-approver")
        resp = integ_client.get("/api/v1/approvals", headers=approver_header)
        approvals = resp.get_json()
        approval_id = next(a["id"] for a in approvals if a["order_id"] == order_id)

        # Approve
        resp = integ_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=approver_header,
            json={"reason": "Approved"},
        )
        assert resp.status_code == 200

        # Check order status is now approved
        resp = integ_client.get(
            f"/api/v1/orders/{order_id}",
            headers=requester_header,
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "approved"


class TestTemplateApprovalAlwaysRequired:
    def test_template_flag_triggers_approval(
        self, integ_client, integ_session, seed_approval_required_template,
    ):
        """Template with approval_always_required=True triggers pending_approval."""
        requester_header = _auth_header(integ_client, "test-requester")
        order_id = _create_validated_order(
            integ_client, requester_header, template_slug="vm-approval-required",
        )

        resp = integ_client.post(
            f"/api/v1/orders/{order_id}/submit", headers=requester_header,
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "pending_approval"
