**# Cross-Domain Model Relationships Specification**

Authorization actors, permitted resource operations, and current enforcement status are summarized in `.ai/project-context/authorization-matrix.md`. Relationships below describe data and business boundaries; a relationship alone does not grant access.

**## 1. Purpose**

This document defines the conceptual relationships between business entities owned by the Grocery Platform's Django domain applications. It is the bridge between domain specifications and a future Database Design Specification.

\`\`\`text

Domain Specifications

        ↓

model-relationships.md

        ↓

Database Design Specification

        ↓

Django Models

        ↓

Migrations

\`\`\`

This document answers which domain owns an entity, how entities relate conceptually, which relationships express ownership or authorization, which relationships are business interactions, which cardinalities are known, and which decisions remain open.

It does not define Django fields, foreign keys, primary keys, constraints, indexes, deletion behavior, migrations, APIs, serializers, views, services, tests, or physical database structure.

**## 2. Relationship Classification**

Every relationship in this document uses one or more of the following classifications.

**### Business relationship**

A domain event or workflow connects two domains. For example, an Order may trigger a Notification. A business relationship does not automatically require a persistent database reference.

**### Data ownership relationship**

One business entity owns or scopes another entity. For example, a Shop owns the business context within which a shop-specific Customer exists. Ownership usually needs a durable and trustworthy tenant path, but the physical representation remains a later design decision.

**### Reference relationship**

One entity refers to another entity for meaning or configuration. For example, a shop catalog entry may reference a platform Master Product. Reference direction must not be confused with ownership direction.

**### Authorization relationship**

An actor is authorized to access or operate within another entity's context. For example, a User may be authorized to access a Shop. Authorization is distinct from business ownership and must follow the final authentication and membership decisions.

**### Reporting dependency**

Analytics consumes facts from another domain to derive metrics. A reporting dependency does not make Analytics the owner of the source facts or require a direct foreign key.

**## 3. Status Vocabulary**

Relationship status is intentionally limited to these labels:

\- **\*\*APPROVED:\*\*** The source of truth establishes the business relationship sufficiently for the relationship itself to be treated as required.

\- **\*\*CONCEPTUAL:\*\*** The relationship is supported as a useful business concept, but cardinality, representation, or implementation details remain open.

\- **\*\*UNRESOLVED:\*\*** The source of truth does not establish the relationship or leaves a business decision open. It must not be implemented by assumption.

\- **\*\*NOT APPLICABLE:\*\*** The connection is explicitly outside the domain boundary or is not a business relationship.

A relationship can be conceptually real while its database representation remains unresolved.

**## 3A. Cardinality Vocabulary**

Relationship cardinality must use one of these forms:

\- \`1 → 1\`

\- \`1 → many\`

\- \`many → 1\`

\- \`many ↔ many\`

\- \`TBD\`

The presence of \`1 → 1\` in the vocabulary does not assert that any current domain relationship is one-to-one. No one-to-one relationship is approved by the current source documents.

**## 4. Central Tenant Principle**

\> **\*\*Shop is the primary tenant boundary for merchant-owned business data.\*\***

Every tenant-owned entity must have a clear, trustworthy, server-derived path to its Shop context before implementation. A client-provided \`shop_id\`, object identifier, URL, or filter is not proof of authorization.

The conceptual tenant tree is:

\`\`\`text

Shop

 ├── Shop catalog / merchant product configuration

 ├── Inventory

 ├── Shop-specific customers

 ├── Cart

 ├── Orders

 ├── Platform-owned Campaign display scope (no Shop ownership)

 ├── Notifications with shop context

 └── Analytics reporting context

\`\`\`

Not every entity must have a direct Shop reference. The final design must nevertheless explain the tenant path and prevent cross-shop access through direct, related, aggregated, cached, exported, scheduled, or background operations.

**## 5. Application Ownership Map**

\| Django app | Primary business concepts | Ownership status |

\|---|---|---|

\| \`users\` | User, Merchant, authentication/access and membership concepts | Merchant business relationship approved; technical User representation unresolved |

\| \`shops\` | Shop and shop business context | Owns Shop concept and tenant context |

\| \`catalog\` | Platform master catalog, merchant catalog, products, variants, categories | Owns catalog concepts; exact identity relationships unresolved |

\| \`inventory\` | Shop-scoped Product/Variant stock state | Owns current Shop-scoped stock state; Product/Variant rules are approved |

\| \`customers\` | Shop-specific customers and customer contact context | Owns shop-specific customer identity concept |

\| \`cart\` | Cart and CartItem | Owns current shopping state |

\| \`orders\` | Order and OrderItem | Owns historical purchase transaction |

\| \`campaigns\` | Campaign and promotional configuration | Owns platform campaign content and Shop display scope; business rules finalized |

\| \`notifications\` | Notification and delivery-related concepts | Owns communication/delivery facts; source references unresolved |

\| \`analytics\` | Reporting and derived metric concepts | Owns reporting interpretation, not source business facts |

No additional application is introduced by this relationship specification.

**## 6. Core Conceptual Map**

```text
Merchant
   ↓ may own only one Shop at a time
Merchant login credentials
   ↓ provide access to Merchant's Shop; credentials may be shared with staff
Shop (primary tenant boundary)
   ├── Shop catalog
       ├── Shop product/listing
       ├── Product variant
       └── Category relationship
   ├── Inventory
   ├── Shop-specific Customer
       └── Cart -> CartItem -> Catalog product/variant reference
   ├── Order
       └── OrderItem -> historical product/variant meaning
   ├── Campaign display scope (platform-owned; Shop is not the owner)
   ├── Notification delivery context
   └── Analytics reporting context

Platform Master Catalog
   └── Master Product

Each Shop Catalog independently owns its Shop Products, variants, categories, brands, and custom attributes.

Platform Campaign
   └── may target shops or catalog concepts, subject to approved rules

Super Admin
   └── platform-level authorization and management, subject to final access design
```

The Merchant-to-Shop relationship and Shop tenant boundary are approved business relationships. User and Merchant identity representations are documented below. This is a conceptual map, not a schema diagram.

**## 7. Users, Merchant, and Shop**

The source documents distinguish three concepts:

```text
User
    = platform identity/person accessing the system

Merchant
    = business/operator identity representing the grocery business

Shop
    = store/tenant operated by a Merchant
