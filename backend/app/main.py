import os
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="Agent Loop Dashboard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5180",
        "http://127.0.0.1:5180",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoopStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class AgentRunStatus(str, Enum):
    planned = "planned"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


def parse_model_labels(raw: str | None = None) -> dict[str, str]:
    raw = raw if raw is not None else os.getenv("ANTHROPIC_MODEL_LABELS")
    if not raw:
        return {}

    labels: dict[str, str] = {}
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            continue
        label, model = item.split("=", 1)
        label = label.strip()
        model = model.strip()
        if label and model:
            labels[label] = model
    return labels


def default_model_label() -> str:
    labels = parse_model_labels()
    return next(iter(labels), "default")


def resolve_model_label(label: str | None) -> tuple[str, str | None]:
    labels = parse_model_labels()
    selected = label or default_model_label()
    if labels and selected not in labels:
        raise ValueError(f"Unknown model_label '{selected}'. Available labels: {', '.join(labels)}")
    return selected, labels.get(selected)


class LoopCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    jira_query: str | None = None
    gitlab_project_id: str | None = None
    mode: str = "review"
    model_label: str | None = None

    @model_validator(mode="after")
    def validate_model_label(self):
        try:
            selected, _ = resolve_model_label(self.model_label)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        self.model_label = selected
        return self


class Loop(LoopCreate):
    id: str
    status: LoopStatus
    created_at: datetime
    updated_at: datetime


class FireLoopRequest(BaseModel):
    dry_run: bool = True
    context_limit: int = Field(default=20, ge=1, le=100)


class AgentRun(BaseModel):
    id: str
    loop_id: str
    provider: str = "anthropic"
    status: AgentRunStatus
    dry_run: bool
    model_label: str
    model: str | None
    base_url: str | None
    created_at: datetime
    summary: str


class FireLoopResponse(BaseModel):
    loop: Loop
    run: AgentRun


loops: dict[str, Loop] = {}
runs: dict[str, AgentRun] = {}


def now() -> datetime:
    return datetime.now(timezone.utc)


def connector_status(prefix: str, required: list[str]) -> dict:
    missing = [name for name in required if not os.getenv(name)]
    return {
        "base_url": os.getenv(f"{prefix}_BASE_URL"),
        "configured": not missing,
        "missing": missing,
    }


def anthropic_runtime_status() -> dict:
    required = ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL_LABELS"]
    missing = [name for name in required if not os.getenv(name)]
    return {
        "provider": "anthropic",
        "configured": not missing,
        "base_url": os.getenv("ANTHROPIC_BASE_URL"),
        "missing": missing,
        "model_labels": parse_model_labels(),
    }


def build_anthropic_client():
    """Build the official Anthropic SDK client with custom endpoint config.

    The app intentionally uses ANTHROPIC_AUTH_TOKEN instead of exposing provider-
    specific API key naming in loop config. The token is only passed to the SDK
    and is never returned by status/run endpoints.
    """
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("The anthropic SDK is not installed") from exc

    return Anthropic(
        api_key=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )


def create_agent_run(loop: Loop, payload: FireLoopRequest) -> AgentRun:
    _, model = resolve_model_label(loop.model_label)
    runtime = anthropic_runtime_status()
    run_status = AgentRunStatus.planned if payload.dry_run else AgentRunStatus.queued
    run = AgentRun(
        id=str(uuid4()),
        loop_id=loop.id,
        status=run_status,
        dry_run=payload.dry_run,
        model_label=loop.model_label or default_model_label(),
        model=model,
        base_url=runtime["base_url"],
        created_at=now(),
        summary=(
            "Dry run created: Anthropic agent call was not dispatched."
            if payload.dry_run
            else "Anthropic agent run queued for dispatch."
        ),
    )
    runs[run.id] = run
    return run


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/connectors/status")
def get_connector_status():
    return {
        "jira": connector_status("JIRA", ["JIRA_BASE_URL", "JIRA_USERNAME", "JIRA_API_TOKEN"]),
        "gitlab": connector_status("GITLAB", ["GITLAB_BASE_URL", "GITLAB_TOKEN"]),
    }


@app.get("/runtime/status")
def get_runtime_status():
    return anthropic_runtime_status()


@app.get("/loops", response_model=list[Loop])
def list_loops():
    return list(loops.values())


@app.post("/loops", response_model=Loop, status_code=201)
def create_loop(payload: LoopCreate):
    loop_id = str(uuid4())
    loop = Loop(id=loop_id, status=LoopStatus.draft, created_at=now(), updated_at=now(), **payload.model_dump())
    loops[loop_id] = loop
    return loop


@app.get("/loops/{loop_id}", response_model=Loop)
def get_loop(loop_id: str):
    if loop_id not in loops:
        raise HTTPException(status_code=404, detail="Loop not found")
    return loops[loop_id]


@app.put("/loops/{loop_id}", response_model=Loop)
def update_loop(loop_id: str, payload: LoopCreate):
    if loop_id not in loops:
        raise HTTPException(status_code=404, detail="Loop not found")
    existing = loops[loop_id]
    updated = Loop(id=loop_id, status=existing.status, created_at=existing.created_at, updated_at=now(), **payload.model_dump())
    loops[loop_id] = updated
    return updated


@app.delete("/loops/{loop_id}", status_code=204)
def delete_loop(loop_id: str):
    if loop_id not in loops:
        raise HTTPException(status_code=404, detail="Loop not found")
    del loops[loop_id]


@app.post("/loops/{loop_id}/fire", response_model=FireLoopResponse)
def fire_loop(loop_id: str, payload: FireLoopRequest):
    if loop_id not in loops:
        raise HTTPException(status_code=404, detail="Loop not found")
    loop = loops[loop_id]
    run = create_agent_run(loop, payload)
    loop.status = LoopStatus.running if not payload.dry_run else LoopStatus.ready
    loop.updated_at = now()
    return FireLoopResponse(loop=loop, run=run)
