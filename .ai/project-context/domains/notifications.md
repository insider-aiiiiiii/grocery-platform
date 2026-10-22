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

## 6. Notification Identity & Schema Specification

A notification represents an approved communication intent created in response to a business event. The platform implements two primary data models for notification delivery:

### 6.1 `NotificationTemplate` (Database-Driven Admin Model)
Administrators configure approved WhatsApp templates corresponding to the 7 canonical business events. No unapproved events can be configured.

| Field | Type | Description |
|---|---|---|
| `id` | BigAutoField | Primary key |
| `event_type` | CharField (unique) | One of the 7 approved event types (e.g., `NEW_ORDER`, `ORDER_RECEIVED_CUSTOMER`) |
| `template_name` | CharField(100) | Meta WhatsApp Cloud API registered template name (e.g., `order_received_v1`) |
| `language_code` | CharField(10) | BCP-47 language tag (e.g., `en_US`, `hi_IN`, default `en_US`) |
| `body_format` | TextField | Human-readable message template format with parameter placeholders (e.g., `{{shop_name}}`) |
| `is_active` | BooleanField | Flag indicating whether this template is active for dispatch |
| `created_at` / `updated_at` | DateTimeField | Standard audit timestamps |

### 6.2 `NotificationOutbox` (Reference-Only Dispatch Model)
Records reference-only delivery intent committed in the same database transaction as the underlying order event.

| Field | Type | Description |
|---|---|---|
| `id` | UUIDField (pk) | Unique notification UUID |
| `shop` | ForeignKey(`shops.Shop`) | Shop tenant context; cascade deleted on Shop removal |
| `order_id` | UUIDField (indexed) | Public or canonical reference of the originating Order |
| `event_type` | CharField(50) | Canonical event type matching the 7 approved events |
| `recipient_type` | CharField(20) | `MERCHANT` or `CUSTOMER` |
| `recipient_phone` | CharField(20) | Authoritative normalized E.164 phone string (e.g., `+919876543210`) |
| `template` | ForeignKey(`NotificationTemplate`) | Configured template reference |
| `template_context` | JSONField | Dynamic parameter key-value pairs (e.g., `{"shop_name": "Fresh Market", ...}`) |
| `status` | CharField(30) | Current lifecycle state (see §7) |
| `retry_count` | IntegerField | Number of transient delivery attempts (default 0) |
| `next_retry_at` | DateTimeField (nullable) | Scheduled time for the next retry attempt (indexed for worker leasing) |
| `provider_message_id` | CharField(100, nullable) | Unique message ID returned by Meta Cloud API (`wamid.HBgL...`) |
| `provider_error_details` | JSONField (nullable) | Error code, message, and diagnostic payload from provider |
| `created_at` | DateTimeField | Creation timestamp (used for 30-day retention cutoff) |
| `submitted_at` | DateTimeField (nullable) | Timestamp when Meta Cloud API accepted the message payload |
| `delivered_at` | DateTimeField (nullable) | Timestamp when Meta confirmed delivery via webhook |

**Database Constraints & Indexes**:
- `UniqueConstraint(fields=["order_id", "event_type", "recipient_phone"], name="notif_outbox_order_event_recipient_uniq")`: Strict idempotency barrier preventing duplicate outbox records for the same business event and recipient.
- `Index(fields=["status", "next_retry_at", "created_at"], name="notif_outbox_worker_lease_idx")`: Optimized composite index for worker batch row-leasing.

## 7. Notification Lifecycle

The notification delivery lifecycle follows a monotonic state machine:

```text
PENDING (created in order transaction)
   ↓
LEASED (locked by worker process)
   ↓
SUBMITTED (accepted by Meta Cloud API; provider_message_id stored)
   ↓
DELIVERED (confirmed via authenticated Meta delivery webhook)
   ↓
READ (optional: confirmed via authenticated Meta read webhook)
```

### State Definitions & Transition Invariants
- `PENDING`: Outbox record is persisted and awaiting worker selection. `next_retry_at` is null or `<=` now.
- `LEASED`: Locked by a worker instance using PostgreSQL `select_for_update(skip_locked=True)` with a temporary leasing timestamp.
- `SUBMITTED`: Meta Cloud API accepted the request with HTTP 200 and returned a `provider_message_id`. **This does not indicate delivery to the handset.**
- `DELIVERED`: Verified delivery receipt received from Meta webhook callback matching `provider_message_id`.
- `READ`: Recipient has opened the message (optional terminal success).
- `FAILED_TRANSIENT_EXHAUSTED`: 3 transient retries have been exhausted without provider acceptance. Terminal failure.
- `FAILED_PERMANENT`: Immediate terminal failure upon receiving a non-retryable provider error (e.g., malformed phone number, non-WhatsApp number, unapproved template name). No further retries allowed.

