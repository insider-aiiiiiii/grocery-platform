# Customer Order-History Access and API Design

> [!IMPORTANT]
> **Architectural Amendment & Deprecation Notice (NOT-004 through NOT-007):**
> The customer-facing web order-history portal, tokenized history-link delivery, and customer session-exchange flow described in this document have been **deprecated and removed from the MVP scope**. 
> - **Customer Communication Model**: Customers receive order receipts, status progress notifications, and reorder links directly within their WhatsApp chat thread with the merchant using direct WhatsApp Click-to-Chat (`wa.me`) messages.
> - **Backend Order History**: Order history is maintained in the backend and exposed strictly to authenticated Merchants through ERP APIs (`/api/v1/customers/`, `/api/v1/shops/me/customers/`, and `/api/v1/orders/`).
> - The specifications below are retained for historical reference and context regarding customer profile isolation and data boundaries.

## 1. Status and scope

This document is the historical Customer Order-history access design register. It combines fixed AUTH-015 behavior, AUTH-017 API/persistence proposals, and AUTH-018 recommendations. Fixed behavior in §2 is approved and must not be reopened. AUTH-018 recommendations are not product/privacy approval: items marked **approval required** remain open. Nothing here authorizes implementation before its blocker decisions are recorded.

**Verified repository status:** Customer, Cart, Order, Inventory, and Notifications remain Django scaffolds. No Customer or Order models/APIs, link grants, Customer sessions, or WhatsApp provider integration exist. Platform authentication is Merchant/Super Admin JWT. The repository has PostgreSQL settings with SQLite fallback, Django CSRF middleware, and no Customer cookie authentication, CORS configuration, general rate-limit backend, or background task framework. See `development-status.md` and AUTH-016 implementation plan.

AUTH-015 fixed the security behavior below. AUTH-017 records a proposed technical realization and explicitly identifies decisions that still need review; no proposal here is runtime behavior or approval to implement unresolved choices.

## 2. Approved behavior (not open for reconsideration here)

- Customers have no traditional username/password account and the approved history flow does not use OTP. Customer credentials are separate from Merchant and Super Admin JWT authentication.
- Knowing a WhatsApp number alone never authorizes private Order history or Customer data. Possession of a delivered link is the initial proof; the resulting session is server-side and bound to exactly one Customer and Shop.
- A link is single-use, expires 15 minutes after issuance, and contains at least 256 bits of CSPRNG entropy. Only a one-way digest is stored. It is bound to purpose, Customer, Shop, issue/expiry and used/revoked state. A new link invalidates earlier unused grants in that Customer + Shop scope. Redemption is atomic.
- A Customer session has an absolute maximum lifetime of 30 days. Only one is active per Customer + Shop; a successful new redemption revokes/replaces the previous one. No silent indefinite renewal. Logout revokes the current session.
- The link is delivered to the number on the matching Shop-specific Customer record. A generic request/reissue flow does not reveal whether a number matches and never accepts a caller-selected delivery destination.
- After successful Order creation, the customer receives an Order-received acknowledgement and access link. The message must not imply the Order was accepted. Delivery is reported successful only after provider confirmation; delivery failure does not roll back the Order.
- A Customer session can cancel only that Customer’s own `PENDING` Order in the same Shop, after explicit confirmation and CSRF protection. The existing `REJECTED` outcome is used and reserved stock is released as part of the transition. WhatsApp messages cannot mutate Order state.
- Shop deletion invalidates grants and sessions for that Shop. Shop Products and Orders are removed under the approved Shop deletion rules. Customer retention follows the approved Customer rules; no retained Customer, history, or credential is transferred or attached to a replacement Shop.

## 3. Customer identity and relationships

### 3.1 Identity and Shop-profile proposal

There is no Customer model yet. AUTH-004 recommends separating a minimal platform-wide contact identity from Shop-specific Customer profiles and a global contact-claim authority. The boundary is a design recommendation, not approval to create a cross-Shop customer account or share Customer data. Product Owner/Privacy approval is still required to decide whether a matching contact across Shops represents one linked identity or only one globally unique contact value.

| Entity / field | Proposed Django representation | Purpose / rule |
|---|---|---|
| `CustomerIdentity.id` | Unselected | Minimal contact principal for Customer identity claims; not an account, profile, or login. No global name, address, Order history, cart, password, credential, authentication/session data, or Shop-specific data belongs here. |
| `ContactIdentityClaim` | Concept only; representation unselected | Reserves one globally unique WhatsApp contact value for exactly one eligible identity owner (authenticated `User` or `CustomerIdentity`). It is a uniqueness/ownership boundary, not proof of contact control, authentication, or authorization. |
| `ShopCustomerProfile.id` | `BigAutoField` | Internal primary key; never an authorization input. |
| `ShopCustomerProfile.shop` | `ForeignKey(shops.Shop, null=True, on_delete=SET_NULL)` | Active profile has one Shop; null is reserved for an inaccessible anonymized tombstone after permanent deletion and is never rebound. This preserves the current rule against globally deleting Customer entities solely due to Shop deletion, subject to approval of tombstone fields. |
| `ShopCustomerProfile.identity` | `ForeignKey(CustomerIdentity, null=True, on_delete=SET_NULL)` | Required for active profiles and unique together with Shop; cleared when a profile becomes a tombstone so it is never implicitly reattached to a surviving/reused global identity. |
| `ShopCustomerProfile.name` | `CharField(max_length=255, null=True, blank=True)` | Current name in this Shop only; required for an active profile and cleared for an anonymized tombstone; exact limit follows checkout contract. |
| `ShopCustomerProfile.created_at`, `updated_at` | `DateTimeField(auto_now_add=True)`, `DateTimeField(auto_now=True)` | Profile lifecycle timestamps. |
| address relation | Optional `CustomerAddress` child of profile | Saved-address support is not yet approved; if present, never shared across Shop profiles and never overwrites Order snapshots. |

**Recommended concept (approval required):** keep the global identity and claim minimal and separate from each `ShopCustomerProfile`, which owns only that Shop's Customer context. Do not store profile attributes, addresses, carts, Orders/history, credentials, authentication state, or sessions on a global record. Do not copy or expose names, addresses, Orders, or history between profiles. A contact submitted at Shop B may resolve to the identity already associated with Shop A only if an approved cross-Shop identity policy allows it; either way it never authorizes access to Shop A. The globally unique claim is the conceptual authority shared by authenticated `User` identities and `CustomerIdentity` records. Its physical ownership representation is not selected.

Examples: if a person with number X orders at Shop A and later Shop B, the recommendation creates Profile A and Profile B linked to one minimal CustomerIdentity, with separate names/addresses/carts/Orders; Shop B sees no Shop A history. If X is already claimed by a Merchant/Super Admin, Customer registration cannot claim it. The number is not verified merely because it was entered, and recycled-number ownership remains a product/privacy risk.

Alternatives: (1) one global Customer with profile-per-Shop relation can tempt accidental sharing of mutable Customer data; (2) one Customer row per Shop plus globally unique number prevents the same contact from being used at another Shop; (3) unlinked per-Shop Customers plus a global claim owner enforces uniqueness without representing cross-Shop recognition. The minimal identity/claim boundary with separate Shop profiles is recommended, not approved. Cross-Shop linkage, identity merge, claim transfer, number recycling, and how a Shop profile is created from an existing identity require Product Owner/Privacy approval.

