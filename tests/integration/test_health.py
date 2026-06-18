class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client):
        response = client.get("/api/v1/health")
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["auth_mode"] == "stub"


class TestReadinessEndpoint:
    def test_ready_returns_200_when_db_reachable(self, client):
        response = client.get("/api/v1/ready")
        assert response.status_code == 200

    def test_ready_reports_database_ok(self, client):
        response = client.get("/api/v1/ready")
        data = response.get_json()
        assert data["status"] == "ready"
        assert data["database"] == "ok"

    def test_ready_returns_503_when_db_unreachable(self):
        from app import create_app
        app = create_app({
            "AUTH_MODE": "stub",
            "ENV": "development",
            "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_does_not_exist_xyz",
        })
        response = app.test_client().get("/api/v1/ready")
        assert response.status_code == 503
        assert response.get_json()["database"] == "error"
