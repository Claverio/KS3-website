# Evidence-Driven LikeC4 Standard

This standard is mandatory for every role in `.c4-agent/roles/`.

The objective is not to produce many boxes. The objective is to create a trustworthy, navigable architecture model that answers concrete engineering questions without forcing readers to inspect the whole repository again.

## 1. Definition of Done

A C4 task is complete only when all applicable conditions are true:

- The model is based on actual code, configuration, deployment files, templates, scripts, and tests.
- All four C4 levels are represented where the repository contains meaningful evidence for them.
- Every authored view has an explicit level prefix in its ID and title.
- Important elements have exact source-path traceability.
- Relationships describe real behavior with directional, meaningful labels.
- Application-owned HTTP routes are reconciled against the repository when API coverage is in scope.
- External integrations show the local adapter/service and the external provider.
- Important state transitions, transaction boundaries, idempotency, retries, and asynchronous boundaries are visible in focused views or flows.
- Large domains are split into readable views instead of collapsed into an unreadable overview.
- LikeC4 formatting and validation pass.
- Rendered views are inspected when rendering tools are available.
- No generated render/build artifacts are accidentally left in the repository unless explicitly requested.

## 2. Evidence Priority

Use this evidence order from strongest to weakest:

1. Executable application code and runtime configuration.
2. Route registration, dependency injection, framework registration, job scheduling, and deployment configuration.
3. Database models, migrations, schemas, and state constants.
4. Templates, browser code, mobile code, generated clients, CLI commands, workers, and provider adapters.
5. Tests that demonstrate intended behavior, edge cases, or contracts.
6. Current Git changes and commit history as change indicators.
7. Repository documentation and comments.
8. Existing C4 source.
9. Naming-based inference.

If evidence conflicts, follow the higher-priority evidence and update the architecture accordingly. Never preserve a stale diagram merely because it already exists.

## 3. Mandatory Repository Discovery

Before modeling, build a compact evidence ledger covering the following categories.

### 3.1 Repository and runtime boundaries

Identify:

- languages and frameworks;
- executable entry points;
- deployable processes;
- web applications, workers, scheduled jobs, CLIs, mobile apps, and frontend apps;
- databases, caches, queues, object stores, search engines, and file stores;
- container, orchestration, reverse proxy, and deployment definitions;
- development/test implementations that differ from production.

### 3.2 Entry points

Locate and inspect:

- HTTP routes and controllers;
- GraphQL schemas and resolvers;
- RPC handlers;
- message consumers and producers;
- webhook receivers;
- scheduled jobs;
- management commands and operational scripts;
- admin framework extensions;
- browser or mobile entry points.

### 3.3 Domain behavior

For every important use case, trace:

```text
actor/client
  -> entry point
  -> controller/resolver/consumer
  -> input validation
  -> application workflow
  -> domain rules
  -> persistence/query
  -> integration adapter
  -> external system
  -> response/event/redirect/notification
```

Do not stop tracing at the controller.

### 3.4 State and reliability behavior

Search for and verify:

- state/status enums and transition rules;
- database transactions and row locks;
- idempotency keys and duplicate-event handling;
- authentication, authorization, signatures, and callback tokens;
- timeouts, retries, polling intervals, and retry limits;
- after-commit behavior;
- failure persistence and audit fields;
- terminal versus recoverable states;
- compensation, cancellation, expiry, and reconciliation.

### 3.5 Consumers and providers

Trace both directions:

- which UI route, page, component, hook, store, command, or service calls an endpoint;
- which local service calls an external provider;
- which external provider calls a webhook;
- where credentials and provider URLs are configured;
- whether an endpoint has no in-repository consumer.

Never equate “route exists” with “route is used”.

## 4. C4 Level Contract

The repository may have many views at each level. “Four levels” does not mean “exactly four diagrams”.

### L1 — System Context

Purpose: answer who uses the system and what external systems it depends on.

Allowed primary content:

- people and roles;
- the software system in scope;
- external systems and providers;
- high-level relationships and outcomes.

Do not expand containers, components, code symbols, tables, or endpoints in an L1 view.

Naming:

```text
View ID:    L1_01_System_Context
View title: L1 — System Context — <System Name>
Element:    L1 · <Person, System, or External System>
```

### L2 — Container

Purpose: answer which independently runnable, deployable, or persistent units make up the system.

Valid containers include:

- web application;
- frontend application;
- mobile application;
- worker process;
- scheduled-job runtime;
- operational CLI;
- database;
- queue, cache, or object store when owned by the system.

Do not model ordinary source folders, Django apps, packages, controllers, or services as L2 containers unless they are independently runnable or deployable.

Naming:

```text
View ID:    L2_01_Container_Overview
View title: L2 — Container — <Runtime or Responsibility>
Element:    L2 · <Container Name>
```

### L3 — Component

Purpose: answer which cohesive responsibilities collaborate inside one container.

A component should represent a meaningful responsibility such as:

- checkout orchestration;
- payment reconciliation;
- order management;
- notification delivery;
- unified search;
- CMS administration;
- provider adapter;
- acceptance harness.

