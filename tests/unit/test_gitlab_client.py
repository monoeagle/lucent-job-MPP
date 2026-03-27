# tests/unit/test_gitlab_client.py
import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import ConnectionError, Timeout

from app.data.clients.gitlab_client import GitLabClient


@pytest.fixture
def client():
    return GitLabClient(
        base_url="https://gitlab.example.com",
        token="test-token",
        project_id=42,
    )


class TestTriggerPipeline:
    @patch("app.data.clients.gitlab_client.requests.post")
    def test_success_returns_pipeline_dict(self, mock_post, client):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 100, "status": "pending"}
        mock_post.return_value = mock_response

        result = client.trigger_pipeline(ref="main", variables={"ENV": "staging"})

        assert result == {"id": 100, "status": "pending"}
        mock_post.assert_called_once_with(
            "https://gitlab.example.com/api/v4/projects/42/trigger/pipeline",
            json={"ref": "main", "variables": {"ENV": "staging"}},
            headers={"PRIVATE-TOKEN": "test-token"},
            timeout=30,
        )

    @patch("app.data.clients.gitlab_client.requests.post")
    def test_401_raises_auth_error(self, mock_post, client):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        with pytest.raises(GitLabClient.GitLabAuthError):
            client.trigger_pipeline(ref="main", variables={})

    @patch("app.data.clients.gitlab_client.requests.post")
    def test_connection_error_raises_unavailable(self, mock_post, client):
        mock_post.side_effect = ConnectionError("connection refused")

        with pytest.raises(GitLabClient.GitLabUnavailableError):
            client.trigger_pipeline(ref="main", variables={})

    @patch("app.data.clients.gitlab_client.requests.post")
    def test_500_raises_gitlab_error(self, mock_post, client):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(GitLabClient.GitLabError):
            client.trigger_pipeline(ref="main", variables={})


class TestGetPipelineStatus:
    @patch("app.data.clients.gitlab_client.requests.get")
    def test_success_returns_status_dict(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 100, "status": "success"}
        mock_get.return_value = mock_response

        result = client.get_pipeline_status(pipeline_id=100)

        assert result == {"id": 100, "status": "success"}
        mock_get.assert_called_once_with(
            "https://gitlab.example.com/api/v4/projects/42/pipelines/100",
            headers={"PRIVATE-TOKEN": "test-token"},
            timeout=30,
        )

    @patch("app.data.clients.gitlab_client.requests.get")
    def test_404_raises_gitlab_error(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with pytest.raises(GitLabClient.GitLabError):
            client.get_pipeline_status(pipeline_id=999)

    @patch("app.data.clients.gitlab_client.requests.get")
    def test_connection_error_raises_unavailable(self, mock_get, client):
        mock_get.side_effect = ConnectionError("connection refused")

        with pytest.raises(GitLabClient.GitLabUnavailableError):
            client.get_pipeline_status(pipeline_id=100)
