# Analytics Domain Specification

## 1. Domain Purpose

The Analytics domain owns the business concern of deriving reporting and metrics from approved facts owned by other domains. It supports merchant/shop reporting and platform-level reporting for authorized actors.

Analytics does not own or redefine orders, products, inventory, customers, shops, campaigns, notifications, payments, or accounting. It provides an analytical view of those domains without becoming a competing source of truth.

This reconciliation approves no new Analytics formulas. Do not define unapproved formulas or retain historical aggregates from permanently deleted Shops unless a separate retention policy is approved.

## 2. Analytics Ownership Boundary

Analytics owns:

- Metric definitions once they are approved.
- Reporting scope and aggregation concepts.
- Derived measures and rankings.
- Analytical filtering and comparison concepts.
- Reporting freshness requirements once approved.
- The interpretation of approved source facts for reporting.

Analytics does not own:

- Order creation, lifecycle, or historical purchase facts.
- Product, variant, category, or catalog identity.
- Inventory quantity, availability, or stock adjustments.
- Customer identity or contact information.
- Shop identity, membership, or authorization.
- Campaign configuration, targeting, or lifecycle.
- Notification delivery or provider status.

## 3. Source-Domain Ownership

The conceptual ownership boundary is:

```text
Orders
    owns order facts and historical purchased-item facts

Catalog
    owns product, variant, category, and shop-catalog facts

Inventory
    owns stock and availability facts

Customers
    owns shop-specific customer identity facts

Shops
    owns shop identity and tenant context

Campaigns
    owns campaign configuration and targeting concepts

Notifications
    owns notification and delivery facts

Analytics
    derives approved reporting metrics from those facts
```

Analytics must not reconstruct a historical transaction from mutable current Catalog data when the Orders domain provides the historical meaning of the purchase.

## 4. Reporting Actors and Scopes

The product identifies two reporting audiences.

### Merchant / shop scope

A merchant may view analytics for an authorized shop. Merchant analytics are tenant-scoped and must not expose another shop's data.

### Super Admin / platform scope

A Super Admin may view platform-level analytics according to the final authorization design. Platform analytics may aggregate across shops only for an actor with approved platform-level authority.

### Scope hierarchy

The conceptual hierarchy is:

```text
Platform
    ↓
Shop
    ↓
Product / order / customer / campaign facts
```

A shop filter is a reporting scope, not an authorization mechanism. Authorization must independently establish which shop or shops the actor may access.

## 5. Analytics Scope Classification

### Required by current product requirements

The product explicitly supports the following broad reporting areas:

- Merchant/shop analytics.
- Platform analytics.
- Merchant orders and order-status-related reporting.
- Merchant sales- or revenue-related reporting.
- Merchant top-selling products.
- Merchant low-stock information.
- Merchant rejected and completed order visibility.
- Merchant average-order-value-related reporting.
- Merchant customer-related reporting.
- Platform shop reporting, including total and active shops as concepts.
- Platform order reporting.
- Platform sales- or revenue-related reporting.
- Platform shop and product performance concepts.
- Platform customer-related reporting.

These requirements establish reporting areas, not final formulas or guarantees that every example is an implemented metric.

### Future or conditional

The following may be considered later if explicitly approved:

- Notification delivery analytics.
- Campaign views, interactions, attribution, or conversion.
- Historical inventory trends and stock movement reporting.
- Scheduled reports and exports.
- Cross-period comparisons and benchmarking.
- Customer cohorts or segmentation.
- Product and variant trend analysis.
- Forecasting, recommendations, or predictive metrics.

### Not currently supported

The current source of truth does not approve by default:

- Accounting-grade financial reporting.
- Tax reporting.
- Merchant settlement or commission reporting.
- Payment-gateway reporting.
- Profit, margin, cost-of-goods, or expense reporting.
- Cross-shop customer identity merging.
- Predictive analytics or machine-learning models.
- A separate data warehouse, OLAP system, or analytics microservice.

## 6. Merchant Analytics

