# Orders Domain Specification

## 1. Domain Purpose

The Orders domain owns the purchase transaction after checkout. Its business scope includes order identity and shop context, customer/order context, ordered items, historical purchase pricing, fulfillment choice, order lifecycle, merchant order handling, rejection/cancellation decisions, order history, payment context, and notification-triggering events.

Orders does not own shop identity, merchant authentication, product definitions, current catalog pricing, inventory master state, cart state, WhatsApp provider implementation, payment gateway implementation, analytics implementation, or delivery-partner management. Those belong to their respective domains.

## 2. Order Identity

An order conceptually belongs to:

```text
One Shop
+
One Customer context
+
One Purchase Transaction
```

An order belongs to exactly one shop and must not belong to multiple shops. The exact order ID type, order-number format, and public tracking identifier are not finalized. Do not assume integer IDs, UUIDs, or a specific reference format.

## 3. Shop / Tenant Boundary

Shop isolation is mandatory. Every order belongs to one shop context; merchants may access orders only for shops they are authorized to manage; customer order history is shop-specific; and a shop must not expose another shop's orders. Customer-facing order access must not bypass shop isolation. Client-provided identifiers do not establish authorization.

Follow `.ai/skills/multi-tenancy/SKILL.md`. This is the business/security boundary, not a technical tenant implementation.

## 4. Order Creation

The current conceptual flow is:

```text
Customer
   ↓
Cart
   ↓
Checkout
   ↓
Validate cart
   ↓
Create Order
   ↓
Order becomes PENDING
```

The exact order-creation transaction, validation implementation, duplicate-submission handling, and persistence behavior are not defined here. Order creation depends on Catalog, Inventory, Customers, and Cart domain rules.

## 5. Order Snapshot / Historical Meaning

An order represents what the customer actually ordered at the time it was created. Later changes to product name or information, variant information, catalog price, shop catalog, inventory, or customer profile must not silently rewrite the historical meaning or purchase price of an already-created order. The delivery charge used for the Order is also preserved.

The required historical meaning is approved. AUTH-018 recommends immutable checkout-time snapshots for product/variant names and identifiers, quantities/prices/totals, delivery charge, customer name/contact, fulfillment, and (for delivery) the address used. Do not render current Customer profile/address fields as the past Order values. Exact fields, types, currency, address structure, and retention remain in the centralized decision register `.ai/project-context/customer-order-history-access.md` §12; no extra PII or retention period is implied. Merchant-controlled quantity reductions before acceptance are an approved adjustment and recalculate the Order total under the documented lifecycle rules.

## 6. Order Items

An order item conceptually represents a product, a selected variant where applicable, the ordered quantity, the price relevant when the order was created, and an item-level total.

Do not define exact fields or database structure. Not every product is assumed to require a variant. Item meaning must remain consistent with the Catalog domain and preserve the approved historical purchase meaning.

## 7. Pricing

Distinguish:

- **Catalog:** current shop-specific selling price.
- **Cart:** price associated with current shopping state, subject to Cart rules.
- **Order:** historical purchase price for the created transaction.

Checkout uses the latest Catalog price. Once an Order exists, later Catalog price changes must not alter its historical purchase price. If the Merchant reduces an item's fulfillable quantity before acceptance, the Order total is recalculated using the reduced quantity. The delivery charge used for an Order is preserved as part of its history. The Merchant may change the Shop delivery charge; the effect of such a change on an existing or pending Order is controlled by the Merchant, and no more specific mechanism is defined.

No tax calculation applies in MVP unless explicitly documented elsewhere. No discount engine is introduced unless the Campaigns domain later defines one.

## 8. Order Total

The Order total reflects its item quantities and prices and, where applicable, the delivery charge preserved for that Order. No tax calculation applies in MVP unless explicitly documented elsewhere. No discount engine is defined unless Campaigns later approves one.

```text
Item totals, including any Merchant-approved quantity adjustment
+
Preserved delivery charge, for Home Delivery where applicable
=
Order total
```

Do not add unapproved fees or discount calculations. The MVP has no centralized online payment gateway.

## 9. Customer Information

