# Grocery Platform Business Rules

## 1. Purpose

This document captures approved business rules and invariants that application code, APIs, database constraints, tests, and future domain documentation must respect. Business rules describe what the system must do, not how it is implemented. Do not infer rules solely from current implementation.

```text
Product Requirement
        ↓
Business Rule
        ↓
Technical Implementation
```

## 2. Actors

### Super Admin

The Super Admin is a platform-level actor responsible for approved administrative operations, including creating Merchant accounts, managing the platform Master Catalog, campaigns/advertisements, and platform analytics. Super Admin may view dashboard information about Merchant-created products and may promote them into the Master Catalog. In MVP, Super Admin cannot edit Merchant or Shop information after creation. This document does not define the final permissions.

### Merchant / Shopkeeper

A Merchant means the Shop Owner / business owner and is a business entity separate from User and Shop. A Merchant operates their one active Shop at a time in MVP and is responsible for Shop management, the merchant catalog, products and variants, pricing, inventory and availability, incoming orders and order processing, merchant-side analytics, and merchant-provided payment instructions. This document does not define the final user or account architecture.

### Customer

A Customer interacts with a specific shop through its QR/public shop URL, shop catalog, product selection, cart, checkout, pickup or delivery selection, order information, and a WhatsApp number. The current MVP concept does not require a traditional customer username/password account.

## 3. Shop / Tenant Rules

- Shop is the primary tenant boundary.
- Merchant-owned data belongs to a Shop and must remain isolated from other Shops.
- Merchants must not access another Shop's tenant-owned data.
- Super Admin cannot view Shop information, edit Shop information, or deactivate a Shop in MVP. Super Admin may reactivate a deactivated Shop.
- Customer identity is Shop-specific; the same WhatsApp number does not automatically create a globally shared customer identity.
- A customer ordering from Shop A must not gain access to Shop B's customer history.

Follow `.ai/skills/multi-tenancy/SKILL.md` for engineering requirements. This document does not define technical tenant-context implementation.

## 4. Merchant Account and Shop Setup Rules

- Only a Super Admin creates a Merchant account in MVP. There is no Merchant application, review, approval, rejection, re-application, or application status flow.
- The system generates an initial temporary password when it creates the Merchant account. Merchant must change it on first login.
- Merchant logs in using a mobile number unique across Merchant accounts. Email is also unique across Merchant accounts, is used for contact/recovery, and is not the login identifier.
- Merchant exists before Shop creation and may log in without a Shop.
- If the Merchant has no Shop, show the Create Shop flow after login. Merchant creates their own Shop; Super Admin does not create it.
- A newly created Shop becomes ACTIVE immediately.
- A Merchant can have only one active Shop at a time. A Shop belongs to exactly one Merchant and cannot exist without a Merchant.
- Merchant cannot have multiple active Shops. After permanently deleting their current Shop, Merchant may immediately create another Shop; it is a new Shop entity.
- Ownership transfer between Merchants is not supported in MVP.

## 5. Shop Profile Rules

- Required Shop information: Shop name; structured address with address line, area, city, state, and pincode; Shop contact number equal to the Merchant's mobile number.
- Shop name does not need to be unique. Shop description and Shop logo are optional.
- Merchant can edit all Shop details, but cannot change Shop contact number separately from the Merchant mobile number.
- Merchant can manage Merchant personal information and Shop profile. Super Admin cannot edit Merchant or Shop information after creation and cannot view Shop information.

## 6. QR / Public Shop Access Rules

- Customers access a Shop through its system-generated Shop QR code or public Shop link. Public Shop links can be shared.
- The customer flow is QR/public Shop link → Shop details → Categories → Products.
- The QR uses a system-generated public link and does not expose or use the Shop ID as its public identifier. Merchant can regenerate the QR code.
- When a Shop is deactivated, its QR remains technically valid but shows the Shop as unavailable. If the Shop is deleted, the QR and public link become unavailable immediately.
- Deleting and recreating a Shop does not restore its previous QR. If a deactivated Shop is reactivated, its old QR does not work; a new QR must be generated.
- Public access must not expose private Merchant information or grant Merchant/admin access.
## 7. Master Catalog Rules

