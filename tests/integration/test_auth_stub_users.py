from app import create_app


class TestStubUsersEndpoint:
    def test_stub_users_returns_list(self, client):
        response = client.get("/api/v1/dev/auth/stub-users")
        assert response.status_code == 200
        data = response.get_json()
        assert "stub_users" in data
        assert len(data["stub_users"]) == 4
        assert data["static_password"] == "stub-password"

    def test_stub_users_not_available_in_ldap_mode(self):
        app = create_app({"AUTH_MODE": "ldap", "ENV": "development", "TESTING": "True",
                           "JWT_SECRET": "test-secret"})
        client = app.test_client()
        response = client.get("/api/v1/dev/auth/stub-users")
        assert response.status_code == 404
