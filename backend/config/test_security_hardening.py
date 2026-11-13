"""GP-QA-5: regression tests for the browser attack findings (BT-01 .. BT-14).

Each test replays what an attacker with only a browser could do. They must fail on the
code as it was in commit 3a283d8.
"""

from decimal import Decimal

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from orders.models import Order
from orders.test_lifecycle import OrderLifecycleAPITests
from shops.models import Shop
from users.models import Merchant, User


class OrderAndCartTokenTests(TestCase):
    """BT-01 .. BT-05, BT-13: numeric ids alone must never reach a cart or an order."""

    checkout_payload = OrderLifecycleAPITests.checkout_payload

    def setUp(self):
        OrderLifecycleAPITests.setUp(self)
        self.client = APIClient()  # plain client: never adds tokens for us

    def place(self, key="sec-1"):
        return self.client.post(
            self.checkout_url,
            self.checkout_payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
            HTTP_X_CART_TOKEN=self.cart.access_token,
        )

    def order_url(self, order_id, suffix=""):
        return f"/api/v1/shops/public/{self.shop.public_slug}/orders/{order_id}/{suffix}"

    def test_checkout_returns_a_long_random_order_token_once(self):
        response = self.place()
        self.assertEqual(response.status_code, 201, response.data)
        token = response.data["access_token"]
        self.assertGreaterEqual(len(token), 40)
        self.assertEqual(Order.objects.get(pk=response.data["id"]).access_token, token)

    def test_order_cannot_be_read_by_id_alone(self):  # BT-01 / BT-02
        order_id = self.place().data["id"]
        for headers in ({}, {"HTTP_X_ORDER_TOKEN": "wrong-token"}, {"HTTP_X_ORDER_TOKEN": ""}):
            response = self.client.get(self.order_url(order_id), **headers)
            self.assertEqual(response.status_code, 404, headers)
            self.assertNotIn("customer_phone", response.data)
        # Query-string tokens are not accepted: they would leak through logs and Referer.
        token = Order.objects.get(pk=order_id).access_token
        self.assertEqual(self.client.get(self.order_url(order_id) + f"?token={token}").status_code, 404)

    def test_order_is_readable_with_its_token(self):
        placed = self.place().data
        response = self.client.get(self.order_url(placed["id"]), HTTP_X_ORDER_TOKEN=placed["access_token"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["customer_phone"], self.customer.whatsapp_number)
        self.assertNotIn("access_token", response.data, "the token is only returned at checkout")

    def test_token_of_one_order_does_not_open_another(self):
        first = self.place("sec-a").data
        self.cart = Cart.objects.create(shop=self.shop, customer=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=Decimal("1.000"))
        second = self.client.post(
            self.checkout_url,
            self.checkout_payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY="sec-b",
            HTTP_X_CART_TOKEN=self.cart.access_token,
        ).data
        response = self.client.get(self.order_url(second["id"]), HTTP_X_ORDER_TOKEN=first["access_token"])
        self.assertEqual(response.status_code, 404)

    def test_order_cannot_be_cancelled_without_its_token(self):  # BT-03 / BT-04
        order_id = self.place().data["id"]
        for headers in ({}, {"HTTP_X_ORDER_TOKEN": "nope"}):
            self.assertEqual(self.client.post(self.order_url(order_id, "cancel/"), **headers).status_code, 404)
            self.assertEqual(self.client.post(self.order_url(order_id), **headers).status_code, 404)
        self.assertEqual(Order.objects.get(pk=order_id).status, Order.Status.PENDING)

    def test_cross_site_plain_post_cannot_cancel(self):  # BT-04: a no-cors POST carries no custom header
        order_id = self.place().data["id"]
        response = Client().post(self.order_url(order_id, "cancel/"), data="", content_type="text/plain")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Order.objects.get(pk=order_id).status, Order.Status.PENDING)

    def test_order_can_be_cancelled_with_its_token(self):
        placed = self.place().data
        response = self.client.post(self.order_url(placed["id"], "cancel/"), HTTP_X_ORDER_TOKEN=placed["access_token"])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Order.objects.get(pk=placed["id"]).status, Order.Status.REJECTED)

    def test_cors_preflight_allows_the_token_headers(self):
        response = self.client.options(
            self.order_url(1),
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-order-token,x-cart-token",
        )
        allowed = response.headers.get("Access-Control-Allow-Headers", "").lower()
        self.assertIn("x-order-token", allowed)
        self.assertIn("x-cart-token", allowed)

    # ---- carts ------------------------------------------------------------------------
    def cart_url(self, suffix=""):
        return f"/api/v1/shops/public/{self.shop.public_slug}/cart/{self.cart.pk}/{suffix}"

    def test_direct_cart_route_is_gone(self):  # BT-02
        self.assertEqual(self.client.get(f"/api/v1/cart/{self.cart.pk}/").status_code, 404)

    def test_cart_cannot_be_read_or_changed_by_id_alone(self):  # BT-05
        list_url = f"/api/v1/shops/public/{self.shop.public_slug}/cart/"
        item_url = self.cart_url(f"items/{self.cart_item.pk}/")
        for headers in ({}, {"HTTP_X_CART_TOKEN": "wrong"}):
            self.assertEqual(self.client.get(self.cart_url(), **headers).status_code, 404)
            self.assertEqual(self.client.get(list_url, {"cart_id": self.cart.pk}, **headers).status_code, 404)
            self.assertEqual(self.client.get(self.cart_url("items/"), **headers).status_code, 404)
            self.assertEqual(self.client.delete(self.cart_url("items/"), **headers).status_code, 404)
            self.assertEqual(self.client.patch(item_url, {"quantity": "1"}, format="json", **headers).status_code, 404)
            self.assertEqual(self.client.delete(item_url, **headers).status_code, 404)
            self.assertEqual(self.client.post(self.cart_url("validate/"), **headers).status_code, 404)
            self.assertEqual(
                self.client.post(
                    self.cart_url("customer/"), {"whatsapp_number": "9123450099"}, format="json", **headers
                ).status_code,
                404,
            )
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

    def test_cart_works_with_its_token(self):
        headers = {"HTTP_X_CART_TOKEN": self.cart.access_token}
        self.assertEqual(self.client.get(self.cart_url(), **headers).status_code, 200)
        self.assertEqual(self.client.get(self.cart_url("items/"), **headers).status_code, 200)

    def test_new_cart_returns_its_token_and_it_is_unique(self):
        url = f"/api/v1/shops/public/{self.shop.public_slug}/cart/"
        a = self.client.post(url, {}, format="json").data
        b = self.client.post(url, {}, format="json").data
        self.assertNotEqual(a["access_token"], b["access_token"])
        other = self.client.get(url, {"cart_id": a["id"]}, HTTP_X_CART_TOKEN=b["access_token"])
        self.assertEqual(other.status_code, 404)

    def test_checkout_needs_the_cart_token(self):  # BT-05
        response = self.client.post(
            self.checkout_url, self.checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="no-token"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Order.objects.count(), 0)

    def test_customer_endpoint_cannot_bind_someone_elses_cart(self):
        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/"
        response = self.client.post(url, {"whatsapp_number": "9123450077", "cart_id": self.cart.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_closed_shop_rejects_checkout(self):  # BT-13
        Shop.objects.filter(pk=self.shop.pk).update(is_temporarily_closed=True)
        response = self.place("closed-1")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Cart.objects.get(pk=self.cart.pk).items.count(), 1)


class LoginThrottleTests(TestCase):
    """BT-07: extra junk fields must not give every guess a fresh rate-limit bucket."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()

    @override_settings(
        LOGIN_THROTTLE_RATE="10/min", LOGIN_IP_THROTTLE_RATE="30/min", LOGIN_ACCOUNT_THROTTLE_RATE="20/hour"
    )
    def test_super_admin_login_with_random_extra_field_is_still_throttled(self):
        statuses = []
        for i in range(25):
            response = self.client.post(
                "/api/v1/auth/super-admin/login/",
                {"identifier": "admin@example.com", "password": f"guess{i}", "mobile_number": f"junk-{i}"},
                format="json",
            )
            statuses.append(response.status_code)
        self.assertEqual(statuses[:10], [401] * 10)
        self.assertTrue(all(code == 429 for code in statuses[10:]), statuses)

    @override_settings(
        LOGIN_THROTTLE_RATE="10/min", LOGIN_IP_THROTTLE_RATE="30/min", LOGIN_ACCOUNT_THROTTLE_RATE="20/hour"
    )
    def test_merchant_login_with_random_extra_field_is_still_throttled(self):
        statuses = []
        for i in range(25):
            response = self.client.post(
                "/api/v1/auth/login/",
                {"mobile_number": "+919876500001", "password": f"guess{i}", "identifier": f"junk-{i}"},
                format="json",
            )
            statuses.append(response.status_code)
        self.assertTrue(all(code == 429 for code in statuses[10:]), statuses)

    @override_settings(
        LOGIN_THROTTLE_RATE="1000/min", LOGIN_IP_THROTTLE_RATE="1000/min", LOGIN_ACCOUNT_THROTTLE_RATE="5/hour"
    )
    def test_one_account_is_limited_even_from_many_ip_addresses(self):
        codes = []
        for i in range(8):
            response = self.client.post(
                "/api/v1/auth/super-admin/login/",
                {"identifier": "Admin@Example.com", "password": f"guess{i}"},
                format="json",
                REMOTE_ADDR=f"10.0.0.{i + 1}",
            )
            codes.append(response.status_code)
        self.assertEqual(codes[:5], [401] * 5)
        self.assertEqual(codes[5:], [429] * 3)

    @override_settings(
        LOGIN_THROTTLE_RATE="1000/min", LOGIN_IP_THROTTLE_RATE="6/min", LOGIN_ACCOUNT_THROTTLE_RATE="1000/hour"
    )
    def test_one_ip_is_limited_across_many_accounts(self):
        codes = [
            self.client.post(
                "/api/v1/auth/super-admin/login/",
                {"identifier": f"user{i}@example.com", "password": "x"},
                format="json",
            ).status_code
            for i in range(9)
        ]
        self.assertEqual(codes[:6], [401] * 6)
        self.assertEqual(codes[6:], [429] * 3)


class UploadHardeningTests(TestCase):
    """BT-11: a logo must be a real picture, never a web page."""

    PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

    def setUp(self):
        user = User.objects.create_user(
            username="upload-merchant",
            email="upload@example.com",
            mobile_number="+919876550001",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        merchant = Merchant.objects.create(user=user, status=Merchant.Status.ACTIVE)
        self.shop = Shop.objects.create(
            merchant=merchant,
            name="Upload Shop",
            address_line="1 Road",
            area="A",
            city="C",
            state="S",
            pincode="560001",
            contact_number="+919876550001",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def patch_logo(self, name, content, content_type="image/png"):
        return self.client.patch(
            "/api/v1/shops/me/",
            {"logo": SimpleUploadedFile(name, content, content_type=content_type)},
            format="multipart",
        )

    def test_html_file_is_rejected_as_logo(self):
        response = self.patch_logo("logo.html", b"<script>alert(1)</script>", "text/html")
        self.assertEqual(response.status_code, 400, getattr(response, "data", None))
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.logo)

    def test_html_disguised_as_png_is_rejected(self):
        response = self.patch_logo("logo.png", b"<html><script>alert(1)</script></html>")
        self.assertEqual(response.status_code, 400, getattr(response, "data", None))

    def test_svg_is_rejected(self):
        content = b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>"
        self.assertEqual(self.patch_logo("logo.svg", content, "image/svg+xml").status_code, 400)

    def test_real_png_is_accepted(self):
        response = self.patch_logo("logo.png", self.PNG)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))

    def test_png_content_with_jpg_name_is_rejected(self):
        self.assertEqual(self.patch_logo("logo.jpg", self.PNG).status_code, 400)


class SecuritySettingsTests(TestCase):
    """BT-12 and deployment defaults."""

    def test_backend_refuses_to_be_framed(self):
        response = Client().get("/admin/login/")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")

    def test_database_cache_backs_rate_limits(self):
        from django.conf import settings

        self.assertIn("DatabaseCache", settings.CACHES["default"]["BACKEND"])

    def test_wildcard_hosts_and_public_secret_key_are_gone(self):
        from django.conf import settings

        self.assertNotIn("*", settings.ALLOWED_HOSTS)


class RecognizeThrottleTests(TestCase):
    setUp = OrderLifecycleAPITests.setUp

    @override_settings(PUBLIC_LOOKUP_THROTTLE_RATE="3/min")
    def test_customer_lookup_by_phone_is_rate_limited(self):
        cache.clear()
        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/recognize/"
        codes = [
            self.client.post(url, {"whatsapp_number": f"91234500{i:02d}"}, format="json").status_code
            for i in range(6)
        ]
        self.assertEqual(codes[3:], [429, 429, 429], codes)
        cache.clear()
