# Customer Order-History Access Implementation Plan

## 1. Purpose, scope, and decision status

This AUTH-016 document plans implementation of the finalized customer access-link design. It does not implement application behavior or settle deployment-dependent choices. No Customer/Order models, migrations, endpoints, providers, or tests are added by this planning task.

Three labels distinguish what follows:

- **Repository fact:** AUTH-017 documentation is merged to `main`; the implementation audit remains as recorded in §2 and `development-status.md`.
- **Approved requirement:** binding behavior from the AUTH-016 task and finalized AUTH-015 design.
- **Recommendation:** proposed technical direction that still needs review where it affects an unresolved API, schema, deployment, provider, or retention choice.

AUTH-015 PR #39 and AUTH-017 PR #42 have merged. AUTH-017 reconciled the AUTH-015 copy and canonical docs. AUTH-018's detailed recommendations and approval gates are maintained in the authoritative decision register `.ai/project-context/customer-order-history-access.md` §12; this plan is only the sequencing overview. AUTH-016's fixed decisions below match approved AUTH-015 behavior and are not reopened by recommendations.

### Approved requirements this plan preserves

- No OTP and no traditional Customer username/password account.
- A WhatsApp number alone never authorizes access to Order history or Customer details.
- Access is bound server-side to exactly one Customer and Shop and stays separate from Merchant/Super Admin JWT authentication.
- A link uses a cryptographically random secret of at least 256 bits, is single-use, and expires 15 minutes after issuance. Store only a digest; bind it to purpose, Customer, Shop, timestamps, and used/revoked state. Reissue invalidates prior unused grants in that Customer + Shop scope. Redemption must be atomic.
- A Customer session has a 30-day maximum absolute lifetime. At most one session is active per Customer + Shop; a new successful redemption replaces the prior session. Logout revokes the current session.
- Customer cancellation is allowed only for that Customer’s own `PENDING` Order in the scoped Shop session, with explicit confirmation and CSRF protection. It uses the existing `REJECTED` outcome and releases reserved inventory as required.
- Shop deletion invalidates grants and sessions for that Shop. Neither credentials nor Customer/Order data transfer to a replacement Shop; Customer profile retention follows its existing rules.
- The post-checkout message is an Order-received acknowledgement, not acceptance. Delivery may be reported successful only after provider confirmation.

## 2. Current implementation audit

