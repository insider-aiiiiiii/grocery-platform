# Customer Order-History Access Design

## 1. Status and scope

This document records the finalized AUTH-015 Customer Order-history access design. It does not implement a Customer model, an Order API, a delivery provider, a URL domain, or a new Customer account. Customer access remains separate from Merchant and Super Admin JWT authentication. No OTP or Customer username/password account is introduced.

The no-OTP requirement, the rule that a WhatsApp number alone is not authorization, Customer + Shop scoping, the 15-minute one-use link, 30-day maximum session lifetime, one active session per Customer + Shop, and pending Order cancellation through that scoped session are approved. Section 8 lists only unresolved deployment and technical details. Exact routes and schema remain for later API/database design.

## 2. MVP flow

1. A customer places an order using the existing checkout concept. The server resolves or creates the Shop-specific Customer according to the approved Customer rules; it does not grant access merely because a submitted phone number matches.
2. After successful Order creation, the server creates a 15-minute, single-use history-link grant for that exact Customer and Shop. The link is delivered to the Customer's WhatsApp number using the Order-received message flow. The message must say the Order was received, not accepted, and must not contain private Order details beyond reviewed minimal notification content. Delivery is reported as successful only when the WhatsApp provider confirms it.
3. A returning customer can request a replacement link from the customer-facing Shop context by submitting the Shop's public identifier and WhatsApp number. The response is the same whether or not a matching Customer exists. If one exists, the service may deliver a link to its recorded number; it must never return the link or a Customer/Order identifier in the API response. A number-only request does not create a Customer, reveal order history, or authenticate the requester.
4. The customer opens the link. The link carries a random bearer secret in the URL fragment (after `#`), so browsers do not send it automatically in the HTTP request or `Referer` header. A minimal first-party page reads it, immediately removes it from browser history with `history.replaceState`, and submits it once in a POST body to exchange it for a restricted Customer session. A GET, preview, crawler, or link scanner must not consume a grant or perform a state change.
5. The exchange endpoint validates and atomically consumes the grant, then creates a server-side session bound to the exact Customer and Shop. The browser receives only that session credential in a Secure, HttpOnly cookie, with SameSite and cookie scope selected for the reviewed deployment. The session opens the Shop-specific Order history page. It is not a platform User login and cannot call Merchant or Super Admin APIs.
6. For repeat ordering, the history page may offer a reorder action that creates a new cart/order attempt using the same Customer + Shop context. The server re-reads current product visibility, price, availability, and fulfillment rules; it never clones an old Order as a new purchase or trusts its historical line data as current catalog data.

## 3. Token and session lifecycle

### Link grant

- Generate at least 32 cryptographically random bytes with the platform language's secure random source and encode them as URL-safe text. This gives 256 bits of entropy and makes online guessing infeasible; never derive the secret from a phone number, Shop ID, Customer ID, Order ID, timestamp, or ordinary Django/JWT identifiers.
- Store only a one-way digest of the secret, never the plaintext. A plain SHA-256 digest is suitable for a uniformly random 256-bit value; use constant-time digest comparison where application comparison is needed. Do not reuse Merchant/Super Admin JWT signing or refresh-token mechanisms.
- Bind each grant server-side to purpose=`order_history`, one Customer, one Shop, creation time, expiry, and used/revoked state. Resolve the Customer and Shop from database relationships; do not trust IDs or claims supplied by the client.
- Initial-link lifetime is 15 minutes from issuance; each grant is single use. On link reissue, invalidate earlier unused history grants for that same Customer + Shop so old unredeemed links cannot linger.
- Consume the grant transactionally (for example, lock the matching row and mark it used before issuing a session) so simultaneous requests cannot exchange the same link twice. Used, expired, revoked, malformed, and unknown grants receive indistinguishable external errors.

### Restricted Customer session

- Issue a separate random session secret; persist only its digest and the Customer, Shop, issue time, expiry, and revocation state. Check the current server-side session and its Customer/Shop relationships for every history or mutation request. Do not treat decoded client claims as the source of tenant scope.
- A Customer session has a maximum absolute lifetime of 30 days, with no silent indefinite renewal. After expiry, the customer requests a new link.
- Allow one active session per Customer + Shop. Successful redemption of a new link revokes/replaces the previous active session for that scope.
- Provide an explicit logout/revoke operation that invalidates the current session. Shop deletion revokes every outstanding grant and Customer session scoped to that Shop before or as part of deletion. A Customer retained after Shop deletion is not rebound to a replacement Shop and cannot retain a usable credential for the deleted Shop. Any future Customer deletion must also invalidate that Customer's grants and sessions; Customer retention/deletion policy remains unresolved.
- A session authorizes only the Customer's minimized history and the explicitly approved customer actions for the same Shop. It never grants Merchant/admin access or another Customer's data.