- The Master Catalog is a platform-level reusable product library managed by Super Admin.
- Every Shop has an independent Shop Catalog, fully controlled by its Merchant. Master Catalog data does not control or automatically synchronize to existing Shop Products.
- A Merchant may select a Master Product or create a Shop Product directly. Directly created products require no Super Admin approval and may be sold by that Merchant.
- Super Admin may view Merchant-created product information on the dashboard and may promote a product into the Master Catalog. Promotion makes the Master Product available for other Merchants to select; it does not automatically link, replace, or update the original Shop Product.
- Multiple Shops may select the same Master Product while maintaining independent Shop Product information. Deleting a Master Product does not delete or impair existing Shop Products.
- Do not automatically match or merge products by name, brand, category, or SKU. Master Products are identified by Master Product ID.

## 8. Merchant Catalog Rules

- Each Shop has its own Shop Catalog. The Merchant has full control over Shop Products and Shop-specific catalog information, including product information, variants, prices, categories, brands, custom attributes, images, visibility, and manual availability.
- Merchant catalog operations must remain isolated from other Shops and must not modify Master Catalog data unless Super Admin performs a Master Catalog operation.
- Merchants may create and manage Shop Catalog categories with CRUD, including subcategories. Products may belong to multiple categories. Deleting an assigned category leaves its products uncategorized.
- Merchants control their Shop Catalog brands and custom attributes. Products may have multiple attributes and values; variants may have custom attributes. No fixed global attribute system is required by this decision.

## 9. Product Rules

- A Shop Product can be sellable without variants or can have variants. Product-level and variant-level information are supported. Merchants can create, edit, and delete variants, including name, price, SKU, image, and custom attributes. Merchants may add Shop-specific variants to a selected Master Product.
- Product information includes name, description, image, category, and brand. Products may have no image. A product's name need not be unique; do not infer identity or auto-match by product name.
- MVP supports one image per product and an optional image per variant. A variant can use the product image as fallback. Merchants can replace/delete images; a primary image is supported when images exist. Image galleries are not included.
- Merchant-entered SKUs may be changed and need not be unique. Duplicate SKUs, including across variants, are allowed.
- Product pricing is Shop-specific and Merchant-controlled. Non-variant products may have a price; variant products support product-level and variant-level prices. Decimal values are supported. Master Catalog pricing does not control Shop prices.
- Merchants control product visibility. Hidden products are not visible to customers and cannot be ordered; Merchants may make them visible again.
- Manual availability is separate from inventory quantity. Manually unavailable products remain in the catalog but cannot be ordered.
- Out-of-stock products remain visible, are shown as **Out of Stock**, and cannot be ordered. Customers see only available variants; if every variant is unavailable or out of stock, the main product shows **Out of Stock**.
- Customers may see product name, description, brand, attributes, SKU, images, available variants, and applicable price. Hidden products are not visible; out-of-stock and manually unavailable products cannot be ordered.
- Merchants may delete Shop Products. This does not delete a Master Product or affect another Shop. Historical Orders must retain required product information/references after deletion; physical retention and snapshot strategy are technical decisions.

## 10. Pricing Rules

- Merchant/shop-specific pricing is independent.
- A master-catalog product does not automatically dictate a merchant's selling price.
- Changing one merchant's price must not change another merchant's price.
- Customer checkout uses the applicable shop-specific price.

Tax and discount calculation, currency architecture, price history, and promotional pricing algorithms are **Not Finalized / Require Decision**.

## 11. Inventory and Availability Rules

