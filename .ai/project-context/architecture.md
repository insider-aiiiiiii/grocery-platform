# Grocery Platform Architecture

## 1. Architecture Overview

The backend uses Django and Django REST Framework (DRF) with PostgreSQL. It is a modular monolith organized into domain-oriented Django applications, with REST APIs under `/api/v1/`.

The product includes web-based interfaces for Super Admin and Merchant users, plus a public/customer-facing shop catalog and ordering flow. External integrations are limited to concepts approved by the product specification, including WhatsApp for notifications and acknowledgements. Payment remains merchant-handled in the MVP; no centralized online payment gateway is approved.

A modular monolith fits the current foundation stage: domains can have clear boundaries in one project and backend while the product and domain specifications evolve, without prematurely adding distributed-system complexity. Keep the backend as one deployable application initially; do not introduce microservices.

## 2. Architectural Principles

- Maintain clear domain boundaries and explicit domain ownership.
- Begin with a single deployable backend.
- Separate concerns and follow Django conventions rather than adding unnecessary custom architecture.
- Treat PostgreSQL as the source of persisted business state.
- Enforce shop-level tenant isolation and server-side authorization.
- Keep API contracts consistent.
- Prefer minimal abstractions and evolve the architecture incrementally.
- Do not add speculative infrastructure or architecture.

## 3. High-Level System Components

The system is organized conceptually as follows:

```text
Client Interfaces
        |
        v
Django REST API
        |
        +----------------+
        |                |
        v                v
 Domain Applications   Shared Platform Concerns
        |                |
        v                v
 PostgreSQL          External Integrations
```

This is a logical view, not a prescription to create additional services. Shared concerns and integrations remain within the approved application architecture unless separately decided.

## 4. Django Application Boundaries

Each current Django app represents a business domain. The responsibilities below are high-level only and come from the product context; they do not define models, fields, endpoints, or final relationships.

### `users`

Actor identity is represented by one custom Django `User` model with `SUPER_ADMIN` and `MERCHANT` roles. Merchant credentials and account state live in a separate Merchant profile. Authentication flows, Merchant profile/Shop relationships, and authorization remain to be finalized.

### `shops`

Shop and merchant business context, shop profile, lifecycle support, and the shop-level tenant boundary. Membership and authorization implementation are not finalized.

### `catalog`

Platform master-catalog concepts, merchant-specific catalog concepts, products, variants, category/catalog relationships, and product-review concepts where applicable. The final catalog schema is not defined here.

### `inventory`

Merchant/shop inventory, availability, and stock-related behavior. Inventory algorithms are not defined here.

### `customers`

Shop-specific customer identity, customer information required by approved product behavior, and repeat-order customer context. Do not assume customers are globally shared across shops.

### `cart`

Customer cart behavior, shop-specific cart context, and cart-item handling. The cart persistence strategy is not finalized.

### `orders`

Order creation, order data, order lifecycle, and fulfillment-related order state. The complete order state machine is not finalized.

### `campaigns`

Platform/shop campaign concepts and promotional content where approved. The final campaign schema is not defined here.

### `notifications`

Notification orchestration and WhatsApp notification integration, including notification status or handling where appropriate. WhatsApp is a notification and acknowledgement channel, not the merchant's primary order-operation interface.

### `analytics`

Merchant and platform analytics and aggregation/reporting behavior. Analytics must respect tenant boundaries.

## 5. Domain Boundary Rules

- Each application owns its domain behavior.
- Do not put unrelated business logic in another app.
- Make cross-domain interactions explicit and avoid circular dependencies.
- Introduce shared logic only when it is genuinely shared.
- Do not create a generic `utils` layer for unrelated business logic.
- When domain logic becomes complex, follow the service/domain-layer guidance in `.ai/skills/django/SKILL.md`; do not require a service layer for every simple CRUD operation.

## 6. Dependency Direction

Prefer this conceptual dependency direction:

```text
API / Interface Layer
        |
        v
Domain/Application Logic
        |
        v
Persistence / ORM
```

Views and controllers coordinate requests and responses; they should not become the primary location for complex business rules. Avoid unnecessary abstraction layers. Do not introduce a repository pattern without a concrete requirement.

## 7. Request Flow

A typical API request follows this conceptual flow:

```text
Client
  ↓
URL routing
  ↓
DRF view/viewset
  ↓
Authentication context
  ↓
Authorization / tenant context
  ↓
Serializer validation
  ↓
Domain/business logic
  ↓
Django ORM
  ↓
PostgreSQL
  ↓
Response serialization
  ↓
Client
```

The exact authentication and authorization implementation is not finalized.

## 8. Tenant Architecture

The shop is the primary tenant boundary. Merchant-owned data is shop-scoped, and merchants must not access another shop's data. Super Admin has platform-level access according to the final authorization design. Customer identity is shop-specific. Keep platform-global data distinct from tenant-owned data.

Follow `.ai/skills/multi-tenancy/SKILL.md`. This architecture states the high-level boundary only; it does not finalize how tenant context is established or enforced.

## 9. Platform-Global vs Tenant-Owned Data

Keep a conceptual distinction between:

**Platform-global data**, which may include master-catalog information, platform configuration, platform-level campaign concepts, and platform analytics.

**Tenant-owned data**, which may include merchant catalog configuration, shop-specific pricing, inventory, orders, shop-specific customer identity, and merchant analytics.

These are architectural classifications derived from product context, not final database models or guarantees of specific relationships. Domain and database specifications determine actual ownership.

## 10. Authentication and Authorization Boundary

Authentication architecture is **not finalized**. Authorization architecture is **not finalized**. This document does not select JWT, session authentication, OAuth, API keys, identity providers, permission classes, role tables, or membership tables.

The architectural requirement is:

```text
Authentication identifies the actor.
Authorization determines what the actor may access.
Tenant isolation determines which shop-scoped data is accessible.
```

## 11. API Architecture

The backend exposes REST APIs implemented with DRF under `/api/v1/`. Design resource-oriented contracts. Use explicit workflow endpoints/actions where a documented state transition or operation requires them. Use serializers for validation and representation, and keep errors consistent without assuming an unapproved response format.

Pagination, filtering, and searching may be used where applicable and approved by the API contract. Follow `.ai/skills/api-design/SKILL.md` for contract design and `.ai/skills/drf/SKILL.md` for implementation. Do not define actual endpoints here.

## 12. Database Architecture

PostgreSQL is the primary database, and the Django ORM is the default database access layer. Django migrations record schema history. Use database constraints for important invariants, indexes based on real query patterns, and transactions for appropriate multi-step operations. Database integrity is an architectural responsibility.

Do not define the actual schema or choose a primary-key strategy unless it has been explicitly finalized elsewhere. Follow `.ai/skills/database-design/SKILL.md` for schema standards.

## 13. External Integrations

Only document integrations approved conceptually by the product specification.

### WhatsApp

Used for order notifications and merchant/customer acknowledgement communication as approved. It is not the merchant's primary order-operation interface. The provider and integration architecture are not selected.

### Payment

In the MVP, payment is handled by the merchant. The merchant may share UPI, UPI QR, or other payment instructions. No centralized online payment gateway is approved; do not select a payment provider.

### Storage / Media

No storage provider is finalized unless explicitly approved in canonical product or architecture documentation.

## 14. Application Boundaries vs Infrastructure

Keep this document focused on application architecture. Do not prematurely define Kubernetes, microservices, message brokers, event buses, service mesh, container orchestration, complex caching, or distributed tracing. Such infrastructure may be considered later if justified by actual requirements and approved.

## 15. Error Handling Architecture

- Handle validation errors at the appropriate validation layer.
- Represent business-rule errors consistently.
- Ensure authorization failures do not expose sensitive information.
- Handle unexpected errors centrally.
- Prevent production responses from leaking internal implementation details.

Do not define a final error JSON format unless separately approved.

## 16. Background Processing

Asynchronous/background processing may be introduced for appropriate work, such as notifications, analytics processing, or other operations that should not block a request. Do not select Celery, Redis, Kafka, SQS, or another queue system until separately approved.

Any background processing must respect tenant isolation and security rules.

## 17. Analytics Architecture

Merchant analytics must remain shop-scoped. Platform analytics may aggregate across shops only for actors with platform-level authorization. Analytics must not become a way to bypass tenant isolation. Expensive aggregation may be optimized later based on real usage; do not define warehouse or OLAP infrastructure here.

## 18. Security Architecture Principles

Follow `.ai/skills/security/SKILL.md`. Enforce security server-side, apply least privilege, preserve tenant isolation, validate untrusted input, protect secrets, use secure API behavior, maintain auditability where required, and include negative security tests. Do not define the final authentication system.