Merchant analytics may provide reporting for the merchant's authorized shop, including:

- Total orders.
- Order status distribution.
- Rejected and completed order counts.
- Sales- or revenue-related metrics once defined.
- Average order value once defined.
- Top-selling products.
- Low-stock information sourced from Inventory.
- Customer-related activity within the shop.

The source documents do not finalize every metric, display, filter, timeframe, or freshness requirement. No dashboard or UI behavior is defined here.

## 7. Platform Analytics

Platform analytics may provide Super Admin reporting for approved platform operations, including:

- Total shops.
- Active shops, once shop activity/status definitions are approved.
- Platform order counts and status distribution.
- Platform sales- or revenue-related metrics once defined.
- Shop performance comparisons or summaries.
- Product performance summaries.
- Customer-related metrics within approved privacy limits.

A metric appearing in this list is not permission to invent a formula. The source domain, scope, time period, inclusion rules, and aggregation behavior must be approved for each metric.

## 8. Metric Definition Principles

Every finalized metric must define:

- Its business meaning.
- Its authoritative source domain.
- Its reporting scope.
- Its unit and monetary interpretation, where applicable.
- Its order-state inclusion rules, where applicable.
- Its time field and timezone.
- Its filters and grouping dimensions.
- Its treatment of missing, deleted, rejected, or changed source facts.
- Its freshness expectation.

Terms such as `sales`, `revenue`, `active shop`, `customer`, and `top product` must not be treated as self-defining.

## 9. Metric Catalogue and Current Status

| Metric area | Conceptual source | Current status | Definition boundary |
|---|---|---|---|
| Total orders | Orders | Finalized for MVP (ADR 0006) | Count qualifying orders in period with full status distribution (`PENDING`, `ACCEPTED`, `PREPARING`, `READY`, `COMPLETED`, `REJECTED`). |
| Order status distribution | Orders | Finalized for MVP (ADR 0006) | Count orders grouped by approved lifecycle status within the period. |
| Completed orders | Orders | Finalized for MVP (ADR 0006) | Count orders in terminal successful `COMPLETED` state. |
| Rejected orders | Orders | Finalized for MVP (ADR 0006) | Count orders in `REJECTED` state (includes merchant rejections, customer pending cancellations, and expiry timeouts). |
| Sales / revenue | Orders | Finalized for MVP (ADR 0006) | Operational realized sales: $\sum \text{Order.total\_amount}$ for orders in `COMPLETED` status. Unpaid/rejected/pending excluded. |
| Average order value | Orders | Finalized for MVP (ADR 0006) | $\sum \text{total\_amount for COMPLETED orders} / \text{COUNT of COMPLETED orders}$. Returns `0.00` if count is zero. |
| Top products | Orders and Catalog | Finalized for MVP (ADR 0006) | Sourced from `OrderItem` on `COMPLETED` orders. Ranked by total quantity sold ($\sum \text{quantity}$), grouped by snapshot product/variant identifiers. |
| Customer count | Customers and Orders | Finalized for MVP (ADR 0006) | Distinct `customer_id` count on `COMPLETED` orders in the period. Strictly shop-scoped. |
| Returning customers | Customers and Orders | Finalized for MVP (ADR 0006) | Distinct shop-specific customers having $\ge 2$ `COMPLETED` orders. |
| Low-stock information | Inventory | Finalized for MVP (ADR 0006) | Out of stock items (`available_quantity <= 0.000`). Strictly no arbitrary low-stock threshold. |
| Total shops | Shops | Finalized for MVP (ADR 0006) | Platform reporting area: count of all registered shops. |
| Active shops | Shops | Finalized for MVP (ADR 0006) | Platform reporting area: count of shops with `status == "ACTIVE"`. |
| Product performance | Orders and Catalog | Finalized for MVP (ADR 0006) | Units sold and revenue contribution from completed order items. |
| Campaign performance | Campaigns and Analytics | Excluded from MVP | Any future attribution and retention requires separate approval. |
| Notification performance | Notifications | Excluded from MVP | Delivery analytics require separate approval; retention must be decided before Notifications implementation. |