Do not create one component per file or directory by default. Group code by responsibility and collaboration boundary.

Naming:

```text
View ID:    L3_01_<Domain>_Components
View title: L3 — Component — <Domain or Container>
Element:    L3 · <Responsibility Name>
```

### L4 — Code

Purpose: answer exactly which implementation symbols participate and how they are connected.

Use L4 for evidence-backed elements such as:

- route/endpoint;
- controller, view, resolver, or consumer function;
- form, serializer, validator, or request schema;
- workflow or application service;
- domain service;
- model, entity, aggregate, value object, or state machine;
- repository/query helper;
- provider adapter and request helper;
- template and browser/mobile caller;
- management command, job, and admin extension.

Every important L4 element description must include a repository-relative source path.

Preferred title patterns:

```text
L4 · GET|POST /orders/{id}/pay/
L4 · create_order()
L4 · OrderService.confirm()
L4 · Order
L4 · CheckoutForm
L4 · checkout.tsx / submitOrder()
L4 · process_payment_webhook
```

Naming:

```text
View ID:    L4_01_<Use_Case>_Code
View title: L4 — Code — <Use Case>
Element:    L4 · <Exact Route or Symbol>
```

### FLOW — Dynamic behavior

`FLOW_` is a supporting dynamic view category, not a fifth C4 level.

Naming:

```text
View ID:    FLOW_01_<Scenario>
View title: FLOW — <Scenario>
```

Rules:

- Use actual elements already defined at L1-L4.
- Let LikeC4 number sequence steps. Do not add `1.`, `2.`, and similar prefixes to relationship labels.
- Use verb-first labels such as `Validate requested quantity`, `Lock order row`, or `POST /sessions`.
- Separate materially different scenarios instead of placing every branch into one sequence.

## 5. Element Taxonomy and Color Contract

Use semantic element kinds. Do not use one generic element kind for everything.

Recommended global notation and colors:

| Level/category | Recommended style | Meaning |
|---|---|---|
| L1 person | green, person shape | human actor or operational role |
| L1 external system | gray | provider or system outside the ownership boundary |
| L1 software system | indigo | software system and expanded ownership boundary |
| L2 application/CLI container | primary | independently runnable application process |
| L2 data container | amber, cylinder | owned persistent store |
| L3 component | secondary, component shape | cohesive responsibility boundary |
| L4 endpoint | red, browser shape | inbound HTTP/API route or framework route family |
| L4 controller/view | indigo | request/event adapter |
| L4 form/workflow/service | green | validation and behavior |
| L4 domain/config model | amber, storage/document | persistent domain state, value object, or configuration |
| L4 template | gray, document | rendered UI/email/text artifact |
| L4 operation/admin extension | red or secondary | management and operational entry point |
| L4 helper/query | muted | supporting utility, mapper, or query function |

Always define `notation` for each kind so the Diagram Browser can show a legend.

Color is supplementary. The `L1 ·`, `L2 ·`, `L3 ·`, and `L4 ·` prefixes remain mandatory for accessibility and unambiguous screenshots.

## 6. Element Description Contract

Descriptions must explain responsibility, not restate the title.

### L1-L3 description

Include:

- what the element owns;
- why it exists;
- important runtime or business responsibility;
- technology when useful.

### L4 description

Include:

- exact behavior;
- important validation, state, or side effect;
- source path.

Example:

```text
Validates callback token and event reference, rejects duplicate webhook IDs,
and invokes the shared payment transition.
Source: payments/views/webhook.py
```

Do not paste entire function bodies, payloads, or database schemas into descriptions.

## 7. Relationship Contract

Every relationship must be directional and labeled with real behavior.

Good labels:

```text
Submits checkout form
Routes POST request
Validates request schema
Locks order and rechecks capacity
POST /payment-sessions over authenticated HTTPS
Stores provider reference and waiting status
Publishes OrderPaid event
Retries up to three attempts
```

Bad labels:

```text
Uses
Calls
Related to
Data
API
Connects
```

Generic labels are allowed only when the diagram level is intentionally high and the detailed view provides the exact relationship.

When relevant, relationship labels should expose:

- method and protocol;
- sync versus async;
- authentication mechanism;
- read versus write;
- transaction or lock boundary;
- retry, timeout, or polling behavior;
- event or state produced.

## 8. View Design and Splitting Rules

Each view must answer one explicit question.

Examples:

- Who uses the platform and which providers does it depend on?
- Which runtime units exist in production?
- Which components own order and payment behavior?
- Which exact route, validator, service, model, and provider call create an order?
- Which endpoint is called by which frontend route or store action?
- How does a webhook become an idempotent paid transition?

### Default density limits

Use these as forcing functions, not absolute syntax rules:

- Static overview: target 6-18 primary nodes.
- Focused L4 view: target 8-20 nodes.
- Dynamic flow: target 5-12 participants and 5-18 steps.
- Endpoint inventory: may exceed 20 nodes only when grouping and layout remain understandable.

Split a view when any condition is true:

- more than one independent question is being answered;
- multiple business domains compete for attention;
- browser, server, provider, and asynchronous callback paths create excessive crossings;
- happy path and recovery path cannot be read independently;
- endpoint labels become unreadable at normal Diagram Browser zoom;
- a reader cannot identify the entry point and terminal outcome within a few seconds.

Preferred split axes:

- business domain;
- inbound versus outbound API;
- public versus admin API;
- synchronous request versus asynchronous webhook/event;
- happy path versus failure/recovery;
- browser/mobile consumer versus server-to-server integration;
- framework-owned route families versus repository-owned routes.

## 9. API Completeness Contract

When APIs are in scope, classify every discovered route as one of:

1. Repository-owned concrete route.
2. Framework-generated route family.
3. Development/debug-only route family.
4. External provider endpoint called by the repository.
5. External webhook/event entering the repository.

For each repository-owned route, capture when evidence exists:

- HTTP method or protocol operation;
- full path pattern;
- route name;
- authentication/authorization;
- controller/resolver/consumer;
- validator/serializer/form;
- workflow/service;
- state read or written;
- caller/consumer;
- response, redirect, or event;
- source path.

Reconcile the number of modeled concrete routes with actual route declarations. Explain intentional exclusions.

Framework-generated children must be represented as a clearly labeled route family instead of pretending they were individually audited.

## 10. State, Security, and Reliability Contract

Expose these only when supported by code, but never omit them when present:

- allowed status transitions;
- terminal states;
- database transaction scope;
- row or distributed locks;
- optimistic concurrency/version checks;
- authentication and authorization;
- webhook signatures or callback tokens;
- idempotency and duplicate-event rejection;
- retry and timeout values;
- polling rate limits;
- after-commit actions;
- audit and error persistence;
- rollback or compensation;
- secrets/configuration ownership.

Security mechanisms belong on the relationship or responsible L4 element. Do not create a vague “Security” box unless there is a real component with that responsibility.

## 11. Existing-Model Preservation Contract

When editing an existing model:

- preserve correct information and deliberate view organization;
- preserve custom style and manual layout unless it conflicts with this standard or new evidence;
- update both elements and all affected relationships/views;
- remove stale elements only after confirming they no longer exist or are no longer reachable;
- update counts in view descriptions when inventories change;
- keep naming consistent with existing IDs when semantics are unchanged;
- rename misleading IDs only when the benefit exceeds link/history disruption;
- never append duplicate elements for the same code symbol.

## 12. Required Quality Gates

Run these gates after editing.

### Gate A — Source integrity

- Every referenced source path exists.
- Every exact function/class/route name exists or is clearly marked conceptual.
- No secret values are copied into the model.
- No relationship is based only on naming similarity.

### Gate B — Coverage reconciliation

- Recount application-owned routes when API scope is involved.
- Recount external integrations.
- Verify important states against code constants or model choices.
- Verify frontend/browser/CLI consumers against actual call sites.
- Verify added, modified, deleted, and renamed Git paths when maintenance is involved.

### Gate C — LikeC4 formatting and validation

From the C4 workspace, run the repository's installed LikeC4 command when available. Otherwise use an appropriate `npx likec4` command.

```bash
likec4 format . --check
likec4 validate .
```

If formatting is required, format and validate again.

Never report success when validation exits non-zero.

### Gate D — Render inspection

Export to a temporary directory, not the repository:

```bash
likec4 export png . --flat --notation --description -o <temporary-directory>
```

For dynamic views, inspect sequence layout as well:

```bash
likec4 export png . --flat --notation --description --sequence -o <temporary-directory>
```

Inspect at minimum:

- one L1 view;
- every L2 view changed;
- every L3 view changed;
- every L4 view changed;
- every new endpoint inventory;
- every new or changed dynamic flow.

Fix unreadable labels, excessive crossings, accidental orphan nodes, incorrect nesting, and misleading boundaries.

### Gate E — Repository hygiene

- Confirm only intended C4/rule files changed.
- Do not overwrite unrelated user changes.
- Do not leave `dist`, exported PNG, JSON, or browser artifacts in the repository unless requested.
- Review the final C4 diff or file content after formatter changes.

## 13. Required Final Self-Audit

Before responding, answer all questions internally:

```text
[ ] Can a reader identify L1, L2, L3, and L4 from every view ID and title?
[ ] Does each important L4 element contain a valid Source path?
[ ] Are container boundaries based on runtime/deployment reality?
[ ] Are components based on responsibilities instead of folders?
[ ] Are routes connected to their real handlers?
[ ] Are handlers connected beyond the controller layer?
[ ] Are external providers connected through local adapters?
[ ] Are frontend/browser/CLI consumers shown when present?
[ ] Are state changes, locks, idempotency, retries, and async boundaries shown when present?
[ ] Are large inventories split into readable views?
[ ] Are dynamic flow labels free of manual sequence numbers?
[ ] Did LikeC4 formatting and validation pass?
[ ] Were changed views rendered and visually inspected?
[ ] Are coverage counts accurate and explained?
```

If any applicable answer is “no”, continue working.