**Core Invariant**: A message is **never** reported or recorded as `DELIVERED` merely upon submission to the API; it remains `SUBMITTED` until the authenticated delivery callback is received. Delivery failure never affects or rolls back the originating Order state.

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

## 16. Fixed Templates & Parameter Mapping

The platform uses database-driven `NotificationTemplate` records strictly bound to the 7 approved business events. No additional events may be configured.

### 16.1 Template Registry & Placeholder Contracts

| Event Type | Intended Recipient | Placeholder Variables | Template Copy Example |
|---|---|---|---|
| `NEW_ORDER` | Shop's configured merchant WhatsApp number | `shop_name`, `order_number`, `total_amount`, `item_count`, `portal_url` | `New Order #{{order_number}} received for {{shop_name}}! Total: ₹{{total_amount}} ({{item_count}} items). View in merchant portal: {{portal_url}}` |
| `ORDER_RECEIVED_CUSTOMER` | Customer's stored WhatsApp number | `shop_name`, `order_number`, `total_amount`, `history_link` | `Your order #{{order_number}} from {{shop_name}} has been received! Total: ₹{{total_amount}}. Store will review your order shortly. View order status: {{history_link}}` |
| `ORDER_ACCEPTED` | Customer's WhatsApp number | `shop_name`, `order_number`, `total_amount` | `Great news! Your order #{{order_number}} has been accepted by {{shop_name}}. Total: ₹{{total_amount}} is confirmed.` |
| `ORDER_REJECTED` | Customer's WhatsApp number | `shop_name`, `order_number` | `Update: Your order #{{order_number}} could not be accepted by {{shop_name}}. Any reservation has been released.` |
| `QUANTITY_REDUCED` | Customer's WhatsApp number | `shop_name`, `order_number`, `total_amount` | `Notice: Item quantities for order #{{order_number}} at {{shop_name}} were adjusted by the store. Updated total: ₹{{total_amount}}. Please check order details.` |
| `CUSTOMER_CANCELLATION` | Shop's configured merchant WhatsApp number | `shop_name`, `order_number` | `Order update: Customer has cancelled pending order #{{order_number}} for {{shop_name}}. Inventory reservations have been released.` |
| `MERCHANT_CANCELLATION` | Customer's WhatsApp number | `shop_name`, `order_number` | `Important: Your order #{{order_number}} has been cancelled by {{shop_name}}. We apologize for the inconvenience.` |

### 16.2 Dynamic Parameter Resolution & Security Rules
- All template parameters are serialized into `NotificationOutbox.template_context` as clean key-value pairs during outbox enqueueing.
- **AUTH-018 Security Rule**: For `ORDER_RECEIVED_CUSTOMER`, the one-use history access token is **never** written to `template_context` or stored in the outbox. The background worker mints the one-use token in memory, stores its cryptographic digest (SHA-256) into `CustomerGrant`, formats the full URL, and sends it directly in the provider payload.

## 17. Delivery Attempts, Bounded Retries, and Error Classification

Delivery attempts are tracked per outbox row and categorized into transient and permanent errors:

### 17.1 Bounded Retry Policy
- **Maximum Retries**: 3 attempts (`retry_count` <= 3).
- **Exponential Backoff**:
  - Attempt 1: retry after 60 seconds (`now + 1 minute`)
  - Attempt 2: retry after 300 seconds (`now + 5 minutes`)
  - Attempt 3: retry after 900 seconds (`now + 15 minutes`)
- Once retries exceed 3, the status transitions to `FAILED_TRANSIENT_EXHAUSTED`.

### 17.2 Error Classification
- **Transient Errors** (eligible for retry):
  - HTTP 408 Request Timeout, HTTP 429 Rate Limit
  - HTTP 500, 502, 503, 504 Provider Outage / Internal Server Error
  - Network / TLS socket connection timeout
- **Permanent Errors** (immediate fast-fail to `FAILED_PERMANENT` without retries):
  - HTTP 400 Bad Request (invalid phone number format, non-E.164)
  - Meta Error 131026: Phone number is not registered on WhatsApp
  - Meta Error 132001: Template does not exist or has not been approved by Meta
  - Meta Error 132000: Number of template parameters does not match approved definition

