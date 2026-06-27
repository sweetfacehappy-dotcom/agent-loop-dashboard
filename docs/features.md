# Features

This document is the feature inventory and lightweight roadmap for Agent Loop Dashboard. Status values are intended to make the file usable as an idea log as well as product documentation.

## Status legend

- **Implemented**: available in the current app and covered by tests or build verification.
- **Scaffolded**: interface or architecture exists, but the behavior is partial, in-memory, or not connected to real external systems yet.
- **Planned**: described product capability that is not implemented yet.

## Dashboard and user interface

### Dashboard shell

- **Status**: Implemented
- **Description**: React/Vite dashboard for creating, monitoring, and firing bounded agent loops.
- **Current behavior**:
  - Loads loop list and Anthropic runtime status on startup.
  - Shows API errors in an on-page error panel.
  - Displays loop cards with name, description, status, and selected model label.
- **Primary files**: `frontend/src/main.jsx`, `frontend/src/style.css`

### Runtime config panel

- **Status**: Implemented
- **Description**: Dashboard section for Anthropic runtime visibility and model-label management.
- **Current behavior**:
  - Shows runtime configured/missing state.
  - Shows configured Anthropic endpoint without exposing tokens.
  - Lists configured model labels.
  - Lets users add model labels from the dashboard.
  - Lets users edit model IDs inline.
  - Lets users delete labels.
  - Refreshes runtime state after changes so new labels are immediately selectable for loops.
- **Primary API**: `/runtime/status`, `/runtime/model-labels`
- **Primary files**: `frontend/src/main.jsx`, `backend/app/main.py`

### Loop creation form

- **Status**: Implemented
- **Description**: Dashboard form for creating loop definitions.
- **Current behavior**:
  - Creates a loop with a name, default review description, review mode, and selected model label.
  - Select options come from the editable runtime model-label map.
  - If labels exist, the first configured label becomes the default selection.
- **Primary API**: `POST /loops`

### Loop list and optimistic fire updates

- **Status**: Implemented
- **Description**: Loop cards show current loop state and update after a fire request.
- **Current behavior**:
  - Displays each loop as a dashboard card.
  - `Dry-run fire` calls the backend and replaces the updated loop in local UI state.
  - Last dry-run/run metadata is shown after firing.
- **Primary API**: `POST /loops/{loop_id}/fire`

## Backend API

### Health check

- **Status**: Implemented
- **Description**: Basic service health endpoint.
- **Endpoint**: `GET /health`
- **Response**: `{ "status": "ok" }`

### Connector status

- **Status**: Scaffolded
- **Description**: Reports whether required Jira and GitLab environment variables are present.
- **Endpoint**: `GET /connectors/status`
- **Current behavior**:
  - Checks Jira env vars: `JIRA_BASE_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`.
  - Checks GitLab env vars: `GITLAB_BASE_URL`, `GITLAB_TOKEN`.
  - Returns base URL, configured boolean, and missing variable names.
- **Not yet implemented**:
  - Actual Jira API connectivity check.
  - Actual GitLab API connectivity check.
  - Permission/scope validation.

### Runtime status

- **Status**: Implemented
- **Description**: Reports Anthropic runtime configuration without leaking credentials.
- **Endpoint**: `GET /runtime/status`
- **Current behavior**:
  - Returns provider name, configured state, base URL, missing config keys, and model-label map.
  - Does not return `ANTHROPIC_AUTH_TOKEN` or any raw secret value.
  - Treats dashboard-created model labels as satisfying the model-label config requirement.

### Model label CRUD

- **Status**: Implemented
- **Description**: Manage friendly model labels that map to concrete Anthropic model IDs.
- **Endpoints**:
  - `GET /runtime/model-labels`
  - `POST /runtime/model-labels`
  - `PUT /runtime/model-labels/{label}`
  - `DELETE /runtime/model-labels/{label}`
- **Current behavior**:
  - Seeds labels from `ANTHROPIC_MODEL_LABELS` when available.
  - Allows dashboard/API users to add labels at runtime.
  - Rejects duplicate labels with `409`.
  - Rejects update/delete for unknown labels with `404`.
  - Accepts labels matching `A-Z`, `a-z`, `0-9`, `_`, and `-`.
- **Current limitation**:
  - Runtime edits are in-memory only; they do not persist to database or `.env` across process restarts.

### Loop CRUD

- **Status**: Implemented
- **Description**: CRUD API for loop definitions.
- **Endpoints**:
  - `GET /loops`
  - `POST /loops`
  - `GET /loops/{loop_id}`
  - `PUT /loops/{loop_id}`
  - `DELETE /loops/{loop_id}`
- **Loop fields**:
  - `id`
  - `name`
  - `description`
  - `jira_query`
  - `gitlab_project_id`
  - `mode`
  - `model_label`
  - `status`
  - `created_at`
  - `updated_at`
- **Current behavior**:
  - New loops start in `draft` status.
  - Unknown loop reads/updates/deletes return `404`.
  - Loop model labels are validated against configured labels when labels exist.
  - A missing model label defaults to the first configured label, or `default` if no labels exist.
- **Current limitation**:
  - Loop state is in-memory only; it does not persist across backend restarts.

### Fire loop / agent run creation

- **Status**: Scaffolded
- **Description**: Creates an agent run record for a loop and updates loop status.
- **Endpoint**: `POST /loops/{loop_id}/fire`
- **Request fields**:
  - `dry_run`: boolean, default `true`
  - `context_limit`: integer, default `20`, min `1`, max `100`
