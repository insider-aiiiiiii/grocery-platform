# Inventory Domain Specification

## 1. Domain Purpose

The Inventory domain owns the current Shop-specific stock state of Shop Products and Variants, merchant stock updates, and stock behavior in coordination with Orders.

Inventory does not own product definitions, product names/categories/variant definitions, Shop identity, customer identity, carts, orders, payments, campaigns, analytics, or authentication. Those belong to their respective domains.

## 2. Catalog vs Inventory

```text
Catalog
  owns Shop Products and Variants
  defines the sellable unit

Inventory
  owns the current stock state for a Shop's sellable Product/Variant
```

Catalog owns product and variant definitions. Inventory owns stock state and respects the sellable unit represented by the Catalog Product or Variant. Decimal quantities are allowed. No separate Unit-of-Measure system or fixed global unit list is introduced.

## 3. Inventory Tenant Boundary

- Inventory belongs to a Shop and is strictly Shop-scoped.
- One Shop must never read or modify another Shop's inventory.
- A Merchant may modify inventory only for the Merchant's authorized Shop.
- Client-provided Shop, Product, or Variant identifiers must not bypass tenant authorization.
- Super Admin does not modify Merchant inventory in the finalized MVP rules.
- Do not select authentication technology or implementation details here.

## 4. Inventory Identity and Stock Granularity

Inventory represents current stock for a Shop's sellable Product or Variant:

- A Shop Product without variants has Product-level stock.
- For a Shop Product with variants, Variant quantities are the authoritative stock balances. Product-level stock is an aggregate derived from those variant quantities, not an independent balance.
- The Merchant may modify non-variant Product stock or individual Variant stock. Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted.

The physical identifiers and database representation are technical design decisions. Exact aggregate derivation mechanics remain unresolved, but the aggregate must derive from Variant stock and cannot be independently maintained.

## 5. Quantity

- Decimal quantities are allowed.
- The minimum stock quantity is `0`; inventory quantity cannot become negative.
- Quantity must respect the sellable unit represented by the Catalog Product or Variant.
- No separate Unit-of-Measure system or fixed global unit list is defined.

## 6. Initial Stock and Product Removal

- A newly created Shop Product starts with stock `0`.
- A newly created Variant starts with stock `0`.
- When a Catalog Product or Variant is removed from the Shop Catalog, its Inventory record is removed with it.
- This rule does not define hard-delete or soft-delete mechanics.

## 7. Stock Availability

Customers can see the exact available quantity. If available quantity is `0`, the customer sees **Out of Stock**. An out-of-stock product remains visible in the catalog and cannot be ordered.

Catalog visibility and manual availability remain separate Catalog concepts. Inventory quantity must not be conflated with manual availability.

## 8. Low Stock

The MVP has no low-stock threshold. Do not add Merchant- or Super Admin-configurable thresholds, low-stock alerts, or low-stock notification events.

## 9. Inventory Updates

The Merchant is responsible for modifying inventory and may:

- Add stock.
- Subtract stock.
- Set the exact stock quantity.

No reason is required for a manual stock adjustment. All updates must respect the zero minimum and Shop isolation rules.

## 10. Inventory and Orders

The finalized conceptual stock flow is:

```text
Order Created
    ↓
Required Quantity Reserved
    ↓
Merchant Accepts
    ↓
Reserved Quantity Becomes Deducted Stock
```

For rejection:

```text
Order Rejected
    ↓
Reserved Quantity Released
```

For accepted-order cancellation:

```text
Accepted Order Cancelled
    ↓
Deducted Quantity Restored
    ↓
Quantity Immediately Available Again
```

Reserved quantity must be visible to the Merchant. Rejected or expired pending Orders release reserved quantity. Cancelling an accepted Order restores the deducted quantity, and restored stock is immediately available again.

When requested quantity exceeds what can be fulfilled, the Merchant may manually reduce the fulfillable quantity before accepting the Order. The Customer is notified and the Order reflects the reduced quantity. The system does not automatically reduce quantities without Merchant action. The Order total is recalculated for the reduced quantity.

The Order lifecycle and cancellation rules are defined in `.ai/project-context/domains/orders.md`. Transaction/concurrency mechanics remain technical decisions.

## 11. Inventory History

The MVP stores current stock state and does not maintain a persistent inventory movement/history ledger. Do not introduce persistent movement records or inventory history requirements.

## 12. Concurrency and Technical Design

The implementation must preserve the approved stock rules under concurrent operations. Exact transaction, locking, and concurrency behavior are technical design decisions. Order business behavior is finalized in the Orders specification.

## 13. Cart and Customer Ordering

Cart and customer ordering must respect the approved Inventory availability rules. This document does not add Cart behavior or prescribe the technical implementation of Merchant quantity adjustment and customer notification.

## 14. Cross-Domain Relationships

### Shops

Provide Shop ownership and tenant context. Inventory is isolated by Shop.

### Users & Merchant Accounts

The Merchant modifies stock only for the Merchant's authorized Shop. Authentication and authorization implementation remain outside this domain.

### Catalog

Defines Shop Products, Variants, and their sellable units. Inventory stores Shop-scoped Product-level or Variant-level stock according to the granularity rules above.

### Cart

Customer ordering respects Inventory availability. No additional Cart behavior is defined here.

### Orders

Order creation reserves required quantity; acceptance deducts it; rejection and pending Customer cancellation release it; eligible Merchant cancellation after acceptance restores/releases it. When stock is insufficient, Merchant manually reduces the fulfillable quantity before acceptance, the Customer is notified, and the Order total reflects the reduced quantity. No automatic quantity reduction occurs. Exact transaction/concurrency implementation remains a technical dependency.

### Notifications and Analytics

No low-stock threshold, low-stock alert/event, or persistent inventory history is defined for MVP. Do not introduce such Notifications or Analytics behavior.

## 15. Unresolved Decisions

The following remain unresolved and must not be decided in this document:

- Exact technical/database representation of Product, Variant, and aggregate stock.
- Exact technical derivation of aggregate Product-level stock from authoritative Variant quantities.
- Exact transaction, locking, and concurrency implementation.
- Physical hard-delete or soft-delete mechanics when a Catalog Product or Variant is removed.

These unresolved implementation details do not change the finalized Inventory business rules above.

## 16. Explicit Non-Goals

This specification does not define Django models, database schema, migrations, serializers, API endpoints, authentication technology, authorization implementation, product definitions or variants, Catalog categories, Cart implementation, payment processing, WhatsApp implementation, delivery management, low-stock thresholds or alerts, inventory history, frontend implementation, or transaction/locking implementation.

## 17. Implementation Gate

Inventory business decisions and the technical transaction design are finalized in ADRs 0001–0004. Inventory models, constraints, stock services, and Merchant stock APIs are implemented. ORD-010 routes Order acceptance through Inventory's acceptance deduction service and routes Merchant rejection, eligible Merchant cancellation, and pending expiry through the Inventory transition coordinator. These operations share the Order transaction and Order row lock; multi-item Inventory operations use deterministic target ordering. Pending Customer cancellation uses the same pending-reservation release operation when its ORD-008 endpoint is merged. No persistent stock movement ledger is maintained. PostgreSQL concurrency behavior remains the production authority; local SQLite checks do not verify row-lock races.