An Order is associated with one `ShopCustomerProfile`; the profile is its single source of Shop scope in the AUTH-018 technical recommendation. The Customers domain owns current profile/contact context; Orders owns the historical transaction and immutable checkout snapshots. This proposed FK avoids independently supplied Customer and Shop references that could disagree. Cross-Shop identity semantics and schema approval remain open in `.ai/project-context/customer-order-history-access.md` §12.

## 10. Customer Contact Information

The current checkout concept includes customer name and WhatsApp number. The approved repeat-customer/order-history flow must not require OTP. A WhatsApp number alone is never authorization. The finalized mechanism is a single-use link with a 15-minute expiry, exchanged for a server-side Customer session scoped to the exact Customer and Shop. A session lasts no more than 30 days, with one active session per Customer + Shop. Do not introduce a traditional Customer account or reuse Merchant/Super Admin JWT authentication. Limit exposed customer information to what is needed for the Order experience. See `.ai/project-context/customer-order-history-access.md` for security controls and deployment decisions still open.

Home delivery also requires a delivery address. Additional contact fields are not defined here.

## 11. Fulfillment

The product supports:

- **Pickup:** the customer collects the order from the shop.
- **Home delivery:** the shop delivers the order to the customer's address.

Fulfillment choice is part of the order context. The MVP does not include centralized delivery-partner management. Do not define delivery-partner assignment, pricing, tracking, or detailed delivery operations here.

## 12. Delivery Address

For Home Delivery, an address is required. At checkout, the customer may select a saved address or enter a new address. Pickup does not require a delivery address.

The address used for delivery must remain meaningful for the Order through an immutable Order-time snapshot, independent of later profile/address changes. Free-form versus structured fields, pincode/landmark, optional coordinates, saved-address support, and snapshot retention remain unresolved in `.ai/project-context/customer-order-history-access.md` §12. Pickup has no delivery-address snapshot.

## 13. Order Lifecycle

The product requirements describe this conceptual lifecycle:

```text
PENDING
   ↓
ACCEPTED
   ↓
PREPARING
   ↓
READY
   ↓
COMPLETED
```

An order may alternatively follow:

```text
PENDING
   ↓
REJECTED
```

This is the approved MVP lifecycle. Rejection, cancellation, and pending expiry use the existing `REJECTED` outcome/state; no separate `CANCELLED` or `EXPIRED` state is added. Rejected/cancelled/expired Orders cannot be reopened. A `PENDING` Order expires after a configurable timeout, cannot be accepted after expiry, and automatically releases its reserved stock. The default timeout and technical representation of expiry time/reason remain unresolved.

## 14. PENDING

The customer has submitted the Order and it is awaiting Merchant action. It automatically expires after a configured timeout and its reservation is released. Expiry moves the Order to the existing `REJECTED` outcome/state; it cannot be accepted or reopened afterward. The exact default timeout value and expiry reason/time representation are not defined.

## 15. ACCEPTED

The Merchant has accepted the Order for fulfillment by the Shop. An `UNPAID` Order may be accepted and prepared. The Merchant decides per Order whether payment is required before acceptance.

## 16. PREPARING

The Shop is preparing the accepted Order. The Merchant controls fulfillment status through the ERP/web interface. Merchant cancellation is allowed after acceptance only before the Order enters `PREPARING`.

## 17. READY

The Order is ready for customer pickup or Home Delivery completion.

## 18. COMPLETED

The Merchant marks both Pickup and Home Delivery Orders `COMPLETED`. An Order cannot be marked `COMPLETED` while `UNPAID`; it must first become `PAID`.

## 19. REJECTED

The Merchant may reject a `PENDING` Order and may optionally provide a rejection reason. Rejection is final: the Order cannot be reopened and reserved stock is released automatically. Customer cancellation while the Order is `PENDING` and Merchant cancellation after acceptance but before `PREPARING` use the existing `REJECTED` outcome/state. Rejected/cancelled Orders release or restore reserved stock as defined by Inventory.

## 20. Merchant Order Operations

The product requires merchant order operations through the merchant ERP/web interface. The Merchant views incoming Orders, accepts or rejects them, controls fulfillment status, and marks Pickup and Home Delivery Orders `COMPLETED` subject to the payment rule.

Operations are scoped to shops the merchant is authorized to manage. Merchants do not accept or reject orders through WhatsApp in the current product scope. Exact UI behavior and API endpoints are not defined here.

## 21. Customer Order Visibility

