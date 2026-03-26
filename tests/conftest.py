import pytest
from app import create_app


@pytest.fixture
def app():
    app = create_app({
        "AUTH_MODE": "stub",
        "ENV": "development",
        "TESTING": "True",
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Factory fixture: returns auth headers for a given username."""
    def _get_headers(username="test-requester"):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "stub-password"},
        )
        token = response.get_json()["token"]
        return {"Authorization": f"Bearer {token}"}
    return _get_headers


@pytest.fixture
def requester_headers(auth_headers):
    return auth_headers("test-requester")


@pytest.fixture
def approver_headers(auth_headers):
    return auth_headers("test-approver")


@pytest.fixture
def admin_headers(auth_headers):
    return auth_headers("test-admin")
