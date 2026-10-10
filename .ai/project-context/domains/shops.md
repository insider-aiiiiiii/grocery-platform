# Shops Domain Specification

## 1. Domain Purpose

The Shops domain owns the Shop business concept, profile, lifecycle, customer-facing access, and Shop-level operational settings. Shop is the platform's primary tenant boundary.

This domain does not own Merchant account identity, catalog/products/variants, inventory, customer identity, carts, orders, campaigns, notifications, or analytics. Those belong to their respective domains.

## 2. Shop Concept and Tenant Boundary

A Shop is the store context in which merchant-owned catalog data, inventory, customer identity, carts, orders, and operations are scoped. Merchant-owned data must remain isolated between Shops. A client-provided Shop identifier is not proof of authorization; tenant context and access must be checked server-side.

A Shop cannot exist without a Merchant. The Shop remains the primary tenant boundary; Merchant is not the tenant boundary.

## 3. Merchant and Shop Relationship

```text
Merchant 1 → 1 active Shop
```

- Merchant is the Shop Owner / business owner and creates their Shop after logging in.
- A Merchant may have only one active Shop at a time.
- A Shop belongs to exactly one Merchant and cannot exist without that Merchant.
- A Merchant cannot have multiple active Shops.
- If the current Shop is permanently deleted, the Merchant may immediately create another Shop. The new Shop is a new entity.
- Ownership transfer between Merchants is not supported in MVP.

A Merchant with no Shop sees the Create Shop flow after login. A deactivated Shop is retained until deletion; it is not an active Shop. This relationship describes business ownership and does not prescribe database representation.

## 4. Shop Creation and Required Information

Super Admin creates Merchant accounts directly. There is no public Merchant application or approval workflow in MVP.

Once onboarded, if no Shop exists, the Merchant creates their Shop and it becomes `ACTIVE` immediately.

Shop creation requires:

- Shop name. It does not need to be unique.
- Full structured address: address line, area, city, state, and pincode.
- Shop contact number, which strictly equals the Merchant's mobile number.

Shop description and Shop logo are optional.

The Shop contact number cannot be changed separately from the Merchant mobile number.

### Shop Creation API Contract (`POST /api/v1/shops/`)

- **Endpoint**: `POST /api/v1/shops/`
- **Authentication**: JWT Bearer token required (`PlatformJWTAuthentication`). Role must be `MERCHANT` with active status. If merchant has not changed their initial temporary password, returns `403` (`PASSWORD_CHANGE_REQUIRED`).
- **Permissions**: `IsActiveMerchant`. Super Admins and unauthenticated requests cannot call this endpoint.
- **Request Payload**:
  - Required: `name`, `address_line`, `area`, `city`, `state`, `pincode`.
  - Optional: `description`, `logo`, `opening_time`, `closing_time`, `is_temporarily_closed`, `is_home_delivery_enabled`, `is_pickup_enabled`, `delivery_fee_type`, `delivery_charge`.
  - Derived server-side: `contact_number` (auto-mirrored from `request.user.mobile_number`), `status` (`ACTIVE`), `public_slug` (12-char hex QR token).
- **One-Shop-Per-Merchant**: If the merchant already has a shop, returns `400 Bad Request` with `{"detail": "Merchant already has a shop.", "code": "SHOP_ALREADY_EXISTS"}`.
- **Response**: `201 Created` with complete Shop profile details.

### Merchant Shop Retrieval API Contract (`GET /api/v1/shops/me/`)

- **Endpoints**: `GET /api/v1/shops/me/` (alias: `GET /api/v1/shops/`)
- **Authentication**: JWT Bearer token required (`PlatformJWTAuthentication`). Role must be `MERCHANT` with active status. If merchant has not changed their initial temporary password, returns `403` (`PASSWORD_CHANGE_REQUIRED`).
- **Permissions**: `IsActiveMerchant`. Super Admins and unauthenticated requests cannot call this endpoint.
- **Tenant Context**: Derived strictly from server authentication (`request.user.merchant.shop`). Arbitrary client-provided Shop IDs (in query parameters or payload) are ignored.
- **Lifecycle Invariants**:
  - If the merchant has no shop yet: returns `404 Not Found` with `{"detail": "Merchant does not have a shop.", "code": "SHOP_NOT_FOUND"}`.
  - If the shop is `DEACTIVATED` or `SUSPENDED`: returns `403 Forbidden` with `{"detail": "Shop is deactivated or suspended.", "code": "SHOP_INACTIVE"}`.
