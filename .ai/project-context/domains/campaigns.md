# Campaigns Domain Specification

## 1. Domain Purpose

The Campaigns domain owns platform-level promotional content and its Shop display scope. In the MVP, campaigns are managed exclusively by Super Admin and may display across all Shops or a selected set of Shops. Displaying a campaign does not make a Shop its owner.

Campaigns does not own product definitions, stock, prices, product availability, checkout totals, Orders, discounts, customer identity, notification delivery, or analytics reporting.

## 2. Campaign Ownership

Campaigns are platform-level promotional content. Super Admin exclusively creates and manages campaigns. A campaign may display across all Shops or a selected set of Shops; inclusion in the display scope does not transfer ownership to a Shop.

Merchant-created and Shop-owned campaigns are excluded from the MVP.

## 3. Campaign Identity

A campaign conceptually has an identity and a business context, but the source documents do not define a final schema or required field list. Approved concepts include:

- campaign name or title
- descriptive content
- platform ownership
- visibility or public presentation context
- scheduling context
- lifecycle status
- optional Shop display scope (all Shops or selected Shops)

The following are not approved as final design requirements unless explicitly added elsewhere:

- exact database fields
- exact primary-key strategy
- exact campaign-number format
- exact URL or slug patterns
- exact customer-facing banner schema
- exact target-entity schema

Campaign identity must be understood as a business concept, not as a finalized data model.

## 4. Campaign Lifecycle

The MVP lifecycle has three states:

```text
Draft ? Active ? Ended
```

- A Draft campaign may be edited.
- Super Admin may activate a Draft campaign and deactivate an Active campaign.
- An Active campaign becomes Ended when its configured end time is reached.
- Ended campaigns cannot be reactivated in the MVP.
- Active and Ended campaigns are deactivated or retained rather than deleted through the normal campaign-management workflow.

Exact state representation and transition enforcement are technical design choices.

## 5. Campaign Scheduling

Start and end times are optional. When configured, a campaign is customer-visible only while its lifecycle state is Active, the current time is within its configured schedule, and the customer is viewing a Shop within the campaign's display scope. An unset start or end time imposes no corresponding time boundary. A campaign outside its schedule is not customer-visible; an Active campaign that reaches its end time becomes Ended and cannot be reactivated in the MVP.

Timezone handling, schedule evaluation mechanism, and whether evaluation occurs on request or through a scheduled process are technical design choices.

## 6. Campaign Content and Targets

Campaign display scope is either all Shops or a selected set of Shops. Campaigns may mention products, categories, brands, or Shops in their text/content only. The MVP creates no persistent Catalog targeting relationships. Merchant-created campaigns, customer segmentation, and personalization are excluded.

## 7. Campaign vs Pricing

Campaigns do not modify product prices, inventory, product availability, checkout totals, Orders, or discounts. Coupons, discount rules, and all other campaign-driven price or Order adjustments are excluded from the current MVP. Any future discount engine requires a separate approved product decision and must be reconciled with Catalog and Orders rules.

## 8. Customer-Facing Campaign Visibility

Customers may see a campaign only when it is Active, within its optional schedule, and within the Shop display scope for the Shop they are viewing. Exact storefront placement and presentation remain product/UI design details; this document does not require a particular page or component.

## 9. Platform Campaign Management

Super Admin exclusively manages platform campaigns. Campaigns may display across all Shops or a selected set. Their customer visibility follows the lifecycle, schedule, and display-scope rules above. Detailed platform authorization implementation is a technical/security design concern.

## 10. Merchant Campaign Management

Merchant-created campaigns and merchant campaign management are excluded from the MVP. A Shop's inclusion in a campaign's display scope grants no campaign ownership or management rights.

## 11. Multi-Tenancy and Isolation

Campaigns are platform-level and managed exclusively by Super Admin. Their display scope does not create Shop ownership or permit Merchants to manage them. Customer-facing campaign results must be limited to the intended Shop display scope. Public requests must not expose campaigns outside that scope. This document does not define the technical enforcement mechanism.

## 12. Campaign Visibility vs Campaign Status

Campaign visibility is determined by lifecycle state, optional schedule, and Shop display scope together:

```text
Lifecycle: Draft, Active, or Ended
Visibility: Active + within configured schedule + Shop in display scope
```

Draft and Ended campaigns are not customer-visible. An Active campaign outside its configured schedule is also not customer-visible.

## 13. Catalog Relationship

Catalog owns products, variants, categories, brands, and Shop-specific catalog structure. Campaigns owns promotional content and platform display scope. Campaign content may mention products, categories, or brands as text/content only. The MVP creates no persistent Product, Variant, or Category targeting relationships and no Catalog dependency for campaign content.

Campaigns does not own or mutate Catalog data, prices, or availability.

## 14. Inventory Relationship

Campaigns does not own or change inventory, stock state, or product availability. Promoting or mentioning an item does not make it available or affect whether it can be ordered. Catalog and Inventory remain the sources of truth for product visibility, manual availability, and stock.

## 15. Order Relationship

Campaigns do not modify checkout totals or Orders and do not create an Order relationship in the MVP. Order history and pricing remain under Orders rules. Campaigns do not apply discounts or other Order adjustments.

## 16. Customer Targeting and Personalization

Customer segmentation and personalization are excluded from the MVP. Campaigns are displayed based on lifecycle, schedule, and Shop scope, not customer profile or purchase history.

## 17. Campaign Analytics Boundary

Campaign attribution analytics are excluded from the MVP. Campaigns does not track or define impressions, clicks, conversions, or sales attribution. Any later reporting requires separate approval and belongs to Analytics.

