# Cart Domain Specification

## 1. Domain Purpose

The Cart domain owns a customer's current shopping state for a specific shop. Its conceptual scope includes cart identity and shop context, customer context, cart items, selected products and variants, requested quantities, cart validation, business-level cart totals, and handoff from checkout to order creation.

The Cart domain does not own shop identity, customer identity, product definitions, inventory quantities, order lifecycle, payment processing, WhatsApp notifications, delivery-partner management, analytics, or authentication. Those belong to their respective domains.

## 2. Cart Is Shop-Specific

A cart belongs to one shop context and must not contain products from multiple shops. The same customer may interact with separate shop contexts:

```text
Customer
   ↓
Shop A
   ↓
Cart A
```

```text
Customer
   ↓
Shop B
   ↓
Cart B
```

Do not assume a global platform cart. A cart's product references and operations must remain within its intended shop/catalog context.

## 3. Customer and Cart Relationship

The Customers domain is the source of truth for customer identity. Conceptually:

```text
Customer
=
shop-specific identity

Cart
=
current shopping state for that customer/shop context
```

The current product does not require traditional customer login/account behavior. Cart ownership does not imply that a customer must authenticate. Anonymous or session-based cart behavior is unresolved.

An initially anonymous Cart may exist without a Customer. When the customer first provides their WhatsApp number for the Shop, the Cart may become associated with the Shop-specific Customer, and the permanent Customer record may be created before checkout.

## 4. Cart Creation

The conceptual flow is:

```text
Customer opens a shop
        ↓
Browses its catalog
        ↓
Adds the first item
        ↓
A cart exists in that shop context
   ↓
Customer provides WhatsApp number
   ↓
Cart may become associated with the Shop-specific Customer
```

This does not decide API or persistence behavior. Whether an empty cart exists before the first item is added is unresolved.

## 5. Cart Contents

A cart item conceptually represents a product selected in a shop context. It identifies the intended shop, Catalog product, selected variant where applicable, requested quantity, and applicable product/price context.

This does not finalize fields or schema. Do not assume every product must have a variant if the Catalog domain does not require one.

## 6. Product and Variant Selection

Customers may select a product, select a variant where applicable, choose a quantity, and add it to their cart. The cart item must refer to a product/variant valid for the cart's intended shop catalog.

A product identifier from another shop must not bypass tenant isolation. Product and variant definitions belong to Catalog; this domain does not define them.

## 7. Quantity

Conceptually, customers may add quantity, increase or decrease it, and remove an item. Invalid quantities and quantities exceeding availability require validation according to approved Catalog and Inventory rules.

Do not define numeric limits or quantity types here. Fractional quantity behavior is unresolved; refer to the Inventory and Catalog domain decisions.

## 8. Pricing

Catalog defines the current shop-specific price. Cart uses the applicable price for the current shopping state. Order owns the final historical purchase price.

Once an order has been created, later Catalog or Cart changes must not retroactively change that order's historical purchase price or meaning. The exact order representation and snapshot strategy remain an Orders-domain decision; the existing business-rules source also marks the snapshot strategy as unresolved.

Checkout uses the latest applicable Catalog price. The Order preserves that historical purchase price after creation. No tax calculation applies in MVP unless explicitly documented elsewhere, and no discount engine is introduced unless Campaigns later defines one. Cart price-lock timing and other unapproved charges remain unspecified.

## 9. Cart Totals

A cart total reflects item amounts and, when applicable, the Shop delivery charge shown for the order flow. No tax calculation applies in MVP unless explicitly documented elsewhere. No discount engine is introduced unless Campaigns later defines one; do not add other unapproved charges.

The delivery-charge change effect on an existing or pending Order is controlled by the Merchant, with no more specific mechanism defined. The MVP has no centralized payment gateway; payment processing does not belong to Cart.

## 10. Inventory Interaction

Cart does not own inventory. It may request or consume stock-availability information from Inventory when validating requested quantities:

```text
Cart
   ↓
Requests quantity
   ↓
Inventory
   ↓
Availability validation
```

Do not assume that adding an item to a cart reserves inventory. The validation point and response to stock changes require an approved business decision.

## 11. Stock Reservation

Whether adding an item to a cart reserves stock is **Not Finalized / Requires Decision**. `Add to Cart` does not mean `Reserve Stock` unless an approved business rule explicitly establishes that behavior.

Physical, reserved, and available quantities are possible concepts to evaluate, not approved Inventory states or fields. See `.ai/project-context/domains/inventory.md`.

## 12. Out-of-Stock Behavior

The following cases require defined behavior:

- A product is out of stock when added to a cart.
- A product becomes out of stock while in a cart.
- Requested quantity exceeds availability.
- A product becomes unavailable after being added.
- A product or variant is removed or deactivated after being added.

Do not choose whether to reject, remove, warn, allow, hide, or otherwise handle these cases. Record the approved behaviors in the relevant Cart, Catalog, Inventory, and Order specifications.

## 13. Cart Validation