- **Response**: `200 OK` returning only approved fields:
  `id`, `name`, `description`, `logo`, `address_line`, `area`, `city`, `state`, `pincode`, `contact_number`, `status`, `is_temporarily_closed`, `opening_time`, `closing_time`, `is_home_delivery_enabled`, `is_pickup_enabled`, `delivery_fee_type`, `delivery_charge`, `public_slug`, `created_at`, `updated_at`.
  Internal `merchant` foreign key is omitted.



## 5. Shop Profile Editing & Operational Controls

- Merchant can edit Shop details (name, description, logo, structured address).
- Merchant cannot change the Shop contact number separately because it is strictly linked to the Merchant's mobile number.
- Merchant controls operational open/closed state (temporary closure / daily business hours) and delivery options.
- Merchant can deactivate their own Shop but cannot reactivate or suspend it.
- Super Admin may suspend or reactivate a Shop under existing rules. This does not permit browsing or editing private Shop information.

## 6. Shop Status and Lifecycle

Shop status is `ACTIVE`, `DEACTIVATED`, or `SUSPENDED`.

- **Merchant**: May deactivate their own Shop. This is distinct from platform suspension.
- **Super Admin**: May suspend or reactivate a Shop under existing rules. Existing rules assign permanent deletion to Super Admin; this document does not add permission to browse or edit private Shop information.
- **Merchant Controls Operations Only**: Merchant controls operational ON/OFF status (temporary closure outside business hours).
- Deactivating a Merchant account automatically deactivates that Merchant's Shop. This account-lifecycle rule is distinct from the Merchant's authority to deactivate their own Shop.
- A deactivated or suspended Shop cannot be accessed by customers or by the Merchant; Shop data remains preserved.
- When Super Admin reactivates or unsuspends a Shop, a new QR code / public link is assigned; previous QR code does not work. Existing data mapping (products, previous orders, customer history) remains completely intact.

## 7. Business Hours and Temporary Closure

Business hours are an MVP feature managed by the Merchant.

- Each configured Shop schedule has one opening time and one closing time.
- Merchant may change business hours at any time.
- Multiple daily time slots are not part of MVP.
- Merchant may temporarily mark the Shop closed outside its normal operating hours.
- When marked closed, customers see **"Shop Closed"**.
- Customers can still place orders while the Shop is closed.

The Shop's temporary closed state does not deactivate the Shop. Time formats, time zone handling, and the schedule's exact day configuration remain implementation details unless separately decided.

## 8. Home Delivery and Pickup

- **Home Delivery:** Merchant controls the delivery charge policy and may choose between two options:
  1. **Fixed Fee (or ₹0):** Merchant sets a fixed delivery charge (including ₹0 for free delivery), which is displayed to the customer at checkout and added to the order total.
  2. **Fee Confirmed on WhatsApp:** No delivery charge is added to the checkout total; checkout displays a clear notice: *"Delivery charges will be communicated by the merchant via WhatsApp."*
  Merchant may change this configuration at any time.
- **Delivery eligibility:** There is no delivery radius or delivery-area configuration in MVP. Merchant handles delivery eligibility manually.
- **Pickup:** Customers collect the order from the Shop.

No centralized delivery-partner management, radius configuration, or delivery-area configuration is part of MVP.

## 9. Customer Access, Public Link, and Shop Details

Customers can access a Shop through its Shop QR code or public Shop link. Public links can be shared. The customer-facing flow is:

```text
QR code / public Shop link
        ↓
Shop details
        ↓
Categories
        ↓
Products
```

Public access is limited to the intended Shop's customer-facing information and does not grant Merchant or administrative access. A deactivated Shop is unavailable to customers.

The exact public link format, domain, and routing implementation remain unresolved. The public identifier is a system-generated link and must not directly expose or use the Shop ID.

## 10. Shop QR Code

- The system generates a QR code that uses a system-generated public Shop link; the Shop ID is not the public identifier.
- The QR code remains fixed for an active Merchant to preserve printed materials and customer access. Merchant cannot regenerate the QR code.
- Super Admin can regenerate the QR code if an issue arises or if the link is compromised.
- When a Shop is deactivated or suspended, its existing QR displays the Shop as unavailable.
- When a deactivated or suspended Shop is reactivated by Super Admin, a new QR code is assigned, and the old QR stops working.
- Regenerating a QR code updates only the public link token (`public_slug`); all existing data mapping (products, orders, customer history) remains completely preserved and unaffected.
- When the Shop is deleted, its QR and public link become unavailable immediately.

