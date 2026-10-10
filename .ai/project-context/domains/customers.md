# Customers Domain Specification

## 1. Domain Purpose

The Customers domain owns customer identity within a shop, customer contact information, customer ordering context, repeat-customer recognition, customer information needed for approved checkout behavior, shop-specific customer history, and delivery-related customer information where applicable.

It does not own merchant users or authentication, shop identity, products, inventory, carts, orders, payments, WhatsApp provider/integration, delivery-partner management, or analytics implementation. Those belong to their respective domains.

## 2. Customer Identity Model

The current product does not require traditional customer accounts with usernames/passwords or customer login. A Customer is a lightweight profile that must belong to one Shop. Customer profiles remain separate from authenticated User accounts. A WhatsApp number is globally unique across the platform, including Customer, Merchant, and Super Admin identities.

```text
Shop A
   └── Customer X

Shop B
   └── Customer Y
```

Customer profiles and Order history are Shop-scoped; the platform does not automatically link customer history across Shops. The repeat-customer/order-history experience must not require OTP, but a WhatsApp number alone is not proof of identity and must not expose Order history. The privacy-safe access mechanism remains unresolved pending approval.

## 3. Shop-Specific Customer Isolation

Follow `.ai/skills/multi-tenancy/SKILL.md` as the governing engineering rule.

- Customer identity and history belong to a specific shop.
- Customer information must not cross shop boundaries.
- Shop A must not access Shop B's customer records.
- A WhatsApp number may be associated with at most one identity across the platform, including Customer, Merchant, and Super Admin identities.
- An identifier from one shop must not grant access to another shop's customer data.

These are business and security requirements; this specification does not design their technical implementation.

## 4. Customer Information

The currently approved checkout concepts are:

- Customer name.
- WhatsApp number.
- Delivery address when home delivery is selected.

Do not automatically add email, date of birth, gender, profile photo, loyalty information, or preferences; these are not supported by existing product requirements.

## 5. WhatsApp Number

The product uses a WhatsApp number as customer contact information and an order-communication destination. It is also the primary identifier for recognizing a returning Customer within the Customer's Shop. The number is globally unique across Customer and authenticated User identities.

A globally unique WhatsApp number does not make the Customer profile global: every Customer profile still belongs to one Shop. The number is used for contact and repeat-customer recognition, but is not by itself authorization to access Order history. The approved access flow must not require OTP; a privacy-safe mechanism is unresolved and requires approval. The same number cannot be registered as a Customer at a second Shop or as a Merchant/Super Admin identity. For example:

```text
Shop A: Customer identity with name Rahul and WhatsApp number X
Shop B: No second Customer profile can use WhatsApp number X
```

Customer information and accessible Order history remain Shop/customer-context scoped. Expose only the customer information needed for the Order experience. Phone-number normalization and formatting rules are not finalized.

For MVP Order notifications, Notifications resolves the recipient from the relevant Shop-specific Customer record and its WhatsApp number. Checkout contact information creates or identifies that Customer; notification delivery does not introduce another customer identity or authorize Order-history access.

## 6. Customer Creation

Conceptually, customer information is provided in the context of a shop's shopping flow:

```text
Customer visits Shop A
        ↓
Browses Shop A catalog
        ↓
Adds products to cart
        ↓
Provides WhatsApp number for Shop A
        ↓
Permanent Shop-specific Customer record is created or recognized
        ↓
Checkout may continue with current customer information
        ↓
Order is created
```

The permanent Shop-specific Customer record is created when the customer first provides their WhatsApp number for that Shop. Successful Order creation is not required; an abandoned Cart may therefore be associated with a Customer.

This describes product behavior only. It does not decide an API, persistence mechanism, session mechanism, phone-number normalization, or detailed customer-data update rules.

## 7. Returning Customer

A returning customer may be recognized within the same Shop using the customer's WhatsApp number as the primary identifier. The intended experience may prefill a customer name or reuse previously known delivery information where appropriate.

Do not assume automatic login, cross-shop recognition, or that all historical information is always prefilled. The exact prefill, update, normalization, and privacy behavior remains unresolved.

## 8. Customer Data Used During Checkout

Distinguish conceptually between:

- **Customer profile/history:** longer-lived shop-specific customer information, if maintained.
- **Checkout information:** information supplied for the current order.
- **Order snapshot:** information that may need to remain associated with a historical order.

The exact storage and snapshot behavior is not decided here. The Orders domain defines the historical order representation; this domain does not define its schema.

## 9. Delivery Address

Home-delivery checkout requires a customer delivery address. Do not assume a complex address model.

The existing requirements do not decide whether the MVP supports one address or multiple saved addresses, address labels, GPS coordinates, landmarks, separate city/state/pincode fields, or a free-form address. Those details are unresolved.

## 10. Pickup vs Delivery

For pickup, customer contact information is required according to checkout requirements; no delivery address is required unless another approved requirement says otherwise. For home delivery, customer contact information and a delivery address are required.

Final validation rules belong in the relevant Order/checkout specification and are not defined here.

