import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum
from uuid import uuid4
from datetime import datetime, timezone

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

class LoopCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    jira_query: str | None = None
    gitlab_project_id: str | None = None
    mode: str = "review"

class Loop(LoopCreate):
    id: str
    status: LoopStatus
    created_at: datetime
    updated_at: datetime

class FireLoopRequest(BaseModel):
    dry_run: bool = True
    context_limit: int = Field(default=20, ge=1, le=100)

loops: dict[str, Loop] = {}

def now() -> datetime:
    return datetime.now(timezone.utc)

def connector_status(prefix: str, required: list[str]) -> dict:
    missing = [name for name in required if not os.getenv(name)]
    return {
        "base_url": os.getenv(f"{prefix}_BASE_URL"),
        "configured": not missing,
        "missing": missing,
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/connectors/status")
def get_connector_status():
    return {
        "jira": connector_status("JIRA", ["JIRA_BASE_URL", "JIRA_USERNAME", "JIRA_API_TOKEN"]),
        "gitlab": connector_status("GITLAB", ["GITLAB_BASE_URL", "GITLAB_TOKEN"]),
    }

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

@app.post("/loops/{loop_id}/fire", response_model=Loop)
def fire_loop(loop_id: str, payload: FireLoopRequest):
    if loop_id not in loops:
        raise HTTPException(status_code=404, detail="Loop not found")
    loop = loops[loop_id]
    loop.status = LoopStatus.running if not payload.dry_run else LoopStatus.ready
    loop.updated_at = now()
    return loop
