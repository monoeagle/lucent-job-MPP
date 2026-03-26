class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client):
        response = client.get("/api/v1/health")
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["auth_mode"] == "stub"