## 10. Sales, Revenue, and Monetary Metrics

The grocery platform payment model is merchant-handled (offline, cash-on-delivery, or direct merchant settlement) without a centralized online payment gateway. Therefore, Analytics defines **Operational Realized Sales** rather than accounting-grade audited revenue:

- **Operational Realized Sales**:
  $$\text{Realized Sales} = \sum \text{Order.total\_amount} \quad \text{where } \text{status} = \text{"COMPLETED"}$$
- **Order States Excluded**: Unpaid orders, pending orders, and rejected/cancelled orders are strictly excluded from sales metrics.
- **Delivery Charges**: `total_amount` encapsulates both item subtotals and preserved delivery charges snapshot.
- **Currency & Precision**: Preserves standard 2-decimal monetary currency formatting (`Decimal("0.01")`).
- **Accounting Disclaimer**: Analytics operational reporting does not constitute accounting-grade revenue, tax reporting, or merchant settlement.

## 11. Average Order Value

Average Order Value (AOV) is finalized as the average realized value of completed orders:

$$\text{AOV} = \frac{\sum_{\text{status} = \text{COMPLETED}} \text{Order.total\_amount}}{\text{COUNT}(\text{Order.id})_{\text{status} = \text{COMPLETED}}}$$

- **Zero-Order Handling**: If the count of completed orders within the period is zero, AOV evaluates to `Decimal("0.00")`.
- **Inclusion Rules**: Only `COMPLETED` orders qualify for both numerator and denominator. Rejected, cancelled, pending, and in-progress orders are excluded. Zero-value completed orders (if any) are included.
- **Scope**: Computed per shop (for merchant analytics) and across all shops (for Super Admin platform analytics).

## 12. Order-Based Metrics

Orders owns the order lifecycle and historical transaction meaning. Analytics consumes those facts.

The finalized MVP Order lifecycle is:

```text
PENDING → ACCEPTED → PREPARING → READY → COMPLETED
PENDING → REJECTED
```

Customer cancellation while `PENDING`, eligible Merchant cancellation after acceptance, and pending timeout expiry use the existing `REJECTED` Order outcome/state; there is no separate `CANCELLED` or `EXPIRED` Order state. Orders also have `PAID` / `UNPAID` status, and inventory effects are defined in the Orders and Inventory specifications. The default pending timeout and expiry time/reason representation remain unresolved.

For each Order-based metric, the approved design must specify whether `PENDING`, `ACCEPTED`, `PREPARING`, `READY`, `COMPLETED`, and `REJECTED` contribute. Do not treat cancellation or expiry as separate Order statuses. Pending expiry uses `REJECTED`; its time/reason representation remains open.

## 13. Historical Accuracy

Analytics must preserve the historical meaning of completed transactions. If a current product name, price, category, variant, availability, or customer profile changes, past order reporting must not silently change because Analytics re-read mutable current data.

The Orders domain owns the historical purchase representation. Analytics may combine historical order-item facts with Catalog metadata only where the relationship is approved and does not rewrite the transaction's historical meaning.

Analytics must not calculate historical sales by multiplying current price by historical quantity when the Orders domain has a different historical purchase value.

## 14. Product Analytics

Product analytics may conceptually include:

- Units sold.
- Orders containing a product or variant.
- Product sales value.
- Top-selling products.
- Product performance by period.
- Variant performance where variant identity is approved.

Orders owns the historical purchased-item facts; Catalog owns product identity and current catalog metadata. Per ADR 0006:
- **Top-Selling Products**: Ranked by total quantity sold ($\sum \text{OrderItem.quantity}$) on orders in `COMPLETED` status.
- **Historical Snapshot Preservation**: Grouping evaluates immutable checkout snapshots (`product_name_snapshot`, `variant_name_snapshot`, `sku_snapshot`) alongside `product_id`/`variant_id`. If a live catalog product is renamed or deleted, past analytics figures remain immutable and historically accurate.

