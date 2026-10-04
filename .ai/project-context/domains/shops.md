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

The approved creation flow is:

```text
Merchant logs in
        ↓
If no Shop exists
        ↓
Merchant creates Shop
        ↓
Shop becomes ACTIVE
```

Shop creation requires:

- Shop name. It does not need to be unique.
- Full structured address: address line, area, city, state, and pincode.
- Shop contact number, which is the Merchant's mobile number.

Shop description and Shop logo are optional.

The Shop contact number cannot be changed separately from the Merchant mobile number. The technical representation and synchronization of these values are not defined here.

## 5. Shop Profile Editing

- Merchant can edit all Shop details.
- Merchant cannot change the Shop contact number separately because it is the Merchant's mobile number.
- Merchant can change business hours and delivery charge at any time.
- Merchant can independently enable or disable Home Delivery and Pickup.
- Shop name uniqueness is not required.
- Super Admin cannot view or edit Shop information. Super Admin can reactivate a deactivated Shop as described in the lifecycle rules.

## 6. Shop Status and Lifecycle

Shop status is `ACTIVE` or `DEACTIVATED`.

- Merchant can deactivate their Shop.
- Super Admin cannot deactivate a Shop.
- Only Super Admin can reactivate a deactivated Shop. Merchant cannot reactivate it.
- Deactivating a Merchant account automatically deactivates that Merchant's Shop.
- A deactivated Shop cannot be accessed by customers or by the Merchant; Shop data remains until the Shop is permanently deleted.
- A reactivated Shop requires a newly generated QR code; its previous QR does not work.

Super Admin's Shop capability in MVP is limited to reactivating a deactivated Shop. Super Admin cannot view Shop information, edit Shop information, or deactivate the Shop.

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

The Shop supports Home Delivery and Pickup. The Merchant can independently enable or disable each option. If an option is disabled, it is hidden from customers.

- **Home Delivery:** Merchant controls the delivery charge and may change it at any time. Merchant decides whether a zero charge (₹0) is allowed for their Shop. Delivery charge is shown to the customer at checkout.
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
- Merchant can regenerate the QR code.
- When a Shop is deactivated, its QR remains technically valid and displays the Shop as unavailable.
- When the Shop is deleted, its QR and public link become unavailable immediately.
- Deleting and recreating a Shop creates a new Shop and does not restore the previous QR.
- If a deactivated Shop is reactivated, its old QR does not work; a new QR must be generated.

QR encoding, image format/storage, and link-generation implementation remain technical decisions.

## 11. Shop Deletion

Merchant can permanently delete their Shop, including when it has existing orders.

- Deletion requires confirmation.
- Before confirmation, the system must clearly warn that Shop data and orders will be deleted.
- Deletion is permanent; a deleted Shop cannot be restored.
- Shop products and Shop orders are deleted.
- The Shop QR and public link become unavailable immediately.
- Merchant may immediately create a new Shop after deletion. It is a new Shop entity with a new QR/link.

This approved deletion behavior is a business rule. Physical deletion mechanics and database-level handling of related records are not defined here.

## 12. Super Admin and Merchant Access

### Merchant

- If the Merchant has no Shop, show the Create Shop flow after login.
- If the Shop is active, Merchant can manage it.
- If the Shop is deactivated, Merchant cannot access Shop data.
- Merchant can create another Shop only after the prior Shop has been permanently deleted.

### Super Admin

For MVP, Super Admin cannot view, edit, or deactivate Shop information. Super Admin can reactivate a deactivated Shop. No additional Shop-management capabilities are approved.

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
- Physical handling of related records when Shop data is permanently deleted.

These unresolved technical choices do not change the approved business behavior above.

## 16. Security and Audit Requirements

- Enforce Shop tenant isolation server-side; a Shop ID or public link is not authorization to access Merchant data.
- Public access exposes only customer-facing Shop information and follows the Shop's active/deactivated status.
- Shop creation, profile changes, status changes, temporary closure, fulfillment setting changes, QR regeneration, and permanent deletion may require auditability. Exact audit events, retention, and implementation remain unresolved.

## 17. Implementation Boundary

This document defines approved Shop business behavior, not Django models, database fields or constraints, APIs, serializers, views, permission classes, frontend screens, URL/QR implementation, or physical deletion mechanics. Those remain implementation decisions. No Shop implementation is asserted by this specification.
