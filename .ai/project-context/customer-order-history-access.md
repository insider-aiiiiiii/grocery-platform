# Customer Order-History Access and API Design

## 1. Status and scope

This document combines the approved AUTH-015 security rules with the AUTH-017 proposed API and persistence design. The approved behavior in §2 is fixed. The data schema and API contracts below are the recommended technical design for review; they are not implemented or finalized until the review decisions in §12 are recorded.

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

### 3.1 Customer profile proposal

There is no Customer model yet. The following is a proposal, with open deletion/address decisions kept explicit.

| Field | Proposed Django representation | Purpose / rule |
|---|---|---|
| `id` | `BigAutoField` (repository default) | Internal primary key; never an authorization input. |
| `shop` | `ForeignKey(shops.Shop, null=True, on_delete=SET_NULL)` | Active Customers are Shop-scoped. Null is reserved for a retained orphan after permanent Shop deletion; it is never reassigned to a replacement Shop. Whether retention needs a different tombstone representation is open. |
| `name` | `CharField(max_length=255)` | Current profile name; exact length should follow the approved checkout contract. |
| `created_at`, `updated_at` | `DateTimeField(auto_now_add=True)`, `DateTimeField(auto_now=True)` | Profile lifecycle timestamps. |
| address relation | Proposed `CustomerAddress` child model, not a field on Customer | Supports saved address options without overwriting prior Order delivery details; number of addresses and fields remain open. |

Require a Shop when a Customer is created for checkout. On physical Shop deletion, `SET_NULL` is the recommended way to retain an orphan Customer without retaining an active Shop relation; querysets for checkout/history/link issuance must exclude null-Shop Customers. This recommendation still needs Customer-retention approval. `PROTECT` would prevent permanent Shop deletion until every Customer were separately deleted; `CASCADE` would delete Customer rows despite the approved retention boundary. Do not implement either behavior without the retention decision.

### 3.2 Global WhatsApp uniqueness

**Approved business rule:** the canonical WhatsApp identity is globally unique across Customers, Merchants, and Super Admin mobile identities, and within Customers it identifies a returning Customer. Phone normalization is unresolved, so the platform cannot yet safely define equality for formatting variants.

Independent `UNIQUE` constraints on `Customer.whatsapp_number` and `User.mobile_number` cannot enforce cross-table uniqueness. Options are:

1. **Shared identity-claim registry (recommended for review):** one row per canonical normalized number, with a unique number key and exactly one owner reference for either platform User or Customer. All account/customer creation and number change goes through a transactionally locked claim operation. This centralizes uniqueness and provides a serialization point, but requires a staged migration of existing `User.mobile_number` values and a reviewed owner-reference design. A polymorphic owner reference has no ordinary FK; alternate FK layouts add migration/cross-domain coupling.
2. **PostgreSQL trigger across tables:** keeps current model fields but is PostgreSQL-specific, complicates SQLite development/tests and Django migration portability, and creates hidden write behavior.
3. **Application-only cross-table checks:** simplest initially but has a race between concurrent Customer/User creation and cannot guarantee the approved global uniqueness invariant.

**Recommendation:** adopt a shared `ContactIdentityClaim` registry after approving canonical phone normalization and migration/backfill rules. Proposed fields are `id: BigAutoField`, `normalized_number: CharField(max_length=16, unique=True)` (E.164-shaped candidate), `owner_type: CharField(choices=USER/CUSTOMER)`, `owner_id: PositiveBigIntegerField`, and `created_at: DateTimeField(auto_now_add=True)`. Add a unique constraint on `(owner_type, owner_id)` so a principal has at most one claim. A generic owner reference avoids cyclic app migrations but has no FK; all creation, reassignment, and deletion must run through a locked claim service and integrity reconciliation. A typed FK/registry design gives stronger referential integrity but adds cross-domain migration coupling. Preserve `User.mobile_number` during a staged compatibility migration, but make the claim row the serialized uniqueness authority. Migration must detect duplicate/canonicalization collisions before adding uniqueness; do not silently choose an owner. Add reconciliation tests. This owner representation and migration plan require review before schema implementation.

Do not add OTP or mark a number as verified merely because it is entered at checkout. The history link is a separate bearer credential delivered to the recorded destination.

