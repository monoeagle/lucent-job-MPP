class TestErrorFormat:
    def test_404_returns_standard_format(self, client):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.get_json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data
        assert data["error_code"] == "NOT_FOUND"

    def test_response_has_request_id_header(self, client):
        response = client.get("/api/v1/nonexistent")
        assert "X-Request-ID" in response.headers
        data = response.get_json()
        assert response.headers["X-Request-ID"] == data["request_id"]

    def test_success_response_has_request_id_header(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_405_returns_standard_format(self, client):
        response = client.put("/api/v1/health")
        assert response.status_code == 405
        data = response.get_json()
        assert data["error_code"] == "METHOD_NOT_ALLOWED"

    def test_validation_error_format(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "request_id" in data
