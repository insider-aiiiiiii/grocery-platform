# 0007: Secret access tokens for public carts and orders

Status: Accepted (GP-QA-5)

## Context
Customers shop without logging in. Carts and orders were reachable by their numeric id
(`/orders/3/`, `/cart/3/`), so anyone could read other customers' names, phone numbers and
addresses, cancel their orders, or empty their baskets. A cross-site page could also cancel
orders because the endpoint needed no secret.

## Decision
- `Cart.access_token` and `Order.access_token`: 256-bit random URL-safe strings, unique, generated
  server-side (`config/tokens.py`).
- Every cart request and every order read/cancel must send the token in the `X-Cart-Token` /
  `X-Order-Token` header. A wrong or missing token returns the same 404 as a missing record.
- The cart token is returned when the cart is created; the order token only in the checkout
  response. The storefront keeps them in localStorage; the order confirmation link carries
  `?t=<token>` so it works on another device.
- Tokens are not accepted in query strings (logs, Referer). The frontend sends
  `Referrer-Policy: same-origin`.
- A custom header forces a CORS preflight, so a hostile web page cannot send the request.
- The direct `/api/v1/cart/<id>/` detail route was removed.

## Alternatives considered
- Phone number as proof: guessable and shared by family members; rejected.
- Signed (stateless) tokens: cannot be revoked and add a second secret; rejected.

## Consequences
- Existing carts and orders are back-filled with tokens by migrations; old order links without a
  token stop working (intended).
- Customers who lose their token cannot reopen an order page; the merchant still sees it.
