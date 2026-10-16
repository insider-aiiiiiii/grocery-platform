# ADR 0001: Inventory Concurrency, Row-Level Locking, and Invariant Guarantees

## Status
Approved

## Context

The grocery platform backend is a Django modular monolith serving multi-tenant grocery stores. Inventory owns the current stock state of a Shop's sellable Products and Variants. Decimal quantities are supported (up to 3 decimal places).

During high-traffic shopping periods, multiple customers may concurrently attempt to order the same physical stock items, or an order cancellation/rejection may occur concurrently with incoming orders and manual merchant adjustments.

Per `.ai/project-context/domains/inventory.md` §12, §15, and §17:
- The implementation must preserve the approved stock rules under concurrent operations.
- Inventory quantity cannot become negative (`quantity >= 0`).
- Available quantity cannot drop below zero (`reserved_quantity <= quantity`).
- Product-level stock for variant-based products must derive dynamically from authoritative variant stock, never as an independent balance.
- Technical dependencies and locking mechanisms must not be silently or arbitrarily introduced outside approved architectural design.

## Problem

Under concurrent requests, classic race conditions (e.g., Read-Modify-Write) could permit:
1. **Overselling / Double Allocation**: Two concurrent orders reading available stock as `5.000` could both proceed to reserve `4.000`, resulting in a total reservation of `8.000` against an on-hand stock of `5.000`.
2. **Negative Stock State**: Concurrent subtraction or uncoordinated adjustment pushing stock below zero.
3. **Deadlocks**: Multiple concurrent multi-item orders locking overlapping items in differing orders.

## Alternatives Considered

### Alternative 1: Optimistic Concurrency Control (OCC) with a Version Field
- **Mechanics**: Add a `version` integer to `InventoryItem`. When saving, execute `UPDATE ... WHERE version = old_version`. If 0 rows updated, retry or fail.
- **Drawbacks**: Under high contention on limited items (e.g. popular flash sale or low-stock item), OCC causes high transaction retry storms, poor latency, and wasted compute.

### Alternative 2: External Distributed Locking (Redis / Redlock)
- **Mechanics**: Introduce an external Redis instance to acquire distributed mutex locks per item.
- **Drawbacks**: Violates the Ponytail Minimalist Principle and anti-bloat guidelines. Adds operational complexity, network latency, failure modes around network partitions, and an unapproved dependency outside the approved technology stack (Python 3.12, Django 5.x, PostgreSQL).

### Alternative 3: Database Pessimistic Row-Level Locking (`select_for_update()`) with Database Invariant Floor (Selected)
- **Mechanics**:
  1. Use standard Django `transaction.atomic()` with `select_for_update()` row-level locks on authoritative `InventoryItem` records.
  2. For multi-item batch orders, deterministically sort item identifiers `(is_variant, target_id)` before lock acquisition to completely eliminate database deadlocks.
  3. Enforce database-level `CheckConstraint` rules (`quantity >= 0`, `reserved_quantity >= 0`, `reserved_quantity <= quantity`) directly in PostgreSQL/SQLite as an unbypassable safety floor.

## Decision

We adopt **Alternative 3: Pessimistic Row-Level Locking (`select_for_update()`) with Database Check Constraint Safety Floor**.

### Implementation Rules:
1. **Strict Atomicity**: All state-changing inventory operations (`reserve_order_stock`, `release_order_stock`, `deduct_order_stock`, `restore_cancelled_order_stock`, `reduce_and_accept_order_stock`, and batch variants) must run inside `transaction.atomic()`.
2. **Row Locking**: Fetch the target `InventoryItem` using `.select_for_update()`.
3. **Deterministic Batch Ordering**: In `reserve_order_items_stock` and other multi-item helpers, items are sorted by `(is_variant, id)` prior to lock acquisition to prevent circular lock wait-chains (deadlocks).
4. **Database Safety Floor**:
   - `inventory_quantity_non_negative`: `quantity >= 0`
   - `inventory_reserved_quantity_non_negative`: `reserved_quantity >= 0`
   - `inventory_reserved_lte_quantity`: `reserved_quantity <= quantity`
   Even if an application code path bypassed locking, the database engine will abort the transaction with an `IntegrityError` before any invalid stock balance can be committed.
5. **Zero External Dependencies**: All concurrency guarantees utilize native PostgreSQL row-locking and Django ORM standard primitives.

## Consequences

### Positive
- Completely prevents double-allocation and overselling races under concurrency.
- Deterministic locking order eliminates deadlocks in multi-item orders.
- Zero extra infrastructure or dependencies required (YAGNI / Ponytail anti-bloat).
- Database-level constraints provide an unbreakable guarantee of positive inventory balances.

### Trade-offs / Limitations
- Row locks hold PostgreSQL row-level locks for the duration of the short atomic block. Operations inside the block must remain minimal (pure DB reads and updates; no external HTTP or WhatsApp network calls).