### 3.3 Addresses and Order-time snapshots

Customer profile data is mutable; a prior Order must retain what was used at checkout. Recommended distinction:

- `CustomerAddress`: `id`, `customer_id`, optional user-facing `label`, address components/text, `created_at`, and `updated_at`. Each address belongs to one Customer; it is never a platform-global or cross-Shop address. One-versus-many addresses, exact fields, and address deletion behavior are unresolved.
- `Order`: keep immutable checkout-time customer name/contact and, for home delivery, address snapshot fields (or one structured snapshot representation selected by the Orders schema design). Do not render the current Customer profile as if it were the historical delivery address.

For a simpler MVP, a single current address on Customer is possible, but it overwrites the address used for prior purchases unless Orders still snapshots all required details. Recommend a separate address row plus Order-time snapshot, subject to the address/privacy decision. Customer history responses should not return full contact/address values by default; include only fields approved as necessary for the Order experience.

### 3.4 Relationships and deletion

```text
Shop 1 ── * Customer (active Customer has one Shop; retained orphan may have null Shop)
Customer 1 ── * CustomerAddress
Shop 1 ── * Order
Customer 1 ── * Order
Order 1 ── * OrderLine ── ShopProduct / Variant (with historical line snapshots)
Customer 1 ── * HistoryLinkGrant ── Shop 1
Customer 1 ── 0..1 active CustomerSession ── Shop 1
User / Customer 1 ── ContactIdentityClaim (generic owner type + id; one globally unique canonical number claim)
```

All order, grant, and session relations must agree on Shop and Customer scope. Because separate FKs do not express `customer.shop_id == order/grant/session.shop_id`, enforce the invariant in the transactional domain boundary and with database constraints/triggers only if later schema review selects them. Protected API queries always filter on both the authenticated Customer and Shop.

Recommended deletion behavior, pending review:

- `HistoryLinkGrant.shop` and `.customer`: `CASCADE` so deleted scope/customer cannot leave usable credentials. Invalidate/revoke first in the Shop deletion transaction where practical; physical row deletion is the final invalidation guarantee. Retaining credential audit rows requires a separate retention decision.
- `CustomerSession.shop` and `.customer`: same invalidation/cascade rule.
- `Order.shop`: `CASCADE` under approved permanent Shop deletion. `Order.customer`: `PROTECT` until Customer deletion policy is approved; Shop deletion removes the Orders before retaining/orphaning Customer profiles.
- `Customer.shop`: candidate nullable `SET_NULL` on Shop deletion as in §3.1. Never attach an orphan to a replacement Shop.
- `CustomerAddress.customer`: `CASCADE` if profile data is deleted; if a retained orphan profile is kept, its addresses remain only under the same retention decision. Do not imply a finalized retention period.

## 4. Credential persistence proposal

These model shapes are the recommended implementation contract for review. They create credentials, not Django User accounts. Use UTC-aware datetimes; enforce comparisons against server time.

### 4.1 `HistoryLinkGrant`

| Field | Proposed type/constraint | Meaning |
|---|---|---|
| `id` | `BigAutoField` | Internal row key. |
| `token_digest` | `CharField(max_length=64, unique=True)` | Lowercase hex SHA-256 digest of 32+ random bytes. Never persist the plaintext bearer secret. |
| `purpose` | `CharField(max_length=32, choices=...)`, non-null | Fixed purpose value `ORDER_HISTORY`; reject any other purpose at exchange. |
| `customer` | `ForeignKey(Customer, on_delete=CASCADE)` | Exact authorized Customer. |
| `shop` | `ForeignKey(Shop, on_delete=CASCADE)` | Explicit tenant binding; must match `customer.shop_id` at issuance and redemption. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Issue time. |
| `expires_at` | `DateTimeField`, non-null | Exactly 15 minutes after issuance; validate `now < expires_at`. |
| `consumed_at` | `DateTimeField(null=True, blank=True)` | Set atomically on successful exchange only. |
| `revoked_at` | `DateTimeField(null=True, blank=True)` | Set on replacement, Shop/Customer deletion, or approved revocation. |

