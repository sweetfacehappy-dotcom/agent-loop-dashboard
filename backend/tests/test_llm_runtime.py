from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app, build_anthropic_client, loops


def test_runtime_status_reports_anthropic_custom_endpoint_and_model_labels(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm-gateway.example.internal")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_MODEL_LABELS", "fast=claude-3-5-haiku-latest,smart=claude-3-5-sonnet-latest")

    client = TestClient(app)

    response = client.get("/runtime/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "anthropic",
        "configured": True,
        "base_url": "https://llm-gateway.example.internal",
        "missing": [],
        "model_labels": {
            "fast": "claude-3-5-haiku-latest",
            "smart": "claude-3-5-sonnet-latest",
        },
    }


def test_runtime_status_reports_missing_anthropic_config_without_leaking_token(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL_LABELS", raising=False)

    client = TestClient(app)

    response = client.get("/runtime/status")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "anthropic"
    assert body["configured"] is False
    assert body["base_url"] is None
    assert body["missing"] == ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL_LABELS"]
    assert "token" not in str(body).lower().replace("anthropic_auth_token", "")


def test_model_label_crud_updates_runtime_configuration(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm-gateway.example.internal")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_MODEL_LABELS", "fast=claude-haiku")
    loops.clear()
    client = TestClient(app)

    assert client.get("/runtime/model-labels").json() == {"fast": "claude-haiku"}

    create_response = client.post(
        "/runtime/model-labels",
        json={"label": "smart", "model": "claude-sonnet"},
    )
    assert create_response.status_code == 201
    assert create_response.json() == {"label": "smart", "model": "claude-sonnet"}
    assert client.get("/runtime/status").json()["model_labels"] == {
        "fast": "claude-haiku",
        "smart": "claude-sonnet",
    }

    update_response = client.put(
        "/runtime/model-labels/smart",
        json={"model": "claude-opus"},
    )
    assert update_response.status_code == 200
    assert update_response.json() == {"label": "smart", "model": "claude-opus"}

    created_loop = client.post("/loops", json={"name": "Smart model loop", "model_label": "smart"})
    assert created_loop.status_code == 201
    assert created_loop.json()["model_label"] == "smart"

    delete_response = client.delete("/runtime/model-labels/smart")
    assert delete_response.status_code == 204
    assert client.get("/runtime/model-labels").json() == {"fast": "claude-haiku"}


def test_model_label_crud_rejects_duplicates_and_unknown_deletes(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL_LABELS", "fast=claude-haiku")
    loops.clear()
    client = TestClient(app)

    duplicate_response = client.post(
        "/runtime/model-labels",
        json={"label": "fast", "model": "claude-other"},
    )
    missing_update = client.put("/runtime/model-labels/missing", json={"model": "claude-opus"})
    missing_delete = client.delete("/runtime/model-labels/missing")

    assert duplicate_response.status_code == 409
    assert missing_update.status_code == 404
    assert missing_delete.status_code == 404


def test_dashboard_created_model_labels_satisfy_runtime_status(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm-gateway.example.internal")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret-token")
    monkeypatch.delenv("ANTHROPIC_MODEL_LABELS", raising=False)
    loops.clear()
    client = TestClient(app)

    client.post("/runtime/model-labels", json={"label": "smart", "model": "claude-sonnet"})

    status = client.get("/runtime/status").json()
    assert status["configured"] is True
    assert status["missing"] == []
    assert status["model_labels"] == {"smart": "claude-sonnet"}


def test_loop_model_label_defaults_and_can_be_selected_per_loop(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm-gateway.example.internal")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_MODEL_LABELS", "fast=claude-haiku,smart=claude-sonnet")
    loops.clear()
    client = TestClient(app)

    default_response = client.post("/loops", json={"name": "Default model loop"})
    smart_response = client.post("/loops", json={"name": "Smart model loop", "model_label": "smart"})

    assert default_response.status_code == 201
    assert default_response.json()["model_label"] == "fast"
    assert smart_response.status_code == 201
    assert smart_response.json()["model_label"] == "smart"


def test_rejects_unknown_model_label(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL_LABELS", "fast=claude-haiku,smart=claude-sonnet")
    loops.clear()
    client = TestClient(app)

    response = client.post("/loops", json={"name": "Bad model loop", "model_label": "unknown"})

    assert response.status_code == 422
    assert "Unknown model_label" in str(response.json()["detail"])


def test_anthropic_sdk_client_uses_custom_endpoint_and_auth_token(monkeypatch):
    captured = {}

    class FakeAnthropic:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm-gateway.example.internal")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret-token")
    monkeypatch.setitem(__import__("sys").modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))

    build_anthropic_client()

    assert captured == {
        "api_key": "secret-token",
        "base_url": "https://llm-gateway.example.internal",
    }


def test_fire_loop_creates_llm_run_with_selected_model_label(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm-gateway.example.internal")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("ANTHROPIC_MODEL_LABELS", "fast=claude-haiku,smart=claude-sonnet")
    loops.clear()
    client = TestClient(app)
    created = client.post("/loops", json={"name": "Smart review loop", "model_label": "smart"}).json()

    response = client.post(f"/loops/{created['id']}/fire", json={"dry_run": True})

    assert response.status_code == 200
    body = response.json()
    assert body["loop"]["status"] == "ready"
    assert body["run"]["provider"] == "anthropic"
    assert body["run"]["model_label"] == "smart"
    assert body["run"]["model"] == "claude-sonnet"
    assert body["run"]["base_url"] == "https://llm-gateway.example.internal"
    assert "secret-token" not in str(body)