### 3.2 Global WhatsApp uniqueness

**Approved business rule:** WhatsApp identity is globally unique across Customers, Merchants, and Super Admin mobile identities. Within a Shop, the number is the primary recognition input. Phone normalization is unresolved, so the platform cannot yet safely define equality for formatting variants. Global uniqueness is not authentication, proof of number control, or permission to link history across Shops.

Independent `UNIQUE` constraints on `Customer.whatsapp_number` and `User.mobile_number` cannot enforce cross-table uniqueness. Options are:

1. **Shared identity-claim authority (recommended concept):** one globally unique claim per WhatsApp contact value, assigned to exactly one authenticated User or CustomerIdentity. This centralizes uniqueness. The claim owner representation, constraints, and write contract remain open; possible implementations have different FK, migration, and app-coupling tradeoffs.
2. **PostgreSQL trigger across tables:** keeps current model fields but is PostgreSQL-specific, complicates SQLite development/tests and Django migration portability, and creates hidden write behavior.
3. **Application-only cross-table checks:** simplest initially but has a race between concurrent Customer/User creation and cannot guarantee the approved global uniqueness invariant.

**Recommendation:** enforce global uniqueness through one shared claim authority assigning a WhatsApp contact value to exactly one authenticated `User` or `CustomerIdentity`. This is conceptual: claim ownership encoding (typed generic reference, explicit foreign keys, or another design), owning app, database constraints, write/locking contract, and reconciliation behavior are not selected. Do not implement a polymorphic owner reference or assume a particular model, table, or API from this recommendation. Before schema work, approve phone normalization and canonical form, cross-Shop linkage, claim transfer/release rules, migration/backfill from existing `User.mobile_number` values, and collision handling. Backfill must identify canonicalization conflicts and pause for explicit resolution; never merge identities or choose a winner automatically. The existing `User.mobile_number` representation may need a compatibility transition, but its migration path is undecided.

Do not add OTP or mark a number as verified merely because it is entered at checkout. The history link is a separate bearer credential delivered to the recorded destination. A global claim reserves a value for uniqueness only; it does not establish current control of a phone number, authenticate its owner, or grant access to a profile or history.

### 3.3 Addresses and Order-time snapshots

Customer profile data is mutable; a prior Order must retain what was used at checkout. Recommended distinction:

- `CustomerAddress`: `id`, `customer_id`, optional user-facing `label`, address components/text, `created_at`, and `updated_at`. Each address belongs to one Customer; it is never a platform-global or cross-Shop address. One-versus-many addresses, exact fields, and address deletion behavior are unresolved.
- `Order`: keep immutable checkout-time customer name/contact and, for home delivery, address snapshot fields (or one structured snapshot representation selected by the Orders schema design). Do not render the current Customer profile as if it were the historical delivery address.

For a simpler MVP, a single current address on Customer is possible, but it overwrites the address used for prior purchases unless Orders still snapshots all required details. Recommend a separate address row plus Order-time snapshot, subject to the address/privacy decision. Customer history responses should not return full contact/address values by default; include only fields approved as necessary for the Order experience.

### 3.4 Relationships and deletion

```text
Global contact-claim authority (one unique WhatsApp contact value; owner representation unresolved)
   └── exactly one User OR CustomerIdentity owner
CustomerIdentity 1 ── * active ShopCustomerProfile ── 1 Shop
Anonymized ShopCustomerProfile tombstone (no CustomerIdentity or Shop link)
ShopCustomerProfile 1 ── * CustomerAddress
ShopCustomerProfile 1 ── * Order ── * OrderLine ── ShopProduct / Variant (historical line snapshots)
ShopCustomerProfile 1 ── * HistoryLinkGrant
ShopCustomerProfile 1 ── 0..1 active CustomerSession
```

**Scope enforcement recommendation:** make `ShopCustomerProfile` the single source of both Customer and Shop scope. Orders, addresses, grants, and sessions reference that profile; they do not store an independent `shop_id` that could disagree. Resolve Shop through `profile.shop_id`, and always filter protected queries by the authenticated profile and its Shop relationship. At creation, load the profile through the active Shop context and reject mismatches; never accept submitted Customer/Shop IDs as authority. Order lines must validate that every selected ShopProduct/Variant belongs to `order.customer_profile.shop_id`; Inventory reservation/release locks and verifies the same ShopProduct/Variant scope.

This normalized relationship makes database cross-column triggers unnecessary for Customer-versus-Shop equality because there is only one path. Use ordinary FK constraints, `UNIQUE(shop_id, identity_id)`, a check requiring Shop, identity, and name on active profiles, and requiring Shop, identity, and name to be null on tombstones; add unique token/session digests, partial active-grant/session uniqueness, check constraints for valid credential expiry/state, and indexes on profile/shop/status/time paths. Contact claim owner existence is validated by the serialized claim service and reconciliation because the recommended generic owner reference cannot have a normal FK; a DB trigger is an alternative but not recommended for MVP. If a later performance decision duplicates `shop_id` on a profile-scoped row, add a PostgreSQL composite FK or constraint trigger in a custom migration and test it on PostgreSQL; application validation alone is not a sufficient guard for deliberately duplicated scope columns. SQLite fallback tests cover basic FK behavior only, not lock correctness or PostgreSQL-specific constraints.

Recommended deletion behavior, pending Product Owner/privacy approval:

- `HistoryLinkGrant.customer_profile` and `CustomerSession.customer_profile`: `CASCADE` if a profile is permanently deleted. Because the recommended tombstone retains the profile with a null Shop, the Shop deletion coordinator must explicitly delete/revoke all grants and sessions for that Shop's profiles before setting their Shop FK to null. Retaining credential audit rows requires separate approval.
- `Order.customer_profile`: `PROTECT` for ordinary profile changes; the authorized Shop deletion transaction explicitly deletes that Shop's Orders before anonymizing/nulling its profiles, consistent with the approved Shop Order deletion rule.
- `ShopCustomerProfile.shop` and `.identity`: `SET_NULL` and anonymize the profile to a non-identifying tombstone when the Shop is deleted. It has no active scope or global identity link and cannot be used for checkout, history, recognition, grants or sessions. This is the recommendation that best preserves the current rule that Customer entities are not globally deleted solely because of Shop deletion while preventing retained PII/identity links from acting as transferable identity. The exact retained non-PII fields require Product Owner/Privacy approval.
- `CustomerAddress.profile`: `CASCADE` when the Shop profile is deleted/anonymized. Do not retain delivery addresses without an approved purpose and retention schedule.
- `CustomerIdentity` and its global claim: retain only while another active Shop profile or platform User requires it. When no active profile remains after deletion, recommend deleting/anonymizing the CustomerIdentity and releasing the number claim, allowing future use to create a new identity; this is a privacy/business choice requiring approval. Never transfer the old profile, address, Order, grant, or session to that new identity.

This recommendation preserves the approved behavior that Shop deletion does not globally delete Customer entities and does not transfer Customer records, while Shop Orders/Products are deleted. The tombstone must contain no active credentials, address, contact number, or history; only minimal non-identifying metadata may remain if approved. Whether a tombstone is required, which fields survive, and when a number may be reused are **Product Owner + Privacy approval items**. No legal retention period is inferred. Alternatives: `SET_NULL` without anonymization retains PII and risks stale access; `CASCADE` deletes the Customer entity contrary to current wording; tombstone/anonymization is recommended pending field-level approval.

