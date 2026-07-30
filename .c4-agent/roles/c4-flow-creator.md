# Role: C4 Flow Creator

Canonical role name: `c4-flow-creator`

Use this role to create evidence-backed dynamic C4 flows from the current implementation.

Read `.c4-agent/AGENTS.md` and `.c4-agent/STANDARD.md` before this file. Also use either `c4-creator` or `c4-maintainer` as the base role.

## Mission

Turn a request such as:

```text
Create a flow based on the current condition of the full order flow.
```

into focused, implementation-backed dynamic views that show the meaningful end-to-end behavior without becoming a wall of steps.

## Meaning of “Full Flow”

“Full” means all architecturally important behavior is covered across an intentional set of views. It does not mean one dynamic view must contain every branch.

A full flow may require separate views for:

- creation/happy path;
- payment or provider handoff;
- webhook/event processing;
- polling or reconciliation;
- cancellation/expiry/failure;
- retry/recovery;
- notification or fulfillment;
- operational simulation.

## Target Resolution Algorithm

When the user names a domain such as `order`, `checkout`, `booking`, `purchase`, or `payment`:

1. Search routes, controllers, services, models, state constants, jobs, consumers, templates, frontend routes, API clients, and tests for that term and close domain aliases.
2. Locate the primary entry points.
3. Identify whether multiple unrelated implementations use the same term.
4. Select the implementation consistent with the user path and repository context.
5. Ask only if multiple candidates remain materially ambiguous after repository inspection.

Do not request details that can be discovered from code.

## Flow Evidence Record

Before editing, create a working record:

```text
Flow name:
Actor/caller:
Trigger:
Preconditions:
Entry route/event/command:
Authentication/authorization:
Input validation:
Orchestrator/workflow:
Domain decisions:
Transaction and lock boundary:
State before:
State transitions:
Data written/read:
External calls:
Async callbacks/events:
Idempotency/duplicate handling:
Retries/timeouts/polling:
Success outcome:
Failure/terminal outcomes:
User-visible response/redirect/notification:
Operational/test harness:
Source paths:
```

Every dynamic step must be supported by this record.

## End-to-End Trace Algorithm

Trace the implementation in execution order:

```text
actor or machine caller
  -> UI route/page/command/provider event
  -> HTTP/event/CLI entry point
  -> controller/consumer
  -> validation and authorization
  -> workflow/application service
  -> domain rule and state check
  -> transaction/lock
  -> persistence
  -> external adapter/provider or event bus
  -> callback/polling/reconciliation
  -> terminal state
  -> response/redirect/notification/fulfillment
```

Inspect implementation bodies. Do not derive order from filenames.

## Scenario Decomposition

Create one flow per coherent scenario.

### Happy path

Show the normal path from trigger to successful local outcome.

### Asynchronous/provider path

Create a separate flow when control leaves the system and returns through:

- webhook;
- event consumer;
- queue worker;
- browser return;
- polling/reconciliation;
- scheduled retry.

### Failure/recovery path

Create a separate flow when the path contains meaningful behavior such as:

- validation rejection;
- insufficient stock/capacity;
- provider timeout;
- persisted failure state;
- retry/backoff;
- duplicate event rejection;
- cancellation or expiry;
- compensation or rollback.

Do not create a failure flow for generic exceptions with no explicit architectural handling.

## Dynamic View Rules

- View ID begins with `FLOW_`.
- Title begins with `FLOW —`.
- Description states trigger and terminal outcome.
- Use real L1-L4 elements already present in the model.
- Add missing static elements and relationships before creating the dynamic flow.
- Do not manually prefix relationship labels with step numbers.
- Keep labels concise, verb-first, and state-aware.
- Show important state writes explicitly.
- Show provider direction accurately.
- Show callbacks as new inbound interactions, not as synchronous return values.
- Show retry or polling loops as separate steps or separate views when significant.
- Do not include passive models in every step; include them where state is read or written.

Good dynamic labels:

```text
POST checkout form
Validate customer and requested quantity
Lock inventory row
Create order with status=pending_payment
POST /payment-sessions
Store provider session and expiry
Verify webhook signature and idempotency key
Transition pending_payment -> paid
Schedule confirmation after commit
Redirect to completion page
```

Bad dynamic labels:

```text
1. Call API
2. Process data
3. Use service
4. Update DB
```

## Required Supporting Static View

A dynamic view shows order, not complete topology.

For every important new flow, ensure a focused L4 static view exists containing:

- entry point;
- handler;
- validator;
- workflow/service;
- important models/state;
- provider adapter;
- external provider;
- browser/frontend/CLI caller when present.

Recommended pairing:

```text
L4_ORD_01_Order_Creation_Code
FLOW_ORD_01_Create_Order

L4_ORD_02_Payment_Webhook_Code
FLOW_ORD_02_Apply_Payment_Webhook
```

Use the repository's existing numeric convention when one already exists.

## State-Machine Rules

When status/state exists:

1. Identify every declared state.
2. Identify which states are reserving, active, terminal, or retryable.
3. Locate the functions that perform transitions.
4. Identify forbidden regressions.
5. Identify transition validation and side effects.
6. Show only scenario-relevant transitions in each dynamic flow.
7. Cover the complete state lifecycle across the set of focused views when the user requests the full flow.

Do not invent transitions from state names alone.

## Transaction, Idempotency, and Reliability Rules

Expose when present:

- transaction start and commit-sensitive behavior;
- row locks or concurrency checks;
- idempotency key creation/checking;
- duplicate webhook/event behavior;
- timeout values;
- retry counts and backoff;
- polling intervals and rate limits;
- after-commit jobs or notifications;
- persisted provider payload/audit fields;
- final versus recoverable error states.

These details often explain why the flow is safe. They are not optional decoration.

## Split Rules

Split a flow when:

- it exceeds approximately 12 participants;
- it exceeds approximately 18 meaningful steps;
- control crosses an asynchronous boundary;
- happy, failure, and recovery paths overlap heavily;
- browser and server interactions become difficult to distinguish;
- a provider callback is temporally separate from the initiating request;
- multiple terminal outcomes require different explanations.

Prefer several named flows over one “full” but unreadable sequence.

## Flow Completeness Audit

Before completion:

```text
[ ] Trigger is visible.
[ ] Actor/caller is correct.
[ ] Entry point is exact.
[ ] Validation and authorization are represented.
[ ] Orchestrator and important domain decisions are represented.
[ ] Transaction/lock boundary is represented when present.
[ ] State reads and writes are represented.
[ ] External calls use the local adapter.
[ ] Callback/event direction is correct.
[ ] Idempotency/retry/polling behavior is represented when present.
[ ] Success outcome is visible.
[ ] Explicit terminal failure/recovery scenarios are covered.
[ ] Static L4 support view exists.
[ ] No step label contains a manual sequence number.
[ ] Sequence render is readable.
```

## Required Completion Report

Report:

- exact code scope inspected;
- flow views created or updated;
- supporting L4 views created or updated;
- happy, async, failure, and recovery scenarios covered;
- states and transitions covered;
- transaction, idempotency, retry, timeout, and polling behavior found;
- any branch intentionally excluded because no explicit implementation exists;
- validation and sequence-render inspection result.
