# Customer Order-History Access Design Proposal

## 1. Status and scope

This is the AUTH-015 security design proposal for the already-approved customer-specific access link. It does not implement or finalize a Customer model, an Order API, a delivery provider, a URL domain, or a new Customer account. Customer access remains separate from Merchant and Super Admin JWT authentication. No OTP or Customer username/password account is introduced.

The no-OTP requirement, the rule that a WhatsApp number alone is not authorization, and Customer + Shop scoping are approved. The concrete flow and values below are recommendations for review; where product or deployment behavior is not decided, it is called out in Section 8. Do not implement them as approved behavior until reviewed.

## 2. Recommended MVP flow

1. A customer places an order using the existing checkout concept. The server resolves or creates the Shop-specific Customer according to the approved Customer rules; it does not grant access merely because a submitted phone number matches.
2. After successful Order creation, the server creates a short-lived, single-use history-link grant for that exact Customer and Shop. The link is delivered to the Customer's WhatsApp number using the Order-received message flow. Delivery must not contain private Order details beyond the reviewed minimal notification content.
3. A returning customer can request a replacement link from the customer-facing Shop context by submitting the Shop's public identifier and WhatsApp number. The response is the same whether or not a matching Customer exists. If one exists, the service may deliver a link to its recorded number; it must never return the link or a Customer/Order identifier in the API response. A number-only request does not create a Customer, reveal order history, or authenticate the requester.
4. The customer opens the link. The link carries a random bearer secret in the URL fragment (after `#`), so browsers do not send it automatically in the HTTP request or `Referer` header. A minimal first-party page reads it, immediately removes it from browser history with `history.replaceState`, and submits it once in a POST body to exchange it for a restricted Customer session. A GET, preview, crawler, or link scanner must not consume a grant or perform a state change.
5. The exchange endpoint validates and atomically consumes the grant, then creates a server-side session bound to the exact Customer and Shop. The browser receives only that session credential in a Secure, HttpOnly cookie under the approved same-site deployment arrangement. The session opens the Shop-specific Order history page. It is not a platform User login and cannot call Merchant or Super Admin APIs.
6. For repeat ordering, the history page may offer a reorder action that creates a new cart/order attempt using the same Customer + Shop context. The server re-reads current product visibility, price, availability, and fulfillment rules; it never clones an old Order as a new purchase or trusts its historical line data as current catalog data.

## 3. Token and session lifecycle

### Link grant

- Generate at least 32 cryptographically random bytes with the platform language's secure random source and encode them as URL-safe text. This gives 256 bits of entropy and makes online guessing infeasible; never derive the secret from a phone number, Shop ID, Customer ID, Order ID, timestamp, or ordinary Django/JWT identifiers.
- Store only a one-way digest of the secret, never the plaintext. A plain SHA-256 digest is suitable for a uniformly random 256-bit value; use constant-time digest comparison where application comparison is needed. Do not reuse Merchant/Super Admin JWT signing or refresh-token mechanisms.
- Bind each grant server-side to purpose=`order_history`, one Customer, one Shop, creation time, expiry, and used/revoked state. Resolve the Customer and Shop from database relationships; do not trust IDs or claims supplied by the client.
- Recommended initial-link lifetime: 15 minutes, single use. The exact lifetime is a proposal for approval. On link reissue, invalidate earlier unused history grants for that same Customer + Shop so old unredeemed links cannot linger.
- Consume the grant transactionally (for example, lock the matching row and mark it used before issuing a session) so simultaneous requests cannot exchange the same link twice. Used, expired, revoked, malformed, and unknown grants receive indistinguishable external errors.

### Restricted Customer session

- Issue a separate random session secret; persist only its digest and the Customer, Shop, issue time, expiry, and revocation state. Check the current server-side session and its Customer/Shop relationships for every history or mutation request. Do not treat decoded client claims as the source of tenant scope.
- Recommended session lifetime: 30 days absolute, with no silent indefinite renewal. After expiry, the customer requests a new link. These durations are proposals, not finalized product policy.
- Recommend one active session per Customer + Shop in MVP: successful exchange replaces the prior session. This gives a simple lost-device recovery path but constrains multiple-device use; product approval is required. If multiple sessions are preferred, provide a way to revoke all sessions before release.
- Provide an explicit logout/revoke operation that invalidates the current session. Shop deletion invalidates every grant and session scoped to that Shop before or as part of deletion. Customer deletion, if later approved, must invalidate that Customer's grants and sessions. A retained Customer row after Shop deletion must never be rebound to a replacement Shop or keep a usable credential for the old context.
- A session authorizes only the Customer's minimized history and the explicitly approved customer actions for the same Shop. It never grants Merchant/admin access or another Customer's data.

