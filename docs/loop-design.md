# Loop design guide

This guide distills public prompt-engineering and agent-workflow guidance into the loop setup structure used by Agent Loop Dashboard.

## Sources reviewed

- OpenAI prompt engineering guide: https://platform.openai.com/docs/guides/prompt-engineering
- OpenAI agent workflow evaluation docs: https://platform.openai.com/docs/guides/evals
- Anthropic prompt engineering overview: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- Anthropic prompting best practices: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-prompting-best-practices
- LangChain agents docs: https://docs.langchain.com/oss/python/langchain/agents
- AutoGen termination guide: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html
- 12-factor agents: https://github.com/humanlayer/12-factor-agents

## Distilled principles

Good agent loops are not just vague prompts. They are bounded operating contracts. The recurring themes across the sources are:

1. Be explicit about the task and success criteria.
2. Separate instructions from context and data.
3. Define available inputs and tools/actions.
4. Constrain unsafe or out-of-scope behavior.
5. Specify the required output format.
6. Give the agent a stopping condition.
7. Include escalation/human-in-the-loop rules for uncertainty or side effects.
8. Make the setup testable by turning desired behavior into criteria/evals.

## Implemented loop setup components

### Name

- **Purpose**: Human-readable label for the loop.
- **Guidance**: Use a short operational name, e.g. `MR release-risk review`.

### Description

- **Purpose**: One-paragraph purpose statement.
- **Guidance**: Explain what the loop is for and where it is used.

### Objective

- **Purpose**: The concrete goal the agent should optimize for.
- **Guidance**: Phrase as an outcome, not an activity.
- **Example**: `Find merge request risks before code is merged.`

### Trigger

- **Purpose**: Defines when the loop should run.
- **Guidance**: Use event-like language even before scheduling/webhooks exist.
- **Example**: `Run when a GitLab MR is opened, updated, or marked ready for review.`

### Input sources

- **Purpose**: Lists the context the loop expects.
- **Guidance**: Separate sources from instructions so context gathering can later be automated.
- **Example**: `Jira ticket, GitLab MR diff, discussions, CI status, and existing review feedback.`

### Instructions

- **Purpose**: The actual work instructions for the agent.
- **Guidance**: Use clear, prioritized imperatives. Avoid burying constraints here if they belong in guardrails.
- **Example**: `Prioritize correctness, security, and maintainability. Cite evidence from the supplied context.`

### Constraints / guardrails

- **Purpose**: Defines what the agent must not do.
- **Guidance**: Include safety, scope, privacy, and authority boundaries.
- **Example**: `Do not approve, merge, deploy, or expose secrets. Do not invent context that was not provided.`

### Allowed actions

- **Purpose**: Defines what actions the loop may propose or eventually execute.
- **Guidance**: Keep this narrow. In this app, external writes should remain backend-controlled and approval-gated.
- **Example**: `Summarize findings, propose review comments, and request human approval for risky actions.`

### Output format

- **Purpose**: Defines the response shape the model should produce.
- **Guidance**: Use explicit sections or JSON when downstream processing matters.
- **Example**: `Markdown with sections: Summary, Blocking risks, Suggested comments, Open questions, Confidence.`

### Success criteria

- **Purpose**: Makes the loop testable and reviewable.
- **Guidance**: State what must be true for the run to be considered useful.
- **Example**: `All blocking risks are identified and each recommendation has a clear next action.`

### Stop conditions

- **Purpose**: Prevents unbounded or repetitive loops.
- **Guidance**: Define completion, missing-context, budget, and termination rules.
- **Example**: `Stop after one complete review or when required context is missing.`

### Escalation policy

- **Purpose**: Captures human-in-the-loop rules.
- **Guidance**: Escalate when confidence is low, side effects are risky, or authority is unclear.
- **Example**: `Escalate to a human for low confidence, production impact, security concerns, or missing requirements.`

## Current implementation

The dashboard now exposes these components in the `Create loop` panel. The backend stores them on each loop and assembles a `prompt_snapshot` when a loop is fired.

The prompt snapshot is currently used for visibility and scaffolding. Future LLM dispatch should use the snapshot as the system/task contract, then append retrieved Jira/GitLab context separately.

## Recommended next step

Before wiring real LLM dispatch, add eval fixtures for common loop types. Each fixture should include:

- loop setup;
- input context pack;
- expected output properties;
- forbidden behavior;
- pass/fail criteria.