## 18. Idempotency and Duplicate Notifications

Duplicate notifications are prevented by database constraints:

### 18.1 Database Enforced Idempotency
`NotificationOutbox` enforces a unique constraint across:
```sql
CONSTRAINT notif_outbox_order_event_recipient_uniq UNIQUE (order_id, event_type, recipient_phone)
```
- If an order state hook is triggered multiple times for the same order and event, subsequent attempts hit an `IntegrityError` or use `get_or_create` / `bulk_create(ignore_conflicts=True)` and are safely discarded without creating duplicate outbox entries.

### 18.2 Provider Idempotency Header
During dispatch, the worker sends a unique idempotency key or client reference (`idempotency_key=str(outbox.id)`) to Meta Cloud API to ensure network retries do not result in duplicate WhatsApp messages.

## 19. WhatsApp Click-to-Chat (wa.me) Deep-Link Architecture

To eliminate reliance on third-party API aggregators, recurring message costs, and merchant onboarding friction, the platform uses standard WhatsApp Click-to-Chat (`https://wa.me/`) deep-links with pre-filled multilingual drafts.

```text
┌─────────────────────────┐          ┌───────────────────────────┐
│  Customer Web Checkout  │          │  Merchant Order Dashboard │
└───────────┬─────────────┘          └─────────────┬─────────────┘
            │                                      │
            ▼                                      ▼
[wa.me/<shop_phone>?text=...]          [wa.me/<cust_phone>?text=...]
 (Order Created / Cancelled)            (Accepted / Rejected / Adjusted)
            │                                      │
            └──────────────┬───────────────────────┘
                           │ Launches native WhatsApp app
                           ▼
             ┌───────────────────────────┐
             │ Merchant's / Customer's   │
             │ Personal WhatsApp Account │
             └───────────────────────────┘
```

### 19.1 URL Construction & Encoding Rules
1. **Endpoint Format**: `https://wa.me/<phone_digits>?text=<url_encoded_text>`
2. **Phone Normalization (E.164 Digits Only)**:
   - All phone numbers must be normalized to strip non-digit characters (`+`, `-`, spaces, parentheses).
   - Standard 10-digit Indian numbers without country code are prefixed with default country code `91`.
   - The resulting string must contain only numerical digits with no leading zero or `+` sign.
3. **URL Encoding**:
   - Message text must be percent-encoded using standard URL-encoding (`urllib.parse.quote`).
   - Must properly encode Unicode characters for Hindi (Devanagari) and Hinglish as well as standard English text and symbols.

### 19.2 Multilingual Message Matrix (English, Hindi, Hinglish)
The platform standardizes drafts across 3 language formats for the canonical events:

1. **`ORDER_ACCEPTED`**:
   - `en`: `"Hello! Your order #{order_number} has been accepted by {shop_name} and is being packed. We will deliver it soon!"`
   - `hi`: `"नमस्ते! {shop_name} ने आपका ऑर्डर #{order_number} स्वीकार कर लिया है और सामान पैक हो रहा है। जल्द ही डिलीवर करेंगे!"`
   - `hinglish`: `"Hello! {shop_name} ne aapka order #{order_number} accept kar liya hai aur packing shuru hai. Jaldi deliver karenge!"`

2. **`ORDER_REJECTED`**:
   - `en`: `"Hello, we are unable to accept your order #{order_number} at {shop_name} at this time. Sorry for the inconvenience."`
   - `hi`: `"नमस्ते, हम अभी {shop_name} पर आपका ऑर्डर #{order_number} स्वीकार करने में असमर्थ हैं। असुविधा के लिए हमें खेद है।"`
   - `hinglish`: `"Hello, hum abhi {shop_name} par aapka order #{order_number} accept nahi kar pa rahe hain. Asuvidha ke liye sorry."`

3. **`QUANTITY_REDUCED`**:
   - `en`: `"Hello! Regarding your order #{order_number} at {shop_name}: some items were unavailable and quantities were adjusted. Updated total is ₹{total_amount}."`
   - `hi`: `"नमस्ते! {shop_name} पर आपके ऑर्डर #{order_number} में कुछ सामान उपलब्ध नहीं था, इसलिए मात्रा बदली गई है। नया कुल बिल ₹{total_amount} है।"`
   - `hinglish`: `"Hello! {shop_name} par aapke order #{order_number} me kuch items out of stock the, isliye quantity adjust ki gayi hai. Updated bill ₹{total_amount} hai."`