## 19. Testing Architecture

Follow `.ai/skills/testing/SKILL.md`. Test at appropriate layers: domain/unit, integration, API, database, security, tenant isolation, and end-to-end where justified. Choose tests according to risk and behavior; do not prescribe a fixed test ratio.

## 20. Code Organization

The following is a high-level repository organization. Entries explicitly marked as planned are not asserted to exist yet; `<domain apps>` represents the Django apps without inventing further files.

```text
grocery-platform/
├── AGENTS.md
├── .ai/
│   ├── project-context/
│   │   ├── product.md
│   │   ├── architecture.md
│   │   ├── business-rules.md (planned)
│   │   └── development-status.md (planned)
│   └── skills/
│       ├── django/
│       ├── drf/
│       ├── database-design/
│       ├── api-design/
│       ├── multi-tenancy/
│       ├── security/
│       └── testing/
├── docs/ (for documentation as introduced)
├── backend/
│   ├── manage.py
│   ├── config/
│   └── <domain apps>
├── .env.example
├── .gitignore
├── README.md
└── CONTRIBUTING.md (planned)
```

## 21. Documentation Hierarchy

Use this source-of-truth hierarchy:

```text
AGENTS.md
    ↓
.ai/project-context/product.md
    ↓
.ai/project-context/architecture.md
    ↓
.ai/project-context/business-rules.md
    ↓
Domain documentation
    ↓
Application code
```

Skills define **how engineering work should be performed**; project-context documents define **what the system is**. If sources conflict, follow the conflict-resolution principles in `AGENTS.md`; do not silently choose an interpretation.

## 22. Architecture Decision Records

Record significant architectural decisions with meaningful long-term consequences as ADRs under `docs/decisions/`. Potential topics include authentication architecture, tenant implementation, payment architecture, storage architecture, background-processing architecture, and major database architecture decisions. Do not create ADRs for ordinary implementation details, and do not create ADR files as part of this task.

## 23. Current Architectural State

### Finalized

- Django and Django REST Framework.
- PostgreSQL.
- Modular monolith with domain-oriented Django apps.
- REST API prefix `/api/v1/`.
- Shop-level tenant boundary.
- Three primary actors: Super Admin, Merchant / Shopkeeper, and Customer.
- Current application boundaries documented in this file.
- Core security and testing principles documented in the project skills.

### Not finalized

- Authentication mechanism.
- Exact authorization model.
- Merchant profile and Shop relationship model.
- Shop/Membership model.
- Exact database and catalog schemas.
- Exact order state machine.
- Exact inventory behavior.
- Exact API endpoint set.
- Payment gateway.
- Background-job technology.
- Storage provider.
- Caching strategy.
- Deployment architecture.

Do not silently convert any not-finalized item into a decision.

## 24. AI Agent Architecture Workflow

Before making an architectural change, an AI agent MUST:

1. Read `AGENTS.md`.
2. Read `.ai/project-context/product.md`.
3. Read this architecture file.
4. Read the relevant skills.
5. Check whether the requested change is already finalized.
6. Check whether it conflicts with an existing decision.
7. Identify affected domains.
8. Identify tenant and security implications.
9. Identify API and database implications.
10. Ask for clarification when an architectural decision is not finalized.
11. Record significant architectural decisions appropriately.
12. Only then implement.

## 25. Git Workflow

Follow the mandatory repository workflow:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/<short-description>
```

Never work directly on `main`. Inspect existing working-tree changes and do not discard them automatically. Destructive Git commands require explicit approval. Ask for a task ID before creating a new task branch if none is provided. Keep commits small and logical, never commit secrets, push task branches, and create PRs against `main`. Do not force-push or rewrite history without authorization. Follow `AGENTS.md` for the complete workflow.

## 26. What This Architecture File Does Not Define

This document does not define detailed business rules, actual database schema or models, exact API endpoints, final authentication or authorization, permission classes, the exact order state machine, detailed inventory or catalog behavior, infrastructure implementation, deployment architecture, or third-party provider selection. Those decisions belong in their appropriate project-context, domain, architecture, or ADR documents.

## Final Requirement

Create only `.ai/project-context/architecture.md`. Do not modify application code, models, migrations, APIs, authentication, permissions, database schema, or business workflows. Do not invent architectural decisions that have not been approved.