- Inventory is Shop-scoped and isolated; a Merchant may modify it only in the Merchant's authorized Shop. Client-provided Shop, Product, or Variant IDs cannot bypass tenant authorization. Super Admin does not modify Merchant inventory in MVP.
- A Shop Product without variants has Product-level stock. A product with variants has independently tracked Variant stock and an overall/aggregate Product-level quantity. The Merchant may modify both levels. Aggregate recalculation behavior remains undefined.
- Decimal quantities are allowed and respect the Catalog Product/Variant sellable unit. No separate Unit-of-Measure system or fixed global unit list is introduced.
- New Shop Products and Variants start with stock `0`. Stock cannot become negative; minimum quantity is `0`.
- The Merchant may add stock, subtract stock, or set the exact quantity. No reason is required for a manual adjustment.
- MVP stores current stock only; it does not maintain a persistent inventory movement/history ledger.
- Creating an Order reserves the required quantity, visible to the Merchant. Accepting the Order deducts the reserved stock. Rejecting the Order releases the reservation. Cancelling an accepted Order restores the deducted quantity, which is immediately available again.
- When requested quantity exceeds available stock, partial quantity is allowed. Detailed customer confirmation, quantity adjustment, and Order behavior remain an Inventory/Orders dependency and must be finalized with the Orders domain.
- Customers can see the exact available quantity. At `0`, they see **Out of Stock**; the product remains visible but cannot be ordered.
- The MVP has no low-stock threshold. Do not add configurable thresholds, alerts, or low-stock notification events.
- Removing a Catalog Product or Variant from a Shop Catalog removes its Inventory record. This does not prescribe hard-delete or soft-delete mechanics.
- Inventory quantity and Catalog manual availability/visibility remain separate concepts.

Exact database representation, Product aggregate recalculation, transaction/concurrency implementation, partial-quantity Order behavior, additional cancellation scenarios, and the complete Order state machine remain unresolved where applicable.

## 12. Customer Identity Rules

- Customer identity is shop-specific, not globally shared across merchants by assumption.
- Within a Shop, the customer's WhatsApp number is the primary identifier for recognizing a returning Customer.
- A permanent Shop-specific Customer record is created when the customer first provides their WhatsApp number for that Shop, even before an Order is successfully created.
- Customer information may be reused or pre-filled for future orders at the same shop when the customer provides the same WhatsApp number.
- A WhatsApp number must not expose another shop's customer history.
- Traditional customer username/password accounts are not required by the current MVP concept.

Phone-number normalization and formatting, detailed recognition behavior, privacy handling, and authentication mechanism are **Not Finalized / Require Decision**. The Shop-scoped WhatsApp identity rule and pre-order Customer creation are approved.

## 13. Cart Rules

- A cart is associated with a specific shop context.
- Products added to a cart belong to its intended shop/catalog context.
- A cart must not mix unrelated shops unless a future approved requirement introduces multi-shop carts.
- An initially anonymous cart may become associated with the Shop-specific Customer when the customer first provides their WhatsApp number.
- Customer creation may therefore occur before checkout and before Order creation.
- Prices and availability are validated appropriately before order creation.

Cart persistence, guest-session mechanism, expiration, quantity limits, and price-snapshot behavior are **Not Finalized / Require Decision**.

## 14. Checkout Rules

The current checkout concept requires customer name and WhatsApp number, selected products/variants, quantities, and a pickup or home-delivery choice. Home delivery requires an address. Pickup does not require a delivery address unless another approved requirement says otherwise.

Do not invent additional mandatory checkout fields. Address validation remains subject to domain decisions. Merchant handles delivery eligibility manually; no delivery-radius or delivery-area configuration exists in MVP.

## 15. Delivery / Pickup and Business Hours Rules

- Shop supports Home Delivery and Pickup. Merchant can independently enable or disable each option. A disabled option is hidden from customers.
- Merchant controls the delivery charge and may change it at any time. Merchant decides whether a delivery charge of ₹0 is allowed for the Shop. Delivery charge is shown to the customer at checkout.
- No delivery radius or delivery-area configuration exists in MVP. Merchant handles delivery eligibility manually.
- Pickup means the customer collects the order from the Shop. Home Delivery requires a delivery address.
- Business hours are an MVP feature managed by the Merchant. One opening time and one closing time apply to each configured Shop schedule; multiple daily time slots are not part of MVP.
- Merchant can change business hours at any time and can temporarily mark the Shop closed outside normal operating hours.
- While closed, customers see **"Shop Closed"** and can still place orders.
- The MVP does not include centralized delivery-partner management.
## 16. Order Rules

