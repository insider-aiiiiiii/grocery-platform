# Customers Domain Specification

## 1. Domain Purpose

The Customers domain owns Shop-specific customer profiles and ordering context, customer contact information, repeat-customer recognition, customer information needed for approved checkout behavior, shop-specific history access context, and delivery-related customer information where applicable. Whether a minimal global CustomerIdentity should sit beneath multiple Shop profiles is an AUTH-018 recommendation pending Product Owner approval; see the single decision register in `.ai/project-context/customer-order-history-access.md`.

It does not own merchant users or authentication, shop identity, products, inventory, carts, orders, payments, WhatsApp provider/integration, delivery-partner management, or analytics implementation. Those belong to their respective domains.

## 2. Customer Identity Model

The current product does not require traditional customer accounts with usernames/passwords or customer login. A Customer profile belongs to one Shop and remains separate from authenticated User accounts. A WhatsApp identity is globally unique across the platform, including Customer, Merchant, and Super Admin identities. The AUTH-018 recommended representation separates a minimal global contact identity/claim from each Shop-specific Customer profile, but this cross-Shop linkage is **pending Product Owner and Privacy approval**; it is not an approved data-sharing rule.

```text
Contact identity X (proposed; no login or history access)
   ├── Shop A Customer profile (name/address/history scoped to A)
   └── Shop B Customer profile (separate name/address/history scoped to B)
```

Customer profiles and Order history are Shop-scoped; the platform must not expose or combine history across Shops. The repeat-customer/order-history experience must not require OTP, and a WhatsApp number alone is never authorization. The finalized mechanism is a one-use link grant with a 15-minute expiry, exchanged for a server-side Customer session scoped to the exact Shop profile and Shop. The session lasts no more than 30 days, and only one active session is allowed per profile + Shop. See `.ai/project-context/customer-order-history-access.md` for the fixed security rules and the AUTH-018 identity/retention decision register. This mechanism is not implemented.

The fixed AUTH-015 requirements are approved. Identity/profile representation, retention, API/schema contract, phone normalization and deployment choices remain under review as listed only in `.ai/project-context/customer-order-history-access.md` §12.

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

The product uses a WhatsApp number as customer contact information and an order-communication destination. It is also the primary identifier for recognizing a returning Customer within that Shop. The number is globally unique across Customer and authenticated User identities.

A globally unique WhatsApp number does not make Customer profiles or history global: each profile belongs to one Shop. Whether one contact identity may be linked to separate profiles at multiple Shops is the pending AUTH-018 product decision. Under the recommended model this can support recognition without sharing profile fields or history; a number-only request still never authorizes access. The approved no-OTP access flow uses a single-use link valid for 15 minutes and a resulting Customer session scoped to that profile and Shop, with a maximum absolute lifetime of 30 days and one active session per profile + Shop. See `.ai/project-context/customer-order-history-access.md` for the security requirements and sole decision register. The same canonical number cannot be claimed by another Customer identity or a Merchant/Super Admin identity.

