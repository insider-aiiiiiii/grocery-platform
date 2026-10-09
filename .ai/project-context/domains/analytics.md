# Analytics Domain Specification

## 1. Domain Purpose

The Analytics domain owns the business concern of deriving reporting and metrics from approved facts owned by other domains. It supports merchant/shop reporting and platform-level reporting for authorized actors.

Analytics does not own or redefine orders, products, inventory, customers, shops, campaigns, notifications, payments, or accounting. It provides an analytical view of those domains without becoming a competing source of truth.

The product requirements explicitly require analytics at both merchant and platform levels. Exact metrics and calculation rules remain subject to the definitions in this document and later approved decisions.

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
- Platform campaign performance concepts.

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
- Campaign performance if campaign attribution is approved.

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
| Total orders | Orders | Required reporting area | Count qualifying orders under approved scope and order-state rules. |
| Order status distribution | Orders | Required reporting area | Count orders by approved lifecycle state and period. |
| Completed orders | Orders | Required reporting area | Count orders in the approved `COMPLETED` meaning. |
| Rejected orders | Orders | Required reporting area | Count orders in the approved `REJECTED` meaning. |
| Sales / revenue | Orders, with Catalog only for product context | Required area, formula unresolved | Must distinguish order value from accounting revenue and paid value. |
| Average order value | Orders | Required area, formula unresolved | Requires numerator and qualifying-order denominator. |
| Top products | Orders and Catalog | Required reporting area | Requires ranking measure, order-state inclusion, and product identity rules. |
| Customer count | Customers and Orders | Required area, counting method unresolved | Must remain shop-specific and define whether it means registered, known, or ordering customers. |
| Returning customers | Customers and Orders | Possible merchant metric, unresolved | Requires repeat definition and time window. |
| Low-stock information | Inventory | Required merchant visibility concept | Inventory remains authoritative; threshold and status rules are unresolved. |
| Total shops | Shops | Platform reporting area | Requires definition of included shop lifecycle/status states. |
| Active shops | Shops | Platform reporting area, definition unresolved | Must not assume an `ACTIVE` state or activity window. |
| Product performance | Orders and Catalog | Platform/merchant reporting area | Requires units, value, state, and historical product identity rules. |
| Campaign performance | Campaigns and Analytics | Platform reporting area, attribution unresolved | Cannot be calculated without approved exposure/attribution facts. |
| Notification performance | Notifications | Future/conditional | Notifications owns delivery state; Analytics may consume approved facts. |

## 10. Sales, Revenue, and Monetary Metrics

The product uses sales- or revenue-related language but does not approve an accounting definition. The following alternatives remain distinct:

- Gross order value.
- Sum of item totals.
- Completed-order value.
- Accepted-order value.
- Merchant-confirmed paid value.
- Net sales after discounts, refunds, or cancellations.
- Profit or margin.

The MVP payment model is merchant-handled and does not include a centralized online payment gateway. Therefore, Analytics must not treat an order total as a verified payment or accounting revenue amount unless a later business decision defines that relationship.

Before implementation, the business must approve the numerator, qualifying order states, discounts/charges, currency, refunds/cancellations, and whether the result is operational reporting or accounting data.

## 11. Average Order Value

Average Order Value is a derived metric, not a source fact. A possible conceptual formula is:

```text
AOV = qualifying order value / qualifying order count
```

The formula is not finalized until the business defines:

- Which value is used.
- Which order states qualify.
- Whether zero-value orders are included.
- Whether rejected, cancelled, or incomplete orders are excluded.
- Whether the result is calculated per shop, platform, product group, or period.
- How an empty denominator is represented.

Do not implement a formula by assuming that all created orders or all order totals qualify.

## 12. Order-Based Metrics

Orders owns the order lifecycle and historical transaction meaning. Analytics consumes those facts.

The finalized MVP Order lifecycle is:

```text
PENDING → ACCEPTED → PREPARING → READY → COMPLETED
PENDING → REJECTED
```