The product requirements describe this conceptual order lifecycle:

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

They also describe the alternative:

```text
PENDING → REJECTED
```

This is not a finalized, complete state machine. Do not infer additional transitions or cancellation, refund, timeout, return, or partial-fulfillment states. The merchant operates order acceptance, rejection, and status updates through the merchant ERP/web interface.

## 17. Merchant Order Operations

- Incoming orders are visible to the appropriate merchant/shop.
- The merchant reviews an order and may accept or reject it according to the approved workflow.
- The merchant may progress an accepted order through the approved fulfillment lifecycle.
- A merchant must not operate on another shop's orders.
- WhatsApp is not the primary order-operation interface; merchant operations occur through the ERP/web interface.

Do not define exact UI behavior or API endpoints here.

## 18. Customer Order Rules

Customers should be able to review their cart, submit an order, provide required checkout information, select pickup or delivery, and receive appropriate order communication. The exact customer order-history experience is **Not Finalized / Requires Decision**.

## 19. Payment Rules

For the MVP, payment is merchant-handled. A merchant may share UPI, UPI QR, or other payment instructions. The platform does not process centralized online payments in the MVP, and no payment gateway is approved.

Payment gateway, automatic payment verification, refunds, settlements, and commission/monetization are **Not Finalized / Require Decision**.

## 20. WhatsApp Rules

WhatsApp is primarily a communication and notification channel. It may be used for order notifications, acknowledgements, and merchant/customer communication when explicitly approved.

It is not the primary merchant interface for accepting or rejecting orders, changing order status, or managing inventory. The merchant ERP/web interface remains the operational interface. Do not select a WhatsApp provider or integration architecture here.

## 21. Merchant Accounts

Merchant credentials may be shared with employees/staff in MVP. Individual employee accounts, roles, and individual staff permissions are not required; they may be introduced later. Merchant may log in from multiple devices. Merchant logout invalidates the current session/token according to the eventual authentication implementation. Failed login attempts have no special application-level lockout rule in MVP; normal authentication security still applies.

Merchant status is `ACTIVE` or `DEACTIVATED`. Deactivation immediately prevents Merchant login and platform access; Merchant data is not permanently deleted. A deactivated Merchant cannot be reactivated in MVP. Deactivating the Merchant account automatically deactivates their Shop. Both Merchant and Super Admin can change or reset the Merchant password. Standard platform password rules apply. The authentication technology and exact session/token implementation remain unresolved technical decisions.

## 22. Campaign / Advertising Rules

Super Admin can manage platform campaigns/advertisements according to the approved product concept. Campaigns may be platform-level or shop-related, subject to the finalized domain design.

Advertising pricing, targeting algorithms, campaign bidding, monetization, and ad ranking are **Not Finalized / Require Decision** unless explicitly approved.

## 23. Analytics Rules

Merchant analytics must be shop-scoped. Conceptual merchant metrics may include orders, sales/revenue-related metrics, top products, rejected/completed orders, average order value, and customers. MVP does not define a low-stock threshold or low-stock metric/alert.

Platform analytics may include shops, orders, sales, shop performance, product performance, customers, and campaigns. Do not define exact metric formulas unless they have been finalized.

## 24. Cross-Domain Business Invariants

The following invariants must hold across domains:

- An order belongs to one shop context.
- Merchant-specific pricing belongs to the appropriate shop.
- Shop-specific customer identity remains within that shop.
- Inventory belongs to the appropriate shop/product context.
- Merchant operations cannot cross shop boundaries.
- Customer-facing catalog access is tied to the intended shop.
- Tenant-specific operations must not accidentally mutate platform-global master data.

These are business invariants, not a definition of database constraints or schema.

## 25. Historical Data

When a business operation changes current information, consider whether historical records must preserve the state that existed when an event occurred. Relevant examples may include order information, the pricing used for an order, the customer/order relationship, and merchant/shop state.

