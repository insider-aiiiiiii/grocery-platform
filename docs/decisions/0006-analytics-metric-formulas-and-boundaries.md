# ADR 0006: Analytics Metric Formulas, Date/Time Boundaries, and Aggregation Rules

## Status
Approved

## Context
The grocery platform backend is a Django modular monolith serving a multi-tenant grocery ecosystem.
- `Orders` owns transactional purchase facts, immutable historical line item snapshots, lifecycle statuses, and monetary totals.
- `Catalog` owns current products, variants, categories, and shop catalog definitions.
- `Inventory` owns physical stock quantities, reservation tracking, and available stock derivation.
- `Customers` owns shop-scoped customer profiles.
- `Shops` owns shop tenant identity and lifecycle status.
- `Analytics` derives reporting and metrics from approved facts owned by these source domains without becoming a competing source of truth.

Per `.ai/project-context/domains/analytics.md` and repository requirements:
1. Business requirements define broad reporting scopes (Merchant and Super Admin platform scope), but left operational formulas, time boundaries, order-state inclusions, and aggregation rules open.
2. Canonical MVP exclusions must be strictly preserved: no accounting/tax reporting, no arbitrary low-stock threshold, no campaign attribution, no notification delivery metrics, and no cross-shop customer identity merging.

## Problem
1. **Unresolved Metric Formulas**: Without explicit formulas for sales, Average Order Value (AOV), top products, and customer counts, implementations risk calculating metrics inconsistently (e.g., counting cancelled orders towards revenue, or misinterpreting merchant-handled offline payments as audited accounting figures).
2. **Historical Distortion**: Re-reading mutable catalog records (e.g., current prices or names) to calculate historical sales would corrupt historical accuracy when prices or product titles change.
3. **Tenant & Data Privacy Leaks**: Without strict authorization boundaries, cross-shop summaries or filters could expose private merchant sales figures or customer personally identifiable information (PII).
4. **Premature Architecture**: Introducing dedicated OLAP databases, event buses, background aggregation workers, or caching layers before data volumes justify them violates the anti-bloat/Ponytail principles.

## Decision

We establish **Authoritative Operational Metric Formulas, UTC Time Boundaries, and On-Demand Django ORM Aggregation**:

### 1. Authoritative Metric Catalogue & Formulas

| Metric | Source Domain & Model | Formula / Definition | Inclusion / Exclusion Criteria |
| :--- | :--- | :--- | :--- |
| **Total Orders** | `orders.Order` | $\text{COUNT}(\text{Order.id})$ | Orders created within the time window. Exposes full status breakdown (`PENDING`, `ACCEPTED`, `PREPARING`, `READY`, `COMPLETED`, `REJECTED`). |
| **Order Status Distribution** | `orders.Order` | $\text{COUNT}(\text{Order.id}) \text{ grouped by } \text{status}$ | All orders in the time window grouped by each of the 6 canonical states. |
| **Completed Orders** | `orders.Order` | $\text{COUNT}(\text{Order.id})$ where $\text{status} = \text{"COMPLETED"}$ | Only orders in terminal successful completion. |
| **Rejected / Cancelled Orders** | `orders.Order` | $\text{COUNT}(\text{Order.id})$ where $\text{status} = \text{"REJECTED"}$ | Includes merchant rejections, customer pending cancellations, and system timeout expiries (all mapped canonically to `REJECTED`). |
| **Realized Sales (Revenue)** | `orders.Order` | $\sum \text{Order.total\_amount}$ | **Strictly** for orders in $\text{status} = \text{"COMPLETED"}$. Because payments are merchant-handled (offline/cash/direct), only completed orders represent realized operational revenue. Unpaid, pending, and rejected orders are excluded. |
| **Average Order Value (AOV)** | `orders.Order` | $\frac{\sum \text{total\_amount for COMPLETED orders}}{\text{COUNT of COMPLETED orders}}$ | If completed order count is 0, AOV returns `Decimal("0.00")`. Zero-value completed orders (if any) are included in numerator and denominator. Non-completed orders are excluded. |
| **Top-Selling Products** | `orders.OrderItem` | $\sum \text{OrderItem.quantity} \text{ grouped by product}$ | Sourced from `OrderItem` on `COMPLETED` orders. Groups by immutable checkout snapshots (`product_name_snapshot`, `variant_name_snapshot`, `sku_snapshot`) and references `product_id`/`variant_id`. Guarantees historical accuracy if current catalog items change or are deleted. Ranked descending by total quantity sold. |
| **Low-Stock Items** | `inventory.InventoryItem` | `InventoryItem.objects.filter(available_quantity__lte=0)` | Directly reflects Out of Stock items (`available_quantity <= 0.000`). Preserves canon: **strictly no arbitrary low-stock threshold** is invented. |
| **Ordering Customers** | `customers.Customer` & `orders.Order` | $\text{COUNT}(\text{DISTINCT } \text{Order.customer\_id})$ | Customers who placed at least one `COMPLETED` order in the time period. Shop-scoped only. |
| **Returning Customers** | `customers.Customer` & `orders.Order` | Customers with $\ge 2 \text{ COMPLETED orders}$ | Count of distinct shop-specific customers with 2 or more completed orders. Customers are **never merged** across shops even if WhatsApp numbers or names match. |
| **Total Shops (Platform)** | `shops.Shop` | $\text{COUNT}(\text{Shop.id})$ | Super Admin platform metric; count of all registered shops. |
| **Active Shops (Platform)** | `shops.Shop` | $\text{COUNT}(\text{Shop.id})$ where $\text{status} = \text{"ACTIVE"}$ | Super Admin platform metric; count of operational, unsuspended shops. |
| **Platform Gross Volume** | `orders.Order` | $\sum \text{Order.total\_amount}$ for all `COMPLETED` orders across platform | Super Admin platform metric. Aggregated across all shops without leaking customer PII. |

