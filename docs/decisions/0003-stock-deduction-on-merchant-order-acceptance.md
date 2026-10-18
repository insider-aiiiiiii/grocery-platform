# ADR 0003: Stock Deduction on Merchant Order Acceptance and Invariant Preservation

## Status
Approved

## Context

The grocery platform backend is a Django modular monolith serving multi-tenant grocery stores. Inventory owns the current stock state of a Shop's sellable Products and Variants. Decimal quantities are supported (up to 3 decimal places).

Per `.ai/project-context/domains/inventory.md` §10, §12, §14 and `.ai/project-context/domains/orders.md` §13, §15, §25:
- The conceptual lifecycle is:
  1. `Order Created` -> Required Quantity Reserved.
  2. `Merchant Accepts` -> Reserved Quantity Becomes Deducted Stock.
  3. `Order Rejected / Expired / Pending Cancelled` -> Reserved Quantity Released.
  4. `Accepted Order Cancelled before Preparation` -> Deducted Stock Restored.
- When requested quantity exceeds what can be fulfilled, the Merchant may manually reduce the fulfillable quantity before accepting the Order. The unfulfilled difference is released to stock, and the accepted quantity is deducted.
- No automatic reduction occurs without Merchant action; no customer confirmation workflow is required.

## Problem

Under concurrent multi-tenant commerce:
1. **Deduction Timing**: If stock were deducted at customer checkout/order creation:
   - Rejected, expired, or cancelled pending orders would require frequent compensatory restoration writes, causing high database churn.
   - The Merchant would be unable to inspect pending orders and adjust fulfillable quantities prior to stock deduction.
2. **Available / Reserved Invariant Preservation**:
   - Stock availability is defined as $\text{Available Quantity} = \max(0, \text{Quantity} - \text{Reserved Quantity})$.
   - Transitions between on-hand `quantity` and `reserved_quantity` must preserve exact balance invariants without creating phantom stock or allowing double-deductions.
3. **Concurrency and Deadlocks**:
   - Multiple merchants accepting orders or customers cancelling pending orders concurrently could produce race conditions or database deadlocks when locking overlapping product/variant records in non-deterministic orders.

## Alternatives Considered

### Alternative 1: Deduct Stock at Checkout (Order Creation)
- **Mechanics**: Immediately decrement `quantity` when an order is created.
- **Drawbacks**: Violates canonical business rules (`inventory.md` §10). Forces rejected/expired orders to perform reverse adjustments, opens windows for inventory discrepancy, and prevents merchant partial-quantity fulfillment adjustments before stock deduction.

### Alternative 2: Distributed Lock Manager (Redis/Redlock)
- **Mechanics**: Acquire external Redis locks during acceptance.
- **Drawbacks**: Violates Ponytail Anti-Bloat principles. Introduces external infrastructure outside the approved Python 3.12 / Django 5.x / PostgreSQL stack.

### Alternative 3: Database Pessimistic Row Locking (`select_for_update()`), Deterministic Batch Sorting, and Deferred Deduction on Acceptance (Selected)
- **Mechanics**:
  1. Checkout/Order creation strictly increments `reserved_quantity`. On-hand `quantity` is untouched.
  2. Stock deduction is executed **strictly on Merchant acceptance** (`deduct_order_stock`, `deduct_order_items_stock`, `reduce_and_accept_order_stock`, `deduct_order_acceptance_stock`).
  3. Inside `transaction.atomic()`: Row-level locks are acquired on authoritative `InventoryItem` records via `select_for_update()`.
  4. Multi-item orders sort target items deterministically by `(1 if is_variant else 0, target.id)` before lock acquisition, eliminating deadlocks per ADR 0001.
  5. On full acceptance: `reserved_quantity -= qty`, `quantity -= qty`. Available stock remains constant for other shoppers.
  6. On partial acceptance: `reserved_quantity -= (original_reserved - accepted_qty)` (unfulfilled released to available stock), and `quantity -= accepted_qty`, `reserved_quantity -= accepted_qty` (accepted quantity deducted).
  7. Enforced by database check constraints: `quantity >= 0`, `reserved_quantity >= 0`, `reserved_quantity <= quantity`.

## Decision

We adopt **Alternative 3: Deferred Stock Deduction on Merchant Acceptance with Pessimistic Row-Level Locking and Invariant Preservation**.

### Implementation Rules:
1. **Deduction Trigger**: Stock deduction occurs strictly during the `PENDING` -> `ACCEPTED` transition by an authorized Merchant. Checkout never deducts stock.
2. **Transaction Boundaries**: All acceptance stock mutations run within Django ORM `transaction.atomic()`.
3. **Deadlock Prevention**: Target items are sorted deterministically by `(1 if is_variant else 0, target.id)` prior to lock acquisition.
4. **Merchant Authorization**: Only an active Merchant owning the Shop may trigger acceptance deduction (`validate_shop_merchant_authorization`). Super Admin is prohibited from modifying Merchant inventory in MVP.
5. **Invariant Bounds**:
   - $\text{Available Quantity} = \max(0, \text{Quantity} - \text{Reserved Quantity})$.
   - Deductions exceeding `reserved_quantity` are rejected with `ValidationError`.
   - Resulting `quantity` and `reserved_quantity` cannot become negative.

## Consequences

### Positive
- Guarantees zero stock deduction at checkout.
- Eliminates inventory churn from unfulfilled/rejected pending orders.
- Enables Merchant-controlled partial fulfillment without customer confirmation bottlenecks.
- Completely prevents overselling, double-deductions, and database deadlocks.
- Zero external dependencies.

### Trade-offs / Limitations
- Short database row-level locks held during the acceptance transaction. All operations inside the block remain strictly database-bound.
