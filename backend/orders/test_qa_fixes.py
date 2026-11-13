from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from config.test_clients import TokenAPIClient as APIClient

from cart.models import Cart, CartItem
from customers.models import Customer
from customers.services import create_or_recognize_customer
from orders.models import Order
from orders.test_lifecycle import OrderLifecycleAPITests


class CheckoutIdempotencyReplayTests(TestCase):
    setUp = OrderLifecycleAPITests.setUp
    checkout_payload = OrderLifecycleAPITests.checkout_payload
    checkout = OrderLifecycleAPITests.checkout

    def test_same_key_replays_original_order_even_after_cart_was_emptied(self):
        first = self.checkout(key="replay-1")
        self.assertEqual(first.status_code, 201)
        self.assertFalse(self.cart.items.exists())

        again = self.checkout(key="replay-1")

        self.assertEqual(again.status_code, 200, again.data)
        self.assertEqual(again.data["id"], first.data["id"])
        self.assertEqual(Order.objects.count(), 1)

    def test_reusing_key_with_different_request_is_rejected(self):
        self.assertEqual(self.checkout(key="reuse-1").status_code, 201)

        response = self.checkout(self.checkout_payload(customer_name="Someone Else"), key="reuse-1")

        self.assertEqual(response.status_code, 400)
        self.assertIn("idempotency_key", response.data)
        self.assertEqual(Order.objects.count(), 1)


class ZeroPriceGuardTests(TestCase):
    setUp = OrderLifecycleAPITests.setUp
    checkout_payload = OrderLifecycleAPITests.checkout_payload
    checkout = OrderLifecycleAPITests.checkout

    def test_zero_priced_product_cannot_be_added_to_cart(self):
        self.product.price = Decimal("0.00")
        self.product.save()
        cart = Cart.objects.create(shop=self.shop)

        response = APIClient().post(
            f"/api/v1/cart/{cart.pk}/items/",
            {"product_id": self.product.pk, "quantity": "1"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    def test_checkout_rejects_cart_item_whose_price_became_zero(self):
        self.product.price = Decimal("0.00")
        self.product.save()

        response = self.checkout(key="zero-price")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)


class CustomerCreationRaceTests(TestCase):
    setUp = OrderLifecycleAPITests.setUp

    def test_lost_race_on_unique_constraint_recognizes_existing_customer(self):
        number = "+919555500001"
        winner = Customer.objects.create(shop=self.shop, whatsapp_number=number, name="")

        # Simulate the race deterministically: first lookup misses, create collides.
        real_filter = Customer.objects.filter
        calls = {"n": 0}

        def flaky_filter(*args, **kwargs):
            calls["n"] += 1
            qs = real_filter(*args, **kwargs)
            if calls["n"] == 1:  # the initial lookup misses: the other request has not committed yet
                return qs.none()
            return qs

        with mock.patch.object(Customer.objects, "filter", side_effect=flaky_filter):
            customer, created = create_or_recognize_customer(
                shop=self.shop, whatsapp_number=number, name="Asha"
            )

        self.assertEqual(customer.pk, winner.pk)
        self.assertFalse(created)
        self.assertEqual(Customer.objects.filter(shop=self.shop, whatsapp_number=number).count(), 1)


@override_settings(LOGIN_THROTTLE_RATE="10/min")
class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_repeated_logins_for_one_account_are_throttled(self):
        client = APIClient()
        url = reverse("auth-login")
        codes = [
            client.post(url, {"mobile_number": "+919000000099", "password": f"bad{i}"}, format="json").status_code
            for i in range(12)
        ]
        self.assertEqual(codes[:10], [401] * 10)
        self.assertEqual(codes[10:], [429, 429])

    def test_throttle_is_per_account(self):
        client = APIClient()
        url = reverse("auth-login")
        for i in range(10):
            client.post(url, {"mobile_number": "+919000000098", "password": "bad"}, format="json")
        other = client.post(url, {"mobile_number": "+919000000097", "password": "bad"}, format="json")
        self.assertEqual(other.status_code, 401)