## 4. Credential persistence proposal

These model shapes are the recommended implementation contract for review. They create credentials, not Django User accounts. Use UTC-aware datetimes; enforce comparisons against server time.

### 4.1 `HistoryLinkGrant`

| Field | Proposed type/constraint | Meaning |
|---|---|---|
| `id` | `BigAutoField` | Internal row key. |
| `token_digest` | `CharField(max_length=64, unique=True)` | Lowercase hex SHA-256 digest of 32+ random bytes. Never persist the plaintext bearer secret. |
| `purpose` | `CharField(max_length=32, choices=...)`, non-null | Fixed purpose value `ORDER_HISTORY`; reject any other purpose at exchange. |
| `customer_profile` | `ForeignKey(ShopCustomerProfile, on_delete=CASCADE)` | Exact Customer + Shop scope; Shop is derived from this profile, avoiding a conflicting duplicate Shop FK. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Issue time. |
| `expires_at` | `DateTimeField`, non-null | Exactly 15 minutes after issuance; validate `now < expires_at`. |
| `consumed_at` | `DateTimeField(null=True, blank=True)` | Set atomically on successful exchange only. |
| `revoked_at` | `DateTimeField(null=True, blank=True)` | Set on replacement, Shop/Customer deletion, or approved revocation. |

Add a partial unique constraint on `(customer_profile, purpose)` where `consumed_at IS NULL AND revoked_at IS NULL`, plus an index for profile/state/expiry cleanup and the unique digest index. Before issuing/reissuing, revoke any prior unconsumed grant for that profile (including expired rows), then insert the new grant in the same transaction. Expiration is time-based; periodic cleanup may remove consumed/revoked/expired grants after an approved operational/audit grace period. No raw token is recoverable from a row.

Generate a URL-safe encoding of `secrets.token_bytes(32)` or stronger; compute SHA-256 over the decoded secret. Compare digests safely. Use a purpose-separated secret format/domain tag if desired, but do not derive secrets from identifiers or use platform JWT signing. The grant secret is present only in worker memory and the outbound delivery body/URL; never write it to DB, outbox, queue payload, logs, analytics, error text, or API response.

### 4.2 `CustomerSession`

| Field | Proposed type/constraint | Meaning |
|---|---|---|
| `id` | `BigAutoField` | Internal row key. |
| `session_digest` | `CharField(max_length=64, unique=True)` | SHA-256 digest of a separate random 32+ byte Customer session secret. |
| `customer_profile` | `ForeignKey(ShopCustomerProfile, on_delete=CASCADE)` | Exact Customer + Shop scope, with Shop derived through the profile. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Absolute session start. |
| `expires_at` | `DateTimeField`, non-null | No later than `created_at + 30 days`; no rolling/sliding extension. |
| `revoked_at` | `DateTimeField(null=True, blank=True)` | Logout, replacement, or lifecycle revocation time. |
| `last_used_at` | Optional `DateTimeField(null=True, blank=True)` | Add only if operational need is approved; avoid unnecessary per-request writes/tracking. |

Enforce at most one unrevoked row per `customer_profile` with a conditional unique constraint on `revoked_at IS NULL`. An expired but not yet revoked row still occupies that key; session exchange must lock the profile, revoke the old/expired row, then create its replacement. Session validation always checks digest, revocation, `now < expires_at`, active Shop, and the profile's current Shop relationship. Cleanup of expired rows follows a reviewed retention period.

### 4.3 Migration dependencies

Recommended migration order, subject to decisions on normalization, claim ownership, and cross-Shop identity:

1. Select the contact-claim representation and owning app; approve phone normalization; audit/backfill existing `User.mobile_number` values and stop on canonical collisions before enforcing global uniqueness. Do not assume a generic owner pair, claim service, or migration graph until reviewed.
2. Add `CustomerIdentity` and its approved claim-owner relationship; add `ShopCustomerProfile` depending on identity and Shop, with the approved Shop/profile uniqueness rule, then any approved address child. Use the approved Shop deletion/tombstone lifecycle contract; do not backfill cross-Shop profile linkage automatically without identity/normalization approval.
3. Add Shop Product/Variant and Inventory base schema in their domains before Order lines/reservations. Preserve app ownership and avoid circular FKs.
4. Add `Order`/`OrderLine` depending on Shop, Customer, Product/Variant; add Inventory reservation rows after their referenced Order/OrderLine contract is established.
5. Add grant/session tables after Customer and Shop exist. They need no FK to Order; link delivery outbox records may depend on Order/Customer/Shop.
6. Add Notifications outbox/delivery schema after its selected event keys and Order/Customer/Shop references are defined.

Use nullable/staged fields and data migrations where needed; do not ship a schema migration that invents phone normalization, releases claims, or hard-deletes Customers. Migration dependencies must be checked with Django's migration graph to avoid cycles across apps.

### 4.4 PostgreSQL transaction and concurrency contract

Use `transaction.atomic()` and PostgreSQL row locks; uniqueness constraints are the final race guard, not a substitute for scope validation. Adopt a global lock order to avoid deadlocks: **Shop → CustomerIdentity/contact claim → ShopCustomerProfile → grant/session → Order → Inventory rows**. A session, grant, Order, or address resolves its Shop from its ShopCustomerProfile FK; do not add a second tenant FK without a reviewed database constraint.

- **Accept issue/reissue request:** resolve active Shop and ShopCustomerProfile server-side; lock Shop, then identity/profile; verify exact scope; revoke prior unused grants and create a safe outbox event in one transaction. The outbox contains only references/reason/generation, never the token. On Order creation the Order transaction writes its notification event; link generation happens only in the delivery worker.
- **Deliver link:** worker claims the current outbox row, locks/checks scope and generation, generates token in memory, stores only its digest and sends the link to the stored Customer number. A retry after losing the in-memory secret must revoke the prior grant, generate a fresh grant, and send a new link. This can make an earlier ambiguously delivered link unusable; retry policy and message UX remain provider decisions. Stale queued events are skipped so older links are not sent after newer requests.
- **Redeem:** hash supplied token to locate candidate; in one transaction lock Shop, CustomerIdentity/profile, then grant in the stated order; re-read and validate purpose, unused/unrevoked state and expiry; set `consumed_at`; revoke any prior unrevoked session; create a new independent session digest and expiry; commit before setting the response cookie. Two simultaneous redemptions of one grant have one winner. If cookie delivery is lost after commit, the customer can request a new link; the next redemption replaces the unreachable session.
- **Link request concurrency:** serialize by Shop + Customer before invalidating/inserting a grant. If using delivery generations/outbox rows, workers must skip superseded requests so an older queued link is not delivered after a newer request.
- **Cancellation:** derive Shop from the session's ShopCustomerProfile, then lock Shop, profile/session, Order, then Inventory records. Re-check profile ownership, active Shop, current state, and stock reservation while locked; update Order to `REJECTED` and release the reservation in the same transaction. On any failure, roll back both. A second request sees non-`PENDING` state and cannot release inventory again.
- **Shop deletion:** lock Shop; delete grants/sessions and Shop Orders/Products scoped through profiles; delete saved addresses; detach profile identity links; release/anonymize contact claims only as approved; anonymize retained profile fields and set profile Shop to null in the same transaction. Since retained tombstone profiles do not cascade from Shop, the deletion coordinator is responsible for explicit credential/order cleanup; tests must prove no credential survives. Replacement Shop creation never changes old profile references.

