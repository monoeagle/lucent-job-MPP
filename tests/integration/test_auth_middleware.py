class TestAuthMiddleware:
    def test_protected_endpoint_without_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        data = response.get_json()
        assert data["error_code"] == "UNAUTHORIZED"

    def test_protected_endpoint_with_valid_token(self, client, requester_headers):
        response = client.get("/api/v1/auth/me", headers=requester_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "test-requester"
        assert data["roles"] == ["requester"]

    def test_protected_endpoint_with_invalid_token(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_malformed_header(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == 401

    def test_admin_only_endpoint_with_requester(self, client, requester_headers):
        response = client.get("/api/v1/admin/health", headers=requester_headers)
        assert response.status_code == 403

    def test_admin_only_endpoint_with_admin(self, client, admin_headers):
        response = client.get("/api/v1/admin/health", headers=admin_headers)
        assert response.status_code == 200
