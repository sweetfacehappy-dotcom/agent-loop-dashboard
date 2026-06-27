from fastapi.testclient import TestClient

from app.main import app


def test_connector_status_reports_configured_and_missing_connectors(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.internal")
    monkeypatch.setenv("JIRA_USERNAME", "carsten")
    monkeypatch.setenv("JIRA_API_TOKEN", "jira-token")
    monkeypatch.setenv("GITLAB_BASE_URL", "https://gitlab.example.internal")
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)

    client = TestClient(app)

    response = client.get("/connectors/status")

    assert response.status_code == 200
    assert response.json() == {
        "jira": {
            "base_url": "https://jira.example.internal",
            "configured": True,
            "missing": [],
        },
        "gitlab": {
            "base_url": "https://gitlab.example.internal",
            "configured": False,
            "missing": ["GITLAB_TOKEN"],
        },
    }