Partial indexes and `select_for_update()` behavior must be verified on the supported PostgreSQL version. SQLite does not provide equivalent row-lock semantics; SQLite tests can cover model/API basics but cannot prove redemption/reissue/cancellation concurrency. Use PostgreSQL-backed transaction tests with separate connections. Django conditional-unique support on SQLite is version-dependent; production integrity must not depend on SQLite behavior.

## 5. API contracts (proposed; require review)

Use `detail` and stable `code` fields consistent with existing auth API style. Candidate errors below are exact proposals; global API error format is not otherwise finalized. Never accept a `customer_id` or `shop_id` as proof of authorization.

### 5.1 Request/reissue a link

**`POST /api/v1/public/shops/{public_slug}/customer-history-link-requests/`**

- Authentication: public (`AllowAny` with platform JWT authentication explicitly disabled for this view).
- Request:

```json
{ "whatsapp_number": "+15551234567" }
```

- Server resolves an active Shop from its public slug, then matches the approved canonical number against that Shop's Customer. The Shop slug only chooses the public context. Destination is read from the Customer/contact identity row; ignore/reject destination overrides.
- Matching and non-matching Customer cases return the identical response, regardless of whether delivery was queued:

```http
HTTP/1.1 202 Accepted
Cache-Control: no-store
```

```json
{ "detail": "If eligible, a history link will be sent.", "code": "HISTORY_LINK_REQUEST_ACCEPTED" }
```

- Malformed request: `400 INVALID_REQUEST`, without profile-match details. Unknown/inactive public Shop: generic `404 SHOP_UNAVAILABLE`. Throttle: generic `429 REQUEST_LIMITED`; thresholds and dimensions are reviewed in §12. Neither errors nor response timing may reveal whether the number exists.
- Each accepted matching request invalidates older outstanding grants as part of the serialized issue request. This is not strictly idempotent: automatic retries can rotate a link and send another message. Add an `Idempotency-Key` only if client retry semantics and its retention are approved.
- Create a safe outbox event transactionally; delivery worker must not write plaintext token to the outbox. No API response returns a token, Customer/Order ID, or provider status.

### 5.2 Exchange the one-use link

**`POST /api/v1/customer/session/exchange/`**

- Authentication: public bearer exchange only; platform JWT authentication explicitly disabled.
- Request:

```json
{ "token": "<url-safe one-time secret>" }
```

- Success: `204 No Content`, `Cache-Control: no-store`, set the separate Customer session cookie. Set a CSRF cookie/token using the reviewed Django CSRF mechanism. The session secret is not returned in JSON.
- Any malformed, unknown, expired, consumed, revoked, wrong-purpose, or wrong-scope token returns the same status/body, proposed as `400`:

```json
{ "detail": "The history link is invalid or expired.", "code": "INVALID_OR_EXPIRED_LINK" }
```

- Rate-limit by source IP and safe grant fingerprint. Do not consume on GET, link preview, scanner, or failed validation. Atomic redemption is as in §4.4.
- Validate token encoding/maximum length before lookup, but return the same public invalid-link response for malformed and unknown values. Do not log the submitted token.
- A custom Customer authentication class must be isolated to Customer endpoints. The exchange view must not issue a Merchant/Super Admin JWT or establish a Django User login.

### 5.3 Read the authenticated Customer’s Order history

**`GET /api/v1/customer/orders/`**

- Authentication: valid Customer session cookie only. No Customer/Shop query parameters. Missing/invalid/expired/revoked cookie returns `401 CUSTOMER_SESSION_REQUIRED`.
- Success: `200`, paginated under the proposed `{ "results": [...], "next": null }` envelope. Example (fields are a minimized proposal pending Orders schema review):

```json
{
  "results": [
    {
      "reference": "4ce12d56-16e5-4a2d-8673-2fdf3465682f",
      "created_at": "2026-10-05T12:00:00Z",
      "status": "PENDING",
      "fulfillment": "PICKUP",
      "total": "125.00",
      "items": [{ "name": "Rice", "variant": "5 kg", "quantity": 1, "line_total": "125.00" }]
    }
  ],
  "next": null
}
```

- Query is rooted in the session Customer and exact Shop. Only reviewed historical fields are serialized; do not expose contact, address, payment instructions, Merchant-only notes, or another Customer’s rows by default. Pagination size/ordering and currency representation must match the Orders design.
- Validate pagination/cursor inputs and cap page size. Apply abuse limits by session and source IP; return no Shop/Customer selectors in the contract.

### 5.4 Read an individual Order

**`GET /api/v1/customer/orders/{public_order_reference}/`**

- Authentication/scope: same Customer session as history list. Candidate Order reference is a non-sequential UUID generated for customer-facing lookup; it is not an authorization credential.
- Success: `200` with the same minimized Order fields plus only approved detail fields.
- Missing and out-of-session Customer/Shop Orders both return `404 ORDER_NOT_FOUND`. No arbitrary Customer/Shop IDs or nested unscoped references are accepted. A valid session never grants access to Orders in another Shop.
- Validate reference format before lookup and rate-limit repeated guessed-reference traffic by session/IP. Keep missing and foreign-scope responses indistinguishable.

### 5.5 Cancel a pending Order

**`POST /api/v1/customer/orders/{public_order_reference}/cancellation/`**

- Authentication: valid Customer cookie; session Customer and Shop derived on the server. CSRF token and approved Origin/Referer checks are mandatory because this is a cookie-authenticated mutation.
- Request:

```json
{ "confirmed": true }
```

- Re-read and lock the Order; require matching session Customer, Shop, and current `PENDING` state. In one transaction call the Inventory-owned release operation and transition to the existing `REJECTED` state. No separate `CANCELLED` state is added.
- Success: `200`:

```json
{ "reference": "4ce12d56-16e5-4a2d-8673-2fdf3465682f", "status": "REJECTED" }
```

- Missing/invalid session: `401`; CSRF/Origin failure: `403`; malformed/missing confirmation: `400 CONFIRMATION_REQUIRED`; absent or foreign-scope Order: `404 ORDER_NOT_FOUND`; owned Order no longer `PENDING`: `409 ORDER_NOT_PENDING`. Error text does not disclose another Customer’s Order.
- A repeated/concurrent cancellation cannot release stock twice: the first transaction moves the status; the next sees non-`PENDING` and returns `409`. If clients need replay of the original success response after network loss, add an approved idempotency key/event record; do not infer a prior Customer cancellation from `REJECTED` alone.
- Accept only the documented confirmation field and reject unexpected/malformed body data. Apply limits by session, Order reference, and source IP without making a foreign Order discoverable.

### 5.6 Log out the current Customer session

**`POST /api/v1/customer/session/logout/`**