Customer cancellation while `PENDING` and eligible Merchant cancellation after acceptance use the existing `REJECTED` Order outcome/state; there is no separate `CANCELLED` Order state. Orders also have `PAID` / `UNPAID` status, and inventory effects are defined in the Orders and Inventory specifications. The default pending timeout and its technical expiry representation remain unresolved.

For each Order-based metric, the approved design must specify whether `PENDING`, `ACCEPTED`, `PREPARING`, `READY`, `COMPLETED`, and `REJECTED` contribute. Do not treat cancellation as a separate Order status. Do not assume an expiry status value; pending timeout behavior is approved, but its technical representation is open.

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

Orders owns the historical purchased-item facts; Catalog owns product identity and current catalog metadata. The exact ranking basis is unresolved. It may be units, order count, value, or another approved measure.

Product analytics must define whether reporting uses product-level identity, variant-level identity, shop listing identity, or historical order snapshots. It must not assume that every merchant-created product has a master-catalog identity.

## 15. Customer Analytics

Customer analytics must respect the shop-specific customer model.

Possible concepts include:

- Customers associated with a shop.
- Customers who placed orders in a period.
- Orders per shop-specific customer.
- Returning customers.
- Customer sales contribution.
- New customers in a period.

The exact definitions are unresolved. In particular, the business must define whether a customer count means known customer records, distinct ordering identities, distinct order contacts, or another approved concept.

Analytics must not merge customers across shops merely because their names or WhatsApp numbers match. A WhatsApp number is not a global identity or authorization credential.

## 16. Inventory Analytics

Inventory remains authoritative for stock quantity, stock status, availability, low-stock concepts, and any stock movement history that is later approved.

Merchant analytics may display low-stock or out-of-stock information if the relevant Inventory rules are finalized. The current Inventory specification leaves stock granularity, thresholds, availability derivation, reservation, deduction, and history unresolved.

Analytics must not:

- change inventory quantities
- define low-stock thresholds
- infer stock movement history that Inventory does not record
- replace current inventory status with a stale analytical copy

Historical inventory trends are future or unresolved unless Inventory approves the required facts and retention.

## 17. Campaign Analytics

Campaigns owns campaign identity, configuration, targeting, scheduling, and lifecycle concepts. Analytics may report campaign performance only if Campaigns and the product requirements define the necessary exposure, interaction, attribution, or order-association facts.

Possible metrics such as campaign views, interactions, campaign-associated orders, sales attribution, and conversion are not finalized. Analytics must not infer campaign influence from temporal coincidence or campaign visibility alone.

Campaign analytics must not change campaign configuration, pricing, targeting, or lifecycle.

## 18. Notification Analytics

Notifications owns message creation, channel delivery, delivery status, and failure concepts. Analytics may consume notification facts for reporting if this is approved.

Possible metrics include:

- Notification count.
- Requested, sent, delivered, or failed count.
- Channel usage.
- Event-type frequency.
- Delivery success ratio.

The Notifications specification leaves lifecycle states, provider confirmation, retries, and retention unresolved. Analytics must not equate provider acceptance with delivery or invent delivery metrics from incomplete status information.

## 19. Time-Based Reporting

Time filtering is a business definition, not merely a query parameter. Possible periods include today, yesterday, current week, previous week, current month, previous month, and custom date ranges, but the product does not approve every range.

Each finalized metric must specify:

- Timestamp source, such as order creation or completion time.
- Timezone used for period boundaries.
- Inclusive and exclusive boundary behavior.
- Treatment of future-dated or invalid timestamps.
- Treatment of events outside the reporting retention period.
- Whether the period is based on event time, business date, or another approved field.

Timezone and date-boundary behavior remain unresolved.

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