## 4. Browser and transport protections

- Put the link secret in the URL fragment rather than the path or query string; fragments are not sent in HTTP requests or referrers. Exchange it promptly through HTTPS POST and remove it from browser history before loading other resources.
- Serve a minimal first-party landing page with no third-party scripts, pixels, fonts, or analytics. Set `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, a restrictive Content Security Policy, and appropriate transport security. Redact link/session values from app, proxy, provider, tracing, error, and analytics logs. Never include secrets in exception text or support tooling.
- Set the session cookie `Secure` and `HttpOnly`, with narrow path/host scope and a SameSite policy selected for the reviewed deployment. Require CSRF protection for state-changing cookie-authenticated requests, including logout and Order cancellation. Do not store session secrets in localStorage or return them to general JavaScript if the deployment can use a same-site HttpOnly cookie.
- The repository does not define the storefront domain or frontend/API origin relationship. If a same-site cookie cannot be used, select and review an alternative transport, CORS policy, and CSRF threat model before implementation; do not silently broaden cookie or origin settings.
- Never mutate state on link GET. The customer must take an explicit action in the first-party page before grant exchange; destructive or Order-changing actions require a separate confirmation POST.

## 5. Abuse prevention and enumeration resistance

- The link-request endpoint returns the same status, response body, and broadly similar timing for existing and non-existing Customer/Shop/number combinations. Do not expose whether the number is registered, whether a Customer exists, or whether a message was sent. Do not return a token, Customer ID, or Order ID.
- Apply request throttles by source IP/network, Shop context, and a keyed digest of the normalized submitted number; also cap outbound messages per Customer/Shop and globally. Use generic throttling responses and avoid logging raw phone numbers. Exact normalization is an unresolved Customer-domain decision and must be settled before implementing the keyed throttle consistently.
- The endpoint should queue delivery only for a matching Customer and use the number already held in the Shop-specific Customer record as destination. Never let the caller substitute a different delivery destination in the link-request call.
- Avoid synchronous provider-dependent responses that reveal account existence through response time. Provider errors must not be reflected in a way that distinguishes existing and non-existing Customers.
- Rate-limit grant exchanges and invalid-session attempts by IP and grant/session fingerprint, while allowing ordinary customers to recover from mistyped or expired links. Alerting/audit records must contain event type and safe identifiers, not bearer secrets or full phone numbers.
- A bearer link is possession-based access. Delivery to WhatsApp is the approved no-OTP path, but compromise or forwarding of the WhatsApp account/link can expose the scoped Customer history until revocation/expiry. Keep the displayed data minimal and document this residual risk in customer-facing copy if the product approves it.

## 6. Proposed API boundary (not implemented)

These are resource/action shapes for review, not approved routes or response contracts:

| Operation | Proposed boundary | Authorization |
|---|---|---|
| Request/reissue history link | Public POST in the addressed Shop context; body contains WhatsApp number | Anonymous request; generic response; matching Customer resolved server-side; outbound delivery goes only to its stored number. |
| Exchange link | Public POST body contains the one-time link secret | Anonymous only for the exchange step; secret must match an unused, unexpired grant bound to one Customer + Shop. Return/set a restricted customer session only. |
| Read own Order history | Customer-scoped GET; no arbitrary Customer selector | Valid Customer session; queryset anchored to its Customer and Shop. An optional Order ID is filtered within that same scope. |
| Revoke/logout | POST | Revoke only the current session; a future revoke-all behavior depends on the approved session-count policy. |
| Cancel pending Order | POST against one Order | Valid Customer session for the Order's exact Customer + Shop; current status must be `PENDING`. Server performs the existing approved cancellation transition and inventory effects atomically. No WhatsApp command and no number-only authority. |
| Repeat order | Customer-scoped action or checkout handoff | Valid Customer session may prefill/associate only the same Customer + Shop. Revalidate current cart/catalog and create a new Order through the normal checkout path. |

Do not put bearer secrets in route paths or query parameters. Customer endpoints must not accept a client-selected `customer_id` or `shop_id` as authorization. Merchant JWT and Super Admin JWT endpoints keep their existing authentication and permission behavior and never accept a Customer link/session as credentials.

## 7. Data-model implications (conceptual only)

The Customers domain will need persisted one-time grants and restricted sessions. Conceptual records contain:

- Secret digest (unique), purpose, Customer reference, Shop reference, created/expiry/used/revoked timestamps for link grants.
- Secret digest (unique), Customer reference, Shop reference, created/expiry/last-used/revoked timestamps for Customer sessions.
- Optional safe audit metadata such as issuance/exchange/revocation event and coarse source information, subject to privacy/retention decisions.

The records are credentials, not User accounts. They must not point at or create `users.User`, Merchant membership, or Customer password fields. The Shop reference should make the tenant boundary explicit even if the Customer also references Shop; enforce that both references identify the same Shop. A grant/session for one Shop must never be re-pointed to a replacement Shop. No Order data or phone number needs to be copied into a grant/session. Exact model names, FK deletion behavior, indexes, migration, transaction/locking approach, audit retention, and whether grant/session state can share a table are database-design decisions, not settled here.

## 8. Decisions required before implementation

| Decision | Recommended starting point | Why approval is still needed |
|---|---|---|
| WhatsApp provider and delivery integration | Use the selected provider and report delivery only after provider confirmation. | Provider choice, integration, failure handling, and operational retry policy are not selected. |
| Frontend/API origin and cookie deployment | Use HTTPS, Secure/HttpOnly cookies with narrow scope and CSRF protection. | Hosting architecture, origin relationship, cookie domain/path, and final SameSite policy depend on deployment. |
| Phone normalization and throttling details | Apply IP, Shop, and normalized-number-based controls. | Phone normalization/validation and rate-limit implementation details and thresholds remain open. |
| Additional revocation and abuse controls | Enforce approved link/session expiry, one active session, replacement, and logout. | Any deployment-specific controls beyond these approved behaviors require technical review. |
| Customer retention and deletion | Revoke access grants and sessions when their Shop is deleted; preserve Customer entity behavior under existing rules. | Broader Customer retention/deletion policy and legal or operational requirements remain unresolved. |
| Exact API and data contract | Keep all routes, request/response contracts, schema, indexes, and transaction mechanics within the documented Customer + Shop boundary. | Exact API routes/contracts, database schema, and implementation details require later design. |
| Delivery failure and customer recovery | Do not claim delivery succeeded without provider confirmation; retain the generic link-request response. | Customer-facing recovery when delivery fails is not defined. |
| Other deployment-dependent controls | Preserve least privilege, no enumeration, secret redaction, and tenant isolation. | Any remaining choice that depends on hosting, provider, or operational capability requires review. |

The 15-minute link lifetime, 30-day maximum session lifetime, one-session-per-Customer-per-Shop policy, and pending cancellation authorization are finalized and must not be reopened as deployment choices. Provider/delivery, frontend/API origin, phone normalization, retention, exact API/schema, and other deployment-dependent details remain open. No design choice turns a WhatsApp number into a credential.

## 9. Required tests before release

- Grant generation uses cryptographically secure randomness, has the configured entropy, stores only digests, and never emits secrets in API responses or logs.
- Wrong-purpose, malformed, unknown, expired, revoked, and previously used grants fail with indistinguishable public behavior; WhatsApp number-only requests never return history or disclose Customer existence.
- Link GET, preview, and scanner requests do not consume grants or change Order state. Successful explicit exchange is single-use under concurrent redemption.
- Exchange creates a restricted session for exactly one Customer + Shop; it cannot authenticate Merchant/Super Admin endpoints or switch Customer/Shop by modifying request IDs, cookies, or payloads.
- History requests are tenant-scoped for list and detail, including guessed Order IDs, query filters, exports, and related objects; response fields are minimized.
- Session expiration, logout, replacement/revocation behavior, Shop deletion, and approved Customer deletion invalidate access as specified; a replacement Shop never inherits an old grant/session.
- Cookies have required flags; state-changing endpoints enforce CSRF and reject disallowed origins. Link secret does not leak through referrer, browser navigation after cleanup, cache, logs, telemetry, or third-party requests.
- Request-link responses and timing do not disclose whether a number is registered; throttles cover IP, Shop, number digest, exchange guessing, and delivery volume without logging raw credentials/phone numbers.
- Customer cancellation requires the correct scoped credential, a matching Customer + Shop Order, `PENDING` state, and explicit POST confirmation; a phone number, another Customer's session, another Shop, or WhatsApp message cannot cancel it. Verify existing rejection-state and stock-release behavior.
- Repeat ordering creates a new Order only after current catalog, price, availability, and fulfillment validation; it cannot copy a deleted/foreign Shop's history into the new Shop.

## 10. Repository implementation status

At review time, `backend/customers/models.py`, `backend/customers/views.py`, `backend/orders/models.py`, and `backend/orders/views.py` are empty Django scaffolds. `backend/config/urls.py` has no Customer or Order routes. There are no Customer profiles, Order records, access-link grants, Customer sessions, or WhatsApp delivery integration to reuse for this design. Merchant/Super Admin JWT and session code exists under `backend/users`; Customer credentials remain separate. AUTH-015 design is finalized, but feature implementation remains pending the deployment/API/database decisions documented above.
