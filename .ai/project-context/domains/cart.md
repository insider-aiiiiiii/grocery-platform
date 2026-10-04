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

Checkout uses the latest valid Shop Catalog price; a price displayed when an item was added is not guaranteed. The Order preserves that historical purchase price after creation. No tax calculation applies in MVP unless explicitly documented elsewhere, and no discount engine is introduced unless Campaigns later defines one. Other unapproved charges remain unspecified.

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

Adding an item to a cart does not reserve inventory. Stock is reserved as part of Order creation under the Inventory/Orders rules, not by adding to the Cart.

## 11. Stock Reservation

`Add to Cart` does not mean `Reserve Stock`. Inventory reservation and subsequent stock effects follow the Inventory and Orders rules.

Order creation reserves required stock under the approved Inventory/Orders flow. The technical representation of reserved and available quantities remains an Inventory implementation detail; see `.ai/project-context/domains/inventory.md`.

## 12. Out-of-Stock Behavior

If an item becomes unavailable or out of stock while in the Cart, keep it visible in the Cart, but prevent checkout until the customer removes or corrects it. Catalog defines visibility, manual availability, and stock presentation; Inventory owns stock state. This applies to these cases:

- A product is out of stock when added to a cart.
- A product becomes out of stock while in a cart.
- Requested quantity exceeds availability.
- A product becomes unavailable after being added.
- A product or variant is removed or deactivated after being added.

Checkout must not proceed with an unavailable or out-of-stock item. The customer must remove it or correct the Cart (for example, by choosing an eligible item or quantity).

## 13. Cart Validation

Before creating an Order, revalidate all of the following against current domain state:

- The Shop still exists and is eligible for the requested operation.
- Each product and selected variant still exists, belongs to the Cart's Shop, and is offered by that Shop.
- Each product remains visible and manually available.
- Requested quantities are valid and can be fulfilled from current stock.
- Current valid Shop Catalog prices are used.
- The selected fulfillment option is eligible for the Shop, and required checkout details are valid.

The business validation requirements above are finalized for MVP. Exact implementation, error presentation, and technical transaction/concurrency behavior remain implementation decisions; relevant domain rules govern Shop, Catalog, Inventory, Customers, and Orders details.

## 14. Cart Lifecycle

Preserve Cart items when a customer leaves and returns, until the Cart expires or an Order is successfully created. Cart expiration duration must be configurable; this specification does not set a duration. Clear the Cart only after successful Order creation, not when checkout begins or fails. Exact lifecycle states and persistence representation are not defined here.

## 15. Cart Modification

Conceptual customer operations include adding an item, increasing or decreasing its quantity, removing an item, updating its quantity, and clearing a cart. These are business-level concepts only; this specification does not define APIs or a persistence strategy.

Each operation must remain within the cart's shop context and follow approved Catalog and Inventory rules.

## 16. Multiple Carts / Multiple Shops

One Cart is scoped to one Shop. A customer may have separate carts for separate Shops; cart operations and contents remain isolated to the relevant Shop. Whether there may be multiple carts for the same customer and Shop, and the active-cart selection/cardinality rules, remain unresolved.

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

Cart supplies validated shopping intent. Checkout does not itself clear the Cart. Once an Order is successfully created, Orders owns the purchase lifecycle and the Cart is cleared. A failed checkout leaves the Cart intact. The technical handoff and transaction boundary remain implementation decisions.

## 18. Cart and Order Independence

```text
Cart
=
temporary/current shopping intent

Order
=
historical purchase transaction
```

After successful Order creation, subsequent Cart changes must not modify that Order. An Order retains its historical meaning independently of future catalog or Cart changes. The specific order snapshot representation remains the responsibility of the Orders domain and is not defined here.

## 19. Customer Information at Checkout

Customers owns customer identity and profile information; Orders defines the order-time customer information. Checkout collects the customer's name and WhatsApp number. When the customer first provides their WhatsApp number for the Shop, the permanent Shop-specific Customer record is created or recognized before successful Order creation; an abandoned Cart may therefore be associated with a Customer. Orders may be accessed with the WhatsApp number in the relevant Shop/customer context without OTP under the MVP rules. Conceptually:

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