- Authentication: the cookie is the only session selector; do not accept a session ID in body/path. The operation is idempotent for absent, invalid, expired, or revoked cookies. Disable platform JWT authentication. Apply CSRF/Origin checks to this cookie-triggered mutation even when the cookie no longer resolves to a live session.
- Revoke only the digest-matched current live session, clear the session cookie with matching attributes, and return `204 No Content` without revealing whether it matched. Never revoke a different session based on client identifiers.
- Ignore/reject arbitrary session selectors in the request. Apply modest session/IP request limits; repeated logout remains safe and idempotent.

### 5.7 Obtain a CSRF token

**`GET /api/v1/customer/session/csrf/`**

- Authentication: valid Customer session cookie.
- Success: `200 OK`, `Cache-Control: no-store`, body `{ "csrfToken": "<masked Django CSRF token>" }`. The browser sends this value in `X-CSRFToken` for cancellation and logout. The endpoint may set Django's CSRF cookie according to the reviewed deployment; only the Customer session cookie is required to be HttpOnly.
- This value is a CSRF defense, not an authentication credential. Do not return the Customer session secret. Same-origin/CORS and cookie attributes remain deployment decisions.
- Limit excessive bootstrap requests by session/IP; do not log CSRF values.

### 5.8 Authentication matrix

| Endpoint class | Authentication | Authorization / scope | Public failure behavior |
|---|---|---|---|
| Link request | Anonymous only | Public Shop slug selects active Shop; Customer resolved by canonical contact server-side | Generic response for number match/non-match; generic throttling. |
| Link exchange | Anonymous one-time bearer input only | Grant digest must resolve to exact Customer + Shop and pass purpose/lifecycle checks | Same response for all invalid grant reasons. |
| CSRF bootstrap | Customer session cookie | Returns only a masked CSRF token for same session; no data access | `401` invalid session; `200` token with no-store. |
| History list/detail | Customer session cookie only | Querysets constrained by session Customer + Shop | `401` invalid session; `404` missing/foreign Order. |
| Cancellation | Customer session cookie + CSRF | Same Customer + Shop, own `PENDING` Order only | `401` auth; `403` CSRF/Origin; `404` foreign/missing; `409` own Order not pending. |
| Logout | Current Customer cookie selector + CSRF; no live session required | Revoke only the matching current session if it remains live | Idempotent `204`; no other-session selector or session-state disclosure. |
| Merchant/Super Admin APIs | Existing platform JWT | Existing roles/permissions and Shop derivation unchanged | Customer cookie is never platform authentication. |

## 6. Browser, cookie, and CSRF boundary

**Recommended end-to-end browser contract (deployment hosts remain open):** (1) customer opens the first-party link page over HTTPS; (2) the page reads the fragment secret and calls `history.replaceState` before loading scripts, fonts, images, or analytics; (3) after explicit page handling, it POSTs the secret in JSON to the exchange endpoint; (4) the exchange response sets only the dedicated Customer-session cookie as `Secure; HttpOnly` and returns `204`, never a session secret; (5) frontend then calls the separate authenticated CSRF bootstrap GET, which returns a masked CSRF token in JSON and may set Django's CSRF cookie; (6) frontend keeps that masked token in memory and sends it in `X-CSRFToken` on cancellation/logout; (7) history GET uses the HttpOnly session cookie; mutation POST uses both session cookie and CSRF header; (8) logout revokes the current session, clears its cookie using identical cookie attributes, and returns idempotent `204`.

The CSRF token is not an authentication credential and may be exposed to same-origin frontend JavaScript. The Customer session secret must never be exposed to JavaScript, localStorage, or JSON. The Django CSRF cookie may be JavaScript-readable if using Django's standard double-submit pattern; alternatively keep it HttpOnly and use the masked token returned by bootstrap. Choose one consistent deployment configuration. For DRF, explicitly disable platform JWT authentication on the public link/exchange views; protected Customer views use only a dedicated cookie authenticator. DRF's custom authentication path must invoke Django CSRF validation for unsafe methods (e.g. `SessionAuthentication.enforce_csrf`-style validation or equivalent), since middleware behavior alone does not prove the custom authenticator enforces CSRF. Enforce configured Origin and Referer checks alongside CSRF for cookie-authenticated mutations; reject absent/untrusted origin according to the selected HTTPS deployment policy. The allowed origins, `CSRF_TRUSTED_ORIGINS`, cookie Domain/Path, and exact SameSite/CORS settings remain deployment decisions.

