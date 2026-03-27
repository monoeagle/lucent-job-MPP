# tests/integration/test_approval_rules_api.py
import os
import pytest

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def approval_app():
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
def approval_client(approval_app):
    app, _ = approval_app
    return app.test_client()


@pytest.fixture
def admin_header(approval_client):
    resp = approval_client.post("/api/v1/auth/login", json={"username": "test-admin"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def requester_header(approval_client):
    resp = approval_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


def _valid_rule(**overrides):
    rule = {
        "name": "High Cost Approval",
        "rule_type": "cost_threshold",
        "threshold_eur": 5000.00,
    }
    rule.update(overrides)
    return rule


class TestCreateApprovalRule:
    def test_create_rule_returns_201(self, approval_client, admin_header):
        resp = approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(),
            headers=admin_header,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "High Cost Approval"
        assert data["rule_type"] == "cost_threshold"
        assert float(data["threshold_eur"]) == 5000.00
        assert data["is_active"] is True
        assert "id" in data

    def test_create_always_rule(self, approval_client, admin_header):
        resp = approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(name="Always", rule_type="always", threshold_eur=None),
            headers=admin_header,
        )
        assert resp.status_code == 201
        assert resp.get_json()["rule_type"] == "always"

    def test_create_service_type_rule(self, approval_client, admin_header):
        resp = approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(
                name="Firewall Rule",
                rule_type="service_type",
                threshold_eur=None,
                service_type_slug="firewall-rule",
            ),
            headers=admin_header,
        )
        assert resp.status_code == 201
        assert resp.get_json()["service_type_slug"] == "firewall-rule"


class TestListApprovalRules:
    def test_list_rules_returns_200(self, approval_client, admin_header):
        approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(),
            headers=admin_header,
        )
        resp = approval_client.get(
            "/api/v1/admin/approval-rules",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1
        assert data[0]["name"] == "High Cost Approval"


class TestUpdateApprovalRule:
    def test_update_rule_returns_200(self, approval_client, admin_header):
        resp = approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(),
            headers=admin_header,
        )
        rule_id = resp.get_json()["id"]

        resp = approval_client.patch(
            f"/api/v1/admin/approval-rules/{rule_id}",
            json={"name": "Updated Name", "is_active": False},
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False


class TestDeleteApprovalRule:
    def test_delete_rule_returns_204(self, approval_client, admin_header):
        resp = approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(),
            headers=admin_header,
        )
        rule_id = resp.get_json()["id"]

        resp = approval_client.delete(
            f"/api/v1/admin/approval-rules/{rule_id}",
            headers=admin_header,
        )
        assert resp.status_code == 204

    def test_delete_rule_with_pending_requests_returns_409(
        self, approval_app, approval_client, admin_header,
    ):
        app, _ = approval_app

        # Create a rule
        resp = approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(),
            headers=admin_header,
        )
        rule_id = resp.get_json()["id"]

        # Manually create a pending approval request referencing this rule
        with app.app_context():
            from flask import g
            session = app.session_factory()
            from app.data.repositories.order_repository import OrderRepository
            from app.data.repositories.approval_repository import ApprovalRepository

            order_repo = OrderRepository(session)
            order = order_repo.create_order(
                requester_id="test-requester",
                title="Test Order for Approval",
                business_reason="Testing",
            )
            order_repo.update_order_status(order.id, "submitted")

            approval_repo = ApprovalRepository(session)
            approval_repo.create_request(order.id, [rule_id], deadline_at=None or __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
            session.close()

        resp = approval_client.delete(
            f"/api/v1/admin/approval-rules/{rule_id}",
            headers=admin_header,
        )
        assert resp.status_code == 409


class TestApprovalRulesAdminOnly:
    def test_create_requires_admin(self, approval_client, requester_header):
        resp = approval_client.post(
            "/api/v1/admin/approval-rules",
            json=_valid_rule(),
            headers=requester_header,
        )
        assert resp.status_code == 403

    def test_list_requires_admin(self, approval_client, requester_header):
        resp = approval_client.get(
            "/api/v1/admin/approval-rules",
            headers=requester_header,
        )
        assert resp.status_code == 403

    def test_update_requires_admin(self, approval_client, requester_header):
        resp = approval_client.patch(
            "/api/v1/admin/approval-rules/some-id",
            json={"name": "Hack"},
            headers=requester_header,
        )
        assert resp.status_code == 403

    def test_delete_requires_admin(self, approval_client, requester_header):
        resp = approval_client.delete(
            "/api/v1/admin/approval-rules/some-id",
            headers=requester_header,
        )
        assert resp.status_code == 403


class TestApprovalSettings:
    def test_get_settings_returns_defaults(self, approval_client, admin_header):
        resp = approval_client.get(
            "/api/v1/admin/approval-settings",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["default_deadline_hours"] == 48
        assert data["allow_self_approval"] is False

    def test_update_settings(self, approval_client, admin_header):
        resp = approval_client.put(
            "/api/v1/admin/approval-settings",
            json={"default_deadline_hours": 72, "allow_self_approval": True},
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["default_deadline_hours"] == 72
        assert data["allow_self_approval"] is True

        # Verify persistence
        resp = approval_client.get(
            "/api/v1/admin/approval-settings",
            headers=admin_header,
        )
        data = resp.get_json()
        assert data["default_deadline_hours"] == 72
        assert data["allow_self_approval"] is True

    def test_settings_requires_admin(self, approval_client, requester_header):
        resp = approval_client.get(
            "/api/v1/admin/approval-settings",
            headers=requester_header,
        )
        assert resp.status_code == 403
