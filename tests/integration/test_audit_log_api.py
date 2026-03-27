# tests/integration/test_audit_log_api.py
import os
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def audit_app():
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
def audit_client(audit_app):
    app, _ = audit_app
    return app.test_client()


@pytest.fixture
def admin_header(audit_client):
    resp = audit_client.post("/api/v1/auth/login", json={"username": "test-admin"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def requester_header(audit_client):
    resp = audit_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def seed_audit_entries(audit_app):
    """Seed audit log entries via the service layer."""
    app, _ = audit_app

    def _seed():
        with app.app_context():
            session = app.session_factory()
            from app.data.repositories.audit_log_repository import AuditLogRepository
            from app.services.audit_service import AuditService

            repo = AuditLogRepository(session)
            service = AuditService(repo)

            service.log("user-1", "order_created", "order", entity_id="ord-1",
                        details={"title": "First Order"})
            service.log("user-1", "order_submitted", "order", entity_id="ord-1")
            service.log("user-2", "approval_approved", "approval_request",
                        entity_id="apr-1", details={"reason": "Looks good"})
            service.log(None, "system_cleanup", "system",
                        details={"removed": 5})
            service.log("user-1", "order_created", "order", entity_id="ord-2",
                        details={"title": "Second Order"})

            session.close()

    return _seed


class TestAuditLogList:
    def test_list_returns_200_with_entries(self, audit_client, admin_header,
                                           seed_audit_entries):
        seed_audit_entries()
        resp = audit_client.get("/api/v1/admin/audit-log", headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_list_filter_by_action(self, audit_client, admin_header,
                                    seed_audit_entries):
        seed_audit_entries()
        resp = audit_client.get(
            "/api/v1/admin/audit-log?action=order_created",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["action"] == "order_created"

    def test_list_filter_by_actor_id(self, audit_client, admin_header,
                                      seed_audit_entries):
        seed_audit_entries()
        resp = audit_client.get(
            "/api/v1/admin/audit-log?actor_id=user-2",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["actor_id"] == "user-2"

    def test_list_filter_by_entity_type(self, audit_client, admin_header,
                                         seed_audit_entries):
        seed_audit_entries()
        resp = audit_client.get(
            "/api/v1/admin/audit-log?entity_type=order",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["entity_type"] == "order"

    def test_list_filter_by_date_range(self, audit_app, audit_client,
                                        admin_header):
        app, _ = audit_app
        with app.app_context():
            session = app.session_factory()
            from app.data.repositories.audit_log_repository import AuditLogRepository
            from app.data.db.models.audit_log import AuditLogModel
            import uuid

            repo = AuditLogRepository(session)

            now = datetime.now(timezone.utc)
            old_entry = AuditLogModel(
                id=str(uuid.uuid4()),
                timestamp=now - timedelta(days=10),
                actor_id="user-old",
                actor_type="user",
                action="old_action",
                entity_type="order",
            )
            new_entry = AuditLogModel(
                id=str(uuid.uuid4()),
                timestamp=now - timedelta(hours=1),
                actor_id="user-new",
                actor_type="user",
                action="new_action",
                entity_type="order",
            )
            session.add_all([old_entry, new_entry])
            session.commit()
            session.close()

        from_date = (now - timedelta(days=2)).isoformat()
        to_date = now.isoformat()
        resp = audit_client.get(
            f"/api/v1/admin/audit-log?from_date={from_date}&to_date={to_date}",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "new_action"

    def test_list_pagination(self, audit_client, admin_header,
                              seed_audit_entries):
        seed_audit_entries()
        resp = audit_client.get(
            "/api/v1/admin/audit-log?limit=2&offset=0",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 0

        resp2 = audit_client.get(
            "/api/v1/admin/audit-log?limit=2&offset=2",
            headers=admin_header,
        )
        data2 = resp2.get_json()
        assert len(data2["items"]) == 2
        assert data2["offset"] == 2


class TestAuditLogExport:
    def test_export_returns_full_array(self, audit_client, admin_header,
                                        seed_audit_entries):
        seed_audit_entries()
        resp = audit_client.get(
            "/api/v1/admin/audit-log/export",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 5

    def test_export_with_filter(self, audit_client, admin_header,
                                 seed_audit_entries):
        seed_audit_entries()
        resp = audit_client.get(
            "/api/v1/admin/audit-log/export?action=order_created",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        for item in data:
            assert item["action"] == "order_created"


class TestAuditLogAdminOnly:
    def test_list_requires_admin(self, audit_client, requester_header):
        resp = audit_client.get(
            "/api/v1/admin/audit-log",
            headers=requester_header,
        )
        assert resp.status_code == 403

    def test_export_requires_admin(self, audit_client, requester_header):
        resp = audit_client.get(
            "/api/v1/admin/audit-log/export",
            headers=requester_header,
        )
        assert resp.status_code == 403


class TestAuditServiceFireAndForget:
    def test_log_does_not_raise_on_exception(self, audit_app):
        """Service.log() should catch exceptions silently."""
        app, _ = audit_app
        with app.app_context():
            from app.services.audit_service import AuditService
            # Pass None as repo to trigger an error inside log()
            service = AuditService(repo=None)
            # Should not raise
            service.log("user-1", "some_action", "some_entity")
