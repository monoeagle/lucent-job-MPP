class TestAuthLogin:
    def test_login_success(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester", "password": "stub-password"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert data["user"]["username"] == "test-requester"
        assert data["user"]["roles"] == ["requester"]
        assert "expires_at" in data

    def test_login_without_password(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester"},
        )
        assert response.status_code == 200

    def test_login_empty_password(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester", "password": ""},
        )
        assert response.status_code == 200

    def test_login_unknown_user(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "unknown", "password": "stub-password"},
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["error_code"] == "INVALID_CREDENTIALS"

    def test_login_missing_username(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "VALIDATION_FAILED"

    def test_login_response_has_auth_mode_header(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester", "password": "stub-password"},
        )
        assert response.headers.get("X-Auth-Mode") == "stub"

    def test_login_multi_role_user(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-multi", "password": "stub-password"},
        )
        data = response.get_json()
        assert set(data["user"]["roles"]) == {"requester", "approver"}