The approved repeat-customer/order-history flow must not require OTP. Knowledge of a WhatsApp number alone must not expose Orders or customer details. A single-use access link expires after 15 minutes and exchanges for a server-side session scoped to the exact Customer and Shop. The session has a maximum absolute lifetime of 30 days; only one active session is allowed per Customer + Shop, and redeeming a new link replaces the previous session. Shop deletion revokes all grants and sessions for that Shop. This mechanism is designed but not implemented; deployment details remain open in `.ai/project-context/customer-order-history-access.md`.

Do not assume a traditional customer account/login. The approved link/token must not expose Orders outside its Customer and Shop scope or make private order/customer information publicly accessible.

The scoped Customer session is the approved proof for the Customer's own `PENDING` Order cancellation. AUTH-017/018 propose its API and transaction contract in `.ai/project-context/customer-order-history-access.md`; these are pending review and no Order or Customer API is implemented.

## 22. Order Cancellation

The Customer may cancel only their own Order while it is `PENDING`, using the authenticated Customer + Shop-scoped session and explicit confirmation. The server verifies session scope, Order ownership, Shop association, and current status on every request and protects the state-changing request against CSRF. The Merchant may cancel an accepted Order only before `PREPARING`. Both use the existing `REJECTED` outcome/state; no separate `CANCELLED` state is required. Rejected/cancelled Orders cannot be reopened. Customer cancellation releases reserved stock immediately; Merchant cancellation after acceptance restores/releases reserved stock automatically. No centralized refund workflow is included in MVP.

## 23. Refunds

The MVP has no centralized online payment gateway or centralized refund workflow.

## 24. Payment Context

For the MVP, payment is handled by the merchant. The merchant may provide UPI, UPI QR, or physical payment instructions. Centralized gateway processing is not approved.

An Order has `PAID` or `UNPAID` payment status. Only the Merchant may update it. The Merchant decides per Order whether payment is required before acceptance. An `UNPAID` Order may be accepted and prepared but cannot be marked `COMPLETED` until it is `PAID`. No centralized payment gateway or refund workflow is included in MVP.

## 25. Inventory Interaction

Order creation reserves stock; Merchant acceptance deducts the reserved quantity. Rejection automatically releases reserved stock. Customer cancellation before acceptance releases reserved stock immediately. Merchant cancellation after acceptance and before preparation automatically restores/releases reserved stock. If requested quantity exceeds what can be fulfilled, the Merchant may manually reduce the fulfillable quantity before acceptance, the customer is notified, and the Order reflects the reduced quantity. Quantities must never be reduced automatically without Merchant action. See `.ai/project-context/domains/inventory.md` for the corresponding rules.

## 26. Order and Cart Boundary

```text
Cart
=
temporary shopping state

Order
=
historical purchase transaction
```

After successful order creation, the order is independent of future cart changes. Cart-clearing behavior after order creation is not defined here; follow approved Cart rules.

## 27. Notifications

Orders is the source of truth for order data, state, and business events; Notifications owns message preparation and delivery handling. Successful Order creation notifies the Shop's configured Merchant number and sends the Customer an Order-received acknowledgement with the one-use history link to the number stored on the Shop-specific Customer. Acceptance, rejection, manual quantity reduction before acceptance, and Merchant cancellation after acceptance but before preparation notify the Customer; pending Customer cancellation notifies the Shop's configured Merchant number. The received acknowledgement must not imply acceptance. Delivery failure does not change Order state and is not reported as success before provider confirmation. See `.ai/project-context/domains/notifications.md` and `.ai/project-context/customer-order-history-access.md` for the full rules.

## 28. WhatsApp Boundary

The conceptual flow is:

```text
Orders
   ↓
Notification event
   ↓
Notifications
   ↓
WhatsApp
```

WhatsApp is a notification/acknowledgement channel. Merchant order operations remain in the ERP/web interface. Do not define or imply WhatsApp commands for accepting, rejecting, preparing, marking ready, or completing orders unless a future product decision explicitly changes scope.

WhatsApp messages must never accept, reject, cancel, or otherwise change an Order. Customer cancellation while `PENDING`, Merchant rejection while `PENDING`, and Merchant cancellation after acceptance but before `PREPARING` use the existing `REJECTED` outcome/state; Notifications communicates which event occurred without adding an Order state. No notifications are required for `PREPARING`, `READY`, or `COMPLETED`.

