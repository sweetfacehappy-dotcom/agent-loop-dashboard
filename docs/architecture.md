# Architecture

## Bounded loop model

A loop is a saved definition containing:

- name and purpose;
- Jira source scope, e.g. JQL or project keys;
- GitLab source scope, e.g. project/group/MR filters;
- mode, e.g. review, implementation, triage, summarization;
- allowed actions;
- approval policy;
- runtime configuration.

## Context ingestion

The backend should construct compact context packs from:

- Jira issue fields and comments;
- linked GitLab MRs, commits, diffs, and discussions;
- existing review feedback;
- loop-specific instructions.

## Side effects

External writes should be explicit backend actions:

- create GitLab MR;
- add GitLab review comment;
- update Jira comment/status;
- create Jira subtasks;
- trigger pipeline.

The agent proposes payloads; the backend validates and executes after approval where needed.
