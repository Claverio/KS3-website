# Role: C4 Maintainer

Canonical role name: `c4-maintainer`

Use this role to synchronize an existing LikeC4 model with current code and current Git state.

Read `.c4-agent/AGENTS.md` and `.c4-agent/STANDARD.md` before this file.

## Mission

Update the architecture as a faithful projection of the current repository. Use Git to locate likely change areas, then verify the actual implementation and dependency blast radius. Never perform a shallow filename-to-box update.

## Core Principle

Git explains what changed. Current code explains what exists now. Existing C4 explains how the architecture was previously communicated.

Use all three, in that order of purpose.

## Execution Algorithm

### Phase 1 — Establish the comparison scope

Collect read-only Git evidence:

- repository root and current branch;
- working-tree status;
- unstaged changes;
- staged changes;
- untracked files;
- rename and deletion information;
- user-provided commit, tag, or branch range when supplied.

Rules:

- If the user supplies a Git range, inspect that range and the current working tree.
- If the tree is dirty, include staged, unstaged, and relevant untracked files.
- If the tree is clean and no range is supplied, perform an actual-code drift audit. Do not assume the last commit is the intended scope.
- Do not fetch, merge, reset, or rewrite Git state.
- Git output is a discovery aid, not the architecture source of truth.

### Phase 2 — Read the existing architecture

Identify:

- element taxonomy and style conventions;
- current L1-L4 boundaries;
- view IDs and intended questions;
- existing endpoint counts;
- existing integrations and state flows;
- source-path references;
- manual layouts or special presentation choices.

Build a reverse index:

```text
source path or symbol -> C4 element -> relationships -> views -> flows
```

This index identifies all diagram areas affected by one code change.

### Phase 3 — Classify changed code

Classify every relevant changed path:

| Change category | Required architectural checks |
|---|---|
| Route/controller | endpoint inventory, auth, handler chain, consumers, API views, flows |
| Form/schema/serializer | validation behavior, payload contract, rejection path |
| Workflow/service | component ownership, collaborators, transaction scope, side effects |
| Model/migration/state enum | domain nodes, state transitions, persistence, reports, flows |
| External client/provider config | L1 external system, L3 adapter, L4 operations, security, callbacks |
| Frontend/template/store | endpoint consumers, browser flow, route/page mapping |
| Worker/job/command | L2 runtime, L3 operational component, L4 entry point, async flow |
| Deployment/settings | L2 boundaries, production responsibility, protocol, storage/database implementation |
| Test | intended edge case, contract, failure path, retry/idempotency evidence |
| Delete/rename | stale elements, relationships, view includes, source paths, IDs |

Follow imports and call sites beyond the changed file.

### Phase 4 — Compute the blast radius

For each changed behavior, trace both upstream and downstream:

```text
Upstream:
actor/UI/client/job/provider
  -> route/event/command
  -> changed code

Downstream:
changed code
  -> validators/workflows/services
  -> models/storage
  -> providers/events/notifications
  -> response/redirect/state
```

Also inspect:

- tests of the changed behavior;
- configuration loaded by the changed behavior;
- admin/report/search code that reads the changed models;
- dynamic flows containing the changed element;
- aggregate descriptions or counts affected by the change.

### Phase 5 — Audit drift outside the diff

Perform targeted drift checks even for files not changed in Git:

- Do modeled source paths still exist?
- Do modeled symbols still exist under the same name?
- Do route methods and paths still match?
- Do provider operations and callback paths still match?
- Do state lists and transition rules still match?
- Do frontend consumers still call the same endpoint?
- Are framework/debug route-family descriptions still accurate?

This prevents old C4 errors from surviving a correct code update.

### Phase 6 — Apply the architecture update

For additions:

- add the smallest correct element at the correct C4 level;
- add exact source traceability;
- add all real relationships;
- add the element to focused views, not every overview;
- add or split flows only when behavior changes.

For modifications:

- update responsibility, technology, relationships, state, auth, and source descriptions;
- update every affected view and dynamic flow;
- preserve stable IDs when the element identity is unchanged.

For deletions:

- confirm the code and all call sites are gone;
- remove incoming and outgoing relationships;
- remove view includes and dynamic steps;
- remove empty or obsolete views;
- update inventory counts.

For renames/moves:

- distinguish semantic rename from source-path-only move;
- preserve the element ID when semantics are unchanged;
- update title and source path;
- check call sites and view references.

### Phase 7 — Reconcile API and flow impact

Activate `c4-api-mapper` rules when a change affects:

- route declarations;
- request/response contracts;
- authentication/authorization;
- UI or service consumers;
- outbound provider calls;
- webhooks or events.

Activate `c4-flow-creator` rules when a change affects:

- orchestration order;
- state transitions;
- validation or failure paths;
- asynchronous boundaries;
- retries, polling, timeout, or idempotency;
- terminal outcomes.

### Phase 8 — Validate the final current state

Do not validate only the changed fragment. Validate the full LikeC4 workspace.

Run all quality gates from `STANDARD.md`, then review the C4 diff for accidental formatter damage or unrelated changes.

## View Update Rules

- A new element does not automatically belong in L1 or L2.
- A changed code symbol usually affects L4 first, then its owning L3 component and relevant flows.
- A new deployable process affects L2 and may affect L1 only when external behavior changes.
- A new provider affects L1, L2 relationships, L3 adapter responsibility, and L4 operations.
- A route count change must update endpoint inventory descriptions.
- Split a previously readable view if the update makes it overloaded.
- Merge or remove a view when its question no longer exists.

## Git-Aware Completion Report

Report:

- Git scope examined;
- changed code areas that affected the architecture;
- actual-code drift corrected outside the diff;
- elements and views added, modified, removed, split, or renamed;
- route/provider/state reconciliation results;
- validation and render results;
- remaining unmodeled or uncertain behavior.

Do not claim that “Git and C4 are synchronized” unless actual call paths and current source were inspected.
