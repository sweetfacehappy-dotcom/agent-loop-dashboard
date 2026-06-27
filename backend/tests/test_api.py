from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from app.main import Loop, LoopStatus, app, loops, now


@pytest.fixture(autouse=True)
def clear_loops():
    loops.clear()
    yield
    loops.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_loop_crud_lifecycle(client):
    create_response = client.post(
        "/loops",
        json={
            "name": "MR review loop",
            "description": "Review GitLab MRs",
            "jira_query": "project = ALD",
            "gitlab_project_id": "123",
            "mode": "review",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"]
    assert created["status"] == "draft"
    assert created["name"] == "MR review loop"

    loop_id = created["id"]
    assert client.get(f"/loops/{loop_id}").json() == created
    assert client.get("/loops").json() == [created]

    update_response = client.put(
        f"/loops/{loop_id}",
        json={"name": "Updated loop", "description": "Updated", "mode": "review"},
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == loop_id
    assert updated["name"] == "Updated loop"
    assert updated["status"] == "draft"
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] >= created["updated_at"]

    delete_response = client.delete(f"/loops/{loop_id}")

    assert delete_response.status_code == 204
    assert client.get(f"/loops/{loop_id}").status_code == 404
    assert client.get("/loops").json() == []


def test_loop_setup_captures_prompt_design_components(client):
    create_response = client.post(
        "/loops",
        json={
            "name": "MR review loop",
            "description": "Review risky merge requests",
            "objective": "Find merge request risks before code is merged.",
            "trigger": "Run when a merge request is opened or updated.",
            "input_sources": "Jira ticket, GitLab MR diff, discussion comments, CI status.",
            "instructions": "Prioritize correctness, security, and maintainability.",
            "constraints": "Do not approve or merge code. Do not expose secrets.",
            "allowed_actions": "Leave review comments, request human approval for risky changes.",
            "output_format": "Markdown summary with risks, required fixes, and confidence.",
            "success_criteria": "Every blocking risk has an actionable comment.",
            "stop_conditions": "Stop after one complete MR review or when required context is missing.",
            "escalation_policy": "Ask a human when confidence is low or production data is involved.",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["objective"] == "Find merge request risks before code is merged."
    assert created["trigger"] == "Run when a merge request is opened or updated."
    assert created["input_sources"] == "Jira ticket, GitLab MR diff, discussion comments, CI status."
    assert created["instructions"] == "Prioritize correctness, security, and maintainability."
    assert created["constraints"] == "Do not approve or merge code. Do not expose secrets."
    assert created["allowed_actions"] == "Leave review comments, request human approval for risky changes."
    assert created["output_format"] == "Markdown summary with risks, required fixes, and confidence."
    assert created["success_criteria"] == "Every blocking risk has an actionable comment."
    assert created["stop_conditions"] == "Stop after one complete MR review or when required context is missing."
    assert created["escalation_policy"] == "Ask a human when confidence is low or production data is involved."


def test_fire_loop_includes_assembled_prompt_snapshot(client):
    created = client.post(
        "/loops",
        json={
            "name": "Fast loop",
            "objective": "Review a merge request for release blockers.",
            "instructions": "Be concise and cite evidence.",
            "output_format": "Return sections: summary, blockers, next actions.",
            "success_criteria": "All release blockers are identified.",
        },
    ).json()

    fire_response = client.post(
        f"/loops/{created['id']}/fire",
        json={"dry_run": False, "context_limit": 5},
    )

    assert fire_response.status_code == 200
    fired = fire_response.json()
    loop = fired["loop"]
    assert loop["id"] == created["id"]
    assert loop["name"] == "Fast loop"
    assert loop["status"] == "running"
    assert loop["updated_at"] >= created["updated_at"]
    assert fired["run"]["loop_id"] == created["id"]
    assert fired["run"]["dry_run"] is False
    assert "## Objective\nReview a merge request for release blockers." in fired["run"]["prompt_snapshot"]
    assert "## Instructions\nBe concise and cite evidence." in fired["run"]["prompt_snapshot"]
    assert "## Output format\nReturn sections: summary, blockers, next actions." in fired["run"]["prompt_snapshot"]
    assert client.get(f"/loops/{created['id']}").json() == loop


def test_unknown_loop_operations_return_404(client):
    assert client.get("/loops/missing").status_code == 404
    assert client.put("/loops/missing", json={"name": "Missing"}).status_code == 404
    assert client.delete("/loops/missing").status_code == 404
    assert client.post("/loops/missing/fire", json={"dry_run": True}).status_code == 404


def test_list_loops_responds_quickly_with_many_loops(client):
    for index in range(500):
        timestamp = now()
        loops[str(index)] = Loop(
            id=str(index),
            name=f"Loop {index}",
            description="Review GitLab MRs using Jira context",
            status=LoopStatus.draft,
            created_at=timestamp,
            updated_at=timestamp,
        )

    start = perf_counter()
    response = client.get("/loops")
    elapsed_ms = (perf_counter() - start) * 1000

    assert response.status_code == 200
    assert len(response.json()) == 500
    assert elapsed_ms < 100
