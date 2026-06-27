# Architecture

## Bounded loop model

A loop is a saved definition containing:

- name and purpose;
- Jira source scope, e.g. JQL or project keys;
- GitLab source scope, e.g. project/group/MR filters;
- mode, e.g. review, implementation, triage, summarization;
- allowed actions;
- approval policy;
- runtime configuration, including a selectable `model_label` mapped to an Anthropic model id.

## Context ingestion

The backend should construct compact context packs from:

- Jira issue fields and comments;
- linked GitLab MRs, commits, diffs, and discussions;
- existing review feedback;
- loop-specific instructions.

## Agent runtime

The backend uses the Anthropic SDK behind an internal adapter. Custom endpoints are configured through:

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL_LABELS`, e.g. `fast=claude-haiku,smart=claude-sonnet`, as the initial editable model-label seed

The dashboard config page exposes CRUD for model labels through `/runtime/model-labels`. Loops store a `model_label`, not a secret or raw runtime config. On fire, the backend resolves the label to a concrete model id and creates an agent run record. The LLM proposes actions; the backend remains the side-effect and approval boundary.

## Side effects

External writes should be explicit backend actions:

- create GitLab MR;
- add GitLab review comment;
- update Jira comment/status;
- create Jira subtasks;
- trigger pipeline.

The agent proposes payloads; the backend validates and executes after approval where needed.