Add a partial unique constraint on `(customer, shop, purpose)` where `consumed_at IS NULL AND revoked_at IS NULL`, plus an index for scoped grant lookup/cleanup and the unique digest index. Before issuing/reissuing, revoke any prior unconsumed grant for that Customer + Shop (including expired rows), then insert the new grant in the same transaction. Expiration is time-based; periodic cleanup may remove consumed/revoked/expired grants after an approved operational/audit grace period. No raw token is recoverable from a row.

Generate a URL-safe encoding of `secrets.token_bytes(32)` or stronger; compute SHA-256 over the decoded secret. Compare digests safely. Use a purpose-separated secret format/domain tag if desired, but do not derive secrets from identifiers or use platform JWT signing. The grant secret is present only in worker memory and the outbound delivery body/URL; never write it to DB, outbox, queue payload, logs, analytics, error text, or API response.

### 4.2 `CustomerSession`

| Field | Proposed type/constraint | Meaning |
|---|---|---|
| `id` | `BigAutoField` | Internal row key. |
| `session_digest` | `CharField(max_length=64, unique=True)` | SHA-256 digest of a separate random 32+ byte Customer session secret. |
| `customer` | `ForeignKey(Customer, on_delete=CASCADE)` | Exact Customer scope. |
| `shop` | `ForeignKey(Shop, on_delete=CASCADE)` | Exact Shop scope; must match Customer at creation and every validation. |
| `created_at` | `DateTimeField(auto_now_add=True)` | Absolute session start. |
| `expires_at` | `DateTimeField`, non-null | No later than `created_at + 30 days`; no rolling/sliding extension. |
| `revoked_at` | `DateTimeField(null=True, blank=True)` | Logout, replacement, or lifecycle revocation time. |
| `last_used_at` | Optional `DateTimeField(null=True, blank=True)` | Add only if operational need is approved; avoid unnecessary per-request writes/tracking. |

Enforce at most one unrevoked row per `(customer, shop)` with a conditional unique constraint on `revoked_at IS NULL`. An expired but not yet revoked row still occupies that key; session exchange must lock the scope, revoke the old/expired row, then create its replacement. Session validation always checks digest, revocation, `now < expires_at`, active Shop, and Customer/Shop relationship. Cleanup of expired rows follows a reviewed retention period.

### 4.3 Migration dependencies

Recommended migration order, subject to review of the global contact-claim owner representation:

1. Add `ContactIdentityClaim` to the platform identity owner (recommended `users`) after approving phone normalization; audit/backfill existing `User.mobile_number` values and stop on canonical collisions before enforcing unique claims.
2. Add `Customer` depending on `shops.Shop` and the contact-claim table; add its address relation after Customer. Customer claim references use the reviewed claim-owner representation.
3. Add Shop Product/Variant and Inventory base schema in their domains before Order lines/reservations. Preserve app ownership and avoid circular FKs.
4. Add `Order`/`OrderLine` depending on Shop, Customer, Product/Variant; add Inventory reservation rows after their referenced Order/OrderLine contract is established.
5. Add grant/session tables after Customer and Shop exist. They need no FK to Order; link delivery outbox records may depend on Order/Customer/Shop.
6. Add Notifications outbox/delivery schema after its selected event keys and Order/Customer/Shop references are defined.

Use nullable/staged fields and data migrations where needed; do not ship a schema migration that invents phone normalization, releases claims, or hard-deletes Customers. Migration dependencies must be checked with Django's migration graph to avoid cycles across apps.

### 4.4 PostgreSQL transaction and concurrency contract

Use `transaction.atomic()` and PostgreSQL row locks; uniqueness constraints are the final race guard, not a substitute for scope validation. Adopt a global lock order to avoid deadlocks: **Shop → Customer/identity claim → grant/session → Order → Inventory rows**.