The exact snapshot strategy and historical-data requirements remain **Not Finalized / Require Decision**, subject to the approved Shop deletion rule that deletes Shop Orders.

## 26. Deactivation / Deletion

Shop lifecycle and deletion rules are approved:

- Shop status is `ACTIVE` or `DEACTIVATED`.
- Merchant can deactivate their Shop. Super Admin cannot deactivate it; only Super Admin can reactivate it.
- A deactivated Shop cannot be accessed by customers or by the Merchant. Its data remains until permanent deletion.
- Merchant account deactivation automatically deactivates the Merchant's Shop.
- Merchant can permanently delete the Shop, including when it has existing orders. Deletion requires confirmation and a clear warning that Shop data and orders will be deleted.
- Shop deletion is permanent. Shop data, including Shop products and orders, is deleted, and the Shop QR/public link becomes unavailable immediately. Merchant may then immediately create a new Shop.

Deletion and retention rules for other business entities remain unresolved. Do not infer physical database deletion mechanics from these business rules.
## 27. Business Rules vs Implementation

A business rule states required behavior:

```text
Business rule:
"Merchant A cannot access Shop B orders."
```

Implementation is a separate technical decision:

```text
Implementation:
"The application may enforce this through tenant-scoped querysets,
authorization checks, database constraints, or another approved design."
```

This document defines the business rule, not a premature implementation choice.

## 28. Unresolved Business Decisions

The following require product/business approval and must not be answered by assumption:

- Customer phone-number normalization and formatting.
- Physical representation of Shop Products and any Master Product selection/link reference.
- Product/variant schema, attribute representation, image storage, and inventory mapping.
- Historical Order product snapshot/reference strategy.
- Detailed partial-quantity behavior with Orders.
- Complete Order state machine and cancellation scenarios beyond accepted-order cancellation stock restoration.
- Inventory technical/database representation, aggregate Product stock recalculation, and transaction/concurrency implementation.
- Complete order state machine.
- Cancellation behavior.
- Refund behavior.
- Customer order-history behavior.
- Payment verification.
- Campaign rules.
- Analytics formulas.
- Deletion and retention policies for entities other than the approved Shop deletion behavior.
- Historical-data requirements outside approved Shop lifecycle and deletion rules.

## 29. AI Agent Business-Rule Workflow

Before implementing business behavior, an AI agent MUST:

1. Read `AGENTS.md`.
2. Read `.ai/project-context/product.md`.
3. Read `.ai/project-context/architecture.md`.
4. Read this business-rules file.
5. Read the relevant domain documentation.
6. Read relevant engineering skills.
7. Identify the applicable business rule.
8. Verify whether it is finalized.
9. Ask for clarification if it is not finalized.
10. Never invent business behavior to complete implementation.
11. Add or update tests for approved business rules.
12. Update documentation when an approved business-rule decision changes.

## 30. Documentation Change Rule

When a business decision changes:

1. Update the canonical business-rule documentation.
2. Update affected domain documentation.
3. Update architecture or ADR documentation if the decision has architectural impact.
4. Update tests and implementation.
5. Ensure all sources remain consistent.

Do not silently encode business decisions only in application code.

## 31. Git Workflow

Follow the mandatory repository workflow:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/<short-description>
```

Never work directly on `main`. Inspect existing working-tree changes first and do not discard them automatically. Destructive Git commands require explicit approval. Ask for a task ID before creating a new task branch when none is provided. Keep commits small and logical, never commit secrets, push task branches, and create PRs against `main`. Do not force-push or rewrite history without authorization. Follow `AGENTS.md` for the complete workflow.

## 32. What This File Does Not Define

This document does not define database schema, Django models, API endpoints, serializers, authentication, permission classes, infrastructure, implementation architecture, specific third-party providers, or unresolved business decisions. Those must be defined in the appropriate specifications and approved before implementation.

## Final Requirement

Create only `.ai/project-context/business-rules.md`. Do not modify application code, models, migrations, APIs, authentication, permissions, or infrastructure. Do not invent or silently finalize a business rule not supported by approved product requirements.
