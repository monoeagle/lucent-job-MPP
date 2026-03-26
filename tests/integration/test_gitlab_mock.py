import pytest
from stubs.gitlab_mock import create_gitlab_mock_app


@pytest.fixture
def mock_client():
    app = create_gitlab_mock_app()
    app.config["TESTING"] = True
    return app.test_client()


class TestGitLabMock:
    def test_trigger_pipeline(self, mock_client):
        resp = mock_client.post("/api/v4/projects/10/trigger/pipeline",
                                 json={"token": "test-token", "ref": "main",
                                        "variables": {"TF_VAR_cpu": "4"}})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["id"] == 1
        assert data["status"] == "pending"

    def test_trigger_without_token(self, mock_client):
        resp = mock_client.post("/api/v4/projects/10/trigger/pipeline",
                                 json={"ref": "main"})
        assert resp.status_code == 401

    def test_get_pipeline_status(self, mock_client):
        mock_client.post("/api/v4/projects/10/trigger/pipeline",
                          json={"token": "t", "ref": "main"})
        resp = mock_client.get("/api/v4/projects/10/pipelines/1")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "pending"

    def test_get_unknown_pipeline(self, mock_client):
        resp = mock_client.get("/api/v4/projects/10/pipelines/999")
        assert resp.status_code == 404

    def test_advance_pipeline(self, mock_client):
        mock_client.post("/api/v4/projects/10/trigger/pipeline",
                          json={"token": "t", "ref": "main"})
        # pending → running
        resp = mock_client.post("/dev/gitlab-mock/pipelines/1/advance")
        assert resp.get_json()["status"] == "running"
        # running → success
        resp = mock_client.post("/dev/gitlab-mock/pipelines/1/advance")
        assert resp.get_json()["status"] == "success"
        # already terminal
        resp = mock_client.post("/dev/gitlab-mock/pipelines/1/advance")
        assert resp.status_code == 409

    def test_inspect_pipelines(self, mock_client):
        mock_client.post("/api/v4/projects/10/trigger/pipeline",
                          json={"token": "t", "ref": "main",
                                 "variables": {"TF_VAR_x": "1"}})
        resp = mock_client.get("/dev/gitlab-mock/pipelines")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["pipelines"][0]["variables"]["TF_VAR_x"] == "1"

    def test_reset_pipelines(self, mock_client):
        mock_client.post("/api/v4/projects/10/trigger/pipeline",
                          json={"token": "t", "ref": "main"})
        mock_client.delete("/dev/gitlab-mock/pipelines")
        resp = mock_client.get("/dev/gitlab-mock/pipelines")
        assert resp.get_json()["total"] == 0

    def test_variables_stored(self, mock_client):
        mock_client.post("/api/v4/projects/10/trigger/pipeline",
                          json={"token": "t", "ref": "main",
                                 "variables": {"TF_VAR_cpu": "4", "TF_VAR_ram": "8"}})
        resp = mock_client.get("/dev/gitlab-mock/pipelines")
        vars = resp.get_json()["pipelines"][0]["variables"]
        assert vars["TF_VAR_cpu"] == "4"
        assert vars["TF_VAR_ram"] == "8"
