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

## 2. Notification Types

The product requirements support certain notification categories directly; other categories are possible future topics or not currently approved.

### MVP-required

The product context explicitly supports the following order-related communications:

- merchant receives a new-order notification
- customer receives an order-received message
- customer receives an order-accepted message
- other relevant order-status notifications may be added later

These are the only notification types that are clearly required by the approved product documentation.

### Future / possible

The following are possible future extensions and are not approved as part of the current MVP unless the product requirements are updated:

- merchant onboarding notifications
- account lifecycle notifications
- low-stock or inventory alerts
- campaign announcements or promotional notifications
- platform administrative announcements
- customer reminders or repeat-order prompts
- merchant/shop operational notices

### Not currently supported

The following should not be assumed to exist unless explicit product decisions are approved:

- marketing automation workflows
- personalized customer segmentation notifications
- dynamic campaign-triggered notifications by default
- automated customer account notifications, where customer accounts are not required
- payment or refund notifications tied to an online payment gateway, because the payment model remains merchant-handled in the MVP

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
- updating order status
- preparing an order
- marking an order ready
- completing an order

Those operational behaviors always belong to the order workflow/business domain and its merchant interface, not to the notification system.

## 4. Other Delivery Channels

The product requirements do not approve a universal multi-channel platform. They identify WhatsApp as the current important channel. Additional channels may be considered later, but they are not approved by default.

### Current approved channel

- WhatsApp

### Potential future channels

- email
- SMS
- in-app notification
- push notification

These are not automatically required. For each channel, the future product decision would need to define:

- whether it is MVP or future scope
- intended recipients
- intended use cases
- provider dependency
- retry and failure behavior
- privacy handling
- tenant restrictions

In the absence of approval, the Notifications domain should not assume they exist.

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

For example:

- when an order is created, the system may send a merchant notification
- when an order is accepted, the system may send a customer notification
- when an order is rejected, the system may send a customer notification
- when an order is ready or completed, a customer notification may be required

These are not necessarily all required in MVP and must be validated against the Order domain and approved product requirements.

## 9. Order Notifications

The Order domain defines the order states and business transitions. Notifications are responsible for communicating approved transitions to the relevant audience.

The approved product requirements mention merchant and customer order notifications. The exact set and order of messages remain partially unresolved. The following table is a conceptual business mapping only.

| Order event | Recipient | Channel | Required by current product docs? |
|---|---|---|---|
| New order received | Merchant | WhatsApp / approved channel | Yes |
| Order created / received acknowledgement | Customer | Approved channel | Yes |
| Order accepted | Customer | Approved channel | Yes |
| Order rejected | Customer | Approved channel | Yes |
| Merchant manually reduces fulfillable quantity | Customer | Approved channel | Yes |
| Order preparing | Customer | Approved channel | Potentially yes; not fully finalized |
| Order ready | Customer | Approved channel | Potentially yes; not fully finalized |
| Order completed | Customer | Approved channel | Potentially yes; not fully finalized |
| Customer/Merchant cancellation using the `REJECTED` outcome | Customer / Merchant | Approved channel | Unresolved |
| Order failed or expired | Customer / Merchant | Approved channel | Unresolved |

The fact that a transition exists in Orders does not automatically imply a notification is required. This must be decided by the approved notification and order requirements.

## 10. Merchant Notifications

Merchant notifications are intended for an authorized merchant user operating on a specific shop.

Approved concepts include:

- new order notification for the shop's merchant
- order status updates relevant to merchant processing
- order-review and workflow notices, if required by the business process

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

Current business requirements suggest:

- customer name and WhatsApp number are present at checkout
- WhatsApp may be used for customer communication
- order communication should go to the order's customer contact information

Customer notifications should be sent only to approved customer contact information for the relevant order and shop context. They must not expose unrelated customer data or accidentally reach another shop's customer.

The exact source of a customer notification address remains a domain boundary question. The Customer/Order specifications determine whether the system uses:

- checkout contact data
- a shop-specific customer record
- a historical order snapshot
- another approved mechanism

Customers may use their WhatsApp number to access their Orders within the relevant Shop/customer context; OTP is not required for this MVP decision. This does not grant access to another customer's information, another Shop's Orders, or merchant/admin data. Notification delivery itself does not authorize Order-history access.

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

Customer notification contact information must not grant access to another customer's Orders or history, or to Orders outside the relevant Shop/customer context. For the approved MVP Order-history experience, Customers may use their WhatsApp number within their own Shop/customer context without OTP; minimize exposed customer information.

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

Templates are a possible requirement for consistent notification wording, but the product documentation does not define a full template-management system.

Possible template concepts include:

- notification type
- channel
- subject/title
- message body
- placeholders/variables
- language or localizations
- status for template activation
- versioning

The product requirements do not approve a full multi-template system by default. A fixed template approach is possible for MVP, but that is not the same as a final template engine.

## 17. Delivery Attempts and Failures

Notification delivery can fail for business or provider reasons. The source documents do not define a finalized failure model, but the business requirement still exists.

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

