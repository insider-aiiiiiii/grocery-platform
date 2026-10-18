# ADR 0004: Inventory Release and Restoration Lifecycle Synchronization

## Status
Approved

## Context

The grocery platform backend is a Django modular monolith serving multi-tenant grocery stores. The Inventory domain owns the current stock state of a Shop's sellable Products and Variants. The Orders domain owns purchase transactions following checkout.

Per `.ai/project-context/domains/inventory.md` (§10, §12, §14), `.ai/project-context/domains/orders.md` (§13, §14, §15, §16, §19, §22, §25), and ADR 0002:
1. **Canonical Lifecycle States**:
   - Standard forward flow: `PENDING` -> `ACCEPTED` -> `PREPARING` -> `READY` -> `COMPLETED`.
   - Terminal cancellation/rejection outcome: `REJECTED`.
   - **No separate `CANCELLED` or `EXPIRED` states are introduced.**
2. **Four Rejection / Cancellation Paths to `REJECTED`**:
   - **Path 1: Merchant Rejection** (Order is `PENDING` -> `REJECTED`).
   - **Path 2: Customer Pending Cancellation** (Order is `PENDING` -> `REJECTED`).
   - **Path 3: Pending Order Expiry** (Order is `PENDING` and expires after timeout -> `REJECTED`).
   - **Path 4: Eligible Merchant Cancellation** (Order is `ACCEPTED` and cancelled **strictly before `PREPARING`** -> `REJECTED`).
3. **Ineligible Transitions**:
   - Once an order enters `PREPARING`, `READY`, or `COMPLETED`, merchant cancellation is **ineligible and strictly forbidden**.
   - Customer cancellation is strictly allowed only while the order is `PENDING`.
4. **Stock Semantics**:
   - **Pending Orders** hold reservations only; stock was never deducted. Rejection, customer cancellation, or expiry must **release reserved stock** (`reserved_quantity -= qty`, `quantity` unchanged). Available stock ($\text{Quantity} - \text{Reserved}$) immediately increases.
   - **Accepted Orders** had reserved stock converted into deducted stock on acceptance (`quantity -= accepted_qty`). Eligible cancellation before preparation must **restore deducted stock** (`quantity += accepted_qty`). Restored stock is immediately available again.
5. **Exactly-Once Semantics**:
   - Stock release or restoration must execute **exactly once** per order transition to prevent duplicate inventory inflation or double-restoration bugs.

## Problem

Under concurrent multi-tenant commerce:
1. **Double Release / Double Restoration**:
   - A customer cancelling a pending order simultaneously with an automated timeout expiry sweep, or repeated cancellation clicks from a merchant ERP, could trigger redundant stock releases or restorations.
2. **Invalid State Cancellation**:
   - An accepted order that is already being prepared (`PREPARING`) or completed (`COMPLETED`) might receive a late cancellation request. Allowing stock restoration for orders already prepared or fulfilled would corrupt physical inventory balances.
3. **State Race Conditions & Deadlocks**:
   - Multi-item orders releasing or restoring stock concurrently could encounter deadlocks or race conditions without strict atomic boundaries and deterministic locking orders.
4. **Tenant Isolation & Actor Authorization**:
   - Super Admins are prohibited from modifying merchant inventory in MVP. Customer cancellation must not alter stock for another shop or an accepted order. Merchant actions must be restricted to the authenticated merchant owning the shop.

## Decision

We adopt **Synchronized Lifecycle Stock Release and Restoration with Pessimistic Row Locking and Exactly-Once Guarantees**.

### 1. Concrete Inventory Mechanics
- **Release Pending Reservation (`release_pending_order_stock`)**:
  - Triggers on Merchant rejection, Customer pending cancellation, or Pending expiry.
  - Requires order status `PENDING` (or items list).
  - Inside `transaction.atomic()`:
    - Pre-locks `InventoryItem` records via `select_for_update()`, sorted deterministically by `(1 if is_variant else 0, target.id)`.
    - Decrements `reserved_quantity -= qty` with bounds checking (`qty <= reserved_quantity`).
    - On-hand `quantity` is untouched. Available stock increases by `qty`.
- **Restore Deducted Stock (`restore_accepted_order_stock`)**:
  - Triggers on eligible Merchant cancellation after acceptance but before preparation.
  - Requires order status `ACCEPTED`. If order is in `PREPARING`, `READY`, `COMPLETED`, or `REJECTED`, raises `ValidationError`.
  - Inside `transaction.atomic()`:
    - Pre-locks `InventoryItem` records via `select_for_update()`, sorted deterministically.
    - Increments on-hand `quantity += qty`.
    - `reserved_quantity` remains untouched. Available stock increases immediately.
- **Unified Transition Coordinator (`synchronize_order_transition_stock`)**:
  - Validates order shop tenant boundary.
  - Inspects `order.status`:
    - If `PENDING` -> executes release and sets order stock released indicator.
    - If `ACCEPTED` -> executes restoration and sets order stock restored indicator.
    - If `PREPARING`, `READY`, or `COMPLETED` -> raises `ValidationError` preventing illegal cancellation.
    - If already `REJECTED` -> idempotent no-op or validation error depending on context, guaranteeing zero double adjustment.

### 2. Authorization Rules
- **Merchant Rejection & Merchant Cancellation**:
  - Verified via `validate_shop_merchant_authorization(shop, actor)`.
  - Actor must be an active Merchant owning the shop. Super Admins and non-owning merchants are rejected.
- **Customer Pending Cancellation**:
  - Allowed only while order is `PENDING`. Verified that customer does not cancel accepted orders.
- **Pending Expiry**:
  - Automated system worker / lazy expiry check (`actor=None`).

### 3. Concurrency and Deadlock Prevention
- All stock updates run within Django ORM `transaction.atomic()`.
- Multi-item locks are acquired in strictly deterministic order: `(1 if is_variant else 0, target.id)` per ADR 0001 and ADR 0003.

## Consequences

### Positive
- Exactly adheres to canonical lifecycle: `REJECTED` outcome handles rejection, cancellation, and expiry without extraneous states.
- Protects inventory integrity: zero stock releases for non-pending orders, zero stock restorations for orders in preparation or beyond.
- Prevents double release and double restoration under retries or concurrent requests.
- Completely prevents database deadlocks and overselling.
- Zero unapproved external dependencies (Redis, Celery, etc.).

### Trade-offs / Limitations
- Database row locks are briefly held during release/restoration transactions; logic within atomic blocks remains strictly database-bound.
