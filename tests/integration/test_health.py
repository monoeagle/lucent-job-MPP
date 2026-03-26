from app import create_app


class TestHealthEndpoint:
    def setup_method(self):
        app = create_app({"AUTH_MODE": "stub", "ENV": "development", "TESTING": "True"})
        self.client = app.test_client()

    def test_health_returns_200(self):
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self):
        response = self.client.get("/api/v1/health")
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["auth_mode"] == "stub"