## 15. Customer Analytics

Customer analytics respects the shop-specific customer model and strict tenant boundaries:

- **Ordering Customers**: Count of distinct `customer_id` values on orders in `COMPLETED` status within the period.
- **Returning Customers**: Count of distinct shop-specific customers having $\ge 2$ lifetime `COMPLETED` orders within the shop.
- **No Cross-Shop Merging**: Customers are **never merged** across shops even if their names or WhatsApp numbers match. A WhatsApp number is a shop-scoped contact attribute, not a global identifier.

## 16. Inventory Analytics

Inventory remains authoritative for stock quantity, reservation state, and stock availability:

- **Low-Stock Visibility**: Defined strictly as **Out of Stock** items (`available_quantity <= 0.000` or `is_in_stock = False`).
- **No Arbitrary Thresholds**: In strict accordance with canonical MVP rules, **no arbitrary low-stock threshold** (such as `< 5` or `< 10`) is invented or configured.
- **Stock Integrity**: Analytics does not mutate stock, infer unrecorded movements, or store stale copies of live inventory.

## 17. Campaign Analytics (Excluded from MVP)

Campaign attribution and campaign performance analytics are excluded from the MVP. Campaigns owns campaign identity, configuration, targeting, scheduling, and lifecycle concepts. Do not add attribution formulas or retain campaign aggregates without separate approval.

Possible metrics such as campaign views, interactions, campaign-associated orders, sales attribution, and conversion are not finalized. Analytics must not infer campaign influence from temporal coincidence or campaign visibility alone.

Campaign analytics must not change campaign configuration, pricing, targeting, or lifecycle.

## 18. Notification Analytics (Excluded from MVP)

Notification delivery analytics are excluded from the MVP. Notifications owns message creation, channel delivery, delivery status, and failure concepts. Any later analytics use requires separate approval and a notification-history retention decision before Notifications is implemented.

Possible metrics include:

- Notification count.
- Requested, sent, delivered, or failed count.
- Channel usage.
- Event-type frequency.
- Delivery success ratio.

The Notifications specification leaves lifecycle states, provider confirmation, retries, and retention unresolved. Analytics must not equate provider acceptance with delivery or invent delivery metrics from incomplete status information. Do not retain historical aggregates from a permanently deleted Shop unless a separate approved retention policy explicitly permits it.

## 19. Time-Based Reporting

Time-based filtering is finalized per ADR 0006:

- **Canonical Timezone**: All timestamp comparisons and date boundary evaluations are performed in **UTC** (`USE_TZ = True`, `TIME_ZONE = "UTC"`).
- **Timestamp Anchor**: Standard date filtering evaluates against `Order.created_at`.
- **Inclusive Range**: Period boundaries are inclusive:
  $$\text{timestamp} \ge \text{start\_date 00:00:00.000000 UTC} \quad \text{and} \quad \text{timestamp} \le \text{end\_date 23:59:59.999999 UTC}$$
- **Supported Filter Presets**:
  - `today`: Current calendar day UTC (00:00:00 to 23:59:59).
  - `yesterday`: Previous calendar day UTC (00:00:00 to 23:59:59).
  - `this_week`: Current week from Monday 00:00:00 UTC to Sunday 23:59:59 UTC.
  - `this_month`: 1st of current month 00:00:00 UTC to end of current month 23:59:59 UTC.
  - `custom`: Client-specified `start_date` and `end_date` in `YYYY-MM-DD` ISO-8601 format (requires `start_date <= end_date`).

## 20. Filters and Dimensions

Potential reporting dimensions include:

- Shop.
- Order status.
- Product or variant.
- Category, if Catalog defines the relationship.
- Customer, within a shop and approved privacy scope.
- Campaign, if attribution exists.
- Notification channel or event type, if approved.
- Time period.

Only approved dimensions may be exposed. A filter must not become an authorization bypass, and a client-supplied shop identifier must not expand the actor's tenant scope.