```

These concepts must not be collapsed into one entity. Merchant means the Shop Owner / business owner and is separate from User and Shop. In MVP, one Merchant may own only one Shop at a time, and each Shop belongs to exactly one Merchant. After permanent deletion, the same Merchant may create a new Shop with a new identity and public QR/link. Merchant login credentials provide access to that Merchant's Shop and may be shared with employees/staff. Individual employee accounts, Merchant memberships, roles, and staff permissions are not required in MVP; individual users and roles may be introduced later.

### User / Merchant login representation

- Meaning: The Merchant has one login/account in MVP, represented by one `MERCHANT` User and one Merchant profile.
- Classification: Identity relationship.
- Cardinality: One-to-one between Merchant profile and User.
- Ownership: Merchant remains a separate business entity, not the same thing as User.
- Status: **IMPLEMENTED** for the User/profile relationship; Merchant-to-Shop remains separate.

### Super Admin identity

- Meaning: A Super Admin is a platform-level User that can be created by another Super Admin.
- Identity: Super Admin login accepts email or mobile number with a password. Each identifier is globally unique across all User accounts.
- Recovery: Super Admin may self-recover through verified registered email or mobile. Administrative reset is initiated only by another authenticated Super Admin after password re-entry; the audit record identifies the initiator and request time. The affected Super Admin chooses a new password from a single-use, expiring link or code sent through a registered contact. Successful resets invalidate that User's sessions and refresh tokens.
- Status: **APPROVED** for recovery/reset behavior; exact provider and technical representation remain implementation decisions.
- Shop ownership: Super Admin does not automatically own a Shop.

### Merchant → Shop

- Meaning: Merchant owns and operates their Shop.
- Classification: Business ownership/association.
- Cardinality: `1 → 1 Shop at a time`.
- Ownership: A Merchant may own only one Shop at a time; each Shop belongs to exactly one Merchant and cannot exist without a Merchant. After permanent deletion, the same Merchant may create another Shop with a new identity and public QR/link. Ownership transfer is not supported in MVP. Shop deletion preserves the Merchant account and credentials; the Merchant may create a replacement Shop with a new identity and public QR/link.
- Status: **APPROVED**.

### Merchant credentials → Shop

- Meaning: Merchant login credentials grant access to the Merchant's Shop.
- Classification: Authorization/access relationship.
- Cardinality: One Merchant login/account and one Merchant profile per Merchant in MVP; one Shop at a time.
- Ownership: Credentials may be shared with employees/staff. No separate employee User or Merchant membership is required in MVP. Access is limited to the Merchant's Shop and does not make User the Shop owner.
- Status: **APPROVED** for the business access rule; profile lifecycle and Shop access enforcement remain unresolved.

### Shop lifecycle and public access

- Merchant can deactivate their own Shop; Super Admin may suspend or reactivate it under existing rules. Super Admin cannot browse or edit private Shop information. Existing permanent deletion authority belongs to Super Admin, with the confirmation safeguards already documented.
- Merchant account deactivation automatically deactivates the Shop; this does not remove the Merchant's separate authority to deactivate their own Shop. Deactivated Shop data remains until deletion; customers and Merchant cannot access the deactivated Shop.
- Shop QR/public access uses a system-generated public link, not the Shop ID. A deactivated Shop QR remains valid and shows the Shop as unavailable. Reactivation requires a newly generated QR; the old QR does not work.
- Super Admin may permanently delete the Shop, including when it has Orders, using the existing confirmation safeguards. Shop products and Orders are deleted; the public link and QR become unavailable immediately. The same Merchant may then create a new Shop with a new identity and QR/link. Shop deletion preserves the Merchant login and credentials. The same Merchant may create a replacement Shop with a new identity and public QR/link; deleted Shop data is not associated with or exposed through that replacement.
- Shop remains the primary tenant boundary.



The required business principle remains:

```text
Merchant
   ↓ owns and operates (1 → 1)
Shop
   ↑ accessed through Merchant login credentials
Merchant; credentials may be shared with staff
```

This must not be collapsed into:

```text
User = Merchant = Shop
```

Future individual users/roles may be introduced without changing the Shop tenant boundary.

**## 8. Shop as Tenant Context**

Shop is the central tenant context for merchant-owned data. The Shop domain owns Shop identity, profile, lifecycle concepts, and the tenant boundary. Other domains own their own business entities within that context.

A relationship from a tenant-owned entity to Shop is an ownership or scoping relationship, not necessarily a direct database foreign key. The later database design must decide whether direct Shop references are needed for integrity, query safety, or authorization.

A merchant must never access another Shop's data through a related entity, direct identifier, aggregation, cache, export, admin interface, management command, or background operation.

**## 9. Shop → Catalog**

\- Meaning: A Shop has a shop-specific catalog context containing offerings and merchant configuration.

\- Classification: Data ownership relationship.

\- Cardinality: \`1 → many\` for Shop to shop catalog entries; exact catalog entity is unresolved.

\- Tenant scope: Tenant-owned.

\- Status: **\*\*CONCEPTUAL\*\***.

\- Database representation: Likely requires an explainable Shop path, but exact entities and fields are not finalized.

The Catalog domain distinguishes platform Master Catalog data from a Shop's catalog/listing configuration. A Shop's catalog is not the same thing as the global master catalog.

**## 10. Shop → Inventory**

- Meaning: Inventory belongs to a Shop and stores current stock for that Shop's sellable Products and Variants.
- Classification: Shop-scoped data ownership.
- Cardinality: Shop to inventory records is conceptually one-to-many; physical representation remains a database-design decision.
- Tenant scope: Tenant-owned and isolated by Shop.
- Status: **APPROVED** as a business rule.

A Merchant may modify inventory only in the Merchant's authorized Shop. One Shop must never read or modify another Shop's inventory. Catalog identifiers supplied by a client do not bypass Shop authorization.
**## 11. Shop → Customer**

\- Meaning: A Shop scopes a customer identity and customer history.

\- Classification: Data ownership relationship.

\- Cardinality: \`1 → many\` Shop to Customers; \`many → 1\` Customer to Shop.

\- Tenant scope: Tenant-owned.

\- Status: **\*\*APPROVED\*\*** as a business concept.

Each Customer profile belongs to one Shop, and Order history remains Shop-scoped. WhatsApp numbers are globally unique across Customers, Merchants, and Super Admins; a number cannot identify profiles at multiple Shops or overlap an authenticated User's mobile number. The approved repeat-customer/order-history flow must not require OTP, but a WhatsApp number alone is not proof of identity and must not expose Orders. The approved mechanism is a customer-specific access link/token scoped to the relevant Customer and Shop. Its expiry, revocation, generation, delivery, storage, and protections against unauthorized reuse are technical design requirements to settle before implementation.

The physical identity key, matching behavior, and database representation remain later design decisions.

**## 12. Shop → Cart**

\- Meaning: A Cart represents current shopping state within one Shop context.

\- Classification: Data ownership/scoping relationship.

\- Cardinality: \`1 → many\` is possible; active-cart cardinality is unresolved.

\- Tenant scope: Tenant-owned.

\- Status: **\*\*CONCEPTUAL\*\***.

The Cart specification establishes that a cart cannot mix products from different Shops. It does not decide whether a customer has one active cart per Shop, multiple carts, an empty cart before the first item, or a persistent cart at all.

A direct Shop relationship may later be needed for safe isolation, but it must not be assumed before Cart persistence and identity are approved.

**## 13. Shop → Order**

\- Meaning: An Order belongs to one Shop transaction context.

\- Classification: Data ownership relationship.

\- Cardinality: \`1 → many\` Shop to Orders; \`many → 1\` Order to Shop.

\- Tenant scope: Tenant-owned.

\- Status: **\*\*APPROVED\*\*** as a business concept.

The Orders domain states that every Order belongs to exactly one Shop and must not belong to multiple Shops. This is a strong tenant and historical boundary. The physical field, key, and constraints remain database-design decisions.

**## 14. Platform → Campaign / Campaign display scope**

Campaign is a platform-level promotional content object, not a Shop-owned promotional/discount engine.

- Meaning: A platform Campaign may be displayed across all Shops or selected Shops.
- Classification: Display targeting/scope relationship, not Shop ownership.
- Cardinality: Potentially `many ↔ many` for selected-Shop display scope.
- Tenant scope: Platform-global campaign with optional Shop display scope.
- Status: **APPROVED MVP BUSINESS RULE**; physical representation remains a technical decision.

Only Super Admin creates campaigns in MVP. A campaign can advertise anything, including products, services, brands, or unrelated businesses. Any product/category/shop mention in advertisement copy is content, not a required relational target.

A Campaign does not control Shop price, inventory, availability, checkout totals, Orders, or discounts. Merchant-created campaigns are not part of MVP.

**## 15. Shop → Notification**

\- Meaning: A Notification may carry the Shop context of the business event, recipient, or merchant delivery target.

\- Classification: Business and tenant-scoping relationship.

\- Cardinality: \`1 → many\` is conceptually possible; final persistence is unresolved.

\- Tenant scope: Usually tenant-scoped for merchant/order notifications; platform scope is possible for platform messages.

\- Status: **\*\*CONCEPTUAL\*\***.

Notifications must preserve tenant isolation. For merchant order notifications, the tenant path is:

```text
Order
  ↓