## 11. Customer History

Customer Order history is Shop/customer-context scoped. The repeat-customer/order-history experience must not require OTP, and a WhatsApp number alone must not expose Orders. The privacy-safe access mechanism remains unresolved pending approval. Merchants can view all historical Orders belonging to their Shop while it exists. Shop deletion removes the Shop's Orders, while the Customer entity remains. Minimize exposed customer information.

Do not assume merchants should automatically see every customer detail. Merchant visibility and access must follow approved authorization and privacy rules. Analytics definitions belong to Analytics, not this domain.

## 12. Customer vs Order

```text
Customer
=
shop-specific identity/contact context

Order
=
historical purchase transaction
```

Customer information may change later without silently changing the meaning of a prior order. The Orders domain defines historical order behavior; this specification does not design its snapshot schema.

## 13. Customer vs Cart

```text
Customer
=
shop-specific identity

Cart
=
current shopping state
```

The Cart domain owns cart persistence and lifecycle. This specification does not define them.

## 14. Customer Deletion / Deactivation

Customer deletion, anonymization, deactivation, and restoration behavior are not finalized. Decisions must account for previous orders, active carts, customer history, and whether the customer can be recognized again later. A Shop deletion removes that Shop's Orders but does not globally delete the Customer entity. Do not assume Customer hard-delete or soft-delete mechanics.

## 15. Customer Privacy

- Customer information remains shop-scoped.
- One shop must not expose another shop's customers or customer history.
- WhatsApp numbers are globally unique across Customer, Merchant, and Super Admin identities.
- Customer information is exposed only to authorized users and processes.
- Public customer-facing pages do not expose customer records.
- Catalog/public-shop behavior does not expose customer information.

Follow `.ai/skills/security/SKILL.md` and `.ai/skills/multi-tenancy/SKILL.md`. This is domain-specific privacy guidance, not a general privacy policy.

## 16. Customer Authentication Boundary

```text
Customer identity
≠
Customer authentication
```

The current product does not establish a traditional customer login/account system. Do not assume JWT, sessions, passwords, OTP, OAuth, or social login. The repeat-customer/order-history flow must not require OTP, but the mechanism must not expose Orders based only on a WhatsApp number. Its privacy-safe design remains unresolved; do not implement or prescribe an authentication mechanism here.

## 17. Customer Identification and Security

The approved repeat-customer/order-history flow must not require OTP. A WhatsApp number alone is not proof of identity and cannot by itself authorize access to Order history. The privacy-safe access mechanism remains unresolved pending approval. Phone-number normalization and formatting remain unresolved. Minimize exposed customer information.

## 18. Customer Access by Merchant

Merchants may need customer information for legitimate shop operations such as order fulfillment. Merchant access is limited to the merchant's authorized shop and does not extend to customers of another shop. Customer profiles remain Shop-scoped even though WhatsApp numbers are globally unique.

Permanent Shop-specific Customer record is created or recognized

## 19. Customer Access by Super Admin

Super Admin may require platform-level operational visibility according to approved authorization. Platform-level status does not by itself define unrestricted access to all customer data. The final access and privacy decision is unresolved.

## 20. Business Invariants
The permanent Shop-specific Customer record is created when the customer first provides their WhatsApp number for that Shop. Successful Order creation is not required; an abandoned Cart may therefore be associated with a Customer.
The following requirements are approved by the product and business-rule sources:

- Customer identity is shop-specific.
- Customer profiles and accessible Order history remain in their Shop/customer context; history is not automatically linked across Shops.
- A WhatsApp number is associated with at most one identity across all Shops and authenticated User accounts.
- The repeat-customer/order-history flow does not require OTP, but knowledge of a WhatsApp number alone must not expose Orders. Its privacy-safe access mechanism remains unresolved. Shop deletion removes those Orders, but the Customer entity remains.
- Merchant access to customer information is limited to authorized shops.
A returning customer may be recognized within the same Shop using the customer's WhatsApp number as the primary identifier. The intended experience may prefill a customer name or reuse previously known delivery information where appropriate.
- Customer identity is separate from merchant identity.
The exact prefill, update, normalization, and privacy behavior remains unresolved.

The customer's WhatsApp number is the approved primary identifier for recognizing a returning Customer within the same Shop. Phone-number normalization, formatting, verification, and any additional context remain unresolved.

These are conceptual domain relationships, not necessarily database foreign keys:

### Shops

| Phone-number normalization and formatting. | WhatsApp number is the primary identifier within a Shop, but accepted formats and normalization are not defined. | Comparisons and accepted input formats cannot be specified. |
| Physical uniqueness enforcement for WhatsApp numbers. | WhatsApp numbers are globally unique across Customer, Merchant, and Super Admin identities. | The shared database representation that enforces uniqueness across domains remains open. |
| Order-history access mechanism. | Repeat-customer/order-history flow must not require OTP, and WhatsApp number alone is insufficient to authorize access. | A privacy-safe mechanism consistent with no OTP requires approval. |