| Decision | Why unresolved | Impact |
|---|---|---|
| Exact required metric catalogue | Product names reporting areas but not a final list. | Scope and acceptance criteria remain open. |
| Sales/revenue definition | Payment is merchant-handled and accounting meaning is not defined. | Monetary reports cannot be finalized. |
| AOV numerator and denominator | Qualifying value and order states are unresolved. | AOV formula remains open. |
| Order-state inclusion | Orders has a conceptual, incomplete lifecycle. | Counts, sales, and product metrics may differ. |
| Cancellation/refund treatment | These order/payment behaviors are not finalized. | Historical and monetary reporting remain open. |
| Active-shop definition | Shop lifecycle and activity window are unresolved. | Platform shop metrics remain open. |
| Customer-count definition | Customer identity is lightweight and shop-specific. | Customer metrics may count different populations. |
| Returning-customer definition | Repeat window and identity rule are not approved. | Retention metrics remain open. |
| Product ranking basis | Units, order count, value, or another basis is possible. | Top-product reports remain open. |
| Product vs variant grouping | Catalog identity and variant relationships are unresolved. | Product-performance dimensions remain open. |
| Low-stock metric behavior | Inventory threshold and availability rules are unresolved. | Merchant low-stock reporting remains open. |
| Inventory history availability | Inventory does not finalize a historical ledger. | Trend reporting may not be possible. |
| Campaign attribution | Campaign exposure and order association are not defined. | Campaign performance cannot be calculated reliably. |
| Notification analytics | Delivery states and provider confirmation are unresolved. | Delivery metrics remain conditional. |
| Supported time ranges | Product does not approve every period type. | Filtering contract remains open. |
| Timezone and date boundaries | No reporting timezone is selected. | Period totals may differ. |
| Freshness requirement | Real-time versus aggregated behavior is not defined. | Architecture and latency remain open. |
| Retention period | Historical analytics retention is not specified. | Long-term reporting and privacy remain open. |
| Corrections and late-arriving facts | Source correction behavior is not defined. | Aggregates may need recomputation rules. |
| Platform privacy thresholds | Cross-shop aggregate exposure rules are not defined. | Small-group and customer privacy remain open. |
| Export and scheduled-report scope | These are not approved features. | Delivery and background-work requirements remain open. |
| Analytics API contract | No endpoints or response shape are defined. | Implementation cannot begin. |

## 35. Explicit Non-Goals

This specification does not define:

- Final metric formulas that the source documents leave unresolved.
- Accounting or legally reportable financial statements.
- Payment verification or settlement.
- Tax, commission, profit, or margin calculations.
- Customer authentication or global customer identity.
- Order, catalog, inventory, customer, shop, campaign, or notification ownership.
- Campaign targeting or attribution implementation.
- Inventory thresholds or stock algorithms.
- Notification delivery state or provider behavior.
- API endpoints or frontend/dashboard behavior.
- Database schema, materialized views, warehouses, or caches.
- Background processing technology.
- Authentication, authorization, or role implementation.

## 36. Implementation Gate

> The Analytics domain must not be implemented until the metrics required for the target release, their authoritative source facts, formulas, order-state rules, time semantics, freshness expectations, privacy boundaries, and tenant authorization behavior are reviewed and approved.

Implementation must not infer business meaning from metric names or choose infrastructure before reporting requirements justify it. Any approved implementation must preserve source-domain ownership and shop-level isolation.

## 37. Git Workflow

Follow the repository's mandatory task-based workflow before implementation changes:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/define-analytics-domain
```

- Never work directly on `main`.
- Inspect existing changes before acting and do not discard unrelated work.
- Do not use destructive Git commands without explicit approval.
- If a task ID is required but not provided, ask for it before creating a branch.
- Keep analytics changes scoped to the approved task.

## Final Requirement

Create only `.ai/project-context/domains/analytics.md`. Do not modify any other file. Do not implement models, APIs, serializers, views, migrations, materialized views, background jobs, dashboards, frontend components, analytics infrastructure, or unsupported metric behavior. Do not resolve unresolved decisions by assumption.
