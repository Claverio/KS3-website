# Role: C4 API Mapper

Canonical role name: `c4-api-mapper`

Use this role to create or update API-focused C4 views that map entry points to handlers, business logic, persistence, providers, and real consumers.

Read `.c4-agent/AGENTS.md` and `.c4-agent/STANDARD.md` before this file. Also use either `c4-creator` or `c4-maintainer` as the base role.

## Mission

Make it possible to answer these questions directly from Diagram Browser:

- How many application-owned endpoints exist?
- Which method and path identifies each endpoint?
- Which handler, validator, workflow, model, and provider does it use?
- Which frontend route, component, store action, browser script, CLI, or service calls it?
- Which endpoints are public, authenticated, admin-only, internal, webhook, or debug-only?
- Which outbound provider operations are used, through which adapter and configuration?
- Which endpoints appear unused inside the repository?

## API Categories

Classify discovered interfaces as:

1. Public browser-facing HTTP routes.
2. Authenticated application APIs.
3. Admin/operations APIs.
4. Internal service-to-service APIs.
5. GraphQL or RPC operations.
6. Webhook/event consumers.
7. Async event producers and consumers.
8. Outbound provider API operations.
9. Framework-generated route families.
10. Development/debug-only route families.

Do not mix all categories into one view by default.

## Discovery Algorithm

### Phase 1 — Find inbound interfaces

Search framework-appropriate registration points, including:

- URL/path/router tables;
- controller annotations or decorators;
- GraphQL schema/resolver registration;
- RPC service definitions;
- webhook registrations;
- message-topic subscriptions;
- admin-framework registered URLs;
- debug/static/media route registration.

Inspect the registration code and the referenced handler.

### Phase 2 — Trace handlers to business behavior

For each concrete interface, trace:

```text
method/operation + path/name
  -> authentication/authorization
  -> controller/resolver/consumer
  -> request form/schema/serializer
  -> workflow/application service
  -> domain rules/model/state
  -> persistence/query
  -> provider/event/notification
  -> response/redirect/event
```

Do not model only `endpoint -> controller -> database` when intermediate behavior exists.

### Phase 3 — Find real consumers

Search for:

- browser `fetch`, XHR, Axios, GraphQL, generated client, and form actions;
- frontend API modules;
- hooks, stores, thunks, actions, loaders, server actions, and route handlers;
- mobile clients;
- backend service clients;
- management commands and test/acceptance harnesses;
- external-provider webhook configuration;
- templates embedding provider or local URLs.

Map consumer context, not only the call function:

```text
frontend route/page
  -> component/hook/store action
  -> API client function
  -> backend endpoint
```

If no repository consumer is found, say `No in-repository consumer found` in the endpoint description or relationship context. Do not invent one.

### Phase 4 — Find outbound APIs

Locate:

- HTTP/RPC client wrappers;
- provider SDK calls;
- base URLs and operation paths;
- request construction;
- authentication/signing;
- timeout and retry policy;
- response normalization;
- provider error mapping;
- callbacks/webhooks resulting from the request.

Model both the local adapter and the external system.

### Phase 5 — Build an internal API evidence matrix

Before C4 editing, create a working matrix with one row per concrete repository-owned operation:

```text
Category
Method/operation
Path or topic
Route/operation name
Auth/permission/signature
Handler
Validator/schema/form
Workflow/service
Models/state
Consumer/caller
Response/event
External dependency
Source path
```

Use the matrix to reconcile endpoint counts and identify missing consumers or handlers.

## Modeling Rules

### Endpoint node

Use an L4 endpoint element with an exact title:

```text
L4 · GET /api/orders/{order_id}/
L4 · POST /api/orders/{order_id}/pay/
L4 · GraphQL mutation createOrder
L4 · SUBSCRIBE order.payment.updated
L4 · POST /webhooks/payment-provider/
```

The description should include route name, access rules, response purpose, and source path when available.

### Consumer node

Use the most specific meaningful caller:

```text
L4 · /checkout route
L4 · CheckoutPage
L4 · useSubmitOrder()
L4 · orderStore.submit()
L4 · OrderApi.create()
```

Do not create all five layers when only one or two provide architectural value. Always preserve enough context to identify where the endpoint is used.

### Payload/schema node

Create a separate L4 schema/form/value-object node when it contains meaningful validation or is shared across operations. Summarize important fields and invariants; do not copy a full schema into the diagram.

### External operation node

Show provider operations through the local adapter:

```text
workflow
  -> LocalPaymentAdapter.createSession()
  -> POST Provider /sessions
  -> External Payment Provider
```

Never connect business logic directly to a provider when an adapter exists.

## Required API View Set

Choose the applicable views:

```text
L2_API_01_Integration_Landscape
L3_API_01_<Domain>_API_Components
L4_API_01_<Domain>_Inbound_Endpoints
L4_API_02_<Domain>_Frontend_Consumers
L4_API_03_<Provider>_Outbound_Operations
L4_API_04_Webhooks_and_Events
L4_API_05_Admin_and_Framework_Routes
```

IDs may continue an existing numeric convention, but the `L2_`, `L3_`, or `L4_` prefix is mandatory.

Each view description must state its inventory scope and count, for example:

```text
Complete inventory: 12 repository-owned order endpoints.
Framework-generated admin children are grouped in L4_API_05.
```

## Split Algorithm

Start with one inventory matrix, not one giant view.

Split views in this order:

1. public versus authenticated/admin;
2. business domain;
3. inbound versus outbound;
4. request/response versus webhook/event;
5. frontend consumer mapping versus backend implementation chain;
6. framework route families versus concrete repository routes.

Split immediately when:

- more than approximately 12-16 endpoint nodes share one view;
- labels cannot be read at normal Diagram Browser zoom;
- consumer edges cross multiple unrelated domains;
- provider callbacks obscure synchronous request paths;
- route families visually dominate concrete endpoints.

When splitting, keep a concise overview view with components/containers and focused L4 views with exact routes.

## Authentication and Security Rules

Expose evidence-backed mechanisms such as:

- session authentication;
- bearer/API key authentication;
- role or permission checks;
- CSRF behavior;
- webhook signatures/tokens;
- idempotency keys;
- tenant or ownership checks;
- rate limits.

Place these on the responsible element or relationship. Never expose actual secrets.

## Completeness Audit

Before completion:

1. Count concrete repository-owned routes from registration sources.
2. Count modeled concrete endpoint nodes.
3. Reconcile differences explicitly.
4. Count framework and debug route families separately.
5. Verify every concrete endpoint points to a real handler.
6. Verify every modeled consumer has an actual call site.
7. Verify every outbound operation uses a real adapter/client call.
8. Verify webhook direction and authentication.
9. Verify endpoint method/path/name against source.
10. Run all shared quality gates.

## Required Completion Report

Report:

- concrete inbound endpoint count by category/domain;
- framework/debug route-family count;
- outbound provider-operation count;
- endpoints with no in-repository consumer;
- API views created or split;
- important auth, idempotency, retry, and webhook behavior;
- validation and visual-inspection result.
