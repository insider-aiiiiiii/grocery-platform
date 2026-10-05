# Notifications Domain Specification

## 1. Domain Purpose

The Notifications domain owns the business concern of communicating important events to the correct recipient through an approved channel. It is responsible for delivery concerns, message creation, message routing, delivery status, and delivery failure handling.

Notifications does not own the business event itself. The business event remains owned by its originating domain.

For example:

```text
Orders
    owns:
    - order
    - order state
    - state transitions
    - order lifecycle rules

Notifications
    owns:
    - notification decision
    - recipient and channel selection
    - message content preparation
    - delivery processing
    - delivery status and failure state
```

The current source of truth supports the idea that WhatsApp is a communication channel for order notifications and acknowledgements, while the merchant ERP/web interface remains the place where order management occurs. Notifications therefore belongs to communication and delivery, not to business-state ownership.

## 2. MVP Channels and Required Order Notifications

WhatsApp is the only approved channel for MVP order notifications. The following notifications are required:

| Event | Recipient | Trigger |
|---|---|---|
| New order | Shop's configured merchant WhatsApp number | Successful Order creation |
| Order received acknowledgement and history link | Customer's stored WhatsApp number | Successful Order creation |
| Order accepted | Customer's WhatsApp number | Merchant accepts the Order |
| Order rejected | Customer's WhatsApp number | Order is rejected |
| Quantity reduced | Customer's WhatsApp number | Merchant manually reduces fulfillable quantity before acceptance |
| Customer cancellation | Shop's configured merchant WhatsApp number | Customer cancels a pending Order |
| Merchant cancellation | Customer's WhatsApp number | Merchant cancels an accepted Order before preparation |

The immediate customer acknowledgement says that the Order was received; it must not imply that the Merchant accepted it. The later acceptance or rejection message communicates the Merchant's decision.

The Order-received acknowledgement carries the one-use Customer history link. Resolve its recipient only from the Order's Shop-specific profile and authoritative contact claim; do not accept a caller-selected number. AUTH-015 requires appropriate provider confirmation before reporting delivery success. AUTH-018 recommends reference-only database outbox intent committed with the Order and a small Django worker; secrets are generated in worker memory, only digests are persisted, and superseded queued generations are skipped. Provider, deployment, retry limits, and failure copy remain open in the authoritative register at `.ai/project-context/customer-order-history-access.md` §12. A provider message already submitted cannot be recalled; invalidate its grant if a later reissue supersedes it.

Orders defines the lifecycle outcomes: customer cancellation while `PENDING`, Merchant rejection while `PENDING`, and Merchant cancellation after acceptance but before `PREPARING` use the existing `REJECTED` outcome/state. Notification wording must communicate the relevant business outcome without introducing a new Order state.

No notification is required for `PREPARING`, `READY`, or `COMPLETED`. A state transition does not imply a notification unless listed above or separately approved.

The MVP excludes merchant onboarding, account lifecycle, low-stock alerts, campaign or promotional messages, platform announcements, customer reminders, merchant operational notices, customer segmentation, marketing automation, and payment/refund notifications.

## 3. WhatsApp Boundary

The product requirements specifically identify WhatsApp as an important communication channel. The architecture should conceptually support:

```text
Business Domain
    ↓
Notification
    ↓
Provider / Channel Delivery
```

For example:

```text
Order is created
    ↓
Notification is created for merchant/customer
    ↓
WhatsApp delivers the message
```

WhatsApp is a delivery channel, not the order-management interface. This is a critical business boundary.

The product requirements explicitly state that:

- merchant order operations happen in the ERP/web interface
- WhatsApp is primarily a notification and acknowledgement channel
- merchants do not need to accept or reject orders through WhatsApp in the current scope

Therefore, WhatsApp must not be designed as a workflow interface for:

- accepting an order
- rejecting an order
- cancelling an order
- updating order status
- preparing an order
- marking an order ready
- completing an order

Those operational behaviors always belong to the order workflow/business domain and its merchant interface, not to the notification system. WhatsApp messages must never accept, reject, cancel, or otherwise change an Order.

## 4. Channel Scope

Email, SMS, push notifications, and in-app notifications are excluded from the MVP. Supporting them later requires separate product approval and decisions about recipients, use cases, providers, failure behavior, privacy, and tenant restrictions.

## 5. Notification vs Business Event

