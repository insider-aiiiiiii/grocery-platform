# Campaigns Domain Specification

## 1. Domain Purpose

The Campaigns domain owns the business concept of promotional or marketing campaigns for the grocery platform. Its scope includes campaign definition, ownership, scheduling, visibility, target context, lifecycle, and core business boundaries with other domains.

This domain is responsible for the campaign as a business object and its relation to the platform, a shop, and customer-facing catalog experiences. It does not own product definitions, stock, order pricing logic, customer authentication, payment processing, notification delivery, or analytics reporting implementation.

The approved source-of-truth documents establish that Super Admin can create campaigns or advertisements displayed across all shops or selected shops. They also state that campaign data, targeting rules, scheduling, and presentation behavior will be defined later. Merchant/shop-owned campaigns are not explicitly approved as a final requirement and therefore remain an unresolved decision.

## 2. Campaign Ownership

The current product documentation supports at least the following conceptual ownership model:

```text
Platform-level campaign
    =
Super Admin may create and manage campaigns/advertisements for the platform or selected shops

Shop-level campaign
    =
Potential merchant-owned shop campaign, but not explicitly finalized
```

### Platform-level campaigns

The product context explicitly says that the Super Admin can create campaigns or advertisements displayed across all shops or selected shops. A campaign may target one or more shops.

This establishes that platform-level campaigns are a supported product concept.

### Merchant/shop-level campaigns

The current product and domain documents do not define a finalized merchant-created campaign model. The source documents refer to campaigns as a possible platform and/or shop concept, but no approved merchant workflow or merchant-owned campaign lifecycle is documented.

Therefore:

- Platform-level campaign ownership is supported by the approved product documentation.
- Merchant/shop-level campaign ownership is not yet approved as a finalized requirement.
- This document must not silently assert that merchants can create campaigns unless the source-of-truth is updated.

## 3. Campaign Identity

A campaign conceptually has an identity and a business context, but the source documents do not define a final schema or required field list. Approved concepts include:

- campaign name or title
- descriptive content
- an owning platform or shop context
- visibility or public presentation context
- scheduling context
- lifecycle status
- optional targeting context

The following are not approved as final design requirements unless explicitly added elsewhere:

- exact database fields
- exact primary-key strategy
- exact campaign-number format
- exact URL or slug patterns
- exact customer-facing banner schema
- exact target-entity schema

Campaign identity must be understood as a business concept, not as a finalized data model.

## 4. Campaign Lifecycle

The source material does not define a complete or approved final campaign lifecycle state machine. Product requirements mention campaign scheduling, activation/deactivation, visibility, and review at a high level, but they do not finalize exact states or transitions.

Candidate lifecycle concepts that may be discussed in future design include:

```text
DRAFT
SCHEDULED
ACTIVE
PAUSED
ENDED
```

However, these are not approved as final campaign states in the current source-of-truth. They remain possible future design concepts, not selected product behavior.

For any lifecycle state considered later, the product requirements would still need to answer:

- what the state means
- who can transition into or out of it
- whether transitions are manual or automatic
- whether customers can see the campaign while the state is active or scheduled
- whether an ended campaign can be reactivated
- whether a campaign can be edited while active
- whether the system allows a scheduled campaign to become visible automatically

Until those decisions are approved, the lifecycle is a business requirement to be defined later rather than a finalized state machine.

## 5. Campaign Scheduling

The product context mentions campaign scheduling, activation, and deactivation at a high level, but it does not finalize the exact scheduling model. The following are conceptual business questions that must be decided later:

- immediate activation vs delayed activation
- future scheduled starts
- end time or no end time
- timezone rules
- whether a scheduled campaign is visible before it becomes active
- whether a campaign can be manually paused or stopped
- whether an ended campaign can be reactivated
- whether a shop or platform campaign is evaluated in real time or via a scheduled job

This specification does not define a background scheduler or processing mechanism. The scheduling concept is a business rule to be finalized separately from any implementation stack.

## 6. Campaign Content and Targets

The product requirements say campaigns may target shops and may be displayed across all shops or selected shops. They also mention campaign data, targeting rules, and presentation behavior as something to be defined later.

At the current approved business level, the following are conceptual possibilities, not guaranteed requirements:

- platform-wide campaigns
- campaigns targeting selected shops
- campaigns targeting a shop's catalog area
- campaigns featuring products
- campaigns featuring categories
- campaigns featuring a general promotional message

The following are not finalized as approved campaign target types unless later documentation says so:

- product-level targeting for every product type
- variant-level targeting
- customer-segment targeting
- personalized targeting by customer profile
- dynamic campaign pricing logic
- coupon-code campaigns