| Area | Verified repository fact | Gap relevant to AUTH-016 |
|---|---|---|
| Customer identity | `backend/customers/models.py`, `views.py`, `tests.py`, and `migrations/` contain only generated scaffolds/empty migration package. | No Customer profile, address, or customer-session model or API exists. |
| Orders | `backend/orders/models.py`, `views.py`, `tests.py`, and `migrations/` are scaffolds/empty migration package. | No Order, line-item, status, history, or cancellation implementation exists. Existing `REJECTED` rules are documentation only. |
| Cart and checkout | `backend/cart` contains scaffold models, views, tests, and no migrations beyond package init. | No cart, checkout, or successful Order-creation flow exists to trigger access-link issuance. |
| Catalog and products | `catalog` contains a `MasterCategory` model/migrations; no Shop Product or Variant model/API was found. | Order line references, price snapshots, visibility, and stockable variants need prerequisite design and models. |
| Inventory | `backend/inventory` has scaffold model/view/test files and no domain migrations. | No stock, reservation, deduction, release, or restoration implementation exists for cancellation to invoke. |
| Shop ownership/deletion | `Shop.merchant` is a one-to-one FK with `CASCADE`; deleting a Shop row preserves the Merchant/User. Shop create/retrieve/update routes exist, but no Shop deletion route/workflow exists. `backend/shops/tests.py` covers preserving credentials and creating a replacement Shop with a new ID/public slug. | No approved Super Admin deletion API or safeguards are implemented. There are currently no Customer, Order, Shop Product, grant, or session relationships for deletion to clean up. The future workflow must invalidate scoped credentials and delete the old Shop-owned records without rebinding Customers to the replacement. |
| WhatsApp/Notifications | `backend/notifications` has only scaffold files and no models, routes, migrations, or provider integration. Existing recovery sender settings are callback adapters for auth recovery only. | No Order-received message, link delivery, generic reissue, provider callback/confirmation, retry, or failure-recovery flow exists. |
| Authentication and authorization | Platform JWT authentication accepts Merchant/Super Admin users, validates their live auth session and account state, and enforces temporary-password restrictions. Existing Shop APIs derive Merchant/Shop context server-side. | No Customer credential/session authentication exists. Do not reuse or broaden platform JWTs. Customer cookie/CSRF/origin design is not configured. |
| Middleware and cookies | Django `CsrfViewMiddleware` is installed. REST framework defaults to `PlatformJWTAuthentication` and `IsAuthenticated`; no Customer cookie authentication, Customer-specific CSRF handling, CORS configuration, or session-cookie policy was found. | Deployment must select the storefront/API relationship, cookie scope/SameSite policy, and CSRF/origin checks before endpoint implementation. Middleware presence alone does not protect a new cookie-authenticated DRF API contract. |
| Database and migrations | PostgreSQL is used when configured; settings otherwise use SQLite. Migrations exist for `users`, `shops`, and `catalog`; other domain apps have no domain migrations. | Schema design is needed for Customers, products/variants, inventory, cart, Orders, access grants, and Customer sessions. SQLite cannot establish production PostgreSQL row-lock/concurrency behavior. |
| Tests | Django `TestCase` modules exist in `users`, `shops`, and scaffold modules; substantive existing coverage is mainly auth and Shop. No Customer/Order flow tests exist. | Add domain/API/security tests by phase; use PostgreSQL-backed transaction/concurrency tests for row-lock semantics. Existing local Django-version/migration compatibility limitations are recorded in `development-status.md`. |
| Background work | No Celery, task queue, worker, scheduler, or other background-task framework/configuration was found. Auth recovery callbacks are expected to enqueue externally but do not constitute a repository queue integration. | Provider delivery must not block enumeration-sensitive link-request responses. Queue/provider choice and delivery retries need explicit approval before building integration. |

The current URL configuration routes auth and Shop APIs only; it contains no Customer, Order, Cart, Inventory, or Notification endpoints. Shop create/retrieve/update are the only relevant resource APIs presently available.

## 3. Proposed architecture and data flow

### 3.1 Boundaries

- `customers` owns the Customer identity, one-time history grants, and restricted Customer sessions. Customer credentials are not `users.User` records.
- `orders` owns Order state, customer-visible history, and cancellation authorization/state transition. It coordinates stock changes with `inventory` inside a transaction once that domain contract exists.
- `inventory` owns stock availability and reservation/release/restoration behavior. `orders` must not edit inventory fields directly.
- `notifications` owns message preparation/delivery. Orders emits an Order-received event after successful Order creation; Notifications obtains the destination from the stored Shop-specific Customer, never a caller-supplied alternate number.
- Shop deletion remains a Shop lifecycle operation with the already approved authority/safeguards. Its transaction or deletion coordinator invalidates all Shop-scoped grants/sessions before or as part of deleting the Shop-owned data.
- Views authenticate/authorize and serialize; transactional workflows belong in the smallest domain-level module/service that is justified by the cross-row rules. Avoid a generic repository or distributed system.

### 3.2 Proposed customer flow

