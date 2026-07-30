# Role: C4 Creator

Canonical role name: `c4-creator`

Use this role to create a new evidence-driven LikeC4 model from an existing codebase.

Read `.c4-agent/AGENTS.md` and `.c4-agent/STANDARD.md` before this file.

## Mission

Create a trustworthy four-level C4 model of the current repository. “Complete” means the model covers the important runtime units, responsibilities, code paths, data, integrations, APIs, operations, and flows. It does not mean placing every file or class into one diagram.

## Inputs

Required:

- repository root;
- target C4 path, or permission to use `c4/architecture.c4`;
- user-requested scope, if narrower than the repository.

Optional:

- priority domain or use case;
- deployment environment;
- required API or flow views;
- previous diagrams used only as reference.

If scope is not explicit, model the whole repository at L1-L3 and the architecturally important code paths at L4.

## Execution Algorithm

Execute every phase in order.

### Phase 1 — Establish the workspace

1. Confirm repository root and current branch.
2. Inspect the working tree and preserve unrelated changes.
3. Locate all existing `.c4` and `.likec4` files.
4. Locate LikeC4 configuration and available validation commands.
5. Decide the single architecture entry point to create.
6. Do not generate renders inside the repository.

### Phase 2 — Build a repository map

Inspect enough code to identify:

- application and infrastructure technologies;
- deployable/runnable units;
- owned data stores;
- human actors and operational roles;
- external providers and external callers;
- public, authenticated, admin, machine, webhook, CLI, worker, and scheduled entry points;
- business domains and responsibility boundaries;
- important stateful workflows;
- frontend/browser/mobile consumers;
- configuration ownership;
- tests that reveal contracts or edge cases.

Do not begin C4 editing until this map exists in working notes.

### Phase 3 — Build the evidence ledger

For each important responsibility or use case, record:

```text
Name:
Actor or caller:
Entry point:
Handler:
Validator/schema:
Workflow/service:
Domain models/state:
Persistence:
External integration:
Response/event/notification:
Source paths:
```

The ledger is an internal working artifact. It prevents missing the code between a route and a database/provider.

### Phase 4 — Create the specification

Define semantic element kinds and notation before defining the model.

At minimum support:

```text
L1: person, externalSystem, softwareSystem
L2: container, database
L3: component
L4: endpoint, controller/view, form/schema, workflow, service,
    domainModel, settingsModel, template/UI caller, command/job,
    admin extension, helper/query
```

Apply the naming, colors, shapes, notation, and accessibility rules from `STANDARD.md`.

### Phase 5 — Model from the outside inward

Build in this order:

1. L1 people, system, and external systems.
2. L2 runnable/deployable containers and owned data stores.
3. L3 components grouped by cohesive responsibility.
4. L4 code elements for important entry points and flows.
5. Relationships at each abstraction level.
6. Focused static views.
7. Dynamic flow views when requested or architecturally important.

Do not start with L4 and invent parent components later. Parent boundaries must reflect actual ownership.

### Phase 6 — Create the baseline view set

Create only views supported by repository evidence.

Recommended baseline:

```text
L1_01_System_Context
L1_02_<Critical_Domain>_Context                 when useful

L2_01_Container_Overview
L2_02_Production_Runtime_Responsibilities       when deployment detail matters

L3_01_<Primary_Container>_Components
L3_02_<Critical_Domain>_Components
L3_03_<Secondary_Domain>_Components             as needed

L4_01_<Critical_Use_Case>_Code
L4_02_<Integration_or_Callback>_Code
L4_03_<Admin_or_Operations>_Code                as needed
L4_API_01_<Domain>_Endpoint_Map                 when APIs are important

FLOW_01_<Critical_Happy_Path>
FLOW_02_<Async_or_Callback_Path>                when present
FLOW_03_<Failure_or_Recovery_Path>              when present and meaningful
```

The view list may grow. Split by question and domain, never by arbitrary file count.

### Phase 7 — Prove traceability

For every L4 element:

1. Verify the exact symbol or route exists.
2. Include the source path in the description.
3. Connect the route to its actual handler.
4. Connect the handler to validation and orchestration.
5. Connect orchestration to state, persistence, provider adapters, and outcomes.

For external systems:

1. Show the local adapter or integration component.
2. Show configuration ownership without exposing secrets.
3. Label protocol, direction, and operation.
4. Show callbacks as a reverse relationship.

### Phase 8 — Reconcile completeness

Before validation, compare the model against:

- all application-owned route declarations;
- all external provider clients and webhook receivers;
- all runnable application processes and CLIs;
- all major state machines;
- all primary UI consumers;
- all important admin/operational paths.

Add missing elements or document intentional grouping.

### Phase 9 — Validate and inspect

Run every quality gate in `STANDARD.md`.

If a render is visually overloaded:

1. keep the complete model;
2. split the view;
3. keep shared nodes only where they provide necessary context;
4. use a specific title and description for each split view;
5. render again.

## Completeness Rules

- L1 must not expose implementation detail.
- L2 must reflect runtime/deployment reality.
- L3 must cover every major responsibility inside each important container.
- L4 must cover exact implementation chains for critical behavior, integrations, APIs, and operations.
- A complete model may intentionally omit trivial getters, framework internals, generated code, and passive helpers from focused views.
- Framework-generated route children must be grouped as route families unless individually audited.
- Generated clients may be grouped, but the application call site and operation must still be visible.

## Failure Modes to Reject

Reject and correct these outputs:

- only four generic views with no drill-down;
- a directory tree relabeled as components;
- endpoints disconnected from handlers;
- handlers connected directly to databases with all business logic missing;
- an external provider connected directly to a page without the local adapter;
- code nodes with no source paths;
- duplicate elements for the same symbol;
- one giant “complete architecture” view;
- unsupported claims copied from a README;
- validation skipped because the source “looks correct”.

## Required Completion Evidence

Report:

- created C4 path;
- number of modeled elements, relationships, and explicit views when available;
- L1/L2/L3/L4 view names;
- route and integration reconciliation counts;
- important dynamic flows;
- LikeC4 format, validation, export, and inspection result;
- evidence gaps or intentionally grouped framework areas.
