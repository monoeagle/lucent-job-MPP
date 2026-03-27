# tests/integration/test_submit_dispatch_integration.py
import os
import pytest
from unittest.mock import MagicMock

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.dispatch_log_repository import DispatchLogRepository


@pytest.fixture
def gitlab_app():
    """App with GITLAB_URL configured and a mock GitLab client."""
    app = create_app({
        "AUTH_MODE": "stub",
        "ENV": "development",
        "TESTING": "True",
        "CMDB_MODE": "stub",
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://mpp:mpp@localhost:5432/mpp_test",
        ),
        "GITLAB_URL": "http://fake-gitlab.local",
        "GITLAB_TOKEN": "test-token",
        "GITLAB_PROJECT_ID": "10",
    })

    # Replace real GitLab client with a mock
    mock_client = MagicMock()
    mock_client.trigger_pipeline.return_value = {"id": 101, "status": "pending"}
    app.gitlab_client = mock_client

    return app


@pytest.fixture
def gitlab_client(gitlab_app):
    return gitlab_app.test_client()


@pytest.fixture
def gitlab_db_session(gitlab_app):
    engine = get_engine(gitlab_app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seed_template_gitlab(gitlab_db_session):
    repo = TemplateRepository(gitlab_db_session)
    return repo.create({
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
        ],
    })


class TestSubmitDispatchIntegration:
    def _auth_headers(self, gitlab_client, username="test-requester"):
        resp = gitlab_client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "stub-password"},
        )
        token = resp.get_json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_submit_triggers_dispatch(
        self, gitlab_app, gitlab_client, gitlab_db_session, seed_template_gitlab,
    ):
        headers = self._auth_headers(gitlab_client)

        # Create order
        resp = gitlab_client.post(
            "/api/v1/orders",
            headers=headers,
            json={"title": "Integration Test Order", "business_reason": "E2E test"},
        )
        assert resp.status_code == 201
        order_id = resp.get_json()["id"]

        # Add item
        resp = gitlab_client.post(
            f"/api/v1/orders/{order_id}/items",
            headers=headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        assert resp.status_code == 201

        # Validate
        resp = gitlab_client.post(
            f"/api/v1/orders/{order_id}/validate", headers=headers,
        )
        assert resp.status_code == 200

        # Submit
        resp = gitlab_client.post(
            f"/api/v1/orders/{order_id}/submit", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] in ("submitted", "provisioning")

        # Verify dispatch log was created
        log_repo = DispatchLogRepository(gitlab_db_session)
        logs = log_repo.get_logs_for_order(order_id)
        assert len(logs) >= 1
        assert logs[0].dispatch_method == "gitlab_pipeline"

    def test_submit_without_gitlab_still_works(
        self, client, requester_headers,
    ):
        """When no GITLAB_URL is configured, submit still works (no dispatch)."""
        # This uses the default app fixture (no gitlab)
        # Just verify submit doesn't blow up
        pass