1. Checkout creates or resolves the approved ShopCustomerProfile/contact identity within the active Shop, then creates an Order using current Shop catalog and inventory rules. The submitted number is contact/recognition data, never history authorization; AUTH-018's cross-Shop identity link remains pending approval.
2. On successful Order creation, generate a 32-byte-or-stronger CSPRNG link secret and store only its digest in a grant bound to that Customer, Shop, and `order_history` purpose. Revoke previous unused grants in the same scope in the same transaction.
3. Notifications prepares an Order-received acknowledgement with the one-use URL fragment secret and sends it only to the number held on the resolved Customer. Do not claim delivery until the provider confirms it; provider failure does not roll back the Order.
4. A returning visitor may POST the addressed Shop public slug and WhatsApp number to request a replacement link. Return a generic response with the same status/body for matches and non-matches. Resolve the destination from the Customer row and never echo a grant, Customer ID, or Order ID.
5. A first-party landing page reads the secret from the URL fragment, immediately removes it from browser history, then sends it in one explicit HTTPS POST. GET, preview, crawler, and link-scanner visits do not consume the grant.
6. The exchange transaction locks/claims an unused, unexpired grant, marks it consumed, revokes the prior active session for that exact Customer + Shop, and issues a new independent random session secret. Store only its digest. Set the session in a reviewed Secure, HttpOnly cookie; return no bearer secret to general page scripts if the deployment supports this arrangement.
7. History and cancellation derive Customer + Shop only from the validated server-side session. History querysets start from that Customer and Shop. Order detail lookup is constrained by the same scope; never accept `customer_id`/`shop_id` as authorization.
8. Cancellation requires a scoped session, explicit confirmation, CSRF/origin validation, and a fresh check that the Order belongs to the session Customer and Shop and remains `PENDING`. In one transaction, move it to `REJECTED` and release reserved inventory through the Inventory-owned operation. Duplicate or concurrent cancellation cannot release stock twice.
9. Logout revokes the current session. Shop deletion invalidates all grants and sessions for the old Shop. A replacement Shop receives a new identity; no Customer or credential is rebound to it.

### 3.3 Proposed model relationships (conceptual; schema not approved)

```text
Shop 1 ── * Customer
Shop 1 ── * Order
Customer 1 ── * Order
Order 1 ── * OrderLine ──> ShopProduct / Variant (historical snapshots retained)
Customer 1 ── * HistoryLinkGrant ── * Shop (grant also explicitly stores one Shop)
Customer 1 ── * CustomerSession ── * Shop (session also explicitly stores one Shop)
Shop 1 ── * ShopProduct ── * Variant ── Inventory state
```

The grant and session each need a unique secret digest, creation/expiry timestamps, and used/revoked state; the grant also has a purpose. The session has a last-used timestamp only if approved as necessary. Both records bind exactly one Customer and Shop. Enforce `customer.shop_id == credential.shop_id` at the trusted domain boundary; ordinary independent foreign keys cannot guarantee that cross-row equality by themselves. Shop deletion may cascade-delete credential rows after invalidating them; the physical behavior and audit retention choice need schema review. Customer deletion/retention has no approved lifecycle beyond existing domain rules.

**Recommendation for review:** Store a cryptographic digest of 32 random bytes using SHA-256; a password hash is unnecessary for uniformly random high-entropy secrets. Use separate secrets for grants and sessions. Add indexes for unique digest lookup and scoped Customer/Shop/revocation/expiry queries. For the one-active-session rule, serialize replacement in a transaction and consider a conditional unique constraint for non-revoked rows plus retiring expired rows before insertion. Confirm backend support and migration behavior on both PostgreSQL and the repository's SQLite test setup before choosing that constraint. Never rely on application filtering alone for digest uniqueness.

## 4. Proposed API boundary (routes and contracts require approval)

All routes below are proposals, not existing endpoints. Use API v1 conventions. The resolved Shop for a Customer credential always comes from server-side Shop/Customer relationships.

| Proposed operation | Candidate contract | Required behavior |
|---|---|---|
| Request/reissue link | `POST /api/v1/public/shops/{public_slug}/customer-history-links/`; body `{ "whatsapp_number": "…" }`; generic `202` response such as `{ "detail": "If eligible, a link will be sent." }`. | No identity existence disclosure through status/body, IDs, link, delivery result, or meaningful timing difference. Never accept a delivery destination override. Rate-limit by IP, Shop, keyed normalized-number digest, and outbound volume. |
| Exchange link | `POST /api/v1/customer-sessions/exchange/`; body `{ "token": "…" }`. | HTTPS; atomic one-time consume; identical public failure for malformed/unknown/expired/revoked/used/wrong-purpose grant. Success sets restricted session cookie and returns only a generic success/context response, not the reusable session secret. |
| Read history | `GET /api/v1/customer/orders/`; optional detail `GET /api/v1/customer/orders/{public_order_reference}/`. | Customer session required; no caller-selected Shop/Customer. Queryset always filters on both session Customer and Shop. Minimize fields and avoid enumerable sequential identifiers where the later Order design supports a safe public reference. |
| Cancel pending Order | `POST /api/v1/customer/orders/{order_reference}/cancel/`; candidate body `{ "confirmed": true }`. | CSRF/origin validation. Require confirmation, session scope, current ownership/Shop/status checks, and atomic transition plus Inventory release. No WhatsApp command. |
| Logout | `POST /api/v1/customer-sessions/logout/`. | Revoke only the current session, clear its cookie, require CSRF/origin validation for cookie authentication. |