Whether notification delivery is retried automatically, manually retried, or abandoned after a retry limit is not finalized. These are unresolved decisions and must not be implemented by assumption.

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

The exact idempotency rule is not approved by the current product documentation. This requires a later decision to establish the unique business key and the duplicate-handling policy.

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

The product requirements do not specify whether provider acceptance is treated as successful delivery or whether a provider confirmation callback or status update is required before the system marks a notification as delivered.

Therefore, provider delivery confirmation is a business decision to be resolved later. Notifications must not assume that provider acceptance equals final delivery success.

## 21. Scheduling and Background Processing

Notifications may need to be immediate, delayed, or retried. The product requirements do not prescribe a particular background architecture. The current repository is a modular monolith and does not require event-driven infrastructure or queue adoption before the business requirement is known.

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

Campaign-triggered notifications are possible future behavior, but they are not approved by default in the current product requirements.

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

The product requirements do not define a final retention policy for notification records. This is an unresolved decision. The domain may eventually need to keep:

- message content history
- delivery status history
- failed and retried attempts
- provider references
- audit references
- customer contact exposure history

Retention requirements must respect customer privacy and shop isolation. The system should not keep more notification history than is necessary for approved business and compliance behavior.

The product requirements do not approve a final retention period or deletion rule. That remains an unresolved decision.

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
- Merchant notifications are shop-scoped and must remain within the authorized shop context.
- Customer notifications must target the intended recipient and shop context.
- Duplicate processing should not unintentionally create duplicate notifications where idempotency is required.
- Notification delivery failures must not be misreported as success.
- Provider-specific implementation remains behind the provider integration boundary.
- Notification content must not become an alternate source of product or order truth.

## 28. Cross-Domain Responsibilities

| Concern | Owning domain | Notifications responsibility |
|---|---|---|
| Order creation / order state | Orders | Communicate approved order events to the appropriate recipient. |
| Customer identity and contact info | Customers | Provide approved customer contact information for the intended shop/order context. |
| Shop tenant context | Shops | Provide the shop boundary within which notifications are scoped. |
| Merchant access control | Users & Merchant Accounts | Determines which merchants may access which shop notifications. |
| Product and pricing data | Catalog | Owns the product information; Notifications must not alter it. |
| Inventory status | Inventory | Owns stock and availability; Notifications can report but not modify it where later approved. |
| Cart behavior | Cart | Owns current shopping state; Notifications should not modify it. |
| Campaign content | Campaigns | Owns campaign configuration; Notifications only communicates if approved. |
| Notification delivery | Notifications | Owns message creation and delivery processing. |
| Reporting and metrics | Analytics | Owns summarization and reporting from delivery data where approved. |

## 29. Unresolved Decisions

No decision below is finalized by this specification.

| Decision | Why unresolved | Impact |
|---|---|---|
| Required notification channels | Product docs identify WhatsApp as a communication channel, but not all channels are approved. | Channel strategy cannot be finalized. |
| Exact merchant notification event set | Only new-order and some order-status communications are mentioned at a high level. | Event design remains open. |
| Exact customer notification event set | The product requires order-received and order-accepted messaging, but the full set remains open. | Customer communication flow remains open. |
| Notification lifecycle states | No final status model is approved. | Delivery and retry logic remain open. |
| Retry and failure handling | Product docs do not define automated retries or failure policy. | Reliability strategy remains open. |
| Idempotency rule | Duplicate event processing is a risk but no unique message key is approved. | Duplicate sending could occur without a business rule. |
| Template model | Template requirements are not finalized. | Content management remains open. |
| WhatsApp provider choice | Product docs name WhatsApp but not the provider or API architecture. | Provider integration cannot be designed. |
| Provider callback requirement | Delivery confirmation and callbacks are not approved. | Delivery-status handling cannot be finalized. |
| Notification retention policy | No retention or archival policy is approved. | Privacy and storage behavior remain open. |
| Customer notification identity source | Product docs do not finalize whether contact info comes from checkout, customer record, or order snapshot. | Customer notification delivery remains open. |
| Platform-level notification requirements | Platform announcements and admin notifications are not approved. | Super Admin communications remain open. |
| Campaign-triggered notifications | Campaigns may exist; notification delivery is separate and not approved. | This interaction remains open. |
| Delivery scheduling | No final requirement for immediate vs delayed vs queued notifications exists. | Delivery timing cannot be finalized. |
| Notification triggers for low-stock or merchant operational events | These are not approved requirements in the current product docs. | Event generation remains open. |

## 30. Explicit Non-Goals

This specification does not define:

- authentication mechanism
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

> The Notifications domain must not be implemented until this domain specification is reviewed and the unresolved decisions required for implementation are explicitly resolved.

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

Create only `.ai/project-context/domains/notifications.md`. Do not modify any other file. Do not create models, migrations, APIs, serializers, views, workers, provider integrations, or frontend behavior. Do not resolve unresolved notification business decisions by assumption.