- **Accept issue/reissue request:** resolve active Shop and Customer server-side; lock Shop, then Customer; verify exact scope; revoke prior unused grants and create a safe outbox event in one transaction. The outbox contains only references/reason/generation, never the token. On Order creation the Order transaction writes its notification event; link generation happens only in the delivery worker.
- **Deliver link:** worker claims the current outbox row, locks/checks scope and generation, generates token in memory, stores only its digest and sends the link to the stored Customer number. A retry after losing the in-memory secret must revoke the prior grant, generate a fresh grant, and send a new link. This can make an earlier ambiguously delivered link unusable; retry policy and message UX remain provider decisions. Stale queued events are skipped so older links are not sent after newer requests.
- **Redeem:** hash supplied token to locate candidate; in one transaction lock Shop, Customer, then grant in the stated order; re-read and validate purpose, unused/unrevoked state and expiry; set `consumed_at`; revoke any prior unrevoked session; create a new independent session digest and expiry; commit before setting the response cookie. Two simultaneous redemptions of one grant have one winner. If cookie delivery is lost after commit, the customer can request a new link; the next redemption replaces the unreachable session.
- **Link request concurrency:** serialize by Shop + Customer before invalidating/inserting a grant. If using delivery generations/outbox rows, workers must skip superseded requests so an older queued link is not delivered after a newer request.
- **Cancellation:** lock Shop, then Customer/session scope, Order, then Inventory records. Re-check ownership, Shop, current state and stock reservation while locked; update Order to `REJECTED` and release the reservation in the same transaction. On any failure, roll back both. A second request sees non-`PENDING` state and cannot release inventory again.
- **Shop deletion:** lock Shop, revoke/delete its grants and sessions, delete Orders/Products and other owned rows under the approved deletion workflow, and retain/orphan Customer profiles only as the reviewed Customer policy allows. The transaction and `CASCADE` FKs ensure no credential survives the deleted Shop; replacement Shop creation never changes old Customer references.

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

The repository has no worker or queue, while the link secret must be digest-only at rest and provider work must not disclose Customer existence by request timing. The following outbox shape is a recommendation for resolving that boundary without storing plaintext bearer secrets:

- In the Order transaction, write a delivery outbox row containing event kind, safe Order/Customer/Shop references, and deduplication key; do not include a link/token or raw phone number. Link-request acceptance similarly stores an eligible Customer/Shop reference only after server-side match, with a generic API response either way.
- A worker claims the outbox event, revalidates active scope and current generation, generates the random secret in memory, stores only its digest in `HistoryLinkGrant`, and sends the fragment link to the destination loaded from the Customer contact record.
- On transient/ambiguous provider failure, the worker cannot retrieve the old plaintext secret. A retry must revoke the prior grant, generate a fresh secret/grant, and send a new link; the older possibly delivered link becomes invalid. Bound retries and explain UX. This avoids a recoverable plaintext token in database/broker/outbox storage but can create multiple messages.
- Provider confirmation updates delivery state only after authenticated callback/response and uses an idempotency key for the originating event where supported. Duplicate callbacks cannot create new Orders, grants, or repeated cancellation effects.
- Options include a durable queue, a database outbox plus polling worker, or synchronous provider call. Recommend a database outbox and simple worker contract within the modular monolith until volume justifies a separately approved queue. Provider, worker deployment, retries, and callback authenticity remain open.

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

## 12. Decision register (recommendations unapproved)