Determines who may access customer information, subject to approved authorization.

### Catalog

Provides the shop-specific products customers browse.

### Cart

Holds current shopping state in a specific shop context; the Cart domain owns its behavior.

### Orders

Customers place orders; order history is associated with the relevant shop-specific customer context, subject to the finalized Orders specification.

### Notifications

For MVP Order notifications, Notifications resolves the recipient from the relevant Shop-specific Customer record and its WhatsApp number. The Notifications domain owns message preparation and delivery behavior.

### Analytics

Customer metrics may be aggregated at shop or platform level only under approved analytics and privacy rules.

## 22. Unresolved Decisions

No decision below is finalized by this specification.

| Decision | Why unresolved | Impact |
|---|---|---|
| Phone-number normalization and formatting. | WhatsApp number is the primary identifier within a Shop, but accepted formats and normalization are not defined. | Comparisons and accepted input formats cannot be specified. |
| Cross-domain WhatsApp uniqueness implementation. | WhatsApp numbers must be unique across Customers, Merchants, and Super Admins. | A shared database representation is required; independent per-table constraints cannot enforce this rule. |
| Phone-number normalization and formatting. | No format or normalization rule is documented. | Comparisons and accepted input formats cannot be specified. |
| Whether WhatsApp verification is required for purposes beyond Order-history access. | No verification requirement or mechanism is approved; OTP is not required for the MVP Order-history access decision. | Any broader identity verification requirement remains open. |
| Whether customers can edit their information. | Product requirements do not define editing rules. | Customer-data correction behavior remains open. |
| Returning-customer recognition details. | WhatsApp number is the approved primary identifier within a Shop. | Prefill, update, verification, and privacy behavior remain open. |
| What customer information may be prefilled. | Prefill is a product possibility, not a finalized field-by-field rule. | Checkout presentation and data exposure remain open. |
| Delivery address structure. | Only the need for an address on home delivery is approved. | Address collection and validation are unspecified. |
| Multiple saved addresses and address labels. | No saved-address requirement is defined. | Address reuse behavior remains open. |
| Address history. | Retention and historical behavior are not specified. | Prior delivery information handling cannot be finalized. |
| Customer deletion and anonymization. | Deletion policy is unresolved. | Personal data and related records handling remain open. |
| Customer deactivation and restoration. | No lifecycle states or transitions are approved. | Recognition and access after deactivation remain undefined. |
| Historical customer information. | Order snapshot and retention details are unresolved. | Historical order interpretation cannot be fully specified. |
| Merchant access to Customer profile fields beyond Shop Orders. | Merchant can view all Shop Orders; field-level profile access and privacy implementation are not defined. | Limit access to approved operational needs. |
| Super Admin access to customer information. | Platform-level access does not establish unrestricted data access. | Admin visibility and privacy controls remain open. |
| Customer data retention. | No retention period or policy is approved. | Long-term storage and deletion behavior remain undefined. |
| Detailed customer privacy requirements. | Existing documents establish isolation/minimization principles but not a full policy. | Collection, exposure, and retention details need approval. |
| Customer authentication, if ever introduced. | The current MVP does not require traditional customer accounts; future auth is not approved. | Do not implement login or verification flows by assumption. |

## 23. Explicit Non-Goals

This specification does not define Django models, database schema, migrations, serializers, API endpoints, authentication implementation, customer login, OTP or password authentication, WhatsApp provider/API, cart implementation, order state machine, payment processing, delivery-partner management, analytics implementation, frontend implementation, or notification implementation.

## 24. Implementation Gate

> The Customers domain must not be implemented until the unresolved customer-identity, privacy, and checkout-related decisions required for implementation are reviewed and approved.

Customer model implementation also depends on the Shops domain model: every Customer profile must reference an existing Shop.

After approval, implementation must follow `AGENTS.md`, `.ai/project-context/product.md`, `.ai/project-context/architecture.md`, `.ai/project-context/business-rules.md`, `.ai/project-context/development-status.md`, `.ai/project-context/domains/users-and-merchant-accounts.md`, `.ai/project-context/domains/shops.md`, `.ai/project-context/domains/catalog.md`, `.ai/project-context/domains/inventory.md`, this domain specification, and relevant engineering skills. The implementation agent must not silently resolve unresolved business decisions.

## 25. Git Workflow

Follow the mandatory repository workflow:

```text
git status
git checkout main
git pull origin main
git checkout -b <task-id>/<short-description>
```

- Never work directly on `main`.
- Inspect existing changes first; do not discard them automatically.
- Destructive Git commands require explicit approval.
- Ask for a task ID if none is provided before creating a branch.
- Keep commits small and task-related; never commit secrets.
- Push the task branch and create a PR against `main`.
- Do not force-push or rewrite history without authorization.

Follow `AGENTS.md` for the complete workflow.

## Final Requirement

Create only `.ai/project-context/domains/customers.md`. Do not modify any other file. Do not create models, migrations, APIs, authentication, authorization, or customer functionality. Do not resolve unresolved customer-identity decisions.
