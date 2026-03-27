# tests/integration/test_approval_workflow_api.py
import os
import pytest
from datetime import datetime, timezone, timedelta

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.approval_repository import ApprovalRepository
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def workflow_app():
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
def workflow_client(workflow_app):
    app, _ = workflow_app
    return app.test_client()


@pytest.fixture
def workflow_session(workflow_app):
    app, _ = workflow_app
    session = app.session_factory()
    yield session
    session.close()


def _auth_header(client, username):
    resp = client.post("/api/v1/auth/login", json={"username": username})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


def _create_pending_approval(session, requester_id="test-requester"):
    """Create an order with a pending approval request. Returns (order_id, approval_id)."""
    order_repo = OrderRepository(session)
    order = order_repo.create_order(
        requester_id=requester_id,
        title="Order needing approval",
        business_reason="Test reason",
    )
    order_repo.update_order_status(order.id, "submitted")
    order_repo.update_order_status(order.id, "pending_approval")

    approval_repo = ApprovalRepository(session)
    deadline = datetime.now(timezone.utc) + timedelta(hours=48)
    req = approval_repo.create_request(order.id, ["rule-1"], deadline)
    return order.id, req.id


class TestListPendingApprovals:
    def test_list_pending_returns_200(self, workflow_client, workflow_session):
        order_id, approval_id = _create_pending_approval(workflow_session)

        approver_header = _auth_header(workflow_client, "test-approver")
        resp = workflow_client.get("/api/v1/approvals", headers=approver_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) >= 1
        assert any(a["id"] == approval_id for a in data["items"])

    def test_requester_sees_own_orders_only(self, workflow_client, workflow_session):
        _create_pending_approval(workflow_session, requester_id="test-requester")
        _create_pending_approval(workflow_session, requester_id="other-user")

        requester_header = _auth_header(workflow_client, "test-requester")
        resp = workflow_client.get("/api/v1/approvals", headers=requester_header)
        assert resp.status_code == 200
        data = resp.get_json()
        # Requester should only see their own
        for item in data["items"]:
            assert item["requester_id"] == "test-requester"


class TestApproveRequest:
    def test_approve_returns_200(self, workflow_client, workflow_session):
        order_id, approval_id = _create_pending_approval(workflow_session)

        approver_header = _auth_header(workflow_client, "test-approver")
        resp = workflow_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=approver_header,
            json={"reason": "Looks good"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "approved"
        assert data["decided_by"] == "test-approver"

    def test_admin_can_approve(self, workflow_client, workflow_session):
        order_id, approval_id = _create_pending_approval(workflow_session)

        admin_header = _auth_header(workflow_client, "test-admin")
        resp = workflow_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=admin_header,
            json={},
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "approved"


class TestRejectRequest:
    def test_reject_with_reason_returns_200(self, workflow_client, workflow_session):
        order_id, approval_id = _create_pending_approval(workflow_session)

        approver_header = _auth_header(workflow_client, "test-approver")
        resp = workflow_client.post(
            f"/api/v1/approvals/{approval_id}/reject",
            headers=approver_header,
            json={"reason": "Budget exceeded"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "rejected"
        assert data["decision_reason"] == "Budget exceeded"

    def test_reject_without_reason_returns_400(self, workflow_client, workflow_session):
        order_id, approval_id = _create_pending_approval(workflow_session)

        approver_header = _auth_header(workflow_client, "test-approver")
        resp = workflow_client.post(
            f"/api/v1/approvals/{approval_id}/reject",
            headers=approver_header,
            json={},
        )
        assert resp.status_code == 400


class TestSelfApprovalBlocked:
    def test_requester_cannot_approve_own_order(self, workflow_client, workflow_session):
        order_id, approval_id = _create_pending_approval(
            workflow_session, requester_id="test-requester",
        )

        requester_header = _auth_header(workflow_client, "test-requester")
        resp = workflow_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=requester_header,
        )
        assert resp.status_code == 403


class TestRequesterCannotApprove:
    def test_requester_role_cannot_approve_others(self, workflow_client, workflow_session):
        """A user with only requester role cannot approve (no approver/admin role)."""
        order_id, approval_id = _create_pending_approval(
            workflow_session, requester_id="test-admin",
        )

        requester_header = _auth_header(workflow_client, "test-requester")
        resp = workflow_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=requester_header,
        )
        assert resp.status_code == 403


class TestGetApprovalDetail:
    def test_get_detail_returns_200(self, workflow_client, workflow_session):
        order_id, approval_id = _create_pending_approval(workflow_session)

        approver_header = _auth_header(workflow_client, "test-approver")
        resp = workflow_client.get(
            f"/api/v1/approvals/{approval_id}",
            headers=approver_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == approval_id
        assert data["order_id"] == order_id
        assert data["status"] == "pending"