Use a fragment for the link secret; do not put bearer secrets in a path or query string. Apply `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, restrictive CSP, HTTPS, and secret redaction to the landing/exchange flow. Exact response envelopes, public Order references, frontend routes, CORS, cookie domain/path/SameSite, CSRF token delivery, and error conventions must be reviewed against the chosen deployment before implementation.

## 5. Ordered implementation tasks

The domains are currently empty, so the original task sequence must be extended with product-data prerequisites before history access or cancellation can be implemented. Land AUTH-015 first; then review and approve the technical decisions in T1. Avoid building grants around temporary or assumed Customer/Order keys.

| ID / phase | Work and dependencies | Acceptance criteria |
|---|---|---|
| T0 — Source alignment | AUTH-015 PR #39 and AUTH-017 PR #42 are merged; AUTH-018 updates the recommendation register and cross-domain summaries. | Canonical docs consistently state fixed AUTH-015 rules; older “number alone grants history” and “access design unresolved” statements are removed; AUTH-018 product/privacy and deployment/API/schema choices remain visibly unapproved. |
| T1 — AUTH-018 decisions and approvals | Depends on T0 and the AUTH-018 review package. Resolve Product Owner/Privacy decisions, technical schema/API approval, and deployment/provider decisions listed in `.ai/project-context/customer-order-history-access.md` §12. Record durable approved architecture decisions in an ADR where warranted. | Each blocking decision has an owner, recorded disposition, and dependencies; no recommendation is treated as approved by this plan. |
| T2 — Domain foundations | Depends on T1 and existing SHOP/Catalog/Inventory specifications. Design and migrate the approved CustomerIdentity/ShopCustomerProfile/contact-claim representation, Shop Product/Variant, cart/checkout, Order/OrderLine, and inventory reservation records in owning apps. Preserve profile-rooted Shop scope and immutable order-time product/price/customer/address snapshots. | Migrations create the reviewed relationships/constraints; checkout resolves only an active profile in the current Shop and creates an Order with reserved stock; no Customer/Order can cross Shop scope. |
| T3 — Customer grants and sessions | Depends on T2 and approved token schema. Implement secure random secret issuance, digest-only persistence, 15-minute expiry, reissue invalidation, purpose/scope binding, atomic redemption, 30-day absolute sessions, one active session per Customer + Shop, replacement, and logout. | Plaintext secrets are not stored/logged/returned except the one-time link delivery/explicit exchange input; expiry/replay/concurrent redemption rules pass tests; session identity comes only from stored digest and relationships; it cannot authenticate platform APIs. |
| T4 — Link request and exchange API/browser boundary | Depends on T1, T3, and storefront/origin design. Add generic request and exchange endpoints plus the minimal fragment-cleanup landing behavior. | Matching and nonmatching Customer responses do not enumerate; delivery uses the stored Customer number; GET/scanner does not consume a grant; cookie flags, CSRF/origin controls, cache/referrer/CSP, and log redaction pass review. |
| T5 — Customer Order history | Depends on T2–T4. Add list/detail API using a session-rooted queryset and reviewed minimized response serializer. | A Customer can read only their Orders in the linked Shop; guessed foreign IDs, filters, query parameters, nested relations, or another Shop cannot expose records. Unauthenticated/invalid Customer session is denied without platform JWT fallback. |
| T6 — Pending cancellation and Inventory coordination | Depends on T2 and T5 plus Inventory reservation/release behavior. Add explicit confirmation action with session, Customer, Shop, status, CSRF, and concurrency checks; coordinate Order `REJECTED` transition with inventory release atomically. | Only the scoped Customer can cancel their own `PENDING` Order. Rejected/non-owned/cross-Shop/already transitioned Orders do not change; retries/races release stock once; notification events do not mutate state. |
| T7 — WhatsApp delivery and reissue | Depends on approved provider/task design (T1), successful Order flow (T2), and grant issuance (T3). Integrate Order-received link delivery and generic reissue. | Destination is the Customer's stored number; message says received, not accepted; provider confirmation gates delivery-success reporting; provider failure/retry/recovery cannot reveal Customer existence or roll back Order creation. |
| T8 — Shop deletion integration | Depends on T2–T4 and approved Shop deletion workflow. In one authorized transaction, remove Shop-scoped grants/sessions, Orders, Products, and addresses, anonymize retained Customer profiles and set their Shop relation to null, and apply the approved identity-claim release policy while Merchant credentials survive. | Deleted Shop grants/sessions cannot be used; retained profiles are non-identifying and cannot be used for checkout/history; no profile or identity is rebound to replacement Shop; old Orders/Products are absent; deletion authority/safeguards remain unchanged. |
| T9 — Release security validation | Depends on T3–T8. Complete unit, API, PostgreSQL transaction/concurrency, authorization, privacy, and deployment integration checks. | All tests in §7 pass on supported database/deployment configuration; outstanding security findings are resolved; documentation/status reflects only verified behavior. |

### Dependency rationale

T2 comes before grants because tokens need stable Customer and Shop identities, while histories/cancellation need actual Orders and Inventory behavior. T3 precedes endpoint integration so APIs cannot create unsafe provisional credentials. T4 provides the browser/cookie boundary before history and cancellation become available. Cancellation follows Inventory foundations so release is performed by the owning domain and can be atomic with the Order transition. WhatsApp delivery follows the approved provider/background-work decision and actual successful Order creation; otherwise the plan would couple Orders to an unselected integration. Shop deletion integration waits for grant/session rows and the separately approved deletion workflow. T9 spans all phases and must include a PostgreSQL concurrency environment.

## 6. Decision authority

AUTH-018 consolidates all open options, recommendations, approval owners, dependencies, and implementation blockers in `.ai/project-context/customer-order-history-access.md` §12. Do not use the superseded AUTH-016 default suggestions as approval. The implementation sequence below remains conditional on those recorded decisions and preserves the fixed requirements in §1.

## 7. Security and failure scenarios

- **Guessing/replay:** random 256-bit-or-greater secret, digest-only storage, generic errors, rate limits, atomic single-use redemption. Concurrent redemption yields one winner.
- **Enumeration:** link request has the same response for existing/non-existing Customers and does not return delivery state; timing work is queued. Never send to a caller-provided alternate number.
- **Cross-tenant access:** derive Customer and Shop from session row and verify their relationship on each request. Scope list, detail, cancellation, and any export by both. A public Shop slug only identifies the public request context; it grants no private data access.
- **Credential confusion:** Customer session cookie must not be accepted by Merchant/Super Admin JWT endpoints, and platform JWTs do not become Customer sessions. Logout affects only the current Customer session.
- **Browser leakage:** fragment secret is cleaned before navigation/resources; no secret in query/path/referrer, browser storage, third-party assets, caches, logs, tracing, analytics, or exception messages. Require HTTPS, restrictive CSP, no-referrer and no-store.
- **CSRF/origin abuse:** cookie-authenticated cancellation and logout require CSRF validation and approved Origin/Referer policy. CORS alone is not CSRF protection.
- **Stale or deleted scope:** expire links at 15 minutes, sessions by 30-day absolute deadline, reject revoked/used credentials, revoke on Shop deletion, and never associate old Customer rows or tokens with a replacement Shop.
- **Order-state race:** cancellation re-reads ownership, Shop, and `PENDING` state under transaction/locking; a concurrent merchant transition wins only once. Inventory release and status update commit or roll back together.
- **Provider failure/duplication:** provider timeout does not undo Order creation or expose Customer existence. Retries use approved idempotency and bounded policy; only confirmed provider status is represented as delivered.
- **Retention and observability:** do not record bearer values or raw WhatsApp numbers in security logs. Keep audit events to safe IDs/fingerprints and approved retention; avoid order details in notification content.

## 8. Test and security validation plan

Use the repository’s existing Django test structure unless an approved test-design change is needed. Add tests with each implementation phase; this planning task adds/runs none.

### Unit/domain tests

- Generate at least 32 CSPRNG bytes; verify only digests are persisted and secrets are absent from repr/log/error/response surfaces.
- Grant scope, purpose, 15-minute expiry boundary, used/revoked state, reissue invalidation, session absolute 30-day expiry, one-active replacement, logout, and Shop-deletion invalidation.
- Order cancellation transition is only `PENDING` to existing `REJECTED`; stock release occurs once, atomically, and only for the appropriate reservation state.
- Provider event mapping does not mark an Order accepted and only reports delivery after confirmation.

### API/authentication/authorization tests

- Generic link-request status/body for existing and absent Customer numbers; no Customer/Order IDs, token, alternate destination, or delivery result in the response.
- Anonymous request-link and token exchange are deliberately public; invalid Customer session is denied on history/logout/cancel; Merchant/Super Admin JWT does not grant Customer history, and Customer cookie does not grant platform APIs.
- Valid exchange sets the expected cookie attributes and returns no session bearer value. Exercise CSRF checks with CSRF enforcement enabled; reject missing/invalid token and disallowed Origin on logout/cancel.
- History list/detail cannot access another Customer or Shop by guessed public reference, query parameter, filter, nested relation, or submitted `customer_id`/`shop_id`.
- Cancellation requires explicit confirmation, correct Customer + Shop session, owned Order, and current `PENDING`; wrong actor/scope/state returns non-disclosing behavior and leaves inventory unchanged.
- Shop deletion invalidates grants/sessions and clears Shop-owned Orders/Products under the approved lifecycle; replacement Shop has a distinct identity and no historical records or credentials.

### Transaction, concurrency, and privacy tests

- Use PostgreSQL-backed `TransactionTestCase`/independent connections for two simultaneous grant redemptions, link reissue races, session replacement, concurrent Order cancellation/acceptance, and single stock release. SQLite tests alone do not verify row-lock behavior.
- Verify request throttles by IP/network, Shop, keyed normalized-number fingerprint, exchange fingerprint, session fingerprint, and outbound volume, including key rotation/retention as designed. Confirm raw numbers/secrets are not stored in throttle/audit data.
- Test provider unavailable, timeout, duplicate callback, retry, malformed callback, and failure after Order commit without account-existence disclosure or duplicate business effects.
- Test cache headers, referrer policy, CSP, fragment cleanup/no GET mutation, log redaction, and absence of third-party resource requests on the exchange landing flow in an approved frontend/browser test environment.
- Verify no-OTP behavior and no Customer username/password fields or auth-user rows are introduced.

## 9. First implementation task and status

**AUTH-018 is the current design-review task.** It records recommended identity/retention/scope/browser/outbox decisions and marks unresolved product, privacy, technical, provider, and deployment approvals. No Customer, Order, credential, or API implementation should start until the blocking approvals in `.ai/project-context/customer-order-history-access.md` §12 are recorded. Customer, Order, and Inventory models remain absent.

**Implementation has not started.** AUTH-016 is planning/documentation work only. No models, migrations, APIs, runtime behavior, or tests were changed or added for this plan. The Customer history feature remains unimplemented until prerequisite decisions and ordered tasks above are reviewed and approved.

## 10. References

- `AGENTS.md`
- `.ai/project-context/architecture.md`
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
- `.ai/project-context/customer-order-history-access.md` (AUTH-015 fixed behavior and the authoritative AUTH-017/018 technical decision register)