## 18. Deletion, Expiration, and Historical Data

Through normal campaign management, Active and Ended campaigns must be deactivated or retained rather than deleted. Ended campaigns cannot be reactivated. Physical deletion, retention, and archival mechanics remain technical design choices. Campaigns has no persistent Catalog targets whose lifecycle needs handling.

## 19. Notifications Boundary

Campaign-triggered notifications are excluded from the MVP. Notifications remains a separate domain. Any future campaign-driven notifications require a separate approved product decision.

## 20. Security and Authorization

Campaigns must respect platform authorization and public Shop display boundaries:

- Only Super Admin manages campaigns.
- Public customers may see a campaign only when it is Active, within schedule, and in the display scope of the Shop being viewed.
- A client-provided Shop ID does not authorize access to platform campaign management or bypass public visibility rules.
- Draft, Ended, and out-of-schedule campaigns are not customer-visible.

This specification does not choose authentication technology or permission implementation.

## 21. Business Invariants

The following MVP business rules are finalized:

- Campaigns are platform-level promotional content managed exclusively by Super Admin.
- Campaigns may display across all Shops or a selected set; display does not confer Shop ownership.
- Mentions of products, categories, brands, and Shops are content only; no persistent Catalog targeting relationships are created.
- Campaigns do not change prices, inventory, availability, checkout totals, Orders, or discounts.
- The lifecycle is Draft, Active, and Ended; start and end times are optional.
- Customer visibility requires Active status, an in-schedule time, and matching Shop display scope.
- Super Admin can deactivate an Active campaign; Ended campaigns cannot be reactivated.
- Draft campaigns can be edited. Active and Ended campaigns are deactivated or retained rather than deleted through normal campaign management.
- Merchant-created campaigns, coupons, discount rules, customer segmentation, personalization, campaign-triggered notifications, and campaign attribution analytics are excluded from the MVP.
- Campaign access respects platform authorization and public Shop visibility boundaries.

## 22. Cross-Domain Responsibilities

| Concern | Owning domain | Campaigns responsibility |
|---|---|---|
| Product identity and catalog structure | Catalog | Campaign content may mention Catalog concepts as text only; no persistent targeting relationship. |
| Product pricing and availability | Catalog | Campaigns do not change price, visibility, or manual availability. |
| Inventory state | Inventory | Campaigns do not change stock. |
| Shop identity and display context | Shops | Supplies Shop identity; Campaigns defines all-Shop or selected-Shop display scope. A Shop does not own the campaign. |
| Campaign management access | Users & Merchant Accounts | Only Super Admin manages campaigns in the MVP. |
| Customer identity | Customers | Campaigns does not own customer identity or personalization. |
| Order history and totals | Orders | Campaigns does not change Orders or checkout totals. |
| Notifications | Notifications | Campaign-triggered notifications are excluded from MVP. |
| Reporting | Analytics | Campaign attribution analytics are excluded from MVP. |

## 23. Unresolved Decisions

Business behavior listed above is finalized for the MVP. Remaining choices are technical or presentation design decisions and must not be mistaken for unresolved business rules:

### Technical model decisions

- Lifecycle is stored in a constrained `status` field with `DRAFT`, `ACTIVE`, and `ENDED` values.
- Shop display scope is stored in a `shop_scope` field with `ALL_SHOPS` and `SELECTED_SHOPS` values. Selected Shops are represented by a many-to-many relationship to `Shop`; that relationship defines display scope, not ownership. It is ignored for `ALL_SHOPS`.
- Campaign content is stored as a title and free-form text. Product, category, brand, and Shop mentions remain content; no Catalog target relationships are added.
- Optional schedule bounds are nullable `DateTimeField` values. With the project's `USE_TZ = True` configuration and UTC `TIME_ZONE`, timestamps are timezone-aware and stored in UTC; no Shop-local timezone is persisted. When both bounds exist, the start must not be later than the end.
- Expiring an Active campaign still needs application-level schedule evaluation to transition it to Ended; the model does not add a scheduler or endpoint.

### Remaining technical/design choices

| Technical/design choice | Why it remains open | Area |
|---|---|---|
| API shape and authorization enforcement | Endpoints and permission implementation are not specified. | Campaigns, Users |
| Schedule evaluation mechanism | The optional time-window behavior and UTC storage are defined; the runtime mechanism for transitioning an expired Active campaign to Ended is not. | Campaigns |
| Physical deletion, retention, and archival mechanics | Normal management behavior is approved, but storage-level retention/deletion mechanics are not. | Campaigns |
| Customer-facing placement and presentation format | Visibility rules are approved, but exact storefront placement remains a product/UI design detail. | Campaigns, customer-facing product |

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

> Campaign business rules, the initial model schema, Shop display-scope representation, and UTC schedule storage are finalized. API/authorization, runtime schedule evaluation, and retention mechanics remain future technical work.

Implementation must follow `AGENTS.md`, the product and architecture documentation, the relevant domain files, and engineering standards. Do not add campaign capabilities excluded from MVP or silently change approved business behavior.

## 26. Git Workflow

Follow the repository workflow before making any change:

```text
git status
git pull --ff-only origin main
git switch -c feature/<task-id>-campaign-work
```

- Never work directly on `main`.
- Inspect existing changes first and do not discard unrelated work.
- Do not use destructive Git commands without explicit approval.
- If no task ID is provided, ask for it before creating a branch.
- Keep work limited to files authorized for the task.

## Final Requirement

Do not add APIs, serializers, views, background jobs, payment logic, notification logic, or frontend behavior unless separately approved.