- Serve the access link over HTTPS with the bearer secret in the URL fragment, never path/query. The first-party page reads the fragment and immediately calls `history.replaceState` before loading any other resource, then POSTs once to exchange.
- Link GET must not consume or revoke a grant. Preview/crawler/scanner requests only retrieve the static landing page. User action triggers POST.
- Use a dedicated Customer session cookie, separate from Django session and platform JWT. Required: `Secure`, `HttpOnly`, and narrow scope. The exact cookie name, `SameSite`, Domain, Path, frontend/API origins, and CORS credentials remain deployment decisions; prefer host-only scope if topology allows.
- Cookie-authenticated POST cancellation and logout require CSRF protection and Origin/Referer validation. Django’s installed `CsrfViewMiddleware` is not sufficient by itself for a custom DRF cookie authenticator if the APIView is CSRF-exempt. The proposed `CustomerSessionAuthentication` must explicitly invoke Django CSRF validation for unsafe methods or use another reviewed mechanism. Expose a CSRF token through a reviewed same-origin bootstrap/exchange response; never expose the Customer session secret to JavaScript.
- Use `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, restrictive CSP, no third-party scripts/fonts/analytics on exchange page, no-store browser handling, and secret redaction across app/proxy/provider/tracing/error/analytics. Avoid putting links in support logs.
- Public link request and link exchange are the only unauthenticated Customer routes. Set explicit `AllowAny` and disable platform JWT authentication for these views to avoid accidental auth behavior. Customer history routes accept only the dedicated Customer session authenticator.

## 7. Abuse controls and enumeration resistance

- Link request returns the same status, response body, and broadly similar timing for matching and nonmatching Customer number. Provider execution must not occur synchronously in this request. Never expose whether a number is registered, whether a message was sent, or an Order/customer identifier.
- Throttle by IP/network, Shop, keyed digest of normalized number, grant fingerprint, session fingerprint, and outbound volume per Customer/Shop and globally. Do not log raw numbers or bearer values. Exact thresholds, proxy trust, HMAC key rotation, and shared state are unresolved.
- WhatsApp destination is read only from the stored Customer contact identity; caller cannot select or replace destination. Reissue never creates a Customer.
- Keep safe audit events only (event type, internal safe reference, coarse source); never persist the link secret or session secret in logs, analytics, exception output, or request tracing.
- A delivered bearer link can be forwarded or intercepted with the recipient’s messaging account; it grants scoped history until use/revocation/expiry. Minimize displayed fields and use reviewed customer copy to explain link possession risk.

## 8. Notification outbox and secret handoff

The repository has no worker or queue, while the link secret must be digest-only at rest and provider work must not disclose Customer existence by request timing. **Recommended contract:** use a database outbox table and a small Django management-command worker in this modular monolith; do not introduce a broker/distributed queue for MVP absent measured throughput or reliability need. Provider, hosting process, retry limits, and customer-facing failure copy remain approval items.

- In the Order transaction, write a delivery outbox row containing event kind, Order/Profile reference, monotonically increasing per-profile generation, deduplication key, and timestamps/status; do not include a link/token or raw phone number. This row is the durable notification intent and commits atomically with successful Order creation. A link reissue request similarly validates eligibility in a transaction and records a reference-only request event while returning the same generic response for a match or non-match.
- A worker claims one event using a database row lock/lease, revalidates active Shop/Profile and current generation, generates the random secret in memory, commits only its digest in `HistoryLinkGrant`, then sends the fragment URL to the contact destination loaded from the authoritative identity claim. Before provider submission it checks generation again; an older queued generation is marked superseded and never submitted. The profile-generation update and new outbox row are serialized on the profile lock. A message already submitted to the provider cannot be recalled; if a newer request supersedes it, its grant is revoked so a late-arriving old link fails. No design can prevent a provider from delivering an already-submitted message out of order; provider behavior and customer copy remain approval items.
- On transient/ambiguous provider timeout, do not claim delivery failure or success immediately. Record `UNKNOWN/PENDING_CONFIRMATION`; query provider status or await an authenticated callback where supported. If retry policy ultimately retries, revoke the prior grant and create a fresh grant/secret, making any ambiguously delivered prior link invalid; this can create another message and requires approved retry bounds/copy. Never persist recoverable plaintext in DB, outbox, broker, or logs.
- Give each outbox event and provider attempt stable idempotency keys. Enforce unique `(event, attempt)` and provider event/callback IDs; callback handlers are idempotent and update delivery state only, never create Orders or change Order lifecycle. Business effects (Order creation, cancellation, inventory release) remain in their owning transactions and have their own state/uniqueness guards.
- Report delivery success only when the selected provider's authenticated status confirms the agreed success state (accepted/sent versus delivered must be defined by provider semantics); an HTTP submission acknowledgement alone is not represented as delivered. If provider does not offer authenticated status, document the weaker observable status and obtain approval before labeling it success.

## 9. Order and Inventory transaction contract

Orders owns lifecycle and must invoke Inventory-owned operations; it must not mutate Inventory internals directly. On cancellation, lock and validate session scope and Order, verify `PENDING`, then call a release operation in the same database transaction as setting `REJECTED`. The Inventory operation must verify the corresponding reservation and change it at most once. Any exception rolls back both state and stock release. Follow a consistent row-lock order (Shop → Customer/session → Order → Inventory) for issue/redeem/cancel/deletion workflows. PostgreSQL row locks and constraints enforce races; SQLite tests cannot validate this contract.

Merchant acceptance/rejection may race Customer cancellation. Exactly one state transition may commit from `PENDING`; the loser observes the current status and changes no inventory. Repeated cancellation returns `409 ORDER_NOT_PENDING` unless a future idempotency record is approved; stock is never released twice. Notifications are emitted through an outbox after the successful transaction and never change state.

## 10. Implementation tasks and acceptance criteria

| ID | Work/dependencies | Acceptance criteria |
|---|---|---|
| AUTH-018 (proposed; not a GitHub issue) — Approve identity, retention, and deployment decisions | Review §12; agree canonical phone normalization/global claim migration, orphan Customer handling, address/snapshot fields, API/error contract, cookie/CSRF/origin, rate limits, provider/outbox and Customer retention. | Decisions are recorded; AUTH-015 fixed rules remain unchanged; all APIs, fields, FK behavior, deployment config, and provider boundaries have an approved design. |
| CUST-FOUND — Customer/contact identity | Depends on AUTH-018. Add Customer/contact-claim/address schema and staged migration; backfill existing User mobile claims. | Global canonical number uniqueness holds under concurrent Customer/User claim attempts; Shop isolation and approved orphan behavior pass migration/integrity tests. |
| ORDER-FOUND — Product, cart, Order, Inventory prerequisites | Depends on CUST-FOUND and domain schema decisions. Add Shop Product/Variant, inventory reservation, Cart/checkout, Order/OrderLine snapshot data in owning apps. | Checkout creates correctly scoped Customer/Order and reserves stock; models and API derive Shop server-side. |
| CRED-CORE — Grants and sessions | Depends on both foundation tracks. Implement digest-only credentials, lifecycle constraints, atomic reissue/redemption/session replacement/logout. | Fixed TTL, purpose/scope, one-use and one-active behavior passes PostgreSQL transaction tests; no secret persistence/log leakage. |
| CUSTOMER-API — Link request, exchange, history, detail, logout | Depends on CRED-CORE and approved deployment/browser contract. | Exact §5 contracts, generic errors, no enumeration, no cross-tenant reads, cookie/CSRF and no-store/referrer/CSP controls verified. |
| ORDER-CANCEL — Customer cancellation | Depends on CUSTOMER-API and Inventory release operation. | Own pending Order only; confirmation, CSRF, locked status re-check; existing REJECTED outcome and one-time stock release. |
| WHATSAPP-OUTBOX — Delivery/reissue | Depends on approved provider and worker design plus Orders/CRED-CORE. | Outbox stores no bearer secret/raw phone; destination is stored Customer contact; provider confirmation/idempotency and failure retry work without enumeration. |
| SHOP-DELETE — Lifecycle invalidation | Depends on Shop deletion API/safeguards and credential/foundation models. | Delete invalidates grants/sessions and removes Shop Orders/Products; retained Customer follows approved policy and is never rebound to replacement Shop; Merchant credentials preserved. |
| RELEASE-SEC — Release review | Depends on all implementation tasks. | Unit/API/auth/concurrency/privacy/provider tests pass on PostgreSQL and deployment topology; limitations/status docs accurate. |

Acceptance/test detail is in §11. The legacy AUTH-016 plan remains a sequencing overview; this document refines its credential/API and transaction phases.

## 11. Required tests

### Models/domain

- Contact claim canonical uniqueness across User and Customer, migration backfill, concurrent claim attempts, orphan Customer behavior, and no reattachment to replacement Shop.
- Grant random entropy, digest-only persistence, purpose/Customer/Shop binding, 15-minute boundary, consumed/revoked/expired state, prior-grant invalidation, and cleanup policy.
- Session 30-day absolute expiry, one active session per Customer + Shop, replacement, logout, Shop deletion invalidation, and invalid scope relationship.
- Address changes do not rewrite Order-time delivery snapshots; Customer identity/profile updates do not silently rewrite historical Order values.

### API and auth

- Matching/nonmatching/unknown Customer requests return same `202` body/status and do not reveal IDs, token, phone match, or provider status; malformed input and throttles do not become account-existence oracles.
- Exchange has one concurrent winner; GET, previews, and scanners do not consume. All invalid token classes produce identical response; no token/session secret in API errors/logs.
- Customer session cannot authenticate Merchant/Super Admin endpoints; platform JWT alone cannot access Customer routes. Customer history list/detail remain scoped despite guessed Order references, filters, nested IDs, and body/query Customer/Shop parameters.
- Cookie flags match approved deployment. CSRF enforcement is tested with DRF/API client CSRF checks enabled; missing/invalid token or disallowed origin rejects logout/cancel. No state changes on GET.
- Cancellation requires explicit confirmation, session+Customer+Shop scope, own `PENDING` Order, and commits `REJECTED` plus inventory release atomically. Foreign Order returns 404; non-pending returns 409; duplicate/concurrent call never double-releases stock.
- Logout only invalidates current digest and is idempotent. Shop deletion invalidates all credentials and no old records are visible via replacement Shop.

### PostgreSQL concurrency and delivery

- PostgreSQL `TransactionTestCase` with separate connections covers reissue races, grant replay, session replacement, Shop deletion vs exchange, cancellation vs Merchant transition, and cancellation stock release. SQLite is not accepted as evidence of row-lock correctness.
- Outbox event is committed with Order/request intent and contains no token/raw destination; stale events are skipped; callback/retry idempotency prevents duplicate business effects. Failed/ambiguous provider send rotates the grant and does not roll back Order creation.
- Verify rate limits by IP, Shop, canonical number fingerprint, grant/session fingerprint, and outbound volume; raw personal identifiers/secrets are absent from throttle and audit records.
- Verify URL fragment cleanup, referrer/cache/CSP headers, absence of third-party assets, and log/tracing redaction in a frontend/browser deployment test.

## 12. Authoritative decision register

This is the only detailed register for remaining AUTH-015/016/017/018 decisions. Recommendations are defaults for approval, not approved business behavior. “Blocks implementation” means the listed domain work must not begin until the named approval/technical gate is met.

| Decision / options and implications | Recommended default (status) | Approval owner / dependencies | Blocks implementation? |
|---|---|---|---|
| **A. Identity across Shops.** One Customer row per Shop plus global unique number prevents the same number being used at another Shop. One global profile risks cross-Shop data sharing. An unlinked claim owner enforces uniqueness but cannot support clean recognition. | Separate minimal `CustomerIdentity` from `ShopCustomerProfile`; one identity may have multiple Shop-specific profiles, with no shared name/address/history. Example: same contact at Shops A/B has separate profiles and histories. **Pending Product Owner approval** because existing rules do not settle whether cross-Shop contact matching is intended. | Product Owner; identity semantics, normalization and customer-facing duplicate/number-reuse behavior. | **Yes**, Customer/contact schema and checkout recognition. |
| **Phone normalization and contact migration.** Raw formatting comparisons permit duplicates; canonical formats depend on target countries and existing data. | Require an explicit country/number parsing policy (E.164 candidate), preserve display form separately, stage `User.mobile_number` backfill, report collisions and stop for manual resolution. Never infer verification or merge accounts. **Approval required.** | Product Owner for supported countries/input; Users owner for compatibility; migration review. | **Yes**, identity claim and Customer checkout. |
| **Identity-claim integrity and ownership representation.** Independent constraints do not enforce cross-table uniqueness. Generic references lack ordinary FKs; explicit FK layouts can affect app ownership and migration dependencies; database triggers are PostgreSQL-specific. | A shared claim authority reserves each globally unique WhatsApp contact value for one authenticated `User` or `CustomerIdentity`. Its physical owner representation, app ownership, integrity mechanism, and write contract remain undecided. **Technical decision required.** | Users/Customers technical owners; migration graph, supported database behavior, existing duplicate audit. | **Yes**, contact identity migration. |
| **AUTH-004 contact identity boundary.** A global record can accidentally become a cross-Shop customer account or hold data that belongs to tenant profiles. | Keep the global identity minimal and separate from the claim authority and Shop profiles. Store no profile, address, Order/history, cart, credential, authentication, or session data globally. The claim is uniqueness only and grants no identity proof or access. **Recommended direction; Product Owner/Privacy approval required for cross-Shop linkage.** | Product Owner/Privacy; identity semantics, normalization, number reuse. | **Yes**, Customer identity schema and checkout recognition. |
| **B. Shop deletion, Customer retention, PII, address, and phone reuse.** `SET_NULL` preserves rows and possibly PII; cascade deletes Shop profiles; tombstone/anonymization preserves limited evidence but needs field policy. Keeping a global claim blocks reuse; releasing it permits a fresh identity. | `SET_NULL` and anonymize Shop profile to an inaccessible tombstone; cascade addresses, grants, sessions, Orders/Products as approved; never rebind. Retain only minimal non-identifying tombstone fields if approved. Release a number claim only after old identity is no longer identifiable and create a new identity/profile; never transfer. **Product Owner + Privacy approval required; no retention duration proposed.** | Product Owner and Privacy/legal; field-level tombstone and phone-reuse decision. | **Yes**, Shop deletion integration and Customer FK behavior. |
| **Customer addresses and Order snapshots.** One mutable address is simple but rewrites context; multiple saved addresses increase retained PII; immutable Order snapshots preserve purchase meaning. | Optional Shop-profile-owned addresses only if product approves saved addresses; otherwise collect checkout address transiently. Always snapshot the minimum name/contact and required delivery address used by an Order; history serializer minimizes those fields. Address field structure and retention need approval. | Product Owner/Privacy; checkout and Orders schema. | **Yes** for address model; Order foundation can proceed only with a field-level snapshot contract. |
| **C. Customer + Shop scope.** Independent `customer_id` and `shop_id` FKs can disagree. Application-only checks are race/bypass-prone when redundant columns exist. | `ShopCustomerProfile` is the single scope root; address, grant, session and Order point to it, and Shop is derived through profile. Add ordinary FKs, unique `(shop, identity)`, state checks, unique digests and scoped indexes. Validate Product/Variant and Inventory belong to `profile.shop_id` inside the locked transaction. Do not duplicate Shop FKs. This removes need for cross-column trigger; if later denormalized, add PostgreSQL composite FK/constraint trigger. **Technical recommendation ready for review.** | Django/database reviewer; domain schemas and query plan. | **Yes** for Customer/Order/credential schema. |
| **Credential fields, indexes, constraints, deletion.** Partial unique constraints and row-lock behavior vary by DB; retaining credential rows aids audit but increases linkable data. | Keep the proposed digest-only grant/session fields in §§4.1–4.2, tied to profile; unique digest, partial unique outstanding grant/active session, expiry/state checks and scoped cleanup indexes. Cascade-delete credentials on permanent profile deletion; Shop deletion transaction explicitly deletes credentials before tombstoning the retained profile. Separate safe audit retention if approved. PostgreSQL is concurrency authority; SQLite is basic behavior only. **Technical recommendation ready for review.** | Database reviewer; selected PostgreSQL version, Django migration support and audit policy. | **Yes**, credential implementation. |
| **PostgreSQL locks and migration dependencies.** Lock order inconsistency can deadlock; SQLite cannot prove row-lock races; cross-app FKs can cycle. | Use `transaction.atomic()`, lock order Shop → CustomerIdentity/claim → profile → credential → Order → Inventory; rely on DB uniqueness as race guard. Follow §4.3 migration order and check migration graph. Race tests use PostgreSQL separate connections. **Technical recommendation ready for review.** | Backend/database reviewer; CI PostgreSQL availability. | **Yes**, redemption/reissue/cancellation and release. |
| **API paths, responses, errors, fields, public Order reference.** IDs may enumerate; overly generic errors harm usability; exact fields depend on absent Order model. | Use proposed six contracts in §5, UUID public Order references, generic link/exchange errors, 404 for missing/foreign Order, 409 for an owned non-pending Order, stable `detail`/`code`, and minimized list/detail fields. Treat payloads and routes as **candidate contract pending API review**; no `customer_id`/`shop_id` selectors. | API/product reviewer; global response conventions and Order schema. | **Yes**, public API release; foundations can precede route approval. |
| **D. Cookie, CSRF, Origin/Referer, frontend/API deployment.** Same-site supports narrow cookies; cross-site needs credentialed CORS and stronger configuration. | Follow complete sequence in §6: exchange sets only `Secure; HttpOnly` Customer cookie; separate authenticated CSRF bootstrap returns masked token for memory/header; DRF Customer cookie authenticator explicitly enforces Django CSRF on unsafe methods and trusted Origin/Referer. **Security contract recommended; hosts, Domain/Path, SameSite, CORS, trusted origins remain deployment-dependent.** | Deployment owner + security reviewer; frontend/API hosts, TLS proxy behavior and browsers. | **Yes**, browser/API release; core models may proceed after technical schema gate. |
| **Rate-limit keys, storage, thresholds, proxy trust.** Local memory is not shared; DB throttles add write load; trusting forwarded IP headers blindly enables spoofing; aggressive limits affect shared networks. | Layer trusted client IP/network, Shop, keyed HMAC number fingerprint, grant/session fingerprint and outbound caps; use shared deployment storage, rotate HMAC key, do not log raw identifiers. Exact thresholds and proxy trust configuration remain deployment/security approval items. | Security/operations owner; traffic model, proxy chain, shared cache/store. | **Yes**, public link-request/release; not Customer model foundation. |
| **E. Provider, confirmation, retry, failure copy.** Providers differ in idempotency and delivery statuses; timeout may mean message sent or not; retries can invalidate a delivered grant. | Provider-neutral outbox contract in §8. Distinguish submitted/accepted/delivered; claim delivery success only on authenticated provider confirmation matching agreed semantics. Ambiguous retry rotates grant; bounded retry and customer copy remain open. No Order rollback. **Provider/business approval required.** | Product Owner + Notifications/operations; provider contract, templates, callback authentication. | **Yes**, delivery release; Order creation itself need not wait for provider. |
| **Outbox and worker deployment.** Synchronous sending leaks timing; distributed queue adds unapproved infrastructure; DB polling is simpler but requires worker operations. | Reference-only DB outbox committed with Order/request intent; Django management-command worker with row lease/lock; per-profile generation prevents stale sends; secrets generated in memory and digest persisted before send. No broker unless measured need approved. **Technical recommendation ready; operations approval for worker topology.** | Backend/operations; hosting process and monitoring. | **Yes**, link delivery; Order creation can record outbox intent. |
| **Idempotency for reissue, provider callbacks, and cancellation.** Reissue rotates secrets; duplicate callbacks can repeat effects; cancellation retry may see REJECTED after network loss. | Stable outbox/event and provider-attempt IDs with uniqueness; callback processing idempotent and status-only. Reissue remains explicitly non-idempotent unless an approved request key/retention contract is added. Cancellation's locked PENDING transition prevents double stock release; exact replay of success requires a separate approved idempotency record. | API/Product + Notifications owner; retry/client semantics and retention. | **Yes** for external delivery and exact replay; cancellation state safety can use transaction/state guard. |
| **Revocation/recovery beyond approved lifecycle.** Logout revokes the current session; successful link exchange replaces the prior session; Shop deletion invalidates Shop credentials. Revoke-all, operator intervention, compromised-number recovery, and support identity proof are not defined. | Implement only the approved current-session logout, replacement, link reissue, and Shop deletion invalidation. Do not add customer-wide or operator revocation controls until proof, authority, and UX are approved. | Product Owner + Security/Support; recovery support process and number-change policy. | **Yes** for any revoke-all/support workflow; no blocker to implementing the approved logout/reissue flows. |
| **Audit, notification history, credential cleanup and retention.** Detailed logs/history aid support but contain linkable personal data. | Store no secrets/raw phone; keep only safe event metadata. Cascade credential cleanup; minimize outbox/provider identifiers and delete them under approved retention. No retention duration is set here. **Privacy/operations approval required.** | Privacy/legal and operations; retention obligations and support needs. | **Yes** for audit/history implementation, not core token correctness. |

### AUTH-018 approval summary

- **Already approved and fixed:** all requirements in §2, including no OTP/password Customer account, number not credential, link/session lifetimes, scope, cancellation state/CSRF/inventory effects, deletion invalidation, no transfer, and no Order rollback on delivery failure.
- **Technical recommendations ready for approval:** split identity/profile model; shared contact-claim authority with ownership representation still undecided; profile as single scope root; grant/session constraints and PostgreSQL lock/migration strategy; candidate API contract; dedicated HttpOnly session cookie plus separate CSRF bootstrap; reference-only outbox with a simple Django worker and generation/idempotency guards.
- **Product/privacy decisions required:** whether cross-Shop contact identity should create separate linked profiles; Customer/profile/address deletion or tombstone behavior; number-claim release/reuse after Shop deletion or number change/recycling; address fields and retention; exact history fields; notification/audit retention and customer-facing ambiguous-delivery copy. No legal retention period is inferred.
- **Deployment/provider decisions required:** frontend/API origins, cookie Domain/Path/SameSite, CORS and trusted origins; trusted proxy chain and shared rate-limit storage/thresholds; provider, authenticated callback/status semantics, retry bounds, worker hosting/monitoring.
- **Remaining implementation blockers:** record Product Owner/Privacy choices above; approve phone normalization and collision/backfill handling; approve schema/API contract and migration graph; select deployment security settings and provider/worker boundary before exposing link/history/cancel endpoints. No application implementation has started.

## 13. Remaining risks and implementation status

Bearer links can be forwarded or compromised; session theft remains possible until expiry/revocation. Mitigations are scoped/minimized history, 15-minute one-use links, secure cookie, logout/replacement, rate limits, and secret redaction. Provider delivery confirmation does not prove who opened the link. No OTP or phone-number-only access is introduced.

The design does not create customer accounts or grant Customer sessions access to merchant/admin APIs. Exact technical proposals in §§3–12 require review; the fixed requirements in §2 remain approved. ORD-008 adds a digest-only, Shop-profile-scoped `CustomerSession`, dedicated cookie authentication with Django CSRF/Origin validation, and the pending Order cancellation transition with atomic reservation release. The one-use link grant/request/exchange flow, browser landing page, authenticated CSRF bootstrap/cookie issuance, history APIs, provider, and background worker remain unimplemented. The ORD-008 endpoint uses the current `customers.Customer` model as the Shop-scoped profile; remaining technical, privacy, and deployment decisions in §12 are not resolved by that implementation.

## 14. References

- `.ai/project-context/customer-order-history-implementation-plan.md` (AUTH-016)
- `.ai/project-context/business-rules.md`
- `.ai/project-context/model-relationships.md`
- `.ai/project-context/authorization-matrix.md`
- `.ai/project-context/development-status.md`
- `.ai/project-context/domains/customers.md`
- `.ai/project-context/domains/orders.md`
- `.ai/project-context/domains/shops.md`
- `.ai/project-context/domains/catalog.md`
- `.ai/project-context/domains/inventory.md`
- `.ai/project-context/domains/notifications.md`
- `backend/config/settings.py`, `backend/config/urls.py`
- `backend/users/models.py`, `backend/users/authentication.py`, `backend/users/permissions.py`
- `backend/shops/models.py`, `backend/shops/views.py`, `backend/shops/tests.py`
