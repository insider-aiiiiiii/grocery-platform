# Grocery Platform Product Context

## Purpose and Scope

This document is the canonical product and business-context reference for the Grocery Platform backend. It describes expected product behavior for human developers and AI coding agents. It does not define final database tables, Django models, API endpoints, authentication, permissions, infrastructure, deployment, or third-party providers. Those decisions belong in the appropriate architecture, domain, API, or implementation documentation.

The product is a multi-tenant grocery-store platform connecting grocery shops and merchants with customers, with a centralized Super Admin platform for participating shops, a master catalog, campaigns, and analytics. Its three primary actors are:

1. Super Admin
2. Merchant / Shopkeeper
3. Customer

The backend is in the foundation and architecture stage. Domain models and workflows should not be assumed finalized unless documented elsewhere.

## 1. Super Admin

The Super Admin manages the overall platform.

### Shop Management

The Super Admin can onboard shops, review merchant applications, approve or reject applications, create shops directly, and manage shop and platform status. The exact onboarding implementation and approval workflow belong in the Shop domain specification.

### Master Catalog

The Super Admin manages the platform Master Catalog, a reusable product library. Merchants may select Master Products for their independent Shop Catalogs. Master Catalog data does not control or automatically synchronize with existing Shop Products.

### Merchant-Created Products

A Merchant may create and sell a product directly in their Shop Catalog without Super Admin approval. Super Admin may view its information on the dashboard and may promote it to the Master Catalog. Promotion makes it available to other Merchants but does not automatically link or change the originating Shop Product. See the Catalog domain specification for the finalized independence rules.

### Campaigns and Advertisements

The Super Admin can create campaigns or advertisements displayed across all shops or selected shops. A campaign may target one or more shops. Campaign data, targeting rules, scheduling, and presentation behavior will be defined later.

### Analytics

Platform-level analytics are expected eventually and may include total and active shops, orders, sales- or revenue-related metrics, shop and product performance, customer-related metrics, and campaign performance. Metric definitions will be finalized separately.

## 2. Merchant / Shopkeeper

A merchant operates a grocery shop on the platform and uses an ERP-style web interface. The merchant should be able to:

- View and manage shop profile information.
- Manage the shop catalog, products, and product variants.
- Manage prices, stock / inventory, availability, product status, and other shop-specific product configuration.
- View incoming orders and review their details.
- Accept or reject orders and manage order fulfillment status.
- View shop analytics.
- Receive order-related notifications through WhatsApp.

The merchant is responsible for evaluating an order before accepting or rejecting it. In the initial product scope, order acceptance and rejection happen through the merchant ERP. WhatsApp is primarily a notification and communication channel; merchants do not need to accept or reject orders directly through WhatsApp.

## 3. Customer Entry

The primary customer entry point is scanning a shop-specific QR code. The customer should reach that shop's experience without having to search for the shop.

## 4. Customer Catalog Experience

After scanning a shop's QR code, a customer should see only products available for that shop, not another shop's catalog through the same shop-specific flow. The customer should be able to browse categories and products, view product details, select variants and quantities, add products to a cart, modify cart quantities, remove products, and proceed to checkout.

## 5. Product Variants

Products may have multiple variants, for example milk in 500 ml, 1 L, or 2 L sizes, or rice in 1 kg, 5 kg, or 10 kg sizes. The product and variant data model will be defined in the Catalog domain specification.

## 6. Merchant Catalog

Each Merchant fully controls their independent Shop Catalog and can use products from the platform Master Catalog or create products directly. Shop-specific information includes product details, variants, pricing, categories, brands, custom attributes, images, visibility, and manual availability. Each Merchant controls their own pricing and inventory. The same Master Product may have different selling prices in different Shops; Master Catalog values do not dictate or automatically synchronize into Shop Products.

For example, a master product such as Amul Milk 1 L may be sold at ₹65 by Shop A, ₹68 by Shop B, and ₹63 by Shop C.

## 7. Merchant-Created Products

A Merchant may use a product that does not currently exist in the Master Catalog, such as a local homemade product. It remains in that Merchant's Shop Catalog without review or approval. Super Admin may later promote it into the Master Catalog without changing the original Shop Product.

## 8. Customer Checkout

Customers do not need to register or log in before placing an order. At checkout, a customer provides their name and WhatsApp number, and provides an address when choosing home delivery.

The customer chooses one of these fulfillment methods:

- Pickup
- Home delivery

Address information is required for delivery. Address validation and delivery-zone rules will be defined later.

## 9. Repeat Ordering

Repeat ordering should be convenient without requiring a traditional customer account. The platform may maintain a lightweight customer identity associated with a specific shop. Conceptually:

```text
Shop
  ↓
Shop-specific customer
  ↓
Customer information
  ↓
Order history
```

Customer Order history is available within the relevant Shop/customer context using the customer's WhatsApp number. OTP is not required for this MVP decision, and Customer login is not introduced. Minimize exposed customer information. Previously provided name or address may be reused or pre-filled according to Customer-domain rules.

## 10. Orders

A customer creates an order from their cart. The merchant reviews the order before accepting it. The approved MVP lifecycle is:

```text
PENDING
   ↓
ACCEPTED
   ↓
PREPARING
   ↓
READY
   ↓
COMPLETED
```

An order may alternatively be rejected:

```text
PENDING
   ↓
REJECTED
```

`PENDING` Orders expire after a configured timeout; its default value remains a configuration/technical decision. Customer cancellation is allowed while `PENDING`; Merchant cancellation is allowed after acceptance only before `PREPARING`. Rejection and cancellation use the existing `REJECTED` outcome/state, with no separate `CANCELLED` state, and those Orders cannot be reopened. Rejection reasons are optional. The Merchant manually reduces fulfillable quantities when stock is insufficient, the Customer is notified, and the Order reflects the adjusted quantity.

Checkout uses the latest Catalog price. An Order preserves its historical purchase price and delivery charge; Merchant-approved quantity reductions before acceptance recalculate the Order total. The Merchant controls the effect of a delivery-charge change on an existing or pending Order. No tax calculation applies in MVP unless explicitly documented elsewhere, and no discount engine is introduced unless Campaigns later defines one.

Order creation reserves stock; acceptance deducts it; rejection and pending Customer cancellation release it; eligible Merchant cancellation restores/releases it. See the Orders and Inventory specifications for these rules.

## 11. Pickup and Home Delivery

Customers choose `PICKUP` or `DELIVERY` during checkout. Home Delivery requires an address; the Customer may choose a saved address or enter a new one. Pickup does not require an address. The Merchant marks both Pickup and Home Delivery Orders `COMPLETED`. The initial product does not require a centralized delivery-partner system. Delivery partners, tracking, delivery zones, and delivery assignment, if introduced later, will be defined separately.

## 12. Payments

Payment is Merchant-managed. Orders have `PAID` / `UNPAID` status, and only the Merchant can update payment status. The Merchant decides per Order whether payment is required before acceptance. An `UNPAID` Order may be accepted and prepared but cannot be marked `COMPLETED` until it becomes `PAID`. There is no centralized payment gateway or centralized refund workflow in MVP.

## 13. WhatsApp

WhatsApp is an important communication channel used initially for notifications and acknowledgements.

Customer notifications may include an order-received message with the order number, total, and status; an order-accepted message; and other relevant order-status notifications introduced later.

Merchant notifications may include a new-order message with the order number, customer information, items, and total. The merchant reviews and accepts or rejects the order in the ERP, not through WhatsApp in the current scope.

The WhatsApp provider and API architecture will be defined later.

## 14. Shop QR Code

Each shop has a shop-specific QR code that identifies the shop and leads to its shop-specific public URL. A QR code represents a shop, not a table or an individual product. Customers should not have to manually search for the shop after scanning the QR code.

Conceptually:

```text
Shop QR
   ↓
Shop-specific public URL
   ↓
Shop catalog
   ↓
Customer ordering
```

The exact URL structure, QR generation mechanism, security, and implementation will be defined later.

## 15. Merchant Onboarding

Two onboarding paths are supported conceptually.

**Super Admin creates a merchant and shop:**

```text
Super Admin
     ↓
Create Shop
     ↓
Create Merchant
     ↓
Merchant access
```

**Merchant applies:**

```text
Merchant
     ↓
Application
     ↓
Super Admin review
     ↓
Approve / Reject
     ↓
Merchant access
```

Onboarding fields, approval workflow, statuses, and account activation behavior will be defined in the Shop domain specification.

## 16. Merchant Accounts

For the initial product, a merchant / shop may use one shared credential usable by approximately two or three people within the shop. The backend architecture should not prevent future support for individual users and shop-level roles. Authentication and membership architecture are intentionally not finalized. Do not implement assumptions based solely on this section.

## 17. Shop Isolation

Each merchant operates in their own shop context. Conceptually, each shop has its own catalog, inventory, customers, orders, and analytics. Merchant users must only access data belonging to shops they are authorized to manage. The Super Admin has platform-level access. The technical multi-tenancy implementation will be defined separately.

## 18. Analytics

Analytics are required at both merchant and platform levels.

Merchant analytics may initially include orders, sales- or revenue-related metrics, top-selling products, low-stock information, rejected and completed orders, average order value, and customer-related metrics.

Super Admin analytics may initially include total and active shops, platform orders, platform sales- or revenue-related metrics, shop and product performance, customer-related metrics, and campaign performance.

Exact metric definitions and calculation rules will be documented later.

## 19. Product Boundaries

The following are out of scope until explicitly approved:

- Native Android application.
- Native iOS application.
- Centralized online payment gateway.
- Merchant order acceptance or rejection directly through WhatsApp.
- Centralized delivery-partner management.
- Customer password-based accounts.
- Microservices.
- Advanced event-driven architecture.
- Platform monetization or commission model.
- Complex ERP accounting functionality.

These may be considered in future phases.

## 20. Important Documentation Boundary

This document describes product behavior and business context. It does not define final database tables, Django models, API endpoints, authentication implementation, permission classes, serializers, views, infrastructure, deployment architecture, or specific third-party providers. Those decisions belong in the appropriate architecture, domain, API, or implementation documentation.

## 21. Source of Truth

When implementing product functionality:

1. Read the root `AGENTS.md`.
2. Read this `product.md`.
3. Read the relevant domain specification.
4. Follow approved architecture decisions.
5. Do not invent undocumented business behavior.

If a requirement conflicts with this document, do not silently choose a behavior. Identify the conflict and request clarification.