QR encoding, image format/storage, and link-generation implementation remain technical decisions.

## 11. Shop Deletion

Only Super Admin can permanently delete a Shop (Merchants cannot permanently delete a Shop). Keep the existing Super Admin confirmation safeguards and warning of permanent Shop data deletion.

- Deletion requires Super Admin confirmation with clear warnings that Shop data, Shop Products, and Orders will be permanently removed. The Merchant account and login credentials are not removed.
- Deletion is permanent; a deleted Shop cannot be restored.
- The Merchant retains the existing login credentials and may create a replacement Shop with a new identity and public QR/link.
- Shop Products and Orders are deleted with the Shop. Customer entities are not globally deleted solely because of Shop deletion under the existing Customer rules and are not automatically transferred to the replacement Shop.
- The Shop QR and public link become unavailable immediately. Data from the deleted Shop, including Products, Orders, and customer history, must not be associated with or exposed through the replacement Shop.

Physical deletion, relationship cleanup, and tenant isolation mechanics remain technical decisions; they must preserve these approved outcomes.

## 12. Super Admin and Merchant Access

### Merchant

- If the Merchant has no Shop, show the Create Shop flow after login.
- If the Shop is active, Merchant can manage it.
- If the Shop is deactivated, Merchant cannot access Shop data.
- Merchant can create another Shop only after the prior Shop has been permanently deleted, using the same account and credentials. The replacement is a new Shop and receives a new identity and public QR/link; deleted Shop data is not carried over.

### Super Admin

For MVP, Super Admin cannot browse or edit private Shop information. Super Admin can reactivate a deactivated Shop. Existing Super Admin permanent-deletion authority and confirmation safeguards remain documented above; any operational interpretation that would require access to private Shop information is a remaining approval question. No new administrative permission is added.

## 13. Cross-Domain Relationships

These are conceptual boundaries, not necessarily database relationships:

- **Users & Merchant Accounts:** owns Merchant account identity and login credentials; Merchant creates and operates their Shop.
- **Catalog:** owns platform catalog and Shop-specific catalog configuration.
- **Inventory:** owns Shop-specific inventory and availability.
- **Customers:** owns Shop-specific customer identity and information.
- **Cart:** owns customer cart state within the Shop context.
- **Orders:** owns orders placed for the Shop. Shop deletion deletes Shop orders under the approved business rule.
- **Notifications and Analytics:** retain Shop context and tenant isolation.

## 14. Business Invariants

- Shop is the primary tenant boundary.
- A Shop belongs to exactly one Merchant and cannot exist without a Merchant.
- A Merchant can have at most one active Shop at a time and can create another only after permanent deletion of the prior Shop.
- A Merchant operation involving Shop-owned data must use the Merchant's authorized Shop context.
- Deactivated Shops are unavailable to customers and the Merchant, but their data remains until deletion.
- Shop deletion is permanent and removes Shop products and orders.
- The Shop QR/public link resolves only to its intended Shop and does not expose the Shop ID as the public identifier.
- Public Shop access does not grant Merchant or administrative access.

## 15. Unresolved Technical Decisions

The following implementation details remain open and must not be inferred from the approved business rules:

- Shop database fields, identifier format, constraints, and deletion mechanics.
- Exact public link format, domain, and routing.
- QR encoding, generation library, image format, and storage.
- Exact time formats, time-zone handling, and schedule representation.
- How Shop contact number reflects the Merchant mobile number.
- API contracts, authentication, authorization implementation, and audit mechanics.
- Physical handling of related records when Shop data is permanently deleted, including preventing deleted Shop data from being associated with a replacement Shop.

These unresolved technical choices do not change the approved business behavior above.

## 16. Security and Audit Requirements

- Enforce Shop tenant isolation server-side; a Shop ID or public link is not authorization to access Merchant data.
- Public access exposes only customer-facing Shop information and follows the Shop's active/deactivated status.
- Shop creation, profile changes, status changes, temporary closure, fulfillment setting changes, QR regeneration, and permanent deletion may require auditability. Exact audit events, retention, and implementation remain unresolved.

## 17. Implementation Boundary

This document defines approved Shop business behavior, not Django models, database fields or constraints, APIs, serializers, views, permission classes, frontend screens, URL/QR implementation, or physical deletion mechanics. Those remain implementation decisions. No Shop implementation is asserted by this specification.