This boundary is essential.

```text
Business event
    =
state or action defined by the owning domain

Notification
    =
communication about the event, delivered to an approved recipient
```

Notifications must not silently become the owner of the underlying business data.

Examples:

- Orders owns order state and state transitions.
- Notifications communicates those events, but does not create or modify the order itself.
- Campaigns owns campaign content and may define a campaign, but Notifications only delivers communication if that is explicitly approved.
- Customers owns customer identity and contact information as defined by the Customers domain; Notifications does not define customer identity.
- Inventory owns stock state; Notifications does not alter inventory or stock availability.

The system must not allow notifications to:

- change order status
- accept or reject orders
- modify catalog information
- modify inventory figures
- modify customer identity
- change campaign configuration
- act as a payment or refund mechanism

unless a new approved business rule explicitly decides otherwise.

## 6. Notification Identity

A notification conceptually needs an identity and delivery context, but the product requirements do not define a final schema or field set.

Possible conceptual attributes include:

- notification identifier
- related business event
- event type
- recipient actor or contact
- recipient type
- shop context
- channel
- title or subject
- message body/content
- status
- created timestamp
- scheduled timestamp
- sent timestamp
- failure timestamp
- provider reference
- retry count
- provider error details

These are conceptual only. The product requirements do not finalize database fields or a notification schema.

## 7. Notification Lifecycle

The product requirements do not specify a complete final notification lifecycle. The following are possible conceptual states, but they are not automatically approved:

```text
PENDING
PROCESSING
SENT
FAILED
CANCELLED
```

A future design may use a subset or a different lifecycle. For every notification state, the business must define:

- what the state means
- who or what triggers it
- whether retries are allowed
- whether the state is terminal
- whether the recipient sees the result
- whether provider confirmation is required
- whether failure is temporary or permanent

The current product requirements do not provide a finalized state machine; therefore the lifecycle remains subject to later approval.

These are Notification-delivery states only; `CANCELLED` here does not add a separate Order state. Order rejection and cancellation use the approved Order outcome/state documented in the Orders specification.

## 8. Triggering Notifications

Notifications are triggered by business events, not by an unapproved event bus or background infrastructure design. The business flow is conceptual:

```text
Business event occurs
    ↓
Notification request created
    ↓
Notification is evaluated and delivered
```

This specification should identify the business trigger, not force a specific implementation mechanism.

The required triggers and recipients are enumerated in Section 2. This specification defines communication behavior only; Orders remains the source of truth for event meaning and lifecycle transitions.

## 9. Order Notifications

The Order domain defines the order states and business transitions. Notifications are responsible for communicating approved transitions to the relevant audience.

The approved event, recipient, and trigger mapping is in Section 2. In particular, customer cancellation notifies the Shop's configured merchant number, while Merchant cancellation notifies the Customer. Both cancellations use the existing Orders lifecycle outcome and do not introduce a `CANCELLED` state. No notification is required for `PREPARING`, `READY`, or `COMPLETED`.

## 10. Merchant Notifications

Merchant notifications are intended for an authorized merchant user operating on a specific shop.

The Shop's configured merchant WhatsApp number receives new-order notifications and customer-cancellation notifications, as specified in Section 2.

Not currently supported by default:

- merchant notifications for another shop
- merchant access to another shop's notifications
- merchant order acceptance or rejection through WhatsApp
- a general-purpose merchant notification system for every business event without a specific requirement

Merchant notifications must respect the tenant boundary:

```text
Merchant
    ↓
Authorized Shop
    ↓
Shop notifications
```

A merchant must never receive notifications belonging to another shop.

## 11. Customer Notifications

The product requirements are intentionally lightweight on customer identity and do not require a traditional customer account or password system.

Therefore, customer notifications must be tied to the approved customer-contact mechanism, not a new customer-authentication architecture.

Resolve the customer recipient from the relevant Shop-specific Customer record, consistently with Customers and Orders. Checkout contact information is used to create or recognize that Shop-specific Customer; Notifications does not define a separate customer identity or contact source.

Customer notifications must target that Customer in the Order's Shop context and must not expose unrelated customer data or reach another Shop's customer.

The approved repeat-customer/order-history flow must not require OTP. A WhatsApp number alone is not proof of identity and must not expose Orders. AUTH-015 finalizes the one-use link and Customer + Shop-scoped session security rules; delivery-provider and deployment details remain unresolved. Notification delivery itself does not authorize Order-history access. See `.ai/project-context/customer-order-history-access.md`.