### 19.3 Merchant Experience: Installable PWA & Incoming Order Audio Alert
To solve the physical reality of local grocery stores—where merchants cannot constantly monitor a desktop browser:
1. **Zero-Friction Installation (PWA)**:
   - The merchant portal operates as a Progressive Web App (PWA).
   - The merchant taps **"Install App"** / **"Add to Home Screen"** directly from mobile Chrome.
   - Requires **no Google Play Store or Apple App Store submissions, fees, or approvals**.
2. **Soundbox Audio Alert (Chime)**:
   - Upon receiving an incoming order, the application triggers a loud, repeating audio chime (soundbox-style alert) notifying the merchant even if the device is locked, idling on the shop counter, or if their attention is on in-store customers.
3. **One-Tap WhatsApp Reply**:
   - The merchant reviews order availability and taps the desired response button (`Accepted`, `Rejected`, `Quantity Adjusted`).
   - The native WhatsApp client launches instantly with the customer's chat and pre-filled message draft in the merchant's chosen language (English, Hindi, or Hinglish).
   - The merchant sends the message directly from their own personal WhatsApp account without copying or pasting.

## 20. Order State Isolation Invariant

A strict boundary exists between Order domain state transitions and WhatsApp communication:
- Order status changes (`PENDING` -> `ACCEPTED`, `REJECTED`) are processed and committed atomically in the database independently of notification actions.
- Whether a merchant or customer opens, sends, or cancels the WhatsApp draft link has **zero effect** on the Order state.
- External WhatsApp link generation failures or client-side messaging interruptions must never fail or roll back an underlying Order transition.

## 21. Direct Link Generation Service

Instead of running background daemon workers or Celery tasks, notification links are generated deterministically on-demand via `backend/notifications/links.py`:
- `normalize_whatsapp_phone(phone_raw: str, default_country_code: str = "91") -> str`: Sanitizes input into digits-only E.164.
- `build_whatsapp_link(phone: str, text: str) -> str`: Produces a standard `https://wa.me/` link.
- `get_merchant_order_action_links(order, event_type: str, language: Optional[str] = None)`: Resolves customer phone and generates pre-filled links for merchant order actions.

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

## 24. Notification History and Retention Policy

The platform enforces a strict minimal retention and hard-deletion policy for notification records:

### 24.1 Approved 30-Day Retention Window
- **Retention Period**: Exactly **30 days** from record creation (`created_at + 30 days`).
- **Disposal Action**: **Hard deletion**. Expired `NotificationOutbox` rows are permanently purged from the database.
- **Privacy Rationale**: Hard deletion prevents stale phone numbers, recipient snapshots, and message metadata from lingering in storage, conforming strictly to the project's data minimization and customer privacy standards.

### 24.2 Automated Cleanup Command
A lightweight Django management command handles routine purging:
```bash
python manage.py purge_expired_notifications
```
- Query: `NotificationOutbox.objects.filter(created_at__lt=timezone.now() - timedelta(days=30)).delete()`
- Executed periodically (e.g., daily via scheduler/cron).

## 25. Webhooks and Provider Callbacks

Provider status callbacks are fully integrated with the Meta Cloud API:

- **Ownership**: Owned by the Notifications domain under `/api/v1/notifications/webhooks/whatsapp/`.
- **Authentication**: Strict HMAC-SHA256 signature verification via header `X-Hub-Signature-256` matching `settings.META_WHATSAPP_APP_SECRET`.
- **Idempotency**: Webhook status updates match `provider_message_id`. Repetitive callbacks do not mutate timestamps or cause duplicate transitions.
- **Tenant Isolation**: Status updates update only the outbox record tied to the verified `provider_message_id`, preserving shop-scoped integrity.

## 26. Security

Notifications have unique security concerns because they may carry sensitive customer or merchant information.

Required business/security principles include:

- merchant notifications remain shop-scoped
- customer notifications remain scoped to the intended customer and shop
- notification reads, retries, and status views must respect authorization
- provider credential information must never be exposed in source code, logs, or APIs
- delivery status should not leak sensitive order or customer data to unauthorized actors
- Webhook and callback validation must confirm sender authenticity via HMAC-SHA256
- Notification logs must not record secrets, tokens, or unnecessary personal data
- customer contact details must be treated as sensitive data
- Plaintext one-use history access tokens are **never** persisted in the outbox (AUTH-018)

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

