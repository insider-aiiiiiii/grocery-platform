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

Two onboarding paths are supported:
1. **Direct Creation**: Super Admin creates the Merchant account directly.
2. **Merchant Application**: Merchant applies to join; Super Admin reviews and approves the application to onboard the Merchant.

Once onboarded, if no Shop exists, the Merchant creates their Shop and it becomes `ACTIVE` immediately.

Shop creation requires:

- Shop name. It does not need to be unique.
- Full structured address: address line, area, city, state, and pincode.
- Shop contact number, which strictly equals the Merchant's mobile number.

Shop description and Shop logo are optional.

The Shop contact number cannot be changed separately from the Merchant mobile number.

## 5. Shop Profile Editing & Operational Controls

- Merchant can edit Shop details (name, description, logo, structured address).
- Merchant cannot change the Shop contact number separately because it is strictly linked to the Merchant's mobile number.
- Merchant controls operational open/closed state (temporary closure / daily business hours) and delivery options.
- Merchant cannot change platform lifecycle status (`ACTIVE`, `DEACTIVATED`, `SUSPENDED`).
- Super Admin controls platform status and can suspend, deactivate, or activate any shop.

## 6. Shop Status and Lifecycle

Shop status is `ACTIVE`, `DEACTIVATED`, or `SUSPENDED`.

- **Super Admin Only**: Only Super Admin can activate, deactivate, or suspend a Shop. Merchant cannot deactivate or suspend their Shop.
- **Merchant Controls Operations Only**: Merchant controls operational ON/OFF status (temporary closure outside business hours).
- Deactivating a Merchant account automatically deactivates that Merchant's Shop.
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