## 12. Customer Privacy

Notifications may include operationally sensitive information such as:

- customer name
- WhatsApp number
- delivery address
- order status
- order total
- order items
- merchant or shop identity

Because of this, notification content and delivery must follow privacy and security principles:

- only approved data should be included
- recipients must be intended recipients
- customer data must not leak across shops
- merchants must not receive another shop's customer information through a notification
- public or unauthorized access must not expose customer contact details or order details

Customer notification contact information must not grant access to another customer's Orders or history, or to Orders outside the relevant Shop/customer context. The approved repeat-customer/order-history flow does not require OTP, and a WhatsApp number alone is insufficient. The one-use link and scoped Customer session rules are finalized in `.ai/project-context/customer-order-history-access.md`; minimize exposed customer information. Provider and deployment details remain open.

## 13. Merchant Privacy and Tenant Isolation

Notifications must conform to the shop-level tenant model.

```text
Merchant A
    must never access
Shop B notifications
```

This applies to:

- object retrieval
- message lists
- notification details
- retries and failures
- outward messages
- provider responses
- admin or management views
- background processing
- scheduled tasks

The tenant identity must come from trusted server-side context, not from client-provided values. Do not trust direct user input as proof of which shop's notifications should be returned.

## 14. Platform-Level Notifications

The product documents do not clearly approve a platform-level notification system beyond the general idea of campaigns and platform-wide operations. Platform notifications remain a possible future feature, not a confirmed MVP requirement.

Examples of possible platform-level notifications may include:

- merchant application submission or review notice
- merchant approval/rejection
- platform announcement
- campaign or promotion announcement, if approved

These are not final requirements unless separately approved. Platform notifications must not be invented merely because they are technically easy to support.

## 15. Notification Content

Notifications are responsible for communicating content about a business event; they are not the source of truth for the event itself.

The business domain remains the source of truth for:

- order state
- order contents
- product information
- customer contact details used for the order
- shop ownership
- campaign configuration
- pricing or financial decisions

Notifications own the message-building concern, including deciding which fields are appropriate for a channel and audience. For example:

```text
Order domain
    owns the real order data

Notifications domain
    decides which parts of that event are communicated to the merchant or customer
```

This prevents notification templates from silently becoming a second source of truth for business data.

## 16. Templates

Use fixed, reviewed templates for each approved event. The product documentation does not require a template-management system.

Possible template concepts include:

- notification type
- channel
- subject/title
- message body
- placeholders/variables
- language or localizations
- status for template activation
- versioning

Template storage, placeholder representation, localization, and versioning remain technical design choices. Templates must communicate only the approved event and use the minimum order information needed by the recipient.

## 17. Delivery Attempts and Failures

Notification delivery can fail for recipient-data or provider reasons. The following examples are not an exhaustive failure taxonomy:

Potential failure cases include:

- invalid or malformed phone number
- provider timeout
- transient provider outage
- provider rejection
- rate limiting
- message queuing failure
- invalid shop or target configuration

Notifications may need to track:

- retry attempts
- failed delivery state
- provider error metadata
- final delivery outcome

Use bounded retries for transient failures and avoid retries for permanent failures, subject to provider capabilities. Retry limits, error classification, and implementation mechanics remain technical design choices. Failure must remain distinct from Order state.

## 18. Idempotency and Duplicate Notifications

Duplicate notification sending is a real business risk, especially for order events that may trigger repeated processing.

The required business principle is:

```text
the same business event should not unintentionally produce duplicate messages
```

Possible ways to define uniqueness include:

- business event identifier
- order + event type
- recipient + order + event type
- channel + order + event + recipient

Prevent unintended duplicate notifications for the same originating event and recipient. The exact key representation and enforcement mechanism are technical design choices; they must preserve this business rule.

## 19. Provider Boundary

The Notifications domain owns the communication behavior, but it must not leak provider-specific logic through the rest of the application.

Conceptually:

```text
Notifications Domain
    ↓
Provider Adapter / Integration Boundary
    ↓
External Communication Provider
```

The business domain must not depend directly on provider APIs or provider-specific UI behavior. The provider integration boundary is where acquisition, payload formatting, retry, status handling, and provider-specific requests are handled.

