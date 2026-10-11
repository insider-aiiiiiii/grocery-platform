# Role and Resource Authorization Matrix

## 1. Purpose and status

This document consolidates approved actor and resource boundaries for AUTH-013. It is a policy reference, not evidence that a resource API exists. The implementation status below was checked against the current repository. Detailed workflows remain in `business-rules.md` and the relevant domain specification.

Actors:

- **Super Admin (SA):** authenticated platform User with the `SUPER_ADMIN` role.
- **Merchant:** authenticated `MERCHANT` User linked to a Merchant profile. In MVP the Merchant login may be shared with staff; there are no separate staff identities or permissions.
- **Customer:** shop-scoped customer profile; not an authenticated User role and has no general account login in MVP.
- **Anonymous visitor:** unauthenticated person using public shop browsing and checkout flows.
- **Customer using a scoped session:** a Customer who exchanged a valid one-use access link for the approved session bound to the exact Customer and Shop. Possession of a WhatsApp number alone does not qualify.

`Implemented` means a routed API and server-side authorization are present. `Partial` means only the described portion exists. `Policy only` means the rule is documented but no corresponding workflow/API was found. `Not applicable` means the actor has no approved capability.

## 2. Scope and authorization rules

1. Authentication identifies a platform User; authorization checks the User role and the requested resource/action. A Customer profile, WhatsApp number, client-provided identifier, or public Shop slug is not a Merchant or Super Admin credential.
2. Shop-owned resources are limited to the Shop context established by the authenticated Merchant's associated Merchant profile and Shop relationship. Resolve that relationship server-side on every request. Never accept a submitted `shop_id` as proof of access or use it to broaden a Merchant queryset.
3. The approved MVP has one Shop per Merchant at a time. After permanent deletion, that Merchant may create a replacement Shop; old Shop data is not transferred to it.
4. Customer profiles and history remain Shop/customer scoped. The approved one-use 15-minute link exchanges for a maximum 30-day session bound to the exact Shop profile and its Shop; one session is active per profile + Shop and a new exchange replaces it. WhatsApp-number knowledge alone grants no history access. AUTH-018 recommends a normalized profile scope root; any cross-Shop minimal contact identity remains pending Product Owner/Privacy approval. The access behavior is approved and unimplemented; remaining choices are in the single register at `.ai/project-context/customer-order-history-access.md` §12.
5. Anonymous Shop browsing is limited to customer-facing Shop information and catalog data for the addressed active Shop. It confers no access to private Shop data, customer records, carts belonging to another customer, or Merchant/admin functions. Public Shop routing and catalog APIs are not implemented.
6. Super Admin has platform-level functions only where explicitly listed below. In particular, Super Admin cannot browse or edit private Shop information. Shop lifecycle and deletion powers are limited to the explicit documented operations and safeguards; do not infer general tenant-data access.
7. Existing HTTP decisions remain: missing/invalid authentication is `401`; authenticated role or permission denial is `403`; current Shop retrieval returns `404` when the authenticated Merchant has no Shop and `403` when its Shop is inactive. Do not alter these contracts as part of AUTH-013. Resource-specific not-found behavior must not disclose another tenant's resource.

## 3. Resource/action matrix