Shop
  ↓
Notification
  ↓
Shop's one configured merchant WhatsApp number
```

A Shop A order must never produce a merchant notification to Shop B's configured WhatsApp number. For customer order-status notifications, the tenant path is:

```text
Order
  ↓
Shop
  ↓
Shop-specific Customer
  ↓
Customer WhatsApp number
```

The Notifications specification does not require every Notification to have a stored direct Shop reference, because its Shop context may be derived from an underlying business event or recipient relationship. Recipient resolution must never search globally by WhatsApp number in a way that could cross Shop boundaries.

**## 16. Shop → Analytics Context**

\- Meaning: Analytics reports facts for a Shop or aggregates facts across Shops for an authorized platform actor.

\- Classification: Reporting dependency and authorization scope.

\- Cardinality: \`1 → many\` reporting results conceptually; stored aggregate cardinality is unresolved.

\- Tenant scope: Shop-specific or platform-wide according to actor authorization.

\- Status: **\*\*CONCEPTUAL\*\***.

Analytics does not own Shop or source business facts. Merchant analytics must be shop-scoped. Platform analytics may aggregate across Shops only for an authorized platform-level actor.

**## 17. Platform Master Catalog**

The Catalog domain distinguishes:

\`\`\`text

Platform Master Catalog

    = global reusable product knowledge

Shop Catalog

    = shop-specific sellable listing and configuration

\`\`\`

The Master Catalog is platform-global. It is not itself a Shop's sellable catalog and does not imply that every Shop offers every Master Product.

Conceptual entities include Master Product, independent Shop Product, Product Variant, Shop Category, Shop Brand, and custom attributes. Exact model names and physical structure are implementation decisions. Shop Catalogs are fully Merchant-controlled and independent of the platform-global Master Catalog.

**## 18. Shop Product → Variant**

- Meaning: A Shop Product may be directly sellable or have variants; product-level and variant-level information are supported.
- Classification: Shop-owned product information.
- Cardinality: Optional and potentially multiple; exact database representation is unresolved.
- Tenant scope: Shop-specific.
- Status: Business behavior finalized; physical model remains a technical decision.

Merchants manage variant creation, editing, and deletion, including variant name, price, SKU, image, and custom attributes. Merchants may add Shop-specific variants to a Shop Product selected from the Master Catalog.

**## 19. Master Product ↔ Shop Product**

- Meaning: A Merchant may select a Master Product when creating a Shop Product. A Shop Product may also be created directly by the Merchant without a Master Product.
- Classification: Optional source/reference relationship, not ownership or synchronization.
- Cardinality: One Master Product can be selected by multiple Shops; exact physical reference cardinality is not specified.
- Tenant scope: Platform-global Master Product to independent Shop-specific representation.
- Status: Business independence finalized; physical reference representation unresolved.

Each Shop Product is independent. Master Product updates do not automatically update Shop Products, and Master Product deletion does not delete or impair them. Super Admin may promote a Merchant-created product into the Master Catalog; promotion does not automatically link, replace, or update the originating Shop Product. Other Merchants may select the promoted Master Product. No approval/rejection workflow is defined.

**## 20. Shop Product ↔ Category, Brand, and Attributes**

Categories and brands belong to a Shop Catalog and are controlled by the Merchant. Categories support subcategories, and a product may belong to multiple categories. Deleting an assigned category leaves its products uncategorized. A Shop Product may have a Shop-specific brand and multiple custom attributes with multiple values; variants may also have custom attributes. Physical cardinalities and schema are implementation decisions. No Master Category or global attribute system is required by these decisions.

Campaign → Category: **NOT APPLICABLE** as a required relationship in MVP.
**## 22. Shop Catalog Entry → Inventory**

- Meaning: Inventory stores stock state for a Shop's sellable Product or Variant.
- Classification: Shop-scoped stock state associated with Catalog definitions.
- Cardinality: A non-variant Shop Product has Product-level stock. For a variant product, Variant quantities are authoritative and Product-level quantity is a derived aggregate. Physical representation remains a database-design decision.
- Tenant scope: Tenant-owned.
- Status: **APPROVED** as business behavior.

The Merchant may modify non-variant Product stock and individual Variant stock; independent manual changes to aggregate Product stock for a variant-based product are superseded. Inventory respects the Catalog sellable unit, permits decimal quantities, starts at `0` for a new Shop Product or Variant, and cannot fall below `0`. Exact aggregate derivation remains a technical decision. Removing a Product or Variant from the Shop Catalog removes its Inventory record; hard-delete/soft-delete mechanics remain technical details.
**## 23. Customer → Cart**

- Meaning: A Cart represents current shopping state within a Shop.
- Classification: Data ownership/scoping relationship.
- Cardinality: `TBD`.
- Tenant scope: Tenant-owned.
- Status: **CONCEPTUAL**.

A permanent Shop-specific Customer record is created when the customer first provides their WhatsApp number for that Shop. An initially anonymous Cart may become associated with that Customer before checkout; an abandoned Cart may therefore be associated with a permanent Customer record.

The Customer is shop-specific and does not require a traditional login/account. Exact cart persistence and identity representation remain database-design decisions.

**## 24. Cart → CartItem**

\- Meaning: A Cart contains the customer's selected catalog items.

\- Classification: Data ownership relationship.

\- Cardinality: \`1 → many\` Cart to CartItems; each CartItem belongs to \`many → 1\` Cart.

\- Tenant scope: Tenant-owned through Cart and its Shop context.

\- Status: **\*\*CONCEPTUAL\*\***.

A CartItem conceptually references a valid Shop catalog product or selected variant and carries requested quantity and applicable current shopping price context. Exact fields, uniqueness, quantity semantics, and price behavior are unresolved.

A CartItem must not reference a product or variant from another Shop. Cart and customer ordering must respect the approved Inventory availability rules; no additional Cart behavior is defined here.

**## 25. CartItem → Catalog Product/Variant**

\- Meaning: A CartItem identifies what the customer selected from the Shop catalog.

\- Classification: Reference relationship.

\- Cardinality: \`many → 1\` for each CartItem to the applicable catalog item; exact product/variant alternatives are unresolved.

\- Tenant scope: Tenant-owned through Cart and Shop catalog context.

\- Status: **\*\*CONCEPTUAL\*\***.

The Catalog domain owns Product and Variant definitions. Cart does not own them. The source does not decide whether a CartItem references Product, Variant, Shop Product, or a composite sellable-item concept in every case.

**## 26. Cart → Order**

The checkout flow is:

```text
Cart
  ↓