If a campaign targets a product, the campaign must not own the product itself. Product ownership remains with Catalog. If a campaign targets a shop, shop ownership remains with Shops. If a campaign targets a customer-facing presentation, the customer experience is defined by the relevant product flow rather than by this domain.

## 7. Campaign vs Pricing

This domain requires a clear conceptual boundary between campaign configuration and monetary pricing.

```text
Campaign
    =
 promotional/presentation mechanism

Product Price
    =
 merchant/shop-specific price owned by Catalog

Order Price
    =
 historical purchase price owned by Orders
```

The source documentation does not approve promotional pricing as a finalized campaign feature.

The following behaviors are not finalized or approved by default:

- percentage discount campaigns
- fixed discount campaigns
- coupon codes
- bundle pricing
- campaign-only pricing overrides
- campaign-specific order total adjustments
- any formula that changes historical order price after the fact

The Orders domain explicitly states that order price and historical purchase meaning must remain stable. A campaign must not silently become a pricing engine unless an approved product decision introduces that behavior.

## 8. Customer-Facing Campaign Visibility

Campaign visibility belongs to the customer-facing experience. The product context defines the shop-flow model conceptually:

```text
Shop QR
    ↓
Shop public URL
    ↓
Customer catalog
    ↓
Products / categories
    ↓
Cart
    ↓
Checkout
```

Campaigns may appear in a customer-facing experience where product or shop content is promoted, but the approved documentation does not finalize the exact places where a campaign may display. Likely areas include:

- a shop landing page
- the customer catalog header or promotional section
- a category or product listing section
- a shop-level promotional area

However, those are possible display contexts, not a finalized UI contract. The system must not invent a UI requirement or require all of them.

## 9. Platform Campaign Management

The product context explicitly says Super Admin can create campaigns or advertisements displayed across all shops or selected shops, and that campaign data, targeting rules, scheduling, and presentation behavior will be defined later.

This gives Super Admin a supported platform-level campaign-management role. The current documentation does not define an exhaustive admin permission matrix and does not define the exact review or approval workflow for platform campaigns.

Therefore, platform campaign management must remain at the business-concept level until approved:

- Super Admin may create or manage platform-level campaigns.
- Platform campaigns may target one or more shops if approved.
- Platform campaign visibility is subject to approved targeting and scheduling rules.
- The final platform campaign management workflow remains unresolved.

## 10. Merchant Campaign Management

The product and domain specs do not approve a finalized merchant-owned campaign workflow. Therefore, the following must remain unresolved unless the source-of-truth is updated:

- whether merchants can create shop campaigns
- whether merchants can edit their shop campaigns
- whether merchants can activate, pause, or deactivate shop campaigns
- whether merchants can schedule shop campaigns
- whether merchants can delete or archive campaigns
- whether a merchant can manage a campaign that targets selected products or other shop content

The default business boundary is: merchants may only manage campaign content within the shops they are authorized to operate. However, the existence of a merchant campaign capability itself remains unresolved.

## 11. Multi-Tenancy and Isolation

Campaigns must follow the approved multi-tenancy architecture. The shop is the primary tenant boundary, and tenant-owned data must remain within the authorized shop context.

For shop-owned campaigns, the conceptual model is:

```text
Merchant
    ↓
Authorized Shop
    ↓
Shop Campaigns
```

The following rules are business requirements:

- a merchant must not access another shop's campaigns
- a client-provided shop ID must not serve as proof of authorization
- cross-shop campaign references are not allowed unless explicitly approved
- public campaign visibility must still respect the intended shop or platform audience
- platform-wide campaigns are different from shop-owned campaigns and must not be confused with tenant-owned shop data

This domain does not define the technical tenant enforcement mechanism. Follow the relevant multi-tenancy skill and the source-of-truth security guidance.

## 12. Campaign Visibility vs Campaign Status

Campaign visibility and campaign lifecycle must be kept distinct at the business level.

Conceptually:

```text
Campaign lifecycle/status
    =
 whether the campaign is draft, active, scheduled, ended, etc.

Campaign visibility
    =
 whether customers can see it in the public or shop-facing experience
```

The product documentation does not approve a finalized lifecycle model or a final visibility model. The system may later distinguish between:

- scheduled but not yet visible
- active and visible
- active but hidden
- ended and hidden
- paused and hidden

However, these combinations are not approved state rules yet. The domain should not assume that a campaign that is active is automatically visible, or that a campaign that is visible is automatically active.

## 13. Catalog Relationship

Campaigns interact with Catalog, but they do not own it.

The approved boundary is:

```text
Catalog
    owns products, variants, categories, and shop-specific catalog structure

Campaigns
    owns campaign configuration, targeting and presentation context
```

Campaigns may reference catalog entities, but campaigns are not a second owner of product, variant, or category data. The product and business-rules documents keep those domains distinct.

Important boundaries:

- Campaigns do not own product or variant definitions.
- Campaigns do not own catalog pricing or merchant-specific selling price.
- Campaigns do not own inventory state.
- Campaigns must not mutate product or shop catalog data by themselves.

This is a key distinction: campaign content may point to a catalog item, but it does not replace the domain ownership of the catalog item itself.

## 14. Inventory Relationship

Campaigns do not own inventory. A store may present a promotional campaign for items that have inventory, but inventory remains the responsibility of the Inventory domain.

The product and business-rule documents do not say that a campaign changes inventory or automatically makes items available. Therefore:

- a campaign cannot own stock
- a campaign cannot decide available quantity by itself
- a campaign cannot create product availability rules
- a campaign must not implicitly affect inventory state without an approved business decision

If a promoted product becomes unavailable, out of stock, or removed from the merchant catalog, the approved behavior must be defined by Catalog, Inventory, and possibly Order domain rules. Do not assume automatic behavior such as campaign deactivation or hidden status.

## 15. Order Relationship

Campaigns must not interfere with the historical meaning of an Order. The historical purchase price is finalized: it uses the latest Catalog price at checkout and does not change with later Catalog changes. The physical snapshot/reference strategy remains a technical decision.

Campaigns are therefore conceptually separate from Orders. A campaign may present or reference promotional content, but it must not silently alter the historical purchase transaction of an order unless an explicit approved rule is added.

The following are unresolved and must not be assumed:

- whether an order stores campaign reference data
- whether an order stores promotion or discount information
- whether order totals adjust because a campaign changed later
- whether a campaign name or targeting is snapshotted on an order
- whether campaign outcomes are tracked in analytics later

This domain should not define an order-campaign relationship beyond the principle that historical order integrity must be protected.

## 16. Customer Targeting and Personalization

The current product documentation does not establish a finalized customer-segmentation or personalization model. The following are possible concepts to evaluate later, not approved requirements:

- all customers
- selected customer groups
- new-customer promotions
- returning-customer promotions
- location-based promotions
- purchase-history-based targeting
- shop-level audience restrictions

The current product and domain specs do not provide enough approval to implement any of these. This specification therefore marks customer targeting as unresolved unless a later approved requirement defines it.

## 17. Campaign Analytics Boundary

The product context indicates that campaign performance may matter to analytics. However, the same sources also keep analytics architecture as not finalized and state that analytics should not be assumed as a final implementation.

Therefore:

- Campaigns may produce data relevant to reporting.
- Analytics owns aggregated reporting and metric definitions.
- Campaigns do not automatically own analytics implementation.

Potential analytics concepts such as views, clicks, conversion, sales influence, or product interaction may be discussed later, but they are not approved as final campaign metrics unless the Analytics domain explicitly defines them.

## 18. Deletion, Expiration, and Historical Data

The lifecycle of a campaign is not finalized. Similarly, deletion and archival behavior are not defined. The following are not approved by default:

- hard delete vs soft delete
- automatic archive on expiry
- whether historical campaign records should remain accessible after removal
- whether a deleted or expired campaign remains visible to older customer sessions or historical reports
- whether a campaign associated with a removed product or shop should be retained for records

Any final treatment of historical campaign records depends on approved retention and deletion behavior for campaigns and their relationships with shops, products, and customers.

## 19. Notifications Boundary

Campaigns may eventually be associated with notifications or customer communications, but the current product documentation treats notifications as a separate domain.

The approved separation is:

```text
Campaign
    defines a promotional concept or targeting configuration

Notification
    delivers communication to an intended audience
```

The Campaigns domain should not implement WhatsApp, email, SMS, push, or other delivery logic. That belongs to Notifications and any approved external provider integration.

If campaign-driven notifications are later approved, their business meaning and triggering rules must be defined separately from campaign configuration itself.

## 20. Security and Authorization

Campaigns must respect the same authorization and tenant-isolation principles as other shop-scoped application domains.

At the business level:

- Super Admin may access platform-level campaign functions according to approved platform authorization.
- A merchant may only manage campaigns for shops they are authorized to manage, if merchant-owned campaigns are later approved.
- Public customers may only see campaigns intended for public display within the intended shop or platform context.
- Campaign configuration must not bypass tenant isolation.
- A client-provided shop ID is not proof of authorization.
- Hidden, inactive, or scheduled campaigns must still respect the approved visibility and authorization rules.

This specification does not choose authentication technology or permission implementation. It defines the required business/security relationship only.

## 21. Business Invariants

The following invariants are supported by the current product and business-rule sources:

- A campaign is a platform-level or potentially shop-scoped business concept, but the final shop-campaign model is unresolved.
- Platform campaigns are supported as a product concept for Super Admin.
- Campaigns must respect tenant isolation and authorized-shop boundaries when shop-scoped.
- Campaigns must not own catalog or product data directly.
- Campaigns must not own inventory or stock state.
- Campaigns must not replace the shop's catalog as the source of product truth.
- Campaign content must not silently change historical order meaning or price.
- Campaign visibility must not bypass approved security and tenant rules.
- The campaign lifecycle and scheduling model are not finalized and must not be implemented as a complete state machine yet.

## 22. Cross-Domain Responsibilities

| Concern | Owning domain | Campaigns responsibility |
|---|---|---|
| Product identity | Catalog | Campaigns reference products only when approved; do not own product definitions. |
| Product pricing | Catalog | Campaigns do not own selling-price logic. |
| Inventory state | Inventory | Campaigns do not own stock or availability changes. |
| Shop identity | Shops | Campaigns may target a shop or platform context; shop ownership remains with Shops. |
| Merchant access | Users & Merchant Accounts | Determines authorized access to shop-managed data if merchant campaigns are approved. |
| Customer identity | Customers | Campaigns do not own customer identity or customer login logic. |
| Order history | Orders | Orders own historical transaction meaning; campaigns must not change it. |
| Notifications | Notifications | Campaigns may trigger or be associated with notifications only when approved; delivery belongs elsewhere. |
| Analytics | Analytics | Campaign metrics belong to analytics/reporting, not to Campaigns implementation. |

## 23. Unresolved Decisions

No decision below is finalized by this specification.

| Decision | Current status | Why it matters |
|---|---|---|
| Platform campaigns vs merchant/shop campaigns | Unresolved beyond platform-level support | Ownership model affects who can create and manage campaigns. |
| Final campaign lifecycle | Unresolved | The state machine and statuses are not approved. |
| Campaign scheduling model | Unresolved | Start/end time behavior and activation logic remain undefined. |
| Campaign visibility model | Unresolved | Customer-facing visibility and hidden/inactive states need approval. |
| Targeting model | Unresolved | Whether campaigns target specific shops, products, categories, or all customers needs approval. |
| Product/category targeting rules | Unresolved | The domain must know which entities can be promoted and under what conditions. |
| Promotional pricing model | Unresolved | Whether campaigns create discounts, coupons, or special prices is not approved. |
| Coupon or discount logic | Unresolved | Financial/order implications need product approval. |
| Customer segmentation and personalization | Unresolved | This affects targeting and privacy rules. |
| Campaign-triggered notifications | Unresolved | Notification design belongs elsewhere; requirements are not approved. |
| Campaign analytics metrics | Unresolved | Reporting scope and metric definitions require approval. |
| Campaign deletion and archival rules | Unresolved | Historical retention and visibility after removal need decisions. |
| Campaign reactivation rules | Unresolved | The lifecycle model may allow or prohibit reactivation. |
| Campaign changes while active | Unresolved | Editing rules must reflect the approved lifecycle and customer visibility. |
| Platform-level campaign audience scope | Unresolved | The exact meaning of “all shops” or “selected shops” needs definition. |

## 24. Explicit Non-Goals

This specification does not define the following:

- authentication mechanism
- user identity or membership implementation
- merchant account model
- shop model or shop profile schema
- catalog product or category model
- inventory model or stock logic
- cart implementation
- order schema or state machine
- payment gateway or refund logic
- WhatsApp provider or notification delivery implementation
- analytics vendor or metric definitions
- frontend UI implementation
- database schema or migrations
- API endpoints or serializers
- background-job infrastructure
- advanced marketing automation
- customer segmentation infrastructure unless explicitly approved

## 25. Implementation Gate

> The Campaigns domain must not be implemented until the unresolved campaign ownership, lifecycle, scheduling, targeting, pricing, and visibility decisions are reviewed and approved.

Once approved, implementation must follow the repository's agreed documentation hierarchy and engineering standards rather than silently redefining business behavior. This includes `AGENTS.md`, the product and architecture documentation, the relevant domain files, and the engineering skills. The implementation agent must not assume unsupported campaign capabilities or silently select a lifecycle, pricing behavior, or targeting model without explicit approval.

## 26. Git Workflow

Follow the repository workflow before making any change:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/define-campaigns-domain
```

- Never work directly on `main`.
- Inspect existing changes first and do not discard unrelated work.
- Do not use destructive Git commands without explicit approval.
- If no task ID is provided, ask for it before creating a branch.
- Keep work limited to the campaign-domain documentation.
- Do not implement application code while defining this domain specification.

## Final Requirement

Create only `.ai/project-context/domains/campaigns.md`. Do not modify any other file. Do not create models, migrations, APIs, serializers, views, business logic, background jobs, payment logic, notification logic, or frontend behavior. Do not resolve unresolved campaign business decisions by assumption.
