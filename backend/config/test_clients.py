"""Test helper: an APIClient that presents the secret cart/order token a real browser would hold.

Production code requires `X-Cart-Token` / `X-Order-Token` on every cart and order request. The
older functional tests create carts and orders straight through the ORM and then call the API,
so this client looks the token up and sends it, exactly as the storefront does after it created
the cart or placed the order. Anything the test sends explicitly is left untouched, and
config/test_security_hardening.py uses a plain client to prove requests WITHOUT tokens fail.
"""

import json
import re
from urllib.parse import parse_qs, urlsplit

from rest_framework.test import APIClient

_CART_IN_PATH = re.compile(r"/cart/(\d+)/")
_ORDER_IN_PATH = re.compile(r"/shops/public/[^/]+/orders/(\d+)/")


class TokenAPIClient(APIClient):
    def generic(self, method, path, data="", content_type="application/octet-stream", secure=False, **extra):
        from cart.models import Cart
        from orders.models import Order

        parts = urlsplit(path)
        query = parse_qs(parts.query)

        if "HTTP_X_CART_TOKEN" not in extra:
            cart_id = None
            match = _CART_IN_PATH.search(parts.path)
            if match:
                cart_id = match.group(1)
            elif query.get("cart_id"):
                cart_id = query["cart_id"][0]
            elif extra.get("HTTP_X_CART_ID"):
                cart_id = extra["HTTP_X_CART_ID"]
            elif isinstance(data, (str, bytes)) and "json" in (content_type or ""):
                try:
                    cart_id = (json.loads(data) or {}).get("cart_id")
                except (ValueError, AttributeError, TypeError):
                    cart_id = None
            if cart_id is not None:
                try:
                    token = Cart.objects.filter(pk=int(cart_id)).values_list("access_token", flat=True).first()
                except (TypeError, ValueError):
                    token = None
                if token:
                    extra["HTTP_X_CART_TOKEN"] = token

        if "HTTP_X_ORDER_TOKEN" not in extra:
            match = _ORDER_IN_PATH.search(parts.path)
            if match:
                token = Order.objects.filter(pk=int(match.group(1))).values_list("access_token", flat=True).first()
                if token:
                    extra["HTTP_X_ORDER_TOKEN"] = token

        return super().generic(method, path, data, content_type, secure, **extra)
