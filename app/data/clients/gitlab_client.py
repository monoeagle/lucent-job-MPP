# app/data/clients/gitlab_client.py
import requests
from requests.exceptions import ConnectionError, Timeout


class GitLabClient:
    class GitLabUnavailableError(Exception):
        pass

    class GitLabAuthError(Exception):
        pass

    class GitLabError(Exception):
        pass

    def __init__(self, base_url: str, token: str, project_id: int):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.project_id = project_id

    def _headers(self) -> dict:
        return {"PRIVATE-TOKEN": self.token}

    def _handle_response(self, response) -> dict:
        if response.status_code == 401:
            raise self.GitLabAuthError(response.text)
        if response.status_code >= 400:
            raise self.GitLabError(response.text)
        return response.json()

    def trigger_pipeline(self, ref: str, variables: dict) -> dict:
        url = f"{self.base_url}/api/v4/projects/{self.project_id}/trigger/pipeline"
        try:
            response = requests.post(
                url,
                json={"ref": ref, "variables": variables},
                headers=self._headers(),
                timeout=30,
            )
        except (ConnectionError, Timeout) as e:
            raise self.GitLabUnavailableError(str(e))
        return self._handle_response(response)

    def get_pipeline_status(self, pipeline_id: int) -> dict:
        url = f"{self.base_url}/api/v4/projects/{self.project_id}/pipelines/{pipeline_id}"
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=30,
            )
        except (ConnectionError, Timeout) as e:
            raise self.GitLabUnavailableError(str(e))
        return self._handle_response(response)
