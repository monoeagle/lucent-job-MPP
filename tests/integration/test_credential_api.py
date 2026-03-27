# tests/integration/test_credential_api.py
import os
from datetime import datetime, timezone, timedelta

import pytest

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def cred_app():
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
def cred_client(cred_app):
    app, _ = cred_app
    return app.test_client()


@pytest.fixture
def admin_header(cred_client):
    resp = cred_client.post("/api/v1/auth/login", json={"username": "test-admin"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def requester_header(cred_client):
    resp = cred_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def seed_order(cred_app):
    """Seed an order with one item, return (order_id, item_id)."""
    app, _ = cred_app
    with app.app_context():
        session = app.session_factory()
        from app.data.db.models.order import OrderModel, OrderItemModel
        import uuid

        order_id = str(uuid.uuid4())
        item_id = str(uuid.uuid4())
        order = OrderModel(
            id=order_id,
            order_number="ORD-CRED-001",
            requester_id="test-requester",
            status="provisioning",
            title="Test Credential Order",
        )
        item = OrderItemModel(
            id=item_id,
            order_id=order_id,
            template_slug="vm-linux",
            template_version="1.0",
            display_name="Test VM",
            parameters={},
            position=1,
        )
        session.add(order)
        session.add(item)
        session.commit()
        session.close()
    return order_id, item_id


class TestCreateCredentialLink:
    def test_create_credential_link_as_admin(self, cred_client, admin_header, seed_order):
        order_id, item_id = seed_order
        resp = cred_client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/credentials",
            headers=admin_header,
            json={"credentials": {"username": "admin", "password": "s3cret", "host": "10.0.0.1"}},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "token" in data
        assert "url" in data
        assert "expires_at" in data
        assert data["url"] == f"/api/v1/credentials/{data['token']}"

    def test_create_credential_link_requires_admin(self, cred_client, requester_header, seed_order):
        order_id, item_id = seed_order
        resp = cred_client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/credentials",
            headers=requester_header,
            json={"credentials": {"username": "admin", "password": "s3cret", "host": "10.0.0.1"}},
        )
        assert resp.status_code == 403


class TestRetrieveCredentials:
    def test_retrieve_credentials_with_token(self, cred_client, admin_header, requester_header, seed_order):
        order_id, item_id = seed_order
        create_resp = cred_client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/credentials",
            headers=admin_header,
            json={"credentials": {"username": "admin", "password": "s3cret", "host": "10.0.0.1"}},
        )
        token = create_resp.get_json()["token"]

        # Auth required now
        resp = cred_client.get(f"/api/v1/credentials/{token}", headers=requester_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["credentials"]["username"] == "admin"
        assert data["credentials"]["password"] == "s3cret"
        assert data["credentials"]["host"] == "10.0.0.1"
        assert "accessed_at" in data

    def test_retrieve_without_auth_returns_401(self, cred_client, admin_header, seed_order):
        order_id, item_id = seed_order
        create_resp = cred_client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/credentials",
            headers=admin_header,
            json={"credentials": {"username": "admin", "password": "s3cret", "host": "10.0.0.1"}},
        )
        token = create_resp.get_json()["token"]
        resp = cred_client.get(f"/api/v1/credentials/{token}")
        assert resp.status_code == 401

    def test_retrieve_same_token_again_returns_410(self, cred_client, admin_header, requester_header, seed_order):
        order_id, item_id = seed_order
        create_resp = cred_client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/credentials",
            headers=admin_header,
            json={"credentials": {"username": "admin", "password": "s3cret", "host": "10.0.0.1"}},
        )
        token = create_resp.get_json()["token"]

        # First access
        cred_client.get(f"/api/v1/credentials/{token}", headers=requester_header)
        # Second access — consumed
        resp = cred_client.get(f"/api/v1/credentials/{token}", headers=requester_header)
        assert resp.status_code == 410

    def test_retrieve_invalid_token_returns_404(self, cred_client, requester_header):
        resp = cred_client.get("/api/v1/credentials/invalid-token-value", headers=requester_header)
        assert resp.status_code == 404

    def test_retrieve_after_expiry_returns_410(self, cred_client, admin_header, requester_header, seed_order, cred_app):
        order_id, item_id = seed_order
        create_resp = cred_client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/credentials",
            headers=admin_header,
            json={"credentials": {"username": "admin", "password": "s3cret", "host": "10.0.0.1"}},
        )
        token = create_resp.get_json()["token"]

        # Manually expire the link
        app, _ = cred_app
        with app.app_context():
            session = app.session_factory()
            from app.data.db.models.credential_link import CredentialLinkModel
            import hashlib
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            link = session.query(CredentialLinkModel).filter_by(token_hash=token_hash).first()
            link.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            session.commit()
            session.close()

        resp = cred_client.get(f"/api/v1/credentials/{token}", headers=requester_header)
        assert resp.status_code == 410
