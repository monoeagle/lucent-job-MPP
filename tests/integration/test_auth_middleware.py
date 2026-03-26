from app import create_app


class TestAuthMiddleware:
    def setup_method(self):
        self.app = create_app({"AUTH_MODE": "stub", "ENV": "development", "TESTING": "True"})
        self.client = self.app.test_client()

    def _get_token(self, username="test-requester"):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "stub-password"},
        )
        return response.get_json()["token"]

    def test_protected_endpoint_without_token(self):
        response = self.client.get("/api/v1/auth/me")
        assert response.status_code == 401
        data = response.get_json()
        assert data["error_code"] == "UNAUTHORIZED"

    def test_protected_endpoint_with_valid_token(self):
        token = self._get_token()
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "test-requester"
        assert data["roles"] == ["requester"]

    def test_protected_endpoint_with_invalid_token(self):
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_malformed_header(self):
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == 401

    def test_admin_only_endpoint_with_requester(self):
        token = self._get_token("test-requester")
        response = self.client.get(
            "/api/v1/admin/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_only_endpoint_with_admin(self):
        token = self._get_token("test-admin")
        response = self.client.get(
            "/api/v1/admin/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