Before checkout/order creation, cart information may need validation against current domain state, including:

- The shop still exists and is eligible for the requested operation.
- Each product still exists and is offered by that shop.
- Each selected variant remains valid for that product and shop.
- Requested quantities are allowed.
- Product availability and inventory satisfy approved rules.
- Prices follow approved shop-specific pricing rules.
- Pickup or delivery selection and required checkout details satisfy approved Orders/fulfillment rules.

This is a conceptual checklist, not a finalized validation contract. The final validation list and behavior depend on unresolved Shop, Catalog, Inventory, Customer, and Order decisions.

## 14. Cart Lifecycle

No final Cart lifecycle or state model is approved. Concepts such as active, checked out, abandoned, expired, or cleared are not automatically approved states.

Whether the cart persists after checkout, can be resumed, expires, or changes state when an order is created requires a decision.

## 15. Cart Modification

Conceptual customer operations include adding an item, increasing or decreasing its quantity, removing an item, updating its quantity, and clearing a cart. These are business-level concepts only; this specification does not define APIs or a persistence strategy.

Each operation must remain within the cart's shop context and follow approved Catalog and Inventory rules.

## 16. Multiple Carts / Multiple Shops

One cart cannot mix products from different shops. It is not finalized whether a customer can have carts for multiple shops simultaneously, one active cart per shop, or how opening a different shop affects an existing cart.

Do not assume that switching shops clears, preserves, or replaces a cart. These behaviors require explicit approval.

## 17. Checkout Handoff

The conceptual handoff is:

```text
Cart
   ↓
Validate
   ↓
Checkout
   ↓
Order creation
   ↓
Order owns the transaction
```

Cart supplies validated shopping intent. Once an order is created, Orders owns the purchase lifecycle. This does not define the final handoff operation, transaction boundary, or Order state machine.

## 18. Cart and Order Independence

```text
Cart
=
temporary/current shopping intent

Order
=
historical purchase transaction
```

Changing or clearing a cart must not modify an already-created order. An order retains its historical meaning independently of future catalog or cart changes. The specific order snapshot representation remains the responsibility of the Orders domain and is not defined here.

## 19. Customer Information at Checkout

Cart may hold or reference customer context before or during checkout, but Customers owns customer identity and Orders owns order/customer information. When the customer first provides their WhatsApp number for the Shop, Customer creation/recognition may occur before an Order exists. Conceptually:

```text
Customer
      ↓
Cart
      ↓
Customer provides WhatsApp number
   ↓
Shop-specific Customer association
   ↓
Checkout
      ↓
Order
```

Whether customer information is copied, referenced, snapshotted, or otherwise persisted by Orders is not decided here. The Customers and Orders specifications govern those decisions.

## 20. Pickup vs Delivery

The current product supports pickup and home delivery. Checkout may require a fulfillment choice; pickup does not require a delivery address, while home delivery requires an address.

The Orders/fulfillment design owns final validation. Delivery zones, pricing, and delivery-partner behavior are not defined by Cart.

## 21. Cart Expiration / Abandonment

The following are **Not Finalized / Require Decision**: whether carts expire, how long they remain, how abandoned carts are retained, whether they affect inventory, whether customers can return later, and whether carts survive browser/session changes. Do not assume a timeout or inventory reservation.

## 22. Cart Deletion / Clearing

The product concept includes removing individual cart items. Behavior for clearing the entire cart, a product becoming unavailable, a shop becoming unavailable, or a customer returning later is not finalized. Retention and cleanup behavior are also unresolved.

Clearing a cart must not alter an already-created Order.

## 23. Concurrency

Cart and checkout behavior may encounter concurrent catalog price changes, inventory changes, or another order consuming stock. Final checkout behavior must follow approved Catalog, Inventory, and Order rules.

Do not define locking, transaction, or other implementation techniques here. These are implementation concerns after business behavior is approved.

## 24. Business Invariants

The following invariants are supported by product and business-rule sources:

- A cart belongs to one shop context.
- A cart cannot contain products from different shops.
- Cart items reference products/variants valid for that shop.
- Customer identity remains shop-specific.
- Adding an item does not automatically imply inventory reservation unless explicitly approved.
- Cart changes do not modify historical orders.
- Order creation uses validated cart information.
- Cross-shop identifiers do not bypass tenant isolation.
- Later catalog/cart changes do not retroactively alter an already-created order's historical purchase price or meaning.

## 25. Security Requirements

- Cart access remains scoped to its shop.
- Customer cart information must not cross shop boundaries.
- Merchant users do not access customer carts unless explicitly authorized.
- Client-provided cart, shop, or product identifiers cannot bypass tenant boundaries.
- Public customer cart operations do not expose merchant/admin functionality.
- Authorization is enforced server-side.

Follow `.ai/skills/multi-tenancy/SKILL.md` and `.ai/skills/security/SKILL.md`. This document does not define authentication technology.

## 26. Cross-Domain Relationships

These are conceptual domain relationships, not automatically database foreign keys:

### Shops

Provides the cart's tenant context.

### Customers

Provides shop-specific customer identity, if/when associated with a cart.

### Catalog

Provides products, variants, shop-specific prices, and customer-facing catalog availability.

### Inventory

Provides stock availability information according to approved rules; Inventory owns stock state.

### Orders

Receives validated cart information during checkout and owns the purchase lifecycle.

### Notifications

May use Order/customer information after checkout; Cart does not own notification delivery or order notifications.

### Analytics

May consume cart metrics such as abandonment if approved. No cart analytics requirement or implementation is finalized.

## 27. Unresolved Decisions

No decision below is finalized by this specification.

| Decision | Why unresolved | Impact |
|---|---|---|
| Cart identity. | No cart identifier or identity mechanism is approved. | Cart lookup and ownership cannot be finalized. |
| Anonymous cart behavior. | Customer authentication is not required, but anonymous/session behavior is unspecified. | Guest cart continuity and access remain open. |
| Customer/cart relationship. | An initially anonymous Cart may become associated with the Shop-specific Customer when the customer first provides their WhatsApp number. | Exact persistence and physical association representation remain open. |
| One cart versus multiple carts per shop. | No active-cart cardinality is approved. | Cart creation, reuse, and switching behavior remain open. |
| Multiple-shop carts and switching behavior. | Cross-shop carts are not approved; handling separate carts when switching shops is unspecified. | Existing carts may not be assumed cleared, retained, or merged. |
| Cart persistence and browser/session continuity. | No persistence strategy is approved. | Returning to an in-progress cart cannot be specified. |
| Cart expiration and abandoned-cart retention. | No timeout or retention rule is documented. | Cleanup and customer-return behavior remain open. |
| Price locking and price-change behavior. | Shop-specific pricing is approved, but cart price validity/locking is not. | Existing cart totals after catalog changes cannot be determined. |
| Other Cart total presentation and any charges not approved in product rules. | Tax calculation is excluded in MVP; no discount engine is introduced unless Campaigns later defines one. | Do not add unapproved charges or adjustments. |
| Inventory reservation. | No reservation rule is approved. | Adding to cart cannot be treated as holding stock. |
| Inventory validation timing. | Inventory deduction and order workflows are unresolved. | Add-to-cart and checkout validation timing remain open. |
| Out-of-stock and unavailable-product behavior. | Hide/warn/remove/allow/reject behavior is unspecified. | Cart repair and checkout outcomes cannot be finalized. |
| Quantity rules and fractional quantities. | Catalog/Inventory quantity semantics and limits are unresolved. | Valid cart quantities cannot be fully defined. |
| Checkout validation contract. | Rules depend on Catalog, Inventory, Customers, Shops, and Orders. | Final readiness criteria are not set. |
| Pickup/delivery validation. | Fulfillment details belong to Orders/fulfillment and per-shop capabilities are unresolved. | Cart checkout cannot define all fulfillment checks. |
| Cart-to-Order handoff. | The final order-creation behavior and transaction boundary are not defined. | Handoff and failure behavior remain open. |
| Cart clearing after order creation. | Cart lifecycle after checkout is not approved. | Post-order cart state cannot be assumed. |
| Failed checkout behavior. | Retry, preservation, and recovery behavior are unspecified. | Customer recovery and duplicate submission behavior remain open. |
| Customer information handoff. | Orders owns the historical representation; copy/reference/snapshot behavior is unresolved. | Checkout information transfer cannot be finalized. |
| Cart privacy and merchant access. | Final authorization and support visibility are not specified. | Merchant cart visibility and access boundaries need approval. |
| Cart restoration and retention. | No restoration or retained-cart behavior is approved. | Recovery after clearing, expiry, or interruption remains open. |

## 28. Explicit Non-Goals

This specification does not define Django models, database schema, migrations, serializers, API endpoints, authentication, authorization implementation, product definitions, inventory implementation or stock reservation, the Order state machine, payment processing, WhatsApp integration, delivery-partner management, analytics implementation, or frontend implementation.

## 29. Implementation Gate

> The Cart domain must not be implemented until the unresolved cart decisions and its dependencies on Catalog, Inventory, Customers, and Orders are reviewed and approved.

After approval, implementation must follow `AGENTS.md`, `.ai/project-context/product.md`, `.ai/project-context/architecture.md`, `.ai/project-context/business-rules.md`, `.ai/project-context/development-status.md`, `.ai/project-context/domains/users-and-merchant-accounts.md`, `.ai/project-context/domains/shops.md`, `.ai/project-context/domains/catalog.md`, `.ai/project-context/domains/inventory.md`, `.ai/project-context/domains/customers.md`, this domain specification, and relevant engineering skills. The implementation agent must not silently resolve unresolved business decisions.

## 30. Git Workflow

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

Create only `.ai/project-context/domains/cart.md`. Do not modify any other file. Do not create models, migrations, APIs, authentication, authorization, or cart functionality. Do not resolve unresolved business decisions.