## 29. Order History

Orders are historical business records. Merchants can view all historical Orders for their Shop while it exists. Customer history uses the no-OTP, one-use 15-minute link exchanged for a Customer + Shop-scoped session with a 30-day maximum absolute lifetime and one active session per Customer + Shop. A WhatsApp number alone must not expose Orders. The scoped session authorizes cancellation only of that Customer's own `PENDING` Order, subject to explicit confirmation and CSRF protection. Shop deletion revokes its grants and sessions and removes its Orders; retained Customer entities and their credentials are never transferred to a replacement Shop. Minimize exposed customer information. See `.ai/project-context/customer-order-history-access.md` for deployment details still open.

## 30. Order Data Visibility

Distinguish conceptually among:

- **Customer-visible information:** what a customer needs to understand their order.
- **Merchant-visible information:** what an authorized merchant needs to review and fulfill the order.
- **Super Admin-visible information:** what is permitted by platform-level authorization.

Minimize exposed customer data. Exact fields and permissions remain for approved API, privacy, and authorization decisions.

## 31. Historical Data

Orders represent historical business transactions. Consider preservation of product/variant meaning, order-time pricing, customer/order context, fulfillment choice, and relevant order status history. This specification requires that later Catalog or Cart changes do not silently rewrite an existing order's historical meaning or purchase price.

Order history is retained while the Shop exists. Deleting the Shop deletes its Orders. The Customer entity remains after Shop deletion; customer data is not globally deleted solely because a Shop is deleted. AUTH-018 recommends immutable checkout-time snapshot fields; exact fields and retention remain in the decision register `.ai/project-context/customer-order-history-access.md` §12. Customer entities that remain after Shop deletion are not automatically associated with a replacement Shop.

## 32. Concurrency and Idempotency

Conceptual scenarios include duplicate customer checkout submissions, repeated merchant acceptance, and concurrent attempts to update the same order. The system must not create unintended duplicate purchases or allow invalid state transitions once those business rules are approved.

Do not design idempotency keys, database locks, or transaction code here. Exact duplicate-submission and concurrent-transition behavior is unresolved.

## 33. Order State Transition Rules

The currently described transitions are:

| Current state | Conceptual next state | Actor / notes |
|---|---|---|
| `PENDING` | `ACCEPTED` | Merchant reviews and accepts through the ERP/web interface. |
| `PENDING` | `REJECTED` | Merchant rejects, or Customer cancels before acceptance. |
| `ACCEPTED` | `REJECTED` | Merchant cancels before `PREPARING`. |
| `ACCEPTED` | `PREPARING` | Merchant controls fulfillment status. |
| `PREPARING` | `READY` | Merchant controls fulfillment status. |
| `READY` | `COMPLETED` | Merchant completes Pickup or Home Delivery; Order must be `PAID`. |

Rejected/cancelled/expired Orders cannot be reopened. A pending timeout moves the Order to the existing `REJECTED` outcome/state, prevents acceptance, and releases reserved stock. No separate expiry state is added. Exact timeout and expiry reason/time representation are technical/design details. Invalid transitions must be prevented by implementation according to these approved rules.

## 34. Business Invariants

The following requirements are supported by current product and business documentation:

- An order belongs to exactly one shop.
- An order must not expose another shop's data.
- Checkout uses the latest Catalog price; later Catalog changes do not alter the historical purchase price or delivery charge of an existing Order.
- Merchant order operations are limited to authorized shops.
- Customer identity and history remain shop-specific.
- Merchant order operations happen through the ERP/web interface; WhatsApp does not replace order management.
- Order state changes follow the approved lifecycle and transition rules.
- Inventory is reserved on Order creation, deducted on acceptance, released on rejection or pending Customer cancellation, and restored on eligible Merchant cancellation.
- The Merchant manually reduces insufficient quantities before acceptance; the Customer is notified, and the Order total is recalculated.
- Only the Merchant updates payment status; unpaid Orders may be accepted/prepared but cannot be completed.
- Shop deletion deletes the Shop's Orders; the Customer remains.

## 35. Security Requirements