### 2. Date and Time Boundary Rules
- **Canonical Timezone**: All timestamp storage and date-boundary evaluations occur in **UTC** (`USE_TZ = True`, `TIME_ZONE = "UTC"`).
- **Time Field**: Period filtering evaluates against `Order.created_at` (order transaction timestamp). For completed-order sales aggregations, `created_at` within the target window is the standard period anchor.
- **Boundary Range**: Dates are evaluated as inclusive lower bound and inclusive upper bound:
  $$\text{timestamp} \ge \text{start\_date 00:00:00.000000 UTC} \quad \text{and} \quad \text{timestamp} \le \text{end\_date 23:59:59.999999 UTC}$$
- **Standard Supported Period Presets**:
  - `today`: Current calendar day UTC from 00:00:00 to 23:59:59.
  - `yesterday`: Previous calendar day UTC from 00:00:00 to 23:59:59.
  - `this_week`: Current week from Monday 00:00:00 UTC to Sunday 23:59:59 UTC.
  - `this_month`: From the 1st of current month 00:00:00 UTC to end of current month 23:59:59 UTC.
  - `custom`: Client-specified `start_date` and `end_date` in `YYYY-MM-DD` ISO-8601 format. If `start_date > end_date`, validation error is raised.

### 3. Multi-Tenant Authorization & Privacy Boundaries
- **Merchant Reporting**:
  - Strictly tenant-scoped. The shop context is derived directly from the authenticated session (`request.user.merchant.shop`).
  - A client-provided `shop_id` query parameter is **never trusted** as authorization and cannot expand or switch tenant context.
  - Merchants cannot access, view, or compare data from any other shop.
- **Super Admin Platform Reporting**:
  - Accessible exclusively to users with `role == User.Role.SUPER_ADMIN` (verified via `IsSuperAdmin`).
  - Aggregates platform totals across shops.
  - **Privacy Invariant**: Platform analytics strictly omits customer personally identifiable information (PII) such as customer names, WhatsApp phone numbers, and delivery addresses.

### 4. Aggregation Strategy & Anti-Bloat Architecture
- **On-Demand Django ORM Queries**: All metrics are calculated dynamically using database-level aggregations (`QuerySet.aggregate()`, `QuerySet.annotate()`, `Count`, `Sum`).
- **No Premature Caching or Infrastructure**: In strict compliance with YAGNI and anti-bloat guidelines, no external caching layers (Redis), background task queues (Celery), or OLAP data warehouses are introduced. Existing indexed fields (`orders_order_shop_created_idx`, `orders_order_shop_status_idx`) satisfy query efficiency for current scale.

### 5. Preserved Exclusions
The following remain explicitly excluded from the MVP:
1. Accounting-grade financial reporting, tax compliance, or merchant payout settlement.
2. Arbitrary low-stock threshold configurations (only exact available stock and `available_quantity <= 0` out-of-stock reporting are supported).
3. Campaign attribution, click-through, or promotion conversion tracking.
4. Notification delivery status, success ratio, or telecom provider logs.
5. Cross-shop customer identity merging or profiling.
6. Predictive analytics, trend extrapolation, or machine-learning models.

## Consequences

### Positive
- Clear, unambiguous operational definitions for sales, AOV, order distribution, and customer retention.
- Guaranteed historical accuracy through reliance on frozen `OrderItem` snapshot data rather than mutable live catalog records.
- Strict multi-tenant isolation and customer privacy protection baked into query design.
- Minimalist, highly maintainable codebase without extraneous infrastructure or dependencies.

### Negative / Trade-offs
- On-demand calculation relies directly on primary database read queries; if order volumes scale by orders of magnitude in future releases, pre-aggregated tables or read replicas may need to be evaluated with measured telemetry.