- **Current behavior**:
  - Resolves the loop `model_label` to a concrete model ID.
  - Creates an in-memory `AgentRun` record.
  - For dry runs, sets run status to `planned` and loop status to `ready`.
  - For non-dry runs, sets run status to `queued` and loop status to `running`.
  - Returns both the updated loop and the run record.
  - Does not dispatch to the LLM for dry runs.
- **Not yet implemented**:
  - Real asynchronous job queue.
  - Actual Anthropic message dispatch.
  - Run status progression beyond planned/queued scaffolding.
  - Run history listing endpoints.

## Anthropic runtime integration

### Anthropic SDK adapter

- **Status**: Scaffolded
- **Description**: Backend adapter for constructing the official Anthropic SDK client with a custom endpoint.
- **Current behavior**:
  - Uses `ANTHROPIC_AUTH_TOKEN` as the SDK `api_key`.
  - Uses `ANTHROPIC_BASE_URL` as the SDK `base_url`.
  - Keeps auth token out of status and run responses.
- **Not yet implemented**:
  - Prompt/context construction.
  - Message request/response handling.
  - Tool-use protocol for proposed Jira/GitLab actions.
  - Retry and provider error handling.

### Per-loop model selection

- **Status**: Implemented
- **Description**: Each loop stores a friendly `model_label` instead of raw provider configuration.
- **Current behavior**:
  - Users choose a model label when creating a loop.
  - Backend resolves the label to a model ID at run creation time.
  - Run responses include selected label and resolved model ID, but no secrets.

## Jira and GitLab integration

### Jira connector configuration

- **Status**: Scaffolded
- **Description**: Environment-variable based configuration status for self-hosted Jira.
- **Current behavior**:
  - Reports whether Jira base URL, username, and token are present.
- **Planned behavior**:
  - Pull Jira issues by JQL/project scope.
  - Read Jira issue fields and comments.
  - Update Jira comments/status.
  - Create Jira subtasks.

### GitLab connector configuration

- **Status**: Scaffolded
- **Description**: Environment-variable based configuration status for self-hosted GitLab.
- **Current behavior**:
  - Reports whether GitLab base URL and token are present.
- **Planned behavior**:
  - Read GitLab merge requests, commits, diffs, and discussions.
  - Create GitLab merge requests.
  - Add GitLab review comments.
  - Trigger pipelines.

## Agent loop product capabilities

### Bounded loop model

- **Status**: Scaffolded
- **Description**: The app models agent work as saved loop definitions with controlled scope and runtime configuration.
- **Current behavior**:
  - Loop schema includes name, description, Jira query, GitLab project ID, mode, and model label.
  - Status lifecycle enum exists: `draft`, `ready`, `running`, `paused`, `completed`, `failed`.
- **Planned behavior**:
  - Store allowed actions per loop.
  - Store approval policy per loop.
  - Support loop-specific instructions.
  - Support richer loop modes such as implementation, triage, and summarization.

### Context ingestion

- **Status**: Planned
- **Description**: Build compact context packs for agent runs.
- **Planned sources**:
  - Jira issue fields and comments.
  - Linked GitLab MRs, commits, diffs, and discussions.
  - Existing review feedback.
  - Loop-specific instructions.
- **Planned constraints**:
  - Respect `context_limit` on fire requests.
  - Keep context packs auditable and bounded.

### Proposed side effects and approval boundary

- **Status**: Planned
- **Description**: Agents propose external writes, and the backend validates/executes them after approval where needed.
- **Planned side effects**:
  - Create GitLab MR.
  - Add GitLab review comment.
  - Update Jira comment/status.
  - Create Jira subtasks.
  - Trigger GitLab pipeline.
- **Safety principle**: Jira/GitLab writes should be backend connector actions, not arbitrary agent tool calls.

## Infrastructure and developer experience

### Docker Compose topology

- **Status**: Implemented
- **Description**: Local Docker Compose stack for database, backend API, and web dashboard.
- **Services**:
  - `db`: Postgres 16 Alpine with health check.
  - `api`: FastAPI backend, port `${API_PORT:-8000}`.
  - `web`: React/Vite frontend, port `${WEB_PORT:-5173}`.
- **Current limitation**:
  - Postgres service exists, but backend persistence has not been wired yet.

### CORS for local dashboard development

- **Status**: Implemented
- **Description**: Backend allows local dashboard origins to call the API.
- **Allowed origins**:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
  - `http://localhost:5180`
  - `http://127.0.0.1:5180`

### Test coverage and verification

- **Status**: Implemented
- **Description**: Backend tests and frontend production build checks are available.
- **Current coverage**:
  - Health endpoint.
  - Loop CRUD lifecycle.
  - Unknown loop `404` behavior.
  - Fire-loop optimistic UI response contract.
  - Large loop list performance guard.
  - CORS preflight behavior.
  - Runtime status without token leakage.
  - Model label defaults, validation, and CRUD.
  - Anthropic SDK custom endpoint construction.
- **Commands**:
  - Backend: `cd backend && uv run --with-requirements requirements-dev.txt python -m pytest tests -q`
  - Frontend: `cd frontend && npm run build`

## Roadmap summary

### Next candidates

- Persist loops, runs, and model labels in Postgres.
- Add run history APIs and dashboard views.
- Implement real Anthropic dispatch for non-dry runs.
- Implement context pack construction from Jira and GitLab.
- Add real Jira/GitLab connector health checks.
- Add approval workflow for external side effects.
- Add loop editing/deletion controls in the dashboard, not only via API.
- Add dashboard views for connector status and setup guidance.

### Longer-term ideas

- Per-loop allowed actions and approval policy editor.
- Multiple loop modes with mode-specific templates.
- Audit log for runs, model changes, approvals, and external writes.
- Durable screenshots or run artifacts for review outcomes.
- Role-based access controls for internal deployments.
