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


def test_fire_loop_returns_updated_loop_for_optimistic_ui_updates(client):
    created = client.post("/loops", json={"name": "Fast loop"}).json()

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