Checkout and validation
  ↓
Order creation
  ↓
Order becomes PENDING
```

- Meaning: Cart supplies current shopping intent to Order creation.
- Classification: Business interaction.
- Cardinality: No required persistent relationship.
- Tenant scope: Cart and resulting Order share the same Shop context.
- Status: **APPROVED**.

MVP uses **no persistent Cart → Order relationship**. Cart is temporary/current shopping state. Once checkout successfully creates an Order, it becomes the historical transaction and source of truth unless the Merchant permanently deletes the Shop, which also deletes its Orders.

Do not add a Cart foreign key to Order merely because checkout passed through Cart.

**## 27. Customer → Order**

- Meaning: An Order is associated with the Shop-specific Customer who placed it.
- Classification: Data association plus historical business relationship.
- Cardinality: `1 → many` Customer to Orders; `many → 1` Order to Customer.
- Tenant scope: Tenant-owned.
- Status: **APPROVED**.

There is one current Customer record per customer at a Shop. When the same customer places another order, the current Customer details may be updated.

Orders are retained as historical transactions while the Shop exists. Deleting the Shop also deletes its Orders. The Customer entity is not globally deleted solely because of Shop deletion under the existing Customer rules. A retained Customer entity or history is not automatically transferred to or associated with a replacement Shop. The full Customer profile is not copied into every Order. An Order preserves its historical purchase price and delivery charge, plus order-time information required for historical accuracy.

The repeat-customer/order-history flow does not require OTP, but a WhatsApp number alone must not expose Orders; a customer-specific access link/token scoped to that Customer and Shop is approved; its expiry, revocation, generation, delivery, storage, and unauthorized-reuse protections must be settled before implementation. Merchant can view all historical Orders for the Shop while it exists.

**## 28. Order → OrderItem**

\- Meaning: An Order contains the historical purchased lines in the transaction.

\- Classification: Data ownership relationship.

\- Cardinality: \`1 → many\` Order to OrderItems; each OrderItem belongs to \`many → 1\` Order.

\- Tenant scope: Tenant-owned through Order.

\- Status: **\*\*CONCEPTUAL\*\***, with historical requirement approved.

An OrderItem conceptually includes a product or variant reference, quantity, order-time price, item total, and historical product meaning. The exact snapshot fields and references are database-design decisions.

An OrderItem must not silently change meaning because the current Catalog Product, Variant, price, category, or availability changes later.

**## 29. OrderItem → Catalog Product/Variant**

\- Meaning: An OrderItem identifies the product or variant purchased, while preserving order-time historical meaning.

\- Classification: Reference plus historical snapshot relationship.

\- Cardinality: \`many → 1\` is possible for a current identity reference; exact representation is unresolved.

\- Tenant scope: Tenant-owned through Order; referenced catalog data may be global or shop-specific.

\- Status: **\*\*UNRESOLVED\*\*** for physical representation.

The Orders domain requires historical purchase information but does not choose copied fields, immutable references, snapshots, or another strategy. Analytics and later reporting must use the authoritative historical order facts, not current catalog price reconstruction.

**## 30. Order → Inventory**

- Meaning: Orders reserve, deduct, release, or restore the required Shop inventory quantity according to the finalized flow.
- Classification: Business interaction.
- Cardinality: Physical representation remains a database-design decision.
- Tenant scope: Order and Inventory share the same Shop context.
- Status: **APPROVED** as business behavior. Technical transaction/concurrency behavior remains unresolved.

```text
Order Created
    ↓
Required Quantity Reserved
    ↓
Merchant Accepts
    ↓
Reserved Quantity Becomes Deducted Stock
```

```text
Order Rejected
    ↓
Reserved Quantity Released
```

```text
Accepted Order Cancelled before PREPARING
    ↓
Deducted Quantity Restored
    ↓
Quantity Immediately Available Again
```

Reserved quantity is visible to the Merchant. When requested quantity exceeds what can be fulfilled, the Merchant may manually reduce the fulfillable quantity before acceptance; the Customer is notified and the Order reflects the reduced quantity. No automatic quantity reduction occurs. Rejection and pending Customer cancellation release reserved quantity; eligible Merchant cancellation restores/releases it. Exact transaction/concurrency implementation remains unresolved.
**## 31. Order → Notification**

\- Meaning: An Order may trigger communication about an approved business event.

\- Classification: Cross-domain business relationship.

\- Cardinality: Potentially \`1 → many\` Order to Notifications; final persistence is unresolved.

\- Tenant scope: Notification must preserve the Order's Shop context.

\- Status: **\*\*CONCEPTUAL\*\***.

Orders owns order state and lifecycle events. Notifications owns message preparation, recipient/channel selection, delivery, and delivery status. WhatsApp messages must never accept, reject, cancel, or otherwise change an Order.

The source does not require a persistent Order-to-Notification foreign key. The implementation must not create one solely because an order can trigger a message.

**## 32. Notification → Recipient**

MVP WhatsApp notifications use these approved event and recipient mappings:

1. **Successful Order creation → Merchant WhatsApp and Customer WhatsApp**: notify the Shop's configured merchant number of a new Order and send the Customer an Order-received acknowledgement. The acknowledgement does not mean accepted.
2. **Merchant acceptance → Customer WhatsApp**: communicate acceptance.
3. **Merchant rejection → Customer WhatsApp**: communicate rejection.
4. **Merchant manual quantity reduction before acceptance → Customer WhatsApp**: communicate the adjusted fulfillable quantity.
5. **Pending Customer cancellation → Merchant WhatsApp**: notify the Shop's configured merchant number.
6. **Accepted Merchant cancellation before PREPARING → Customer WhatsApp**: communicate the cancellation outcome.

The Customer/Merchant cancellation and Merchant rejection outcomes follow the Orders specification's existing `REJECTED` state; no separate `CANCELLED` state is added. No WhatsApp notification is required for PREPARING, READY, or COMPLETED in MVP.

- Classification: Delivery and tenant-scoping relationship.
- Cardinality: `TBD`.
- Tenant scope: Shop or underlying Order context.
- Status: **APPROVED**.

For MVP, each Shop has exactly one configured merchant WhatsApp number for merchant-side order notifications. Multiple merchant WhatsApp numbers per Shop are out of scope for MVP. Customer notifications target the WhatsApp number belonging to the relevant Shop-specific Customer context.

WhatsApp numbers are contact information, not authentication or authorization. Customer recipients resolve from the relevant Shop-specific Customer record. WhatsApp is notification-only: it must never accept, reject, cancel, or otherwise change Orders. Notification delivery failure must not change the Order state; a message is not reported delivered without provider confirmation. Prevent duplicates for the same originating event and recipient, use bounded retries for transient failures, and do not retry permanent failures, subject to provider capability. Use fixed reviewed templates and minimal content/history; retention period remains undecided.

The exact recipient storage, phone representation, provider, message templates, delivery infrastructure, retry architecture, and API behavior remain later design decisions.

**## 33. Campaign Relationships**

Campaigns owns platform advertising content and display scope. Campaigns does not own Catalog Products, Categories, Shops, Orders, or Notifications merely because advertisement content mentions them.

### Campaign → Platform

- Meaning: A platform-level Campaign is created and managed by Super Admin.
- Status: **APPROVED** as an MVP business concept.

Only Super Admin creates and manages campaigns in the MVP.

### Campaign ↔ Shop

- Meaning: A Campaign may be displayed across all Shops or selected Shops.
- Cardinality: Potentially `many ↔ many` for selected-Shop display scope.
- Classification: Display targeting/scope.
- Status: **APPROVED MVP DISPLAY SCOPE**; exact schema/cardinality representation is a technical decision.

A Shop is not the owner of a platform Campaign merely because the Campaign is displayed on that Shop.

### Campaign → Product / Category / Brand / Shop mentions

- Status: **NOT APPLICABLE** as persistent targeting relationships in MVP.

Campaign advertisement content may mention a product, category, brand, Shop, service, or unrelated business. Such mentions are content only and do not create persistent Catalog targeting relationships.

Campaigns are not a discount engine and do not control product price, inventory, availability, or orders.

**## 34. Campaign → Notification**

- Meaning: Campaign may eventually be used in promotional communication if separately approved.
- Classification: Business interaction.
- Status: **EXCLUDED FROM MVP**.

Campaign-triggered notifications are excluded from the MVP. Any future requirement needs separate approval. Do not add a persistent relationship or provider behavior by assumption.

**## 35. Analytics Relationships**

Analytics queries source domain data directly in MVP.

```text
Orders ──────────┐
Catalog ─────────┤
Inventory ───────┤
Customers ───────┤
Campaigns ───────┤
Notifications ───┤
Shops ────────────┘
                 ↓
             Analytics
