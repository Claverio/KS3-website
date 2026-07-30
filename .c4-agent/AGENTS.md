# C4 Architecture Agent Router

This directory contains the mandatory operating rules for AI agents that create or maintain LikeC4 architecture models.

The rules are designed for agents with limited context, weaker reasoning, or inconsistent repository exploration. Follow the process literally. Do not replace repository evidence with assumptions.

## Invocation Contract

The user should invoke this rule pack with a request similar to:

```text
Read and obey .c4-agent/AGENTS.md.
Role: c4-flow-creator.
Task: Create a flow from the current implementation of the full order flow.
```

Natural-language role aliases are accepted:

| User phrase | Canonical role |
|---|---|
| `roles c4 creator`, `create new c4`, `new architecture` | `c4-creator` |
| `roles c4 updater`, `update existing c4`, `sync architecture` | `c4-maintainer` |
| `roles c4 api mapper`, `map APIs`, `endpoint mapping` | `c4-api-mapper` |
| `roles c4 flow creator`, `create a flow`, `map current flow` | `c4-flow-creator` |

## Required Reading Order

For every task:

1. Read this file completely.
2. Read `.c4-agent/STANDARD.md` completely.
3. Read the selected role file completely.
4. If multiple roles apply, read each selected role file and execute them in the order defined below.
5. Inspect the actual repository before editing any C4 source.

Never act from a role file alone. `STANDARD.md` is mandatory and has higher priority than role-specific convenience guidance.

## Role Selection

Select the smallest role set that fully covers the request:

### `c4-creator`

Read `.c4-agent/roles/c4-creator.md` when no adequate C4 model exists or the user explicitly requests a new model.

### `c4-maintainer`

Read `.c4-agent/roles/c4-maintainer.md` when a C4 model already exists and code, configuration, deployment, routes, integrations, data models, or behavior may have changed.

### `c4-api-mapper`

Read `.c4-agent/roles/c4-api-mapper.md` when the request focuses on inbound APIs, frontend consumers, backend handlers, outbound provider calls, webhooks, payloads, authentication, or endpoint inventory.

This role supplements either `c4-creator` or `c4-maintainer`; it does not waive the four-level modeling standard.

### `c4-flow-creator`

Read `.c4-agent/roles/c4-flow-creator.md` when the request asks for a business, technical, user, payment, order, webhook, reconciliation, operational, or end-to-end flow.

This role supplements either `c4-creator` or `c4-maintainer`. A dynamic flow is not a fifth C4 level.

## Multi-Role Execution Order

When multiple roles apply, use this order:

1. `c4-creator` if no usable model exists; otherwise `c4-maintainer`.
2. `c4-api-mapper` when API coverage is requested or affected.
3. `c4-flow-creator` when behavioral views are requested or affected.
4. Run the shared quality gates from `STANDARD.md` once after all edits.

Examples:

```text
Existing architecture + new checkout endpoints
=> c4-maintainer, then c4-api-mapper

No architecture + full order and payment flow
=> c4-creator, then c4-flow-creator

Existing architecture + current full order flow
=> c4-maintainer for evidence synchronization, then c4-flow-creator
```

## Target Resolution

Resolve the repository and C4 target before editing:

1. Use an explicit repository path from the user when provided.
2. Use an explicit `.c4` or `.likec4` target path when provided.
3. Otherwise, locate C4 sources inside the repository.
4. Prefer an existing architecture entry point such as `c4/architecture.c4`.
5. If multiple unrelated architecture roots exist, do not modify all of them. Determine ownership from paths and configuration. Ask only when the correct target cannot be established safely.
6. If no target exists and the role is `c4-creator`, create `c4/architecture.c4` unless repository conventions clearly specify another location.

## Non-Negotiable Behavior

- Treat actual code and runtime configuration as the source of truth.
- Treat the existing C4 model as a maintained projection, not as evidence that the implementation still behaves that way.
- Inspect implementations, not only filenames, directory trees, README files, or route declarations.
- Trace relationships end to end before modeling them.
- Preserve unrelated working-tree changes.
- Do not edit application code unless the user explicitly requests application changes.
- Do not invent actors, containers, integrations, endpoints, consumers, payloads, states, retries, or failure behavior.
- Do not silently omit behavior because it is difficult to trace.
- State uncertainty in descriptions when evidence is incomplete.
- Do not claim completion until LikeC4 validation succeeds.
- Never put every element into one giant view. Completeness belongs in the model; clarity belongs in focused views.
- Never use a folder tree as a substitute for C4 components.
- Never call a dynamic `FLOW_` view “Level 5”.
- Never manually number dynamic step labels; LikeC4 provides sequence numbers.

## Required Completion Report

At the end of the task, report:

1. Target file or files changed.
2. Selected role or roles.
3. Repository scope inspected.
4. Views added, updated, split, or removed.
5. Endpoint counts when API coverage is involved.
6. Important flows and state transitions covered.
7. Validation, formatting, export, and visual-inspection results.
8. Any evidence gap that remains.

Do not report only “C4 updated”. Provide verifiable coverage numbers and name the important views.