Follow the Customers and Orders specifications for customer profile, saved-address selection, and order-time delivery details. Exact address structure, saved-address cardinality/labels, and historical customer/address snapshot representation remain unresolved there; do not decide them in Cart.

## 20. Pickup vs Delivery

The current product supports Pickup and Home Delivery. Pickup does not require a delivery address. Home Delivery requires a valid address, which may be selected from saved addresses or newly entered at checkout under the Orders rules. Checkout must validate fulfillment eligibility before Order creation.

The Orders/fulfillment design owns final validation. Delivery zones, pricing, and delivery-partner behavior are not defined by Cart.

## 21. Cart Expiration / Abandonment

Cart items persist when a customer leaves and returns until the Cart expires or an Order is successfully created. The Cart expiration duration is configurable, but its configured value and technical expiration representation remain unresolved. Cart expiration does not reserve or otherwise affect stock.

## 22. Cart Deletion / Clearing

Customers may remove individual items or clear a Cart. An unavailable or out-of-stock item remains visible and blocks checkout until removed or corrected. Clear the Cart after successful Order creation only; preserve it when checkout fails or merely begins. Clearing or later changing the Cart cannot alter an already-created Order.

## 23. Concurrency

Cart and checkout behavior may encounter concurrent catalog price changes, inventory changes, or another order consuming stock. Final checkout behavior must follow approved Catalog, Inventory, and Order rules.

Do not define locking, transaction, or other implementation techniques here. These are implementation concerns after business behavior is approved.

## 24. Business Invariants

The following invariants are supported by product and business-rule sources:

- A cart belongs to one shop context.
- A cart cannot contain products from different shops.
- Cart items reference products/variants valid for that shop.
- Customer identity remains shop-specific.
- Adding an item does not reserve inventory.
- Cart changes do not modify historical orders.
- Order creation revalidates product existence, Shop ownership, visibility, manual availability, stock, quantities, current prices, and fulfillment eligibility.
- An unavailable or out-of-stock item remains visible and prevents checkout until removed or corrected.
- Cart items persist until expiration or successful Order creation; expiration duration is configurable.
- Cart clearing occurs after successful Order creation, not when checkout begins or fails.
- Separate Shops have separate Cart contexts, and cross-Shop Cart access/operations are prohibited.
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

The MVP business rules above are finalized where stated. The following business or technical details remain unresolved and must not be inferred from this specification:

| Decision | Why unresolved | Impact |
|---|---|---|
| Cart identity and anonymous access mechanism. | Customer login is not required, but the Cart identifier and secure guest/session access behavior are unspecified. | Cart lookup and anonymous access implementation remain open. |
| Cart persistence mechanism and browser/session continuity. | Persistence across a customer's return is required, but storage and continuity mechanism are not specified. | Technical persistence design remains open. |
| Number of carts for the same customer and Shop. | Separate Shops have separate carts, but same-Shop cart cardinality and active-cart selection are not approved. | Cart reuse and selection behavior remain open. |
| Configured Cart expiration value and representation. | Expiration is required to be configurable, but the configured duration and technical representation are not set. | Deployment configuration and expiration implementation remain open. |
| Quantity limits, units, and fractional quantity behavior. | Quantities must be validated against Catalog and Inventory, but Cart-specific limits and fractional semantics are not set here. | Exact accepted quantities remain governed by relevant domain decisions. |
| Fulfillment eligibility details. | Cart must revalidate fulfillment eligibility; Shop capabilities and any further eligibility rules are not fully specified here. | Exact eligibility criteria remain with Shops/Orders decisions. |
| Cart-to-Order transaction and failure mechanics. | Cart is cleared only after successful Order creation and remains on checkout failure; atomicity, retries, and duplicate submission handling are technical/business details not finalized here. | Handoff implementation remains open. |
| Order-time customer and address representation. | Orders requires name and WhatsApp and a valid delivery address for Home Delivery, but historical snapshot representation and exact address structure remain unresolved in Customers/Orders. | Do not invent fields or snapshot mechanics in Cart. |
| Other Cart total presentation or charges not approved in product rules. | Tax is excluded in MVP; no discount engine is introduced unless Campaigns later defines one. | Do not add unapproved charges or adjustments. |
| Merchant/support access to customer Carts. | Cart is shop-isolated, but exceptional support visibility and implementation details are not defined. | Do not infer merchant access beyond approved authorization. |

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