```

Analytics is a reporting/interpretation layer and does not own source business facts.

### Orders → Analytics

- Meaning: Analytics derives order counts, status reporting, order values, AOV, and product metrics from Orders.
- Status: **CONCEPTUAL**.

### Catalog → Analytics

- Meaning: Analytics uses approved product, variant, category, and Shop listing data for reporting.
- Status: **CONCEPTUAL**.

### Inventory → Analytics

Analytics may report current stock facts. MVP defines no low-stock threshold, metric, or alert, and maintains no persistent movement ledger.
- Status: **CONCEPTUAL**.

### Customers → Analytics

- Meaning: Analytics derives Shop-specific customer metrics.
- Status: **CONCEPTUAL**.

### Campaigns / Notifications → Analytics

- MVP analytics queries approved source-domain data directly; this does not approve metric formulas or change source-domain ownership.
- Campaign attribution and Notification delivery analytics are **EXCLUDED FROM MVP**; future reporting requires separate approval. Do not retain aggregates from permanently deleted Shops without a separately approved retention policy.

No separate analytics database or duplicated fact tables is required for MVP.

**## 36. Master Relationship Table**

| From | To | Relationship meaning | Cardinality | Tenant scope | Classification | Status |
|---|---|---|---|---|---|---|
| Merchant | Shop | Merchant owns one Shop at a time; may create a new Shop after permanent deletion | `1 → 1 Shop at a time` | Shop | Business ownership | **APPROVED** |
| Merchant credentials | Merchant's Shop | Merchant login grants access; credentials may be shared with staff | `1 → 1 Shop at a time` | Shop access | Authorization | **APPROVED** |
| User | Merchant | One-to-one Merchant profile; contact login identifiers live on User | 1-to-1 | Platform/access | Identity | **IMPLEMENTED** |
| User | Super Admin | Platform identity accepts globally unique email or mobile login | Multiple Users | Platform | Identity | **APPROVED** |
| Shop | Shop Catalog | Shop owns catalog context | `1 → many` | Tenant | Ownership | **CONCEPTUAL** |
| Master Product | Shop Product | Optional selection/source; independent Shop-specific representation | One Master Product may be selected by multiple Shops; physical link unresolved | Global → tenant | Reference, not ownership/sync | **APPROVED business rule** |
| Shop Product | Variant | Optional Shop-specific variants; product may also be directly sellable | Optional / potentially many; exact schema unresolved | Tenant | Ownership/configuration | **APPROVED business rule** |
| Shop Product | Category, Brand, Attributes | Shop-specific product information managed by Merchant | Multiple categories supported; remaining physical cardinalities unresolved | Tenant | Ownership/configuration | **APPROVED business rule** |
| Shop | Inventory | Shop owns stock context | `1 → many` | Tenant | Ownership | **APPROVED** |
| Shop Product/Variant | Inventory | Product/Variant and aggregate stock as defined by Catalog and Inventory rules | Product without variants: Product stock; with variants: authoritative Variant stock plus derived Product aggregate | Tenant | Business association | **APPROVED business rule** |
| Shop | Customer | Customer identity is scoped to Shop | `1 → many` | Tenant | Ownership | **APPROVED** |
| Customer | Cart | Cart is current customer/shop state | `TBD` | Tenant | Ownership/scoping | **CONCEPTUAL** |
| Shop | Cart | Cart cannot cross Shop | `1 → many` possible | Tenant | Scoping | **APPROVED** |
| Cart | CartItem | Cart contains selected items | `1 → many` | Tenant | Ownership | **CONCEPTUAL** |
| CartItem | Product/Variant | Item references catalog selection | `many → 1` | Tenant | Reference | **CONCEPTUAL** |
| Customer | Order | Shop/customer-context Customer has historical Orders | one-to-many | Tenant/customer context | Association | **APPROVED** |
| Shop | Order | Order belongs to one Shop; deleting the Shop deletes its Orders | one-to-many | Tenant | Ownership and deletion outcome | **APPROVED business rule** |
| Cart | Order | Cart supplies checkout intent; no persistent link | `TBD` persistent | Tenant | Business interaction | **APPROVED** |
| Order | OrderItem | Order contains historical lines | `1 → many` | Tenant | Ownership | **CONCEPTUAL** |
| OrderItem | Product/Variant | Historical purchase references item meaning | `many → 1` possible | Tenant/global reference | Historical/reference | **CONCEPTUAL** |
| Order | Inventory | Creation reserves; acceptance deducts; rejection, pending Customer cancellation, or pending expiry releases; expiry uses `REJECTED`; eligible Merchant cancellation restores/releases; Merchant manually adjusts insufficient quantity | Physical mapping TBD | Tenant | Business interaction | **APPROVED business behavior** |
| Order | Payment status | Order has `PAID` / `UNPAID` status; only Merchant updates it | Order context; physical representation TBD | Tenant | Business state | **APPROVED business rule** |
| Order | Notification | Seven approved Order events may trigger notifications: new Order, received acknowledgement, accepted, rejected, quantity reduced, Customer cancellation, Merchant cancellation | `1 → many` possible | Tenant | Business interaction | **APPROVED business behavior** |
| Notification | Recipient | Merchant messages resolve to the Shop's configured merchant WhatsApp number; customer messages resolve to the relevant Shop-specific Customer WhatsApp number | `TBD` | Tenant | Delivery/tenant-scoping | **APPROVED** |
| Campaign | Shop | Campaign may display across all or selected Shops | `many ↔ many` possible | Platform/display scope | Targeting/display | **APPROVED BUSINESS SCOPE; schema conceptual** |
| Campaign | Product | Advertisement content may mention products; no persistent target | N/A | Platform | Content only | **NOT APPLICABLE** |
| Campaign | Category | Advertisement content may mention categories; no persistent target | N/A | Platform | Content only | **NOT APPLICABLE** |
| Campaign | Notification | Campaign-triggered notifications excluded from MVP | N/A | N/A | Business interaction | **EXCLUDED FROM MVP** |
| Orders | Analytics | Analytics derives order reporting | `many → analytics` | Tenant/platform | Reporting dependency | **CONCEPTUAL** |
| Catalog | Analytics | Analytics uses product dimensions | `many → analytics` | Tenant/platform | Reporting dependency | **CONCEPTUAL** |
| Inventory | Analytics | Current stock facts may be reported; no low-stock threshold or movement ledger | Reporting relationship | Tenant/platform | Reporting dependency | **CONCEPTUAL** |
| Customers | Analytics | Analytics derives customer metrics | `many → analytics` | Tenant/platform | Reporting dependency | **CONCEPTUAL** |
| Campaigns | Analytics | Campaign attribution analytics excluded from MVP | `many → analytics` | N/A | Reporting dependency | **EXCLUDED FROM MVP** |
| Notifications | Analytics | Notification delivery analytics excluded from MVP | N/A in MVP | N/A | Reporting dependency | **EXCLUDED FROM MVP** |
| Shops | Analytics | Analytics scopes merchant/platform reporting | `1 → many` conceptual | Tenant/platform | Reporting dependency | **CONCEPTUAL** |

The table intentionally includes conceptual interactions as well as likely database relationships. Only relationships marked APPROVED should be treated as settled business decisions; physical representation remains a later database-design task.

**## 37. Tenant Path Table**

\| Entity or context | Tenant path | Direct Shop relationship? | Status | Isolation requirement |

\|---|---|---:|---|---|

\| Shop | Shop | Yes by identity | **\*\*APPROVED\*\*** | Shop is the tenant boundary. |

\| Shop catalog / Shop Product | Shop → catalog context | \`TBD\` | **\*\*CONCEPTUAL\*\*** | Merchant catalog must not cross Shops. |

\| Master Product | Platform-global catalog | No | **\*\*APPROVED\*\*** as global concept | Global visibility must not make tenant configuration global. |

\| Inventory | Shop → Inventory context | Yes, conceptually | **\*\*APPROVED\*\*** | Inventory belongs to and is isolated by Shop. |

\| Customer | Shop → Customer | Conceptually yes | **\*\*APPROVED\*\*** | Customer identity and history must not cross Shops. |

\| Cart | Shop → Cart context | \`TBD\` | **\*\*CONCEPTUAL\*\*** | A Cart cannot contain products from multiple Shops. |

\| CartItem | Cart → Shop; catalog item must match | No independent path required yet | **\*\*CONCEPTUAL\*\*** | Item references must be valid within Cart Shop context. |

\| Order | Shop → Order | Strongly expected conceptually | **\*\*APPROVED\*\*** | An Order belongs to exactly one Shop. |

\| OrderItem | Order → Shop | No independent path required yet | **\*\*CONCEPTUAL\*\*** | Historical line must remain within Order Shop context. |

\| Campaign | Platform campaign with all-Shop or selected-Shop display scope | Platform-global; optional Shop display scope | **APPROVED BUSINESS RULE** | Display scope is not Shop ownership; physical schema remains technical design. |

\| Notification | Order → Shop → Notification → Shop's one configured merchant WhatsApp number; or Order → Shop → Shop-specific Customer → Customer WhatsApp number | \`TBD\` | **\*\*APPROVED\*\*** | Delivery must not cross Shop context; recipient resolution must not be global by WhatsApp number. |

\| Analytics report | Merchant's Shop or authorized platform scope | \`TBD\` | **\*\*CONCEPTUAL\*\*** | Merchant analytics remain within the Merchant's active Shop. |

\| Analytics aggregate | Source facts → approved scope | No fixed path approved | **\*\*UNRESOLVED\*\*** | Platform aggregation requires platform authorization. |

\| Merchant Shop access | Merchant login credentials → Merchant's one active Shop; credentials may be shared with staff | \`1 → 1 active Shop\` in MVP | **\*\*APPROVED\*\*** | Client-provided Shop IDs are not authorization. |
This table is a required input to the later multi-tenancy and database design work.

**## 38. Platform-Global vs Tenant-Owned Classification**

**### Platform-global candidates**

\| Concept | Current classification | Notes |

\|---|---|---|

\| Master Catalog | Platform-global | Shared catalog knowledge; not every Shop offers every item. |

\| Master Product | Platform-global | Identified by Master Product ID; Shop selection does not imply synchronization. |





\| Platform Campaign | Platform-global | Super Admin manages campaigns; all-Shop or selected-Shop display scope is approved. |

\| Super Admin access context | Platform-level authorization | Final permission model unresolved. |

\| Platform Analytics | Platform-global reporting context | Must be restricted to authorized platform actors. |

**### Tenant-owned candidates**

\| Concept | Current classification | Notes |

\|---|---|---|

\| Shop | Tenant boundary | Shop itself is the primary tenant context. |

\| Shop Catalog | Tenant-owned | Each Shop has an independent Merchant-controlled catalog. |

\| Merchant Product Configuration | Tenant-owned | Must not mutate Master Catalog or another Shop. |

\| Inventory | Tenant-owned | Shop-scoped; Product/Variant stock behavior finalized. |

\| Customer | Tenant-owned | Shop-specific identity is approved. |

\| Cart | Tenant-owned context | Persistence and direct Shop relationship unresolved. |

\| CartItem | Tenant-owned through Cart | Must match Cart Shop context. |

\| Order | Tenant-owned historical transaction | One-Shop ownership is approved. |

\| OrderItem | Tenant-owned through Order | Historical meaning must be preserved. |

\| Shop Campaign | Excluded from MVP | A Shop in campaign display scope does not own or manage the campaign. |

\| Shop Notification context | Tenant-scoped candidate | Depends on event, recipient, and message type. |

\| Shop Analytics | Tenant-scoped reporting context | Must be limited to authorized Shop(s). |

Classification is conceptual and does not finalize tables, foreign keys, or storage.

**## 39. Ownership Direction**

Business ownership direction must be kept separate from physical foreign-key direction.

Examples:

```text
Merchant
  operates