## 29. Resolved Technical Decisions (NOT-001)

The technical blockers for the Notifications domain have been formally resolved and approved:

| Decision | Final Resolution | Implementation Standard |
|---|---|---|
| **Notification schema & status representation** | Resolved | `NotificationTemplate` (admin model) and `NotificationOutbox` (reference-only dispatch) models defined with monotonic status progression (`PENDING` -> `LEASED` -> `SUBMITTED` -> `DELIVERED` -> `READ` or `FAILED`). |
| **WhatsApp provider & integration contract** | Resolved | Meta Cloud API (WhatsApp Business Platform) selected behind abstract adapter `WhatsAppProviderBase` (`MetaWhatsAppProvider` and `MockWhatsAppProvider`). |
| **Retry limit & error classification** | Resolved | Maximum 3 bounded retries with exponential backoff (+1m, +5m, +15m) for transient errors; immediate terminal failure (`FAILED_PERMANENT`) for invalid numbers/templates. |
| **Idempotency enforcement** | Resolved | Database unique constraint on `(order_id, event_type, recipient_phone)` prevents duplicate enqueueing; `outbox.id` used as provider idempotency key. |
| **Phone normalization & recipient representation** | Resolved | Recipient stored as canonical E.164 string resolved authoritatively from Shop merchant contact or Customer contact claim. |
| **Notification history & retention policy** | Resolved | **30-day retention** with scheduled hard deletion via `purge_expired_notifications`. |
| **Fixed template storage & parameter contract** | Resolved | Admin-managed `NotificationTemplate` model strictly bound to the 7 approved events with clean parameter mappings and zero raw tokens in outbox (AUTH-018). |
| **Background worker operation** | Resolved | Dedicated Django management command (`run_notification_worker`) using PostgreSQL `select_for_update(skip_locked=True)` row leasing. Zero external broker bloat. |
| **Webhook delivery confirmation** | Resolved | Public endpoint `/api/v1/notifications/webhooks/whatsapp/` with `hub.verify_token` challenge and `X-Hub-Signature-256` HMAC-SHA256 signature verification. |

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
- external broker adoption (Celery/Redis/Kafka)

## 31. Implementation Gate & Readiness

> **Status: Gate Passed.** The technical architecture, provider contract (Meta Cloud API), template schema, bounded retry, idempotency constraint, background worker operation, delivery confirmation webhooks, and 30-day retention policy are resolved and approved.
>
> Implementation may now proceed with the foundational data models, provider adapter, worker command, and webhook handlers under their respective task identifiers, following the approved specifications.

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

## 33. WhatsApp Click-to-Chat (`wa.me`) Notification Architecture (NOT-004, NOT-005, NOT-006)

The MVP notification communication model uses direct WhatsApp Click-to-Chat (`wa.me`) draft links, eliminating third-party Meta Cloud API dependencies and SMS aggregators:

### 33.1 Language Strategy & Defaults
- **Hinglish (`hinglish`)**: The primary default language for both Customer and Merchant interfaces. Uses natural conversational Hindi in Latin script to maximize readability across diverse user demographics.
- **English (`en`)**: The secondary selectable language.
- **Hindi (`hi`)**: Retained as an optional fallback for pure Devanagari script.
- **Default Resolution**: If no language is explicitly requested by a customer or merchant, the system defaults to `hinglish`.

### 33.2 Merchant Action One-Click Links
When a Merchant triggers order transitions in the ERP / Web App (`accept`, `reject`, `cancel`, or `quantity_reduced`), the response payload immediately includes a pre-filled `whatsapp_action_link`:
- Targets the Customer's snapshot phone (`order.customer_phone_snapshot`).
- Pre-filled in the Merchant's default language (`hinglish`).
- Eliminates repeated manual language dropdowns in ERP workflow.

### 33.3 Customer Checkout Confirmation Screen Integration
Upon successful order placement via `PublicCheckoutView`:
- The response returns `whatsapp_notification_links` with options for `hinglish` and `en`.
- Includes store identity (`shop_name`, `shop_contact_number`) and line item summaries (`items`) so the customer has full order acknowledgment on the screen.
- The customer can optionally tap the WhatsApp link to notify the merchant, or skip it entirely.

### 33.4 Strict Order State Isolation
- Delivery failure, network interruptions, or customer/merchant cancellation of WhatsApp interaction must **never** roll back, alter, or block order state transitions.
- Invalid or missing contact numbers safely resolve to `null` links without raising uncaught exceptions.

