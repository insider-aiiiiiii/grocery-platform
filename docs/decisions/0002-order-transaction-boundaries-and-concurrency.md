# ADR 0002: Order Transaction Boundaries, Concurrency Locking, Idempotency, and Pending Expiry

## Status
Approved

## Context

The Grocery Platform backend is a Django modular monolith serving multi-tenant grocery stores. The Orders domain owns purchase transactions following checkout. 

Per `.ai/project-context/domains/orders.md`, `.ai/project-context/business-rules.md` (§10, §11, §16, §17, §18, §19, §24, §25, §34), and `.ai/project-context/domains/inventory.md` (§10, §12):
1. **Canonical Lifecycle**:
   - Forward flow: `PENDING` -> `ACCEPTED` -> `PREPARING` -> `READY` -> `COMPLETED`.
   - Alternative flow: `PENDING` -> `REJECTED`, and `ACCEPTED` -> `REJECTED` (strictly before `PREPARING`).
2. **Approved Invariant on States**:
   - Customer cancellation while `PENDING` uses the existing `REJECTED` outcome.
   - Merchant cancellation after acceptance but before `PREPARING` uses the existing `REJECTED` outcome.
   - Pending order timeout expiry uses the existing `REJECTED` outcome.
   - **No separate `CANCELLED` or `EXPIRED` states are introduced.**
   - Rejected, cancelled, and expired orders are terminal and cannot be reopened.
3. **Payment Invariants**:
   - Merchant-managed only. Exactly two statuses: `PAID` or `UNPAID`.
   - Merchant decides per order whether payment is required prior to acceptance (`UNPAID` orders may be accepted and prepared).
   - An order cannot be marked `COMPLETED` while `UNPAID`; it must become `PAID` before completion.
4. **Merchant-Controlled Partial Quantities**:
   - If stock is insufficient, the Merchant may manually reduce the fulfillable quantity prior to acceptance. Quantities are never reduced automatically.
   - The unfulfilled difference is released to stock, and the accepted quantity is deducted (`inventory.services.reduce_and_accept_order_stock`).
   - Order items and Order total are recalculated; the customer is notified.
5. **Gated Technical Implementation**:
   - Section 37 and 39 of `orders.md` left the technical execution design unresolved: transaction boundaries, locking/isolation, duplicate checkout idempotency, pending timeout representation and default duration, and retry semantics.

## Problem

Under concurrent multi-user grocery commerce:
1. **State Race Conditions**: A customer may submit a cancellation request at the exact moment a merchant clicks "Accept" or the automatic pending expiry worker triggers. Unsynchronized updates could allow double stock releases or invalid state transitions.
2. **Stock Reservation Inconsistency**: Order creation or partial quantity adjustment without strict atomic boundaries could cause inventory reservation to drift from recorded order line items.
3. **Deadlocks**: Concurrent multi-item checkouts or cancellations locking overlapping products in non-deterministic orders could induce database deadlocks.
4. **Duplicate Orders**: Network timeouts during checkout could cause customers to retry submission, causing duplicate order creation and redundant stock reservation.
5. **Expiry Handling**: Pending orders require a concrete timeout value, storage representation, and execution model that reliably releases reserved stock without adding an unapproved `EXPIRED` state.
6. **External Side Effects in Transactions**: Triggering WhatsApp notifications inside database transaction blocks risks holding row locks during network I/O or sending messages for rolled-back transactions.

## Alternatives Considered

### Alternative 1: Distributed Lock Manager (Redis/Redlock) + Celery Task Chains
- **Mechanics**: Acquire external Redis locks on order and inventory IDs; schedule Celery countdown tasks for pending expiry.
- **Drawbacks**: Violates the project's minimalist architecture guidelines and approved tech stack (Python 3.12, Django 5.x, PostgreSQL). Introduces split-brain risks, extra operational infrastructure, and failure modes on network partitions.

### Alternative 2: Optimistic Concurrency Control (Version Fields) for Order State
- **Mechanics**: Use `version` fields with `UPDATE ... WHERE version = old_version` on `Order`.
- **Drawbacks**: Under concurrent actions (merchant acceptance vs customer cancellation vs expiry sweep), optimistic locking results in failed requests requiring complex client-side retry logic, rather than clean serialization.

### Alternative 3: Database Pessimistic Row Locking (`select_for_update`), Deterministic Multi-Item Ordering, and Hybrid Expiry Sweep (Selected)
- **Mechanics**:
  1. Wrap all order lifecycle state mutations inside `transaction.atomic()`.
  2. Use `Order.objects.select_for_update()` to strictly serialize state mutations per order.
  3. Sort multi-item inventory lock targets deterministically by `(is_variant, target_id)` per ADR 0001 to prevent deadlocks.
  4. Enforce idempotency via unique checkout tokens / idempotency keys on `(shop_id, idempotency_key)`.
  5. Store UTC `expires_at` with a 15-minute default timeout. Enforce expiry via a dual evaluation model: a lazy gate on any order read/update plus an active periodic background worker.
  6. Map all cancellations and expirations to the canonical `REJECTED` state, capturing business reasons in metadata fields (`rejection_actor`, `rejection_reason_code`).
  7. Decouple WhatsApp notifications via `transaction.on_commit()` or transactional outbox.