| Resource / operation | Allowed actor | Scope | Restrictions and current implementation |
|---|---|---|---|
| Platform User account: create Merchant login | Super Admin | Platform; created Merchant identity | SA creates Merchant directly; no public Merchant application/review flow. **Policy only**; no Merchant-creation API found. |
| Own login, logout, token refresh | Merchant; Super Admin | Own account/session | Credentials identify actor. Login/recovery/refresh are public entry points; logout requires authenticated session. **Partial / implemented** in `users` APIs. |
| Change password | Merchant | Own account | Merchant role required. First-login temporary-password restriction limits authenticated API use to password change, logout, and refresh. **Implemented**. |
| Merchant password recovery | Merchant claimant | Own registered contact/account | Recovery challenge and throttling; it does not authorize Shop data access. **Implemented API**, delivery adapters are callbacks, not provider integrations. |
| Super Admin self password recovery | Super Admin claimant | Own account | Verified registered contact; successful reset invalidates own sessions. **Implemented API**. |
| Super Admin administrative password reset request | Authenticated Super Admin | Target Super Admin account | Initiator re-enters own password; target chooses new password using the single-use expiring recovery mechanism. This capability grants no target account or Shop data access. **Implemented API**, subject to documented technical/provider boundaries. |
| Shop: create | Merchant | Own authenticated Merchant profile | Only when no current Shop exists. Ownership is bound server-side; ignore client `shop_id` for authorization. **Implemented** at `POST /api/v1/shops/`. |
| Shop: retrieve own private profile | Active Merchant | Own Shop | No arbitrary Shop lookup; inactive Shop denied. **Implemented** at `GET /api/v1/shops/me/` and alias `GET /api/v1/shops/`. |
| Shop: edit profile / manage hours and delivery settings | Merchant | Own Shop | SA cannot browse/edit private Shop information. **Implemented** at `PATCH /api/v1/shops/me/`, `PUT /api/v1/shops/me/` (alias `/api/v1/shops/`). |
| Shop: deactivate | Super Admin | Target Shop | Super Admin controls lifecycle status. Merchant cannot deactivate/reactivate; Merchant requests return 403. **Implemented** at `POST /api/v1/shops/<pk>/deactivate/`. |
| Shop: suspend, reactivate, regenerate public QR/link | Super Admin | Named Shop lifecycle operation | No general private Shop browsing/editing implied. Reactivation rotates public slug/QR token, restores merchant access, and invalidates old slug. Standalone QR regeneration rotates token and invalidates old link. Merchant requests return 403. **Implemented** at `POST /api/v1/shops/<pk>/reactivate/` (alias `<pk>/unsuspend/`) and `POST /api/v1/shops/<pk>/regenerate-qr/` (alias `<pk>/regenerate-link/`). |
| Shop: permanently delete | Super Admin | Confirmed Shop | Super Admin only with explicit confirmation safeguard (`confirm=True`); removes Shop Products and Orders, invalidates public link, preserves Merchant account/credentials. Merchant requests return 403. **Implemented** at `DELETE /api/v1/shops/<pk>/`. |
| Public Shop details / QR destination | Anonymous visitor; Customer | One addressed active Shop, customer-facing fields only | Public identifier is generated `public_slug`, not a Shop ID. Inactive/deleted Shops return 404 `SHOP_UNAVAILABLE`. **Implemented** at `GET /api/v1/shops/public/<slug:public_slug>/`. |
| Master Catalog: browse | Anonymous visitor, Customer, Merchant; Super Admin for platform operations | Platform-global catalog | Visibility is not an authorization shortcut for editing. **Partial**: only `MasterCategory` model exists; no API. |
| Master Catalog: create/edit/remove | Super Admin | Platform-global catalog | Merchant cannot mutate platform catalog. **Policy/domain boundary only**; no workflow/API found. |
| Shop Catalog: browse | Anonymous visitor, Customer | Selected active Shop's customer-facing catalog | Never exposes another Shop's products or private fields. **Policy only**; no API found. |
| Shop Catalog: create/configure/edit/remove | Merchant | Own Shop catalog | Shop-specific products, prices and visibility; master catalog remains platform-owned. **Policy only**; no Shop catalog implementation/API found. |
| Inventory: view/change stock and availability | Merchant | Own Shop inventory | No access to another Shop's inventory; public availability is limited to approved customer-facing information. **Policy only**; no model/API found. |
| Customer profile and addresses: create/update for checkout | Anonymous visitor / Customer through the selected Shop flow | One Shop-specific Customer identity | Customer is not a login role. Only checkout-required details; WhatsApp number identifies/recognizes but does not authorize history. **Policy only**; no model/API found. |
| Customer records: merchant view/manage | Merchant | Own Shop's Customer records only, and only information needed for operations | No cross-Shop access. **Policy only**; no API found. |
| Customer records: platform access | Super Admin | No routine browse/edit authority established | Do not infer access from platform role; no such operation approved here. |
| Cart: create/read/change | Anonymous visitor / Customer | One cart in one Shop context | Anonymous cart may associate with that Shop's Customer when details are provided. No mixing Shops; no access to another customer's cart. Session/ownership mechanism remains a technical design requirement. **Policy only**; no API/model found. |
| Checkout / create Order | Anonymous visitor / Customer | Selected Shop and that cart/customer context | Must validate selected Shop's catalog, prices, fulfillment and required delivery address. Submission creates business transaction; it grants no later history access by phone number. **Policy only**; no API found. |
| Orders: list/detail/history for operations | Merchant | All Orders belonging to own Shop while it exists | No other Shop orders. **Policy only**; no Order model/API found. |
| Orders: customer history/detail | Customer using a scoped session | Only the session's Customer + Shop context | One-use 15-minute link; session maximum absolute lifetime 30 days; one active session per Customer + Shop. WhatsApp number alone is insufficient. Minimize exposed fields. Access flow unimplemented. |
| Order status: accept, reject, prepare, ready, complete; payment status | Merchant | Own Shop's Orders | Apply documented state/payment rules; only Merchant updates payment status. **Policy only**; no workflow/API found. |
| Order cancellation | Customer using a scoped session | Own `PENDING` Order before Merchant acceptance, in the same Shop | Requires server-side session/Customer/Shop/current-state checks, explicit confirmation, and CSRF protection. Uses existing `REJECTED` outcome; no separate `CANCELLED` state; release reserved stock atomically. **Approved policy; API unimplemented.** |
| Order cancellation after acceptance | Merchant | Own Shop's accepted Order before `PREPARING` | Uses existing `REJECTED` outcome. **Policy only**. |
| Campaigns: create/manage platform campaign | Super Admin | Platform campaign | No general access to private Shop data. **Policy/domain only**; no model/API found. |
| Campaigns: Shop display scope | Super Admin configures; Anonymous visitor / Customer views | Platform campaign displayed only in all-Shops or selected-Shop scope | Shop inclusion grants no ownership or management rights; Merchant campaigns are excluded in MVP. **Policy only**; no API found. |
| Notifications: configure/trigger operational messages | Merchant for own Shop settings; system for event delivery | Own Shop and its relevant Order/Customer event | Notification delivery does not grant recipient access to Orders or mutate Order state. **Policy only**; no workflow/API found. |
| Notification history | Merchant | Own Shop's history, subject to documented retention/privacy | Customer receives messages addressed to their Order but no general history query permission is established. **Policy only**; no model/API found. |
| Analytics: merchant reports | Merchant | Own Shop aggregates only | Must not expose another Shop's rows or permit tenant inference through filters/exports. **Policy only**; no API/model found. |
| Analytics: platform reports | Super Admin | Platform-level aggregates within documented privacy limits | Does not authorize browsing private Shop information or customer records. **Policy only**; no API/model found. |

