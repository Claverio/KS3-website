# C4 Agent Rule Pack

This rule pack gives an AI agent a deterministic process for creating and maintaining high-quality LikeC4 architecture models from actual repository evidence.

All rules are written in English for consistent machine interpretation.

## Files

```text
.c4-agent/
├── AGENTS.md
├── STANDARD.md
└── roles/
    ├── c4-creator.md
    ├── c4-maintainer.md
    ├── c4-api-mapper.md
    └── c4-flow-creator.md
```

| File | Purpose |
|---|---|
| `AGENTS.md` | Entry point, role router, required reading order, and completion contract |
| `STANDARD.md` | Shared evidence, C4, naming, styling, splitting, traceability, and validation standard |
| `roles/c4-creator.md` | Create a new four-level model from an existing codebase |
| `roles/c4-maintainer.md` | Synchronize an existing model using Git changes and actual current code |
| `roles/c4-api-mapper.md` | Map endpoints, consumers, handlers, payload validation, providers, webhooks, and route families |
| `roles/c4-flow-creator.md` | Build focused end-to-end dynamic flows and supporting L4 code views |

## Recommended Invocation Format

Always point the agent to the router:

```text
Read and obey .c4-agent/AGENTS.md.
Role: <canonical role>.
Task: <requested outcome>.
Repository: <repository path>.
Target: <C4 file path>.
Do not stop until the applicable quality gates pass.
```

The `Repository` and `Target` lines may be omitted when the current working directory and target are unambiguous.

## Short Invocation Format

This shorter phrasing is also supported:

```text
Check rules: .c4-agent/AGENTS.md.
Role: c4-flow-creator.
Create a flow based on the current implementation of the full order flow.
```

The router requires the flow role to combine itself with `c4-maintainer` when a C4 model already exists.

## Prompt — Create a New C4 Model

```text
Read and obey .c4-agent/AGENTS.md.
Role: c4-creator.

Create a new evidence-driven LikeC4 architecture model from the current repository.
Use four explicit levels with L1_, L2_, L3_, and L4_ view naming.
Model the actual actors, runtime containers, business components, important code chains,
data stores, external integrations, operational tools, APIs, and critical flows.
Split large views by domain or question. Include source paths on important L4 elements.
Validate, render to a temporary directory, visually inspect, and fix all applicable issues.
```

## Prompt — Update an Existing C4 Model

```text
Read and obey .c4-agent/AGENTS.md.
Role: c4-maintainer.

Synchronize the existing LikeC4 model with the current repository.
Inspect staged, unstaged, renamed, deleted, and relevant untracked Git changes,
then verify the complete actual implementation and dependency blast radius.
Update affected elements, relationships, endpoint inventories, counts, focused views,
and dynamic flows. Correct discovered stale architecture even when the stale source
is outside the Git diff. Preserve unrelated working-tree changes.
Run every applicable quality gate before completion.
```

## Prompt — Build an API Map

```text
Read and obey .c4-agent/AGENTS.md.
Roles: c4-maintainer, c4-api-mapper.

Map the current APIs completely. Inventory concrete inbound routes separately from
framework/debug route families. Connect every concrete endpoint to its handler,
validation, workflow, state/models, and actual frontend/browser/mobile/CLI/service
consumer. Map outbound provider operations through their local adapters and show
webhooks in the correct direction. Mark endpoints with no in-repository consumer.
Split views by domain, access category, inbound/outbound direction, or async boundary
when one inventory becomes dense. Include accurate counts in view descriptions.
```

## Prompt — Create a Full Order Flow

```text
Read and obey .c4-agent/AGENTS.md.
Role: c4-flow-creator.

Create an evidence-backed flow from the current implementation of the full order flow.
Discover the actual actor, UI/API/CLI entry points, validation, orchestration, domain
rules, transactions and locks, state transitions, persistence, external providers,
webhooks/events, idempotency, retries/timeouts, notifications, and terminal outcomes.
Create focused FLOW_ views for happy path, asynchronous/provider callback, and explicit
failure/recovery behavior when those scenarios exist. Add or update supporting L4 code
views. Do not create one unreadable sequence and do not manually number dynamic steps.
Validate and inspect sequence renders before completion.
```

## Prompt — New Feature With API and Flow Changes

```text
Read and obey .c4-agent/AGENTS.md.
Roles: c4-maintainer, c4-api-mapper, c4-flow-creator.

The feature is: <feature description>.
Synchronize the architecture with Git and actual code, update the endpoint-to-consumer
map, and update every affected end-to-end flow and state transition. Follow dependency
blast radius beyond changed files. Split any view that becomes overloaded. Run all
quality gates and report exact coverage counts.
```

## Expected Behavior

The agent must:

- inspect implementation bodies instead of summarizing directories;
- model C4 levels by abstraction, not file type;
- connect endpoints through business logic to state and integrations;
- show real consumers and provider adapters;
- expose security, state, transaction, idempotency, retry, polling, and async behavior when present;
- keep the model complete while keeping each view focused;
- use explicit level prefixes and color-coded semantic kinds;
- validate and render before declaring completion.

The agent must not:

- create four empty overview diagrams and call them a four-level model;
- copy stale README claims into the architecture;
- use one giant view as proof of completeness;
- invent missing consumers or flows;
- treat `FLOW_` as C4 Level 5;
- leave route counts unreconciled;
- stop after editing without LikeC4 validation.

## Local Reference Model

The repository's `c4/architecture.c4` demonstrates the intended output characteristics:

- explicit L1-L4 naming;
- semantic notation and color coding;
- focused static views;
- endpoint inventory split by responsibility;
- exact code/source traceability;
- dynamic flows for synchronous and asynchronous behavior;
- separate modeling of external providers and local adapters.

Use it as a presentation reference only. Actual code remains the source of truth.