## Decision

We adopt **Alternative 3: Pessimistic Row-Level Locking, Deterministic Item Ordering, and Hybrid Expiry Sweep**.

### 1. Transaction Boundaries
- **Order Creation**:
  Inside a single `transaction.atomic()` block:
  1. Validate cart and shop tenant boundary.
  2. Acquire pessimistic row locks on authoritative `InventoryItem` records, sorted deterministically by `(is_variant, target_id)`.
  3. Verify available stock and reserve quantities (`reserve_order_items_stock`).
  4. Capture immutable historical pricing, product snapshots, delivery fee, and address snapshots.
  5. Save `Order` and `OrderItem` records.
  6. Mark cart checked out / cleared.
  7. Queue notifications via `transaction.on_commit()`.
- **Merchant Acceptance & Partial Adjustment**:
  Inside `transaction.atomic()`:
  1. Lock `Order` via `select_for_update()`.
  2. Assert `status == PENDING` and `now < expires_at`.
  3. Acquire locks on associated `InventoryItem` records.
  4. If partial quantity adjusted: call `reduce_and_accept_order_stock`, recalculate line totals and order total.
  5. If full quantity accepted: call `deduct_order_stock`.
  6. Update `order.status = ACCEPTED`, record `accepted_at = now`.
- **Rejection, Cancellation, and Expiry**:
  Inside `transaction.atomic()`:
  1. Lock `Order` via `select_for_update()`.
  2. Assert allowed transition:
     - Customer cancellation: `status == PENDING`, `now < expires_at`, verified session customer.
     - Merchant cancellation: `status == ACCEPTED` and `status != PREPARING`.
     - Merchant rejection: `status == PENDING`.
     - Expiry: `status == PENDING` and `now >= expires_at`.
  3. Acquire locks on associated `InventoryItem` records.
  4. Release reserved stock (`release_order_stock`) if prior status was `PENDING`; restore deducted stock (`restore_cancelled_order_stock`) if prior status was `ACCEPTED`.
  5. Set `status = REJECTED`.
  6. Record audit metadata: `rejection_actor` (`CUSTOMER`, `MERCHANT`, `SYSTEM`), `rejection_reason_code` (`CUSTOMER_CANCELLED`, `MERCHANT_REJECTED`, `TIMEOUT_EXPIRED`), and optional note.

### 2. Locking, Deadlock Prevention, and Isolation
- PostgreSQL default isolation level (`Read Committed`) is standard.
- All state updates acquire `select_for_update()` on the target `Order`.
- All inventory stock adjustments sort target items by `(1 if is_variant else 0, item_id)` prior to lock acquisition, adhering to ADR 0001.

### 3. Idempotency Guarantees
- **Order Placement**:
  - `Order` model enforces a database constraint: `UniqueConstraint(fields=['shop', 'idempotency_key'])`.
  - Retried submissions with the same key return the existing order instance without duplicate reservations.
- **State Transitions**:
  - Repeat idempotent actions (e.g., duplicate "Accept" clicks when already `ACCEPTED`) return `200 OK` with current state.
  - Conflicting actions (e.g. attempting to accept an already `REJECTED` order) reject with `409 Conflict`.

### 4. Pending Expiry Representation and Default Timeout
- **Default Duration**: **15 minutes** (matches AUTH-015 customer access token lifetime and grocery retail SLAs). Configurable per shop (`pending_order_timeout_minutes`, default 15).
- **Database Representation**: Stored as `expires_at` (`DateTimeField`, indexed, UTC) computed at creation: `created_at + timeout_delta`.
- **Evaluation**:
  - **Lazy Evaluation**: Any read or action on a `PENDING` order checks `timezone.now() >= expires_at`. If expired, it triggers the atomic rejection and stock release immediately.
  - **Active Sweep**: A scheduled management command / worker runs periodically (every 60 seconds) to find and expire stale pending orders.

### 5. Retry Semantics
- **Database Contention**: Bounded retry with exponential backoff (up to 3 retries) on transient database lock acquisition / deadlock errors (`40P01`).
- **External Notifications**: Strictly executed post-commit (`transaction.on_commit()`). Notification failures do not roll back order state and retry asynchronously according to notification domain policies.

## Consequences

### Positive
- Strict adherence to canonical business rules: zero additional states (`CANCELLED`/`EXPIRED` eliminated in favor of `REJECTED`).
- Eliminates overselling, race conditions between customer cancellation and merchant acceptance, and database deadlocks.
- Guarantees network retries do not create duplicate purchases or corrupt inventory balances.
- Keeps transactions compact with zero external network calls inside atomic database blocks.
- Fully compatible with Python 3.12, Django 5.x, and PostgreSQL without unapproved external dependencies.

### Trade-offs / Limitations
- `select_for_update()` holds PostgreSQL row locks for the duration of the atomic transaction; all logic within the block must remain strictly database-bound.
- Requires periodic sweep execution (cron or management command) to guarantee prompt inventory release when neither merchant nor customer visits the application.