## 21. Aggregation Concepts

Analytics distinguishes source facts from derived results:

```text
Order total
    = source business fact owned by Orders

Total orders
    = derived count over qualifying Orders facts

Units sold
    = derived aggregation of qualifying order items

Average Order Value
    = derived measure over approved order values and counts

Top products
    = derived ranking using an approved measure
```

A derived value must document its source facts, formula, scope, time period, inclusion rules, and freshness. Analytics must not persist a derived result as authoritative merely because it is convenient to query.

## 22. Real-Time vs Aggregated Reporting

The product does not define whether metrics must be real-time, near-real-time, or periodically refreshed.

Possible strategies include:

- Direct calculation from transactional domain data.
- Precomputed aggregation.
- A hybrid approach.

The choice requires evidence about data volume, query complexity, acceptable latency, freshness, reporting frequency, and operational cost. This specification does not select a strategy, materialized view, cache, warehouse, job system, or other infrastructure.

## 23. Performance Considerations

Analytics queries may scan or aggregate more data than ordinary transactional requests. Future implementation should consider:

- Actual query patterns and dataset size.
- Bounded date ranges and pagination where appropriate.
- Avoiding N+1 access patterns.
- Appropriate filtering before aggregation.
- Shop-scoped query plans.
- Expensive platform-wide aggregation.
- Freshness and repeated-query behavior.
- Whether a derived result is justified by measured need.

Do not add indexes, denormalized fields, caches, materialized views, partitions, background jobs, data warehouses, or OLAP systems without a documented requirement and performance evidence.

## 24. Caching and Derived Data

Cached or precomputed analytics are still sensitive to tenant boundaries and freshness rules. A cache key, aggregate, export, or report must not allow one merchant to receive another shop's data.

Before storing derived data, the implementation design must define:

- Authoritative source facts.
- Refresh or invalidation behavior.
- Scope and authorization.
- Historical correction behavior.
- Handling of source deletion or deactivation.
- Acceptable staleness.

No cache, materialized view, or denormalized analytics store is approved by this specification.

## 25. Tenant Isolation

Analytics is a security-sensitive tenant boundary.

```text
Merchant
    ↓
Authorized shop context
    ↓
Shop analytics only
```

A merchant must never access another shop's analytics through:

- list or detail queries
- direct object identifiers
- shop filters
- grouped or cross-shop totals
- cached results
- exports or scheduled reports
- management commands
- background processing
- administrative interfaces
- related product, customer, order, campaign, inventory, or notification data

Platform-wide aggregation is allowed only for an authorized Super Admin or another explicitly approved platform actor. Client-provided `shop_id` is a resource reference, never proof of authorization.

## 26. Platform Aggregation and Privacy

Platform analytics may aggregate across shops only within approved platform authorization. Aggregate reporting must still consider whether small groups, customer dimensions, order details, or exported data could expose private tenant or customer information.

The product does not define a minimum aggregation threshold, anonymization policy, or platform-report export policy. These remain unresolved. Analytics must not expose customer contact information or merchant-private details merely because a platform-level aggregate is requested.

## 27. Exports, Scheduled Reports, and Administrative Operations

The product does not currently finalize exports, scheduled reports, dashboards, or management commands. If introduced later, each must define:

- Actor and authorization.
- Shop or platform scope.
- Included metrics and time period.
- Freshness and retention.
- Sensitive fields and privacy handling.
- Delivery channel, if any.
- Failure and retry behavior.

Background jobs and management commands must resolve trusted tenant context and must not use an unverified client-provided shop identifier.

## 28. Security and Sensitive Data

Analytics may expose commercially and personally sensitive information, including order values, product performance, customer activity, and shop comparisons.

Required principles include:

- Enforce authorization server-side.
- Scope merchant reports to authorized shops.
- Do not expose customer names, WhatsApp numbers, addresses, or contact details unless separately approved and necessary.
- Do not expose another shop's data through grouping, totals, cache keys, exports, or error responses.
- Do not treat identifiers as authorization.
- Do not log sensitive report data unnecessarily.
- Protect credentials and provider secrets if future integrations are added.
- Apply approved retention and deletion rules once defined.