- Order access is shop-scoped.
- Merchants cannot access another shop's orders.
- Customer order access must not expose another customer's orders.
- Client-provided order IDs do not establish authorization.
- State transitions require server-side authorization.
- Merchant order operations verify access to the relevant shop.
- Public order/status access must not expose unnecessary customer data.
- Sensitive information must not be exposed through unauthorized access.

Follow `.ai/skills/security/SKILL.md` and `.ai/skills/multi-tenancy/SKILL.md`. Do not select authentication technology here.

## 36. Cross-Domain Relationships

These are conceptual domain relationships, not automatically database foreign keys:

### Shops

Provides the tenant context for an order.

### Users & Merchant Accounts

Determines which merchant actors may manage orders for authorized shops.

### Customers

Provides the shop-specific customer context for the purchase.

### Catalog

Provides products, variants, and the applicable shop-specific price at order creation.

### Inventory

Provides stock validation and stock-change interactions according to finalized rules.

### Cart

Provides checkout input; cart state remains separate from the created order.

### Notifications

Receives order-related notification events and defines their delivery.

### Analytics

Consumes order data for shop-level or authorized platform-level reporting.

### Campaigns

May affect product or order pricing only if a future approved rule defines that interaction.

## 37. Unresolved Decisions

The technical design decisions for transaction boundaries, locking, idempotency, and expiry representation are approved in `docs/decisions/0002-order-transaction-boundaries-and-concurrency.md`. Historical snapshots, item structure, delivery charge handling, customer/address snapshots, and deletion constraints are approved in `docs/decisions/0003-order-snapshots-and-historical-references.md`. The remaining unresolved decisions are:

| Decision | Why unresolved | Impact |
|---|---|---|
| Exact order identifier, order number, and public reference. | No identifier or reference format is approved. | Order identification and customer access cannot be finalized. |
| Exact Customer/merchant authorization implementation and data minimization details. | Business access is defined; implementation and field-level privacy controls remain open. | Access-control and response design remain open. |
| Physical Shop deletion mechanics and behavior while a Shop is deactivated. | Shop deletion removes Shop Products and Orders, preserves the Merchant account, and does not associate deleted Shop data with a replacement Shop. | Database deletion design and tenant-isolation mechanics remain open. |

## 38. Explicit Non-Goals

This specification does not define Django models, database schema, migrations, serializers, API endpoints, authentication, authorization implementation, Catalog implementation, Inventory implementation, Cart implementation, payment or refund gateway, WhatsApp provider, delivery-partner management, notification implementation, analytics implementation, or frontend implementation.

## 39. Implementation Gate

> Order business rules are finalized. Concurrency, locking, idempotency, transaction boundaries, and pending expiry technical decisions are approved in `docs/decisions/0002-order-transaction-boundaries-and-concurrency.md`. Order historical snapshots, reference relations, and deletion constraints are approved in `docs/decisions/0003-order-snapshots-and-historical-references.md`. Order implementation remains gated on final identifier/public reference format, customer identity resolution, and API contracts. Do not reopen finalized business decisions or invent missing technical details.

After approval, implementation must follow `AGENTS.md`, `.ai/project-context/product.md`, `.ai/project-context/architecture.md`, `.ai/project-context/business-rules.md`, `.ai/project-context/development-status.md`, `.ai/project-context/domains/users-and-merchant-accounts.md`, `.ai/project-context/domains/shops.md`, `.ai/project-context/domains/catalog.md`, `.ai/project-context/domains/inventory.md`, `.ai/project-context/domains/customers.md`, `.ai/project-context/domains/cart.md`, this domain specification, and relevant engineering skills. The implementation agent must not silently resolve unresolved business decisions.

## 40. Git Workflow

Follow the mandatory repository workflow:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/<short-description>
```

- Never work directly on `main`.
- Inspect existing changes first; do not discard them automatically.
- Destructive Git commands require explicit approval.
- Ask for a task ID if none is provided before creating a branch.
- Keep commits small and task-related; never commit secrets.
- Push the task branch and create a PR against `main`.
- Do not force-push or rewrite history without authorization.

Follow `AGENTS.md` for the complete workflow.

## Final Requirement

Create only `.ai/project-context/domains/orders.md`. Do not modify any other file. Do not create models, migrations, APIs, authentication, authorization, order functionality, payment functionality, or WhatsApp functionality. Do not resolve unresolved business decisions.
