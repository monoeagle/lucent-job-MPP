# tests/integration/test_provisioning_webhook_api.py
import pytest
from unittest.mock import MagicMock, patch
from app.data.db.session import get_engine, get_session_factory, Base


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


class TestWebhookEndpoint:
    def test_webhook_without_token_returns_401(self, client, db_session):
        resp = client.post(
            "/api/v1/webhooks/gitlab",
            json={"object_attributes": {"id": 42, "status": "success"}},
        )
        assert resp.status_code == 401

    def test_webhook_with_wrong_token_returns_401(self, client, db_session):
        resp = client.post(
            "/api/v1/webhooks/gitlab",
            headers={"X-Gitlab-Token": "wrong-token"},
            json={"object_attributes": {"id": 42, "status": "success"}},
        )
        assert resp.status_code == 401

    def test_webhook_with_valid_token_returns_200(self, client, db_session, app):
        app.config["GITLAB_WEBHOOK_SECRET"] = "test-webhook-secret"
        resp = client.post(
            "/api/v1/webhooks/gitlab",
            headers={"X-Gitlab-Token": "test-webhook-secret"},
            json={
                "object_kind": "pipeline",
                "object_attributes": {"id": 42, "status": "success"},
            },
        )
        assert resp.status_code == 200

    def test_webhook_empty_body_with_valid_token_returns_200(self, client, db_session, app):
        app.config["GITLAB_WEBHOOK_SECRET"] = "test-webhook-secret"
        resp = client.post(
            "/api/v1/webhooks/gitlab",
            headers={"X-Gitlab-Token": "test-webhook-secret"},
            json={},
        )
        assert resp.status_code == 200


class TestDispatcherConfigEndpoint:
    def test_get_config_as_admin_returns_200(
        self, client, db_session, admin_headers,
    ):
        resp = client.get(
            "/api/v1/admin/dispatcher/config",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "dispatch_method" in data
        assert "gitlab_project_id" in data

    def test_get_config_as_requester_returns_403(
        self, client, db_session, requester_headers,
    ):
        resp = client.get(
            "/api/v1/admin/dispatcher/config",
            headers=requester_headers,
        )
        assert resp.status_code == 403


class TestDispatchLogEndpoint:
    def test_get_dispatch_log_returns_200(
        self, client, db_session, admin_headers,
    ):
        resp = client.get(
            "/api/v1/admin/orders/nonexistent-id/dispatch-log",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