## 29. Historical Corrections and Source Changes

Analytics must define how corrections to source facts affect reports. Relevant unresolved cases include:

- An order is corrected after initial reporting.
- A product or variant is renamed or deactivated.
- A customer record is changed or removed.
- A shop changes status.
- A campaign is edited or ended.
- A notification delivery status arrives later from a provider.

The authoritative domain and correction policy must be identified for each metric. Analytics must not silently mutate historical meaning or hide source corrections.

## 30. Business Invariants

The following invariants are supported by the approved source of truth:

- Analytics derives reporting from domain-owned facts and does not replace their ownership.
- Merchant analytics are restricted to the merchant's authorized shop or shops.
- Platform-wide analytics require platform-level authorization.
- A client-provided `shop_id` is never sufficient authorization.
- Analytics does not change orders, products, inventory, customers, shops, campaigns, or notifications.
- Customer identity remains shop-specific and must not be merged across shops by assumption.
- Historical order analytics must preserve the historical purchase meaning defined by Orders.
- Low-stock and inventory status remain authoritative in Inventory.
- Campaign configuration and lifecycle remain authoritative in Campaigns.
- Notification delivery status remains authoritative in Notifications.
- A metric is not finalized until its source, formula, scope, time semantics, and inclusion rules are defined.
- Derived data must not silently become a competing source of truth.

## 31. Cross-Domain Responsibilities

| Concern | Owning domain | Analytics responsibility |
|---|---|---|
| Shop identity and lifecycle | Shops | Report approved shop facts and scope platform reports. |
| Merchant access | Users & Merchant Accounts | Supply authorization context; Analytics must enforce it. |
| Product and variant identity | Catalog | Use approved product dimensions without changing Catalog data. |
| Stock and low-stock state | Inventory | Consume approved inventory facts; do not define thresholds or mutate stock. |
| Customer identity | Customers | Use shop-specific customer facts without cross-shop merging. |
| Cart state | Cart | Generally outside Analytics unless an explicit requirement is approved. |
| Order transaction and lifecycle | Orders | Source order, state, historical item, and value facts. |
| Campaign configuration | Campaigns | Consume approved campaign facts and attribution evidence. |
| Notification delivery | Notifications | Consume approved delivery facts; do not define delivery state. |
| Reporting and derived metrics | Analytics | Own formulas, aggregation concepts, scope, and reporting behavior once approved. |

## 32. Implementation Constraints

Do not implement as part of this specification:

- Django models or schema.
- Migrations.
- Materialized views.
- Analytics tables or denormalized stores.
- APIs, serializers, views, or permissions.
- Dashboards or frontend components.
- Background jobs, schedulers, queues, or event buses.
- Data warehouses or OLAP infrastructure.
- Caches or exports.
- Accounting, payment, settlement, tax, profit, or commission logic.
- Predictive or machine-learning analytics.

When implementation begins, it must use the approved source-of-truth hierarchy and must not resolve open business decisions through code.

## 33. Testing and Validation Requirements

Once Analytics behavior is finalized and implemented, tests should cover:

- Metric formulas and order-state inclusion.
- Time boundaries, timezone behavior, and empty periods.
- Historical order-price and product-identity accuracy.
- Shop-scoped merchant reporting.
- Direct-ID and filter-based cross-tenant access attempts.
- Platform-only access to cross-shop aggregation.
- Cache, export, scheduled, and background scope where those features exist.
- Missing, corrected, rejected, or later-updated source facts.
- Performance risks such as unbounded aggregation and repeated queries.

No tests or implementation are created by this documentation task.

## 34. Unresolved Decisions

The following decisions require explicit product, domain, or architecture approval:

| Decision | Status / Resolution | Impact |
|---|---|---|
| Exact required metric catalogue | Finalized in ADR 0006 | Total Orders, Distribution, Sales, AOV, Top Products, Low Stock, Customer metrics approved. |
| Sales/revenue definition | Finalized in ADR 0006 | Realized Sales = $\sum \text{total\_amount}$ for `COMPLETED` orders. Operational only. |
| AOV numerator and denominator | Finalized in ADR 0006 | $\sum \text{total\_amount for COMPLETED} / \text{COUNT}(\text{COMPLETED})$. Evaluates to `0.00` if count is zero. |
| Order-state inclusion | Finalized in ADR 0006 | All 6 canonical states tracked; monetary/sales metrics strictly require `COMPLETED`. |
| Cancellation/refund treatment | Finalized in ADR 0006 | Rejections/cancellations mapped to `REJECTED`; excluded from sales and AOV metrics. |
| Active-shop definition | Finalized in ADR 0006 | Platform metric counts shops with `status == "ACTIVE"`. |
| Customer-count definition | Finalized in ADR 0006 | Distinct `customer_id` on `COMPLETED` orders within the period. Strictly shop-scoped. |
| Returning-customer definition | Finalized in ADR 0006 | Distinct shop-specific customers with $\ge 2$ lifetime `COMPLETED` orders. |
| Product ranking basis | Finalized in ADR 0006 | Top products ranked by $\sum \text{OrderItem.quantity}$ on `COMPLETED` orders. |
| Product vs variant grouping | Finalized in ADR 0006 | Groups by immutable checkout snapshots (`product_name_snapshot`, `variant_name_snapshot`, `sku_snapshot`). |
| Low-stock metric behavior | Finalized in ADR 0006 | Sourced from `InventoryItem` with `available_quantity <= 0` (Out of Stock). No arbitrary threshold. |
| Supported time ranges | Finalized in ADR 0006 | `today`, `yesterday`, `this_week`, `this_month`, and ISO-8601 `custom` range. |
| Timezone and date boundaries | Finalized in ADR 0006 | Standardized to UTC (`USE_TZ = True`); inclusive boundaries `[start 00:00:00, end 23:59:59.999999]`. |
| Platform privacy thresholds | Finalized in ADR 0006 | Platform-wide aggregation strictly omits customer PII (names, phone numbers, addresses). |
| Analytics API contract | Next Step | Ready for implementation in dedicated task branches under approved task IDs. |
| Campaign attribution | Excluded from MVP | Preserved as non-goal for MVP. |
| Notification analytics | Excluded from MVP | Preserved as non-goal for MVP. |
| Accounting/Tax reporting | Excluded from MVP | Preserved as non-goal for MVP. |
| Predictive / ML models | Excluded from MVP | Preserved as non-goal for MVP. |

## 35. Explicit Non-Goals

This specification does not define:

- Accounting or legally reportable financial statements.
- Payment verification or settlement.
- Tax, commission, profit, or margin calculations.
- Customer authentication or global customer identity.
- Order, catalog, inventory, customer, shop, campaign, or notification ownership.
- Campaign targeting or attribution implementation.
- Arbitrary inventory low-stock thresholds or stock prediction algorithms.
- Notification delivery state or provider behavior.
- Database schema, materialized views, warehouses, or caches.
- Background processing technology.
- Authentication, authorization, or role implementation.

## 36. Implementation Gate

> Core operational analytics formulas, source facts, order-state rules, date/time boundaries, aggregation principles, privacy boundaries, and tenant authorization are **finalized under ADR 0006**.

Implementation of the Analytics API endpoints and calculation services can proceed under approved task branches adhering to the agreed formulas, multi-tenant isolation, and minimal Django ORM aggregation design.

## 37. Git Workflow

Follow the repository's mandatory task-based workflow before implementation changes:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/<task-description>
```

- Never work directly on `main`.
- Inspect existing changes before acting and do not discard unrelated work.
- Do not use destructive Git commands without explicit approval.
- If a task ID is required but not provided, ask for it before creating a branch.
- Keep analytics changes scoped to the approved task.