```text
Shop A: Profile A (name/contact context and history only for Shop A)
Shop B: Profile B (separate context and history); link to the same minimal contact identity only if the pending product decision approves it
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

Customer Order history is Shop/customer-context scoped. The repeat-customer/order-history experience must not require OTP, and a WhatsApp number alone must not expose Orders. The approved mechanism is a one-use 15-minute link exchanged for a session scoped to the exact Customer and Shop; the session has a 30-day maximum absolute lifetime and one active session is allowed per Customer + Shop. Shop deletion revokes that Shop's outstanding grants and sessions, deletes its Orders, and leaves Customer retention governed by the existing Customer rules. A retained Customer and its credentials are never transferred to a replacement Shop. Minimize exposed customer information. See `.ai/project-context/customer-order-history-access.md` for the design and deployment items still open.

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

Customer deletion, anonymization, deactivation, and restoration behavior are not finalized. Decisions must account for previous orders, active carts, customer history, and whether the customer can be recognized again later. A Shop deletion removes its Orders and invalidates credentials; existing rules say Customer entities are not globally deleted solely because the Shop is deleted. AUTH-018 recommends nulling the deleted Shop relation and anonymizing the Shop profile to an inaccessible tombstone, deleting addresses and credentials, but the fields retained and contact-claim release/reuse require Product Owner and Privacy approval. Do not assume a retention period or implement hard-delete/soft-delete mechanics before that approval.

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

The current product does not establish a traditional customer login/account system. The approved Order-history flow does not require OTP and uses a one-use 15-minute access link exchanged for a Customer + Shop-scoped session. The session has a 30-day maximum absolute lifetime, and there is one active session per Customer + Shop. A WhatsApp number alone never authorizes access. The mechanism is designed but not implemented; see `.ai/project-context/customer-order-history-access.md` for deployment decisions that remain open.

## 17. Customer Identification and Security

The approved repeat-customer/order-history flow must not require OTP. A WhatsApp number alone is not proof of identity and never authorizes access to Order history. A single-use link expires after 15 minutes and exchanges for a Customer + Shop-scoped session with a 30-day maximum absolute lifetime and one active session per Customer + Shop. Phone-number normalization and formatting remain unresolved. The access mechanism is designed but not implemented; see `.ai/project-context/customer-order-history-access.md` for security controls and open deployment decisions. Minimize exposed customer information.

## 18. Customer Access by Merchant

Merchants may need customer information for legitimate shop operations such as order fulfillment. Merchant access is limited to the merchant's authorized shop and does not extend to customers of another shop. Customer profiles remain Shop-scoped even though WhatsApp numbers are globally unique.

Permanent Shop-specific Customer record is created or recognized

## 19. Customer Access by Super Admin

Super Admin may require platform-level operational visibility according to approved authorization. Platform-level status does not by itself define unrestricted access to all customer data. The final access and privacy decision is unresolved.

## 20. Business Invariants

The permanent Shop-specific Customer profile is created when the customer first provides their WhatsApp number for that Shop. Successful Order creation is not required; an abandoned Cart may therefore be associated with a Customer. A separate global identity record/linkage is only an AUTH-018 recommendation pending approval.

The following requirements are approved by the product and business-rule sources:

- Customer profile, contact context, and history are Shop-specific. AUTH-018's proposed minimal cross-Shop contact identity does not make profile data/history global and remains pending approval.
- Customer profiles and accessible Order history remain in their Shop/customer context; history is not automatically linked across Shops.
- A WhatsApp number is associated with at most one identity across all Shops and authenticated User accounts.
- The repeat-customer/order-history flow does not require OTP, and a WhatsApp number alone never exposes Orders or customer details. A one-use access link expires after 15 minutes and exchanges for one active Customer + Shop-scoped session with a maximum absolute lifetime of 30 days. Shop deletion revokes grants and sessions for that Shop and removes its Orders, while Customer retention follows existing Customer rules; no retained Customer or access credential transfers to a replacement Shop. The finalized security design is in `.ai/project-context/customer-order-history-access.md`; delivery, deployment, and retention details remain open.
- Merchant access to customer information is limited to authorized shops.

A returning customer may be recognized within the same Shop using the customer's WhatsApp number as the primary identifier. The intended experience may prefill a customer name or reuse previously known delivery information where appropriate.

- Customer identity is separate from merchant identity.

The exact prefill, update, normalization, and privacy behavior remains unresolved.

The customer's WhatsApp number is the approved primary identifier for recognizing a returning Customer within the same Shop. Phone-number normalization, formatting, verification, and any additional context remain unresolved.

## 21. Cross-Domain Relationships

These are conceptual domain relationships, not necessarily database foreign keys:

### Shops

AUTH-018's proposed identity/profile relationship, contact-claim enforcement, retention/address policy, API/schema, and deployment design are recorded in `.ai/project-context/customer-order-history-access.md` §12. These recommendations remain unapproved; this domain document does not duplicate their options or decision owners.

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

The identity/profile recommendation, contact normalization and migration, Customer retention/address handling, and access API/deployment decisions are maintained only in `.ai/project-context/customer-order-history-access.md` §12. AUTH-018 recommendations remain unapproved until the named Product Owner, Privacy, technical, or deployment owner records a decision. Other Customer-domain questions (profile correction, field-level Merchant access, broader verification, and any future login) remain unresolved and must not be inferred from the access design.

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