The product requirements do not approve a specific WhatsApp provider or delivery platform. Provider-specific design remains outside this domain specification.

## 20. Provider Responses and Delivery Status

There is an important distinction between:

```text
Notification requested
```

and:

```text
Provider accepted request
```

and also between:

```text
Message sent
```

and:

```text
Message actually delivered to the recipient
```

Do not mark or report a message as delivered without provider confirmation. Provider-specific means of receiving confirmation remain an integration design choice. Delivery status is tracked separately from Order state.

## 21. Scheduling and Background Processing

Notification events are triggered by the events and timing in Section 2. The product requirements do not prescribe a particular background architecture or processing mechanism. The current repository is a modular monolith and does not require event-driven infrastructure or queue adoption.

This domain should define business requirements such as:

- immediate delivery after an event
- delayed or scheduled messages
- retry behavior after failure
- asynchronous processing if long-running communication is a problem

It must not prematurely select or require a specific infrastructure such as:

- Celery
- Redis
- RabbitMQ
- Kafka
- SQS
- event-bus architecture

These are implementation details and are not approved here.

## 22. Campaign Relationship

Campaigns may define promotional or marketing content, while Notifications is responsible for communication and delivery.

The business boundary is:

```text
Campaigns
    owns the promotion concept and campaign configuration

Notifications
    owns delivery of a campaign message if the campaign is approved for communication
```

Campaigns must not directly implement WhatsApp or provider logic. Notifications must not become the place where campaign targeting or campaign lifecycle is decided. Those are still campaign-domain concerns.

Campaign-triggered notifications are excluded from the MVP. Any future campaign-driven messages require a separate approved product decision.

## 23. Analytics Relationship

Notifications may generate useful operational data such as:

- message sent count
- failure count
- channel usage
- delivery success ratio
- notification type frequency

However, analytics and reporting belong to the Analytics domain unless the source-of-truth explicitly says otherwise. Notifications should not become an analytics engine.

The relationship is conceptual:

```text
Notifications
    creates delivery events

Analytics
    aggregates and reports them if approved
```

## 24. Notification History and Retention

Keep notification history minimal. The product requirements do not define a retention period or deletion rule; retention must be settled before implementation. Records may need only the information required for delivery status and troubleshooting, such as:

- message content history
- delivery status history
- failed and retried attempts
- provider references
- audit references
- customer contact exposure history

Retention requirements must respect customer privacy and shop isolation. The system should not keep more notification history than is necessary for approved business and compliance behavior.

The exact history fields, retention period, and deletion rule remain open technical/business decisions and must be decided before Notifications is implemented. Do not retain more message content or personal data than necessary. Analytics derived from Notifications delivery history is excluded from MVP.

## 25. Webhooks and Provider Callbacks

If the external provider supports delivery status callbacks or webhooks, those are part of the provider-integration model rather than the business domain itself. The conceptual flow is:

```text
Provider callback/webhook
    ↓
Notification status update
    ↓
Platform records delivery outcome
```

The product requirements do not require provider callbacks in the current MVP. If they are introduced later, the design must specify:

- callback ownership
- authentication/validation of provider requests
- idempotency of callback processing
- tenant association for the message
- mapping from provider response to notification status

This should remain a future design concern until approved.

## 26. Security

Notifications have unique security concerns because they may carry sensitive customer or merchant information.

Required business/security principles include:

- merchant notifications remain shop-scoped
- customer notifications remain scoped to the intended customer and shop
- notification reads, retries, and status views must respect authorization
- provider credential information must never be exposed in source code, logs, or APIs
- delivery status should not leak sensitive order or customer data to unauthorized actors
- Webhook and callback validation must confirm sender authenticity
- Notification logs must not record secrets, tokens, or unnecessary personal data
- customer contact details must be treated as sensitive data

Do not design a notification API that allows arbitrary recipient manipulation, tenant bypass, or exposure of another shop's messages.

## 27. Business Invariants

The following business invariants are supported by the approved product and architecture documentation:

- Notifications do not own the underlying business event.
- Notifications do not change order state, inventory state, catalog state, or campaign state.
- WhatsApp is a delivery channel, not the primary merchant order-management tool.
- Merchant notifications are resolved to the relevant Shop's configured merchant WhatsApp number and remain within the authorized Shop context.
- Customer notifications must target the intended recipient and shop context.
- The seven event/recipient/trigger combinations in Section 2 are the MVP notification set.
- Duplicate processing must not unintentionally create duplicate notifications for the same originating event and recipient.
- Notification delivery failures must not be misreported as success or change Order state.
- A notification is not reported as delivered without provider confirmation.
- Fixed, reviewed templates use only the order information needed for the message.
- Provider-specific implementation remains behind the provider integration boundary.
- Notification content must not become an alternate source of product or order truth.

## 28. Cross-Domain Responsibilities

| Concern | Owning domain | Notifications responsibility |
|---|---|---|
| Order creation / order state | Orders | Own event meaning and lifecycle; Notifications communicates the seven approved events without mutating Orders. |
| Customer identity and contact info | Customers | Resolve the relevant Shop-specific Customer and WhatsApp number for customer messages. |
| Shop tenant context | Shops | Provide the shop boundary within which notifications are scoped. |
| Merchant access control | Users & Merchant Accounts | Determines which merchants may access which shop notifications. |
| Product and pricing data | Catalog | Owns the product information; Notifications must not alter it. |
| Inventory status | Inventory | Owns stock and availability; Notifications can report but not modify it where later approved. |
| Cart behavior | Cart | Owns current shopping state; Notifications should not modify it. |
| Campaign content | Campaigns | Campaign-triggered notifications are excluded from MVP. |
| Notification delivery | Notifications | Owns message creation and delivery processing. |
| Reporting and metrics | Analytics | Owns summarization and reporting from delivery data where approved. |

## 29. Remaining Decisions

The MVP business rules and notification event matrix are finalized. The following decisions remain before implementation:

| Decision | Classification | Impact |
|---|---|---|
| Notification schema, field set, and status representation | Technical | Delivery tracking representation remains open. |
| WhatsApp provider, integration contract, and any callback mechanism | Technical | Provider integration design remains open. |
| Retry limit, transient/permanent error mapping, and scheduling mechanism | Technical | Must implement bounded transient retries subject to provider capabilities. |
| Idempotency key and enforcement mechanism | Technical | Must prevent duplicate delivery for the same event and recipient. |
| Phone normalization/formatting and physical recipient representation | Technical | Recipient persistence and provider payloads remain open. |
| Notification-history fields and retention/deletion policy | Technical/business | Minimal history is required; retention period must be agreed before implementation. |
| Fixed-template storage and placeholder representation | Technical | Template delivery is required; a management system is not. |
| APIs, authorization enforcement, and tenant-context implementation | Technical/security | Access must remain Shop-scoped. |

No additional channels, events, preferences, campaign messages, or low-stock alerts are approved for MVP.

## 30. Explicit Non-Goals

This specification does not define:

- Merchant/Super Admin authentication implementation (Customer Order-history access is specified in `.ai/project-context/customer-order-history-access.md`; Notifications does not authenticate Customers)
- user identity implementation
- merchant membership implementation
- shop model or ownership implementation
- catalog or product implementation
- inventory logic
- cart logic
- order lifecycle or order acceptance logic
- payment gateway or refunds
- customer account system
- campaign lifecycle or target logic
- delivery-partner logistics
- analytics implementation
- frontend UI
- database schema
- migrations
- API endpoints
- provider SDK contracts
- background worker infrastructure
- event-driven architecture
- vendor-specific integration details without product approval

## 31. Implementation Gate

> The Notifications domain must not be implemented until this specification is reviewed and remaining technical/business decisions required for implementation, including notification-history retention, are resolved.

Once approved, implementation must follow the approved documentation hierarchy and engineering standards rather than silently redefining business behavior. This includes `AGENTS.md`, project and domain context documents, and the relevant engineering skills. An implementation agent must not assume unsupported notification channels, message types, or delivery rules.

## 32. Git Workflow

Follow the repository's mandatory workflow before making changes:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/define-notifications-domain
```

- Never work directly on `main`.
- Inspect existing changes first and do not discard unrelated work.
- Do not use destructive Git commands without explicit approval.
- If no task ID is provided, ask for it before creating a branch.
- Keep work limited to the notification-domain documentation.
- Do not modify application code while defining this domain specification.

## Final Requirement

This specification is documentation only. Do not create models, migrations, APIs, serializers, views, workers, provider integrations, or frontend behavior as part of defining Notifications. Do not resolve remaining technical/business decisions by assumption.