| Decision | Options/trade-offs and security impact | Recommended default for review | Dependencies |
|---|---|---|---|
| Global contact uniqueness and phone normalization | Per-table constraints fail cross-table. PostgreSQL trigger is strong but DB-specific. Shared registry adds migrations and owner-reference complexity. E.164 needs country/format policy. | Shared contact-claim registry with one unique normalized value and a serialized claim operation; approve E.164/canonicalization policy and backfill strategy first. | Target countries, data migration, User login compatibility, owner FK/polymorphic design. |
| Customer retention after Shop deletion | `PROTECT` blocks Shop deletion; `CASCADE` deletes Customer contrary to retention boundary; `SET_NULL` keeps an unusable orphan but retains PII; tombstone Shop retains more metadata. | `SET_NULL` Customer.shop and mark/derive orphan state; delete grants/sessions/Orders/Products, never reattach. Retention/anonymization duration still needs legal/product approval. | Existing Customer rules, global contact claim release policy, Shop deletion transaction. |
| Global phone claim after Shop deletion | Keeping a retained Customer's globally unique claim blocks that number from use by any Customer at a replacement Shop. Releasing it permits a fresh profile but requires removing/anonymizing the old profile's contact identity. Reassigning the old claim risks effectively transferring identity/history. | Do not reassign or transfer the old Customer/claim automatically. Product/privacy review must explicitly choose whether to retain the claim (number remains unavailable) or release it while retaining a deidentified orphan. | Global identity uniqueness, replacement-Shop customer experience, retention/legal decision. |
| Customer address and Order snapshot | One current address is simple but overwrites; multiple saved addresses improve experience but increase personal data. Order snapshots preserve transaction meaning but duplicate PII. | Separate CustomerAddress rows plus immutable Order-time snapshot; start with only address fields needed for checkout. Approve single/multiple and retention. | Checkout requirements, Orders history fields, privacy/legal policy. |
| Credential deletion/audit | Cascade delete guarantees no stale credential; retaining revoked rows helps audit but keeps linkable personal data. | Cascade-delete credential rows on Shop/Customer deletion; retain only safe audit events under separate approved retention. Revoke in transaction before cascade. | Audit obligations, database deletion order. |
| PostgreSQL vs SQLite concurrency | SQLite supports ordinary model/API tests but not PostgreSQL row-lock proof. Partial unique support can differ by version. | PostgreSQL is the release concurrency authority; retain SQLite for fast unit tests and run required race tests on PostgreSQL CI. | CI/database availability, PostgreSQL version. |
| API error contract/public reference | IDs simplify routes but can be enumerable; verbose failures leak token/account state. | Use generic invalid-link error, 404 for foreign Order, UUID public Order reference, and minimal detail/status payload. Keep stable `detail`/`code` shape consistent with auth APIs. | Existing global API conventions, Order identifier schema. |
| Cookie/origin/CSRF | Same-site API/browser supports HttpOnly cookie; cross-site needs reviewed CORS credentials and SameSite=None/Secure, increasing exposure. | Prefer same-site HTTPS; cookie is Secure/HttpOnly and host-only where possible; CSRF cookie/header plus Origin/Referer validation. Do not set SameSite/Domain/Path/CORS until deployment hosts are known. | Frontend/API hosts, proxy TLS, allowed origin list, browser support. |
| Rate limit thresholds and storage | In-memory/local cache is not consistent across processes; DB rows add write load; shared cache adds infrastructure. Strict thresholds can block shared networks. | Layer IP/Shop/HMAC-number/grant/session/outbound limits; choose shared storage with deployment. Use HMAC fingerprints and rotate pepper safely; never log raw phone/token. | Trusted proxy config, expected traffic, cache/DB/queue operations. |
| WhatsApp provider, outbox and retry | Synchronous delivery leaks timing and blocks; queue can retain secrets if task payload includes token; provider callbacks vary. | DB outbox contains references only; worker generates secret in memory, persists only digest, sends via selected provider, and rotates grant for retries after loss of plaintext. | Provider confirmation/idempotency, worker deployment, retry bounds, customer failure copy. |
| Background worker | No worker/queue currently exists. Polling DB is simple but adds a worker process; a broker adds another service. | Begin with a DB-backed outbox plus a separately deployed management-command worker; evaluate a broker only with measured need and approval. | Hosting process model, polling/locking, operations/monitoring. |
| Idempotency for reissue/cancel | Grant is single-use; repeat reissue intentionally rotates links. Cancellation state check prevents duplicate stock effects but retry response may be 409. | No key initially for link requests; clients avoid automatic retry. Add persisted idempotency keys only if UX requires replay semantics. For cancellation, use Order state as effect guard; add idempotency record only if exact success replay is required. | Client retry behavior, API conventions, idempotency record retention. |

## 13. Remaining risks and implementation status

Bearer links can be forwarded or compromised; session theft remains possible until expiry/revocation. Mitigations are scoped/minimized history, 15-minute one-use links, secure cookie, logout/replacement, rate limits, and secret redaction. Provider delivery confirmation does not prove who opened the link. No OTP or phone-number-only access is introduced.

The design does not create customer accounts or grant Customer sessions access to merchant/admin APIs. Exact technical proposals in §§3–12 require review; the fixed requirements in §2 remain approved. **Application implementation has not started:** no Customer/Order model, migration, endpoint, frontend, cookie authenticator, provider, or background worker exists in the repository.

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