Shop

Shop
  owns/scopes
Customer

Shop
  owns
Order

Order
  owns
OrderItem

Platform Catalog
  provides/references
Master Product

User / authorized people
  access through
Merchant login credentials (MVP; may be shared with staff)
```

A future database may store references from Customer to Shop or Order to Shop, but those physical references do not change business ownership. Likewise, a Shop Product may reference a Master Product without the Master Product owning the Shop Product's price, inventory, or visibility.

**## 40. Relationship Anti-Patterns**

The following relationships must not be created casually:

**### Do not collapse User, Merchant, and Shop**

\`\`\`text

User = Merchant = Shop

\`\`\`

This is not approved. Identity, business/operator context, tenant context, and authorization are distinct concepts.

**### Keep Customer profiles shop-scoped**

Each Customer profile belongs to one Shop. The approved repeat-customer/order-history flow must not require OTP, but a WhatsApp number alone is not proof of identity and must not expose Orders. The approved mechanism is a customer-specific access link/token scoped to the relevant Customer and Shop. Its expiry, revocation, generation, delivery, storage, and protections against unauthorized reuse are technical design requirements to settle before implementation. Do not expose Orders across Shop/customer contexts, and minimize customer information. WhatsApp/mobile identity values are globally unique across Customer, Merchant, and Super Admin accounts. Enforcing this across domains requires a shared technical representation; independent table constraints are insufficient.

**### Do not make Merchant the tenant**

Shop is the primary tenant boundary. In MVP, Merchant access is limited to the Merchant's one active Shop. Credentials may be shared with staff, but this does not create additional Merchant memberships or expand access to another Shop. Merchant may create a new Shop only after permanently deleting the previous one.

**### Do not make Analytics the source of truth**

Analytics derives reporting from Orders, Catalog, Inventory, Customers, Shops, Campaigns, and Notifications. It does not own those facts.

**### Do not make Notifications own Orders**

Notifications communicates approved Order events. It does not change Order state or become the order-management interface.

**### Do not make Inventory own Products**

Inventory owns stock state in the context of a Shop's sellable item. Catalog owns Product, Variant, and category definitions.

**### Do not make Campaigns own Products**

Campaigns may mention Catalog entities as text/content only; MVP has no persistent Catalog targeting relationships. Campaigns does not own or change product identity, price, inventory, availability, checkout totals, or historical Order values.

**### Do not make Cart equal Order**

Cart is temporary/current shopping state. Order is the historical purchase transaction.

**### Do not make every interaction a foreign key**

An event, report, trigger, or provider delivery may be represented indirectly. Persistent coupling requires a later integrity and ownership decision.

**## 41. Circular Dependency Review**

Cross-domain relationships are expected, but business ownership and dependency direction should remain clear.

### Orders ↔ Notifications

- Orders owns order state; Notifications owns delivery.
- Order events trigger the required MVP messages.
- Notifications must not mutate Order state.
- Status: Business interaction, not automatically a bidirectional model dependency.

### Catalog ↔ Inventory

- Catalog owns Product/Variant identity; Inventory owns Shop-specific stock state.
- Inventory consumes catalog/sellable-item context.
- Status: Conceptual relationship; exact representation is database-design work.

### Catalog ↔ Campaigns

- Campaigns can mention catalog concepts in advertisement content, but MVP does not create persistent Product/Category targeting relationships.
- Status: No Catalog dependency required for campaign content.

### Customers ↔ Orders

- Customers owns current Shop-specific customer identity; Orders owns historical transaction meaning.
- Orders associates with Customer while retaining only the order-time information required for historical accuracy.
- Status: Approved business association.

### Orders ↔ Analytics

- Orders owns facts; Analytics reports them.
- Analytics queries source data directly in MVP.
- Status: Reporting dependency.

### Campaigns ↔ Analytics

- Campaign attribution analytics are excluded from the MVP; future reporting requires separate approval.
- Status: Attribution excluded from MVP.

### Inventory ↔ Analytics

- Inventory owns current stock facts; Analytics may report them. No low-stock threshold or movement ledger is defined for MVP.
- Status: Conceptual reporting dependency.

### Notifications ↔ Analytics

- Notification delivery analytics are excluded from the MVP; future reporting requires separate approval.
- Status: **EXCLUDED FROM MVP**.

Avoid adding abstractions merely to remove a theoretical circular dependency. Identify the actual business owner and minimum required reference or interaction.

**## 42A. Approved Decisions From Relationship Review**

The following business decisions have been explicitly resolved during relationship review and supersede earlier unresolved wording in this document:

1. **Merchant is the Shop Owner / business entity, separate from User and Shop.** One Merchant owns one Shop at a time; each Shop belongs to exactly one Merchant. Shop deletion preserves the Merchant account and credentials. After deletion, the same Merchant may create a new Shop with a new identity and public QR/link; deleted Shop data is not carried over or associated with it. Ownership transfer is not supported in MVP.
2. **MVP Merchant access uses Merchant login credentials for the Merchant's Shop.** Credentials may be shared with staff; individual employee accounts, memberships, roles, and permissions are not required. Individual users and roles may be introduced later.
3. **Products may have multiple variants.** Variant-level price and inventory are supported; non-variant Products may themselves be sellable.
4. **Master and Shop Catalogs are independent.** Merchant-created Shop Products require no Super Admin approval. Super Admin may promote a product into the Master Catalog without automatically linking or changing the existing Shop Product.
5. **Inventory is Shop-specific.** Non-variant products have Product stock. For variant-based products, Variant quantities are authoritative and Product stock is a derived aggregate; independent manual changes to the aggregate are superseded.
6. **Customer records are Shop-specific.** Within a Shop, the WhatsApp number is the primary identifier for recognizing a returning Customer. A permanent Customer record is created when the customer first provides that WhatsApp number, including before checkout; abandoned carts may therefore be associated with permanent Customer records.
7. **Cart has direct Shop context and cannot mix Shops.** Checkout creates the Order, but no persistent Cart → Order relationship is required.
8. **One current Customer record per customer per Shop.** Repeat orders may update the current Customer details. Orders remain complete historical transaction records.
9. **Order history remains available while the Shop exists.** Merchant can view all historical Shop Orders. Customer repeat-customer/order-history flow must not require OTP, but a WhatsApp number alone must not expose Orders; the approved mechanism is a customer-specific access link/token scoped to the Customer and Shop; its expiry, revocation, generation, delivery, storage, and unauthorized-reuse protections must be settled before implementation. Shop deletion removes the Shop's Orders; there is no history-count limit while they exist.
10. **Order preserves order-time delivery information.** The complete current Customer profile is not duplicated into every Order.
11. **Order creation reserves required stock; Merchant acceptance deducts it.** Reserved quantity is visible to the Merchant. Rejection, pending Customer cancellation, and pending timeout expiry release it; expiry moves the Order to the existing `REJECTED` outcome/state, and it cannot be accepted or reopened. No separate `EXPIRED` state is added. Eligible Merchant cancellation after acceptance restores/releases stock. When stock is insufficient, Merchant may manually reduce the fulfillable quantity before acceptance, the Customer is notified, and the Order total reflects the reduced quantity. No automatic reduction is allowed.
12. **MVP campaigns are platform advertising content.** Super Admin manages them; they may display to all or selected Shops; mentions of products, categories, brands, or Shops are content only, not persistent targets. The lifecycle is Draft, Active, and Ended; start/end times are optional; visibility requires Active status, in-schedule time, and matching Shop scope. Super Admin can deactivate Active campaigns; Ended campaigns cannot be reactivated. MVP excludes merchant campaigns, discounts/coupons, customer segmentation/personalization, campaign notifications, and campaign attribution analytics.
13. **MVP WhatsApp notifications use seven approved event/recipient mappings:** successful Order creation → Shop's configured merchant number and Customer received acknowledgement; Merchant acceptance → Customer; rejection → Customer; Merchant manual quantity reduction before acceptance → Customer; pending Customer cancellation → Shop's configured merchant number; and accepted Merchant cancellation before PREPARING → Customer. Received acknowledgement must not imply acceptance. Customer/Merchant cancellations and Merchant rejection use the existing `REJECTED` outcome; no new Order state is added. No notifications are required for PREPARING, READY, or COMPLETED. WhatsApp is notification-only; delivery failure does not change Order state and delivery is not reported without provider confirmation. Prevent duplicates for the same event and recipient; use bounded retries for transient failures and no retries for permanent failures, subject to provider capabilities. Fixed reviewed templates, minimal content, and minimal history are required; retention period remains undecided.
14. **Analytics must use only approved formulas.** Campaign attribution and Notification delivery analytics are excluded from MVP. Do not retain aggregates from permanently deleted Shops unless a separate retention policy is approved. Notification-history retention must be decided before Notifications implementation.
15. **Shop deletion removes the Shop, its Shop Products, and its Orders, but does not globally delete Customer entities under the existing Customer rules.** The Merchant account and credentials remain; the replacement Shop has a new identity and public QR/link. Deleted Shop data is not associated with or exposed through the replacement. Physical deletion mechanics remain for database design; other entities follow their own approved deletion rules.

These decisions are business-level relationship decisions. They do not finalize Django fields, authentication technology, API contracts, database constraints, indexes, or transaction implementation.

**## 42. Relationship vs Foreign Key Rule**

\> **\*\*A conceptual relationship does not automatically require a Django ForeignKey.\*\***

Before creating a database relationship, determine:

1\. Does one domain actually need a persistent reference to the other?

2\. Is the referenced entity part of the domain's ownership model?

3\. Is the relationship required for business integrity?

4\. Is the relationship historical or current-state only?

5\. Can the relationship be derived safely?

6\. Would a direct foreign key create unnecessary coupling?

7\. Does tenant isolation require an explicit Shop relationship?

8\. What happens if the referenced entity changes or is deactivated?

9\. Does the relationship need to preserve historical meaning?

10\. Is cardinality actually approved?

Only after these questions are answered should a relationship become part of the physical schema.

**## 43. Relationship → Database Design Gate**

This document defines conceptual model relationships only. It does not finalize:

\- Django field types.

\- Foreign keys or many-to-many fields.

\- Primary-key strategy.

\- Database constraints.

\- Indexes.

\- Nullability or required fields.

\- Deletion or archival behavior.

\- Historical snapshot representation.

\- Migrations.

\- API contracts.

\- Authentication or authorization implementation.

The next stage is a Database Design Specification based on reviewed relationships and approved cardinalities.

No Django model implementation should begin before this relationship map and the required unresolved decisions are reviewed.

**## 44. Consolidated Unresolved Relationship Decisions**

| Decision | Current understanding | Why still unresolved | Domains affected | Implementation decision blocked |
|---|---|---|---|---|
| User ↔ Merchant representation | One custom Django User supports SUPER_ADMIN and MERCHANT; each Merchant has a one-to-one profile with status and first-login state | Merchant profile lifecycle enforcement and physical relationship to Shop remain unresolved | Users, Shops | Merchant/Shop relationship |
| Merchant credentials ↔ Shop access | Credentials access the Merchant's one active Shop and may be shared with staff | Authentication/access schema is not finalized | Users, Shops | Credential and access representation |
| Shop ↔ Customer identity matching | Every Customer profile belongs to one Shop; WhatsApp is globally unique across Customers, Merchants, and Super Admins | Shop model dependency, phone normalization, formatting, verification, and cross-domain uniqueness representation remain open | Customers, Users, Shops, Orders | Customer model and shared WhatsApp uniqueness implementation |
| Shop ↔ Cart cardinality | Cart is Shop-scoped | Active-cart persistence/cardinality remains to be finalized | Cart, Shops | Cart identity/schema |
| Product/Variant physical model | Product may be directly sellable or have variants | Exact fields, identity, and schema remain DB decisions | Catalog, Inventory | Catalog schema |
| Master Product ↔ Shop Product representation | Shop Product may be selected from Master Catalog or created directly; each remains independent. Promotion does not auto-link the originating Shop Product. | Exact optional reference representation remains a technical decision | Catalog | Catalog reference fields |
| Shop Product/Variant ↔ Inventory representation | Product-only stock without variants; Variant stock plus aggregate Product quantity with variants | Exact database representation and aggregate recalculation behavior remain technical decisions | Catalog, Inventory | Inventory schema |
| Order ↔ Inventory concurrency | Deduct on Merchant acceptance | Exact transaction/locking/error semantics remain implementation details | Orders, Inventory | Stock transaction logic |
| Notification recipient physical representation | The MVP business relationship is approved: a Shop has one configured merchant WhatsApp number, and customer notifications use the relevant Shop-specific Customer WhatsApp number | Exact recipient/phone storage and delivery-record representation remain open | Notifications, Customers, Shops, Orders | Notification schema and delivery-record representation |
| Campaign ↔ Shop display scope | Platform campaign displayed to all or selected Shops | Exact targeting representation remains DB decision | Campaigns, Shops | Campaign scope schema |
| Campaign → Product/Category | No persistent targeting relationship in MVP | Ad content may mention them; content storage format is a technical design detail | Campaigns, Catalog | Campaign content schema |
| Campaign → Notification | Campaign-triggered notifications excluded from MVP | Any future requirement needs separate approval | Campaigns, Notifications | Integration/schema |
| Analytics storage | Direct source-domain queries in MVP | Future precomputation/caching may be considered if scale requires it | Analytics, all source domains | Optimization architecture |
| Historical Order representation | Full Order history retained unless Merchant permanently deletes the Shop; Shop deletion removes its Orders; current Customer record may change | Exact historical fields/snapshot and physical Shop deletion representation remain DB decisions | Orders, Customers, Catalog | Order schema |
| Deletion/retention | Shop deletion permanently removes its Shop data, products, and Orders; other entities may be deactivated or retained under their domain rules | Physical handling of related records remains a DB decision; other entities retain their own deletion rules | All domains | Deletion/archive rules |

These are implementation details that remain to be resolved in the relevant database/API/domain specifications. They must not be invented by an implementation agent.

**## 45. Git Workflow**

Follow the repository's task-based workflow before implementation changes:

\`\`\`text

git status

git checkout main

git pull origin main

git checkout -b \<task-id>/define-model-relationships

\`\`\`

\- Inspect existing changes before acting.

\- Do not discard unrelated work.

\- If no task ID is provided for a new development task, ask for it rather than inventing one.

\- Do not work directly on \`main\`.

\- Do not force-push, rewrite history, reset, or clean unrelated work.

\- Keep this task limited to the relationship documentation.

\- Do not commit secrets or modify \`.env\` files.

**## Final Requirement**

Create only \`.ai/project-context/model-relationships.md\`. Do not create or modify Django models, migrations, serializers, views, URLs, APIs, services, tests, frontend code, database tables, or infrastructure.

The relationship map must remain explicit about what is **\*\*APPROVED\*\***, **\*\*CONCEPTUAL\*\***, and **\*\*UNRESOLVED\*\***. No physical model implementation should begin until the relationship map, cardinalities, tenant paths, ownership boundaries, and unresolved decisions have been reviewed.