## 4. Current authorization implementation

- `PlatformJWTAuthentication` authenticates Merchant and Super Admin Users, validates the live session, checks active account/profile state, and preserves the temporary-password restriction. Customer is not a JWT role.
- `IsMerchant`, `IsSuperAdmin`, and `IsActiveMerchant` protect the implemented role-specific operations. Shop retrieval derives the Shop through the authenticated user's Merchant relation; Shop creation assigns ownership server-side.
- Current implemented protected surfaces are password change, logout, Super Admin administrative reset request, and Merchant Shop create/retrieve. Login and recovery endpoints are intentionally unauthenticated entry points with their own credential/challenge validation.
- Other domain apps are scaffolds except the MasterCategory model. They have no implemented resource authorization to assess. The customer access-link holder currently has no implementation.
- The matrix records actor policy for documentation and future implementation. It does not define new API routes, database schema, authorization library, or token mechanics.

## 5. Required authorization tests before corresponding workflows ship

These are requirements for future implementation; this documentation task does not add or run tests.

- Unauthenticated requests to protected resources return the existing `401` behavior; authenticated wrong-role requests return `403`.
- Merchant A cannot list, retrieve, mutate, export, or infer Merchant B's Shop-owned records by path, query, body, nested relation, or submitted `shop_id`.
- Shop context comes from authenticated identity; no-Shop and inactive-Shop behavior retains current Shop API `404` / `403` contracts.
- Super Admin-only platform operations reject Merchants. Super Admin cannot use platform role to read or edit private Shop data absent an explicitly approved operation.
- Anonymous/public routes expose only intended customer-facing data for the requested active Shop and cannot access merchant, customer, order, or administrative resources.
- Customer-scoped actions cannot cross Shop boundaries. A WhatsApp number alone cannot retrieve Order history. Test the finalized 15-minute single-use grant, 30-day scoped session, one-session replacement, Shop-deletion revocation, enumeration resistance, and secret disclosure protections.
- Cart and checkout ownership/context tests cover cross-Shop product/cart injection, address requirements, and attempts to access another customer's cart or Order.
- Order action tests enforce actor, Shop ownership, allowed state transitions, cancellation windows, and payment-status authority.
- Campaign, notification/history, and analytics tests cover role restrictions, Shop scope, privacy, export/filter bypass, and prevent notification actions from mutating Orders.
- Recovery tests ensure public recovery endpoints do not create an authenticated resource-access session and administrative reset authority does not imply access to the target account's resources.

## 6. Conflicts and unresolved boundaries

1. `product.md` §15 describes Merchant applications and review, while current business and Merchant-account rules state Super Admin directly creates Merchant accounts and there is no public application/approval workflow. The stale Order-history statement in `product.md` §10 has been reconciled to the approved scoped-link/session design; the Merchant-application conflict remains unresolved.
2. `architecture.md` has older statements that authentication transport, Merchant/Shop relationship, and authorization are not finalized, while later architecture sections and current code define JWT/session behavior, role identity, and partial resource authorization. This matrix resolves documented role/resource boundaries for current approved rules; it does not claim full implementation.
3. AUTH-014 corrected `Shop.delete()` to preserve the Merchant profile and User credentials. Shop deletion APIs and invalidation of any future customer access grants/sessions are still unimplemented.
4. AUTH-015 approves pending Customer cancellation through that Customer's scoped session, with explicit confirmation, CSRF protection, the existing `REJECTED` outcome, and inventory release. AUTH-018 recommends an atomic profile-scoped endpoint and transaction; no implementation exists.
5. The link/session security lifecycle is finalized. Physical schema/API, Product/Privacy identity and retention approvals, provider, origin/cookie, and phone normalization/rates remain under review in `.ai/project-context/customer-order-history-access.md` §12.

## 7. References

- `.ai/project-context/business-rules.md`
- `.ai/project-context/architecture.md`
- `.ai/project-context/model-relationships.md`
- `.ai/project-context/development-status.md`
- `.ai/project-context/domains/users-and-merchant-accounts.md`
- `.ai/project-context/domains/shops.md`
- Domain specifications for catalog, inventory, customers, cart, orders, campaigns, notifications, and analytics.