## 4. Browser and transport protections

- Put the link secret in the URL fragment rather than the path or query string; fragments are not sent in HTTP requests or referrers. Exchange it promptly through HTTPS POST and remove it from browser history before loading other resources.
- Serve a minimal first-party landing page with no third-party scripts, pixels, fonts, or analytics. Set `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, a restrictive Content Security Policy, and appropriate transport security. Redact link/session values from app, proxy, provider, tracing, error, and analytics logs. Never include secrets in exception text or support tooling.
- Set the session cookie `Secure`, `HttpOnly`, `SameSite=Lax` (or stricter where compatible), and narrow its path/host scope. Require CSRF protection for state-changing cookie-authenticated requests, including Order cancellation. Do not store session secrets in localStorage or return them to general JavaScript if the deployment can use a same-site HttpOnly cookie.
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

The Customers domain will need persisted one-time grants and restricted sessions if this proposal is approved. Conceptual records contain:

- Secret digest (unique), purpose, Customer reference, Shop reference, created/expiry/used/revoked timestamps for link grants.
- Secret digest (unique), Customer reference, Shop reference, created/expiry/last-used/revoked timestamps for Customer sessions.
- Optional safe audit metadata such as issuance/exchange/revocation event and coarse source information, subject to privacy/retention decisions.

The records are credentials, not User accounts. They must not point at or create `users.User`, Merchant membership, or Customer password fields. The Shop reference should make the tenant boundary explicit even if the Customer also references Shop; enforce that both references identify the same Shop. A grant/session for one Shop must never be re-pointed to a replacement Shop. No Order data or phone number needs to be copied into a grant/session. Exact model names, FK deletion behavior, indexes, migration, transaction/locking approach, audit retention, and whether grant/session state can share a table are database-design decisions, not settled here.

## 8. Decisions required before implementation

| Decision | Recommended starting point | Why approval is still needed |
|---|---|---|
| Delivery point and message content | Send a one-time history link after successful Order creation in the Order-received WhatsApp message; allow generic link reissue from the relevant Shop context. | The link's exact delivery timing/content and behavior when the provider fails are not specified. |
| Link/session lifetimes | Link: 15 minutes, one use. Session: 30 days absolute. | These are security/product tradeoffs and have no approved values today. |
| Session count and renewal | One active session per Customer + Shop; redeeming a new link replaces it; renew only by requesting another link. | Multi-device access and lost-device/session revocation UX are not defined. |
| Pending cancellation authority | Allow the authenticated Customer session to cancel only that Customer's `PENDING` Order in the same Shop, with explicit confirmation and CSRF protection. | The business operation is approved, but the Customer's technical proof/context for cancellation is not. Confirm that the history link is sufficient for this write permission or require a separate order-scoped cancellation capability. |
| Cookie/origin deployment | Same-site HTTPS storefront/API with Secure HttpOnly cookie and CSRF protection. | Frontend origin, domain, and cross-origin deployment are not documented. |
| Phone normalization and throttles | Normalize according to an approved phone-format rule; throttle per normalized-number digest, Shop, and IP/network. | Phone normalization remains unresolved; outbound delivery/provider limits and abuse thresholds need configuration. |
| Customer deletion/retention | Any approved Customer deletion must first revoke credentials; do not delete or retain Customer data beyond current domain rules. | Customer deletion/anonymization and historical data policy remain unresolved. |
| Revocation controls | Logout current session; replacement exchange revokes prior active session under the single-session recommendation. | A customer-wide revoke control, compromise response, and operator support flow are not specified. |
| Storefront technology and delivery adapter | Use the approved web/WhatsApp delivery integration once selected; no new infrastructure is assumed here. | Neither the frontend implementation nor WhatsApp provider/delivery architecture is present in the repository. |

The token/session controls above are a recommended technical security design. The listed delivery, duration, session-count, cancellation, origin, retention, and recovery choices must be reviewed before implementation. No choice here changes the approved no-OTP requirement or turns a WhatsApp number into a credential.

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

At review time, `backend/customers/models.py`, `backend/customers/views.py`, `backend/orders/models.py`, and `backend/orders/views.py` are empty Django scaffolds. `backend/config/urls.py` has no Customer or Order routes. There are no Customer profiles, Order records, access-link grants, Customer sessions, or WhatsApp delivery integration to reuse for this design. Merchant/Super Admin JWT and session code exists under `backend/users`; this proposal keeps customer credentials separate. The design remains unimplemented pending approval and domain/database/API implementation work.
