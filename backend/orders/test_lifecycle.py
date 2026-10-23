from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from catalog.models import ProductVariant, ShopProduct
from customers.models import Customer, CustomerSession
from inventory.models import InventoryItem
from orders.models import Order
from orders.services import create_order
from shops.models import Shop
from users.models import Merchant, User


class OrderLifecycleAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merchant_user = User.objects.create_user(
            username="order-lifecycle-merchant",
            email="order-lifecycle-merchant@example.com",
            mobile_number="+919876540001",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        self.merchant = Merchant.objects.create(user=self.merchant_user, status=Merchant.Status.ACTIVE)
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Lifecycle Shop",
            address_line="1 Market Road",
            area="Central",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            contact_number=self.merchant_user.mobile_number,
            delivery_charge=Decimal("25.00"),
        )
        self.other_user = User.objects.create_user(
            username="other-lifecycle-merchant",
            email="other-lifecycle-merchant@example.com",
            mobile_number="+919876540002",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        self.other_merchant = Merchant.objects.create(user=self.other_user, status=Merchant.Status.ACTIVE)
        self.other_shop = Shop.objects.create(
            merchant=self.other_merchant,
            name="Other Lifecycle Shop",
            address_line="2 Market Road",
            area="West",
            city="Bengaluru",
            state="Karnataka",
            pincode="560002",
            contact_number=self.other_user.mobile_number,
        )
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Original Apples",
            sku="APL-1",
            price=Decimal("10.00"),
            is_visible=True,
            is_available=True,
        )
        self.stock = InventoryItem.objects.get(shop=self.shop, product=self.product, variant__isnull=True)
        self.stock.quantity = Decimal("20.000")
        self.stock.save()
        self.variant_product = ShopProduct.objects.create(
            shop=self.shop,
            name="Milk",
            sku="MLK",
            price=None,
            is_visible=True,
            is_available=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.variant_product,
            name="1 Litre",
            sku="MLK-1L",
            price=Decimal("30.00"),
            is_visible=True,
            is_available=True,
        )
        self.variant_stock = InventoryItem.objects.get(shop=self.shop, variant=self.variant)
        self.variant_stock.quantity = Decimal("10.000")
        self.variant_stock.save()
        self.customer = Customer.objects.create(
            shop=self.shop,
            name="Checkout Name",
            whatsapp_number="+919123450001",
        )
        self.cart = Cart.objects.create(shop=self.shop, customer=self.customer)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=Decimal("3.000"),
        )
        self.checkout_url = reverse("public-order-checkout", args=[self.shop.public_slug])

    def checkout_payload(self, **overrides):
        payload = {
            "cart_id": self.cart.pk,
            "customer_name": "Checkout Name",
            "whatsapp_number": self.customer.whatsapp_number,
            "fulfillment_type": Order.FulfillmentType.PICKUP,
        }
        payload.update(overrides)
        return payload

    def checkout(self, payload=None, key="lifecycle-checkout"):
        return self.client.post(
            self.checkout_url,
            payload or self.checkout_payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def place_order(self, *, key="place-order", payload=None):
        if not self.cart.items.exists():
            self.cart = Cart.objects.create(shop=self.shop, customer=self.customer)
            self.cart_item = CartItem.objects.create(
                cart=self.cart,
                product=self.product,
                quantity=Decimal("3.000"),
            )
        response = self.checkout(payload=payload, key=key)
        self.assertEqual(response.status_code, 201, response.data)
        return Order.objects.get(pk=response.data["id"])

    def merchant_client(self, user=None):
        client = APIClient()
        client.force_authenticate(user=user or self.merchant_user)
        return client

    def test_pickup_checkout_snapshots_context_and_reserves_without_deduction(self):
        response = self.checkout()
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])
        item = order.items.get()

        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_status, Order.PaymentStatus.UNPAID)
        self.assertEqual(order.fulfillment_type, Order.FulfillmentType.PICKUP)
        self.assertEqual(order.customer_name_snapshot, "Checkout Name")
        self.assertEqual(order.customer_phone_snapshot, self.customer.whatsapp_number)
        self.assertEqual(order.total_amount, Decimal("30.00"))
        self.assertFalse(hasattr(order, "delivery_address"))
        self.assertEqual(item.ordered_quantity, Decimal("3.000"))
        self.assertEqual(item.product_name_snapshot, "Original Apples")
        self.assertEqual(item.sku_snapshot, "APL-1")
        self.assertEqual(item.unit_price_snapshot, Decimal("10.00"))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("20.000"))
        self.assertEqual(self.stock.reserved_quantity, Decimal("3.000"))
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())

        self.product.name = "Renamed Apples"
        self.product.sku = "APL-NEW"
        self.product.price = Decimal("99.00")
        self.product.save()
        self.customer.name = "Mutable Profile Name"
        self.customer.whatsapp_number = "+919123450009"
        self.customer.save()
        item.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(item.product_name_snapshot, "Original Apples")
        self.assertEqual(item.sku_snapshot, "APL-1")
        self.assertEqual(item.unit_price_snapshot, Decimal("10.00"))
        self.assertEqual(order.customer_name_snapshot, "Checkout Name")
        self.assertEqual(order.customer_phone_snapshot, "+919123450001")
        self.assertEqual(response.data["shop_name"], "Lifecycle Shop")
        self.assertEqual(response.data["shop_contact_number"], "+919876540001")
        self.assertIn("items", response.data)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["product_name"], "Original Apples")
        self.assertEqual(response.data["items"][0]["quantity"], "3.000")
        self.assertIn("whatsapp_notification_links", response.data)
        links = response.data["whatsapp_notification_links"]
        self.assertIsNotNone(links)
        self.assertEqual(set(links.keys()), {"en", "hinglish"})
        self.assertTrue(links["en"].startswith("https://wa.me/919876540001?text="))
        self.assertTrue(links["hinglish"].startswith("https://wa.me/919876540001?text="))

    def test_checkout_whatsapp_notification_links_isolation_when_shop_contact_missing(self):
        Shop.objects.filter(pk=self.shop.pk).update(contact_number="")
        response = self.checkout(key="missing-shop-contact-checkout")
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertIn("whatsapp_notification_links", response.data)
        self.assertIsNone(response.data["whatsapp_notification_links"])

    def test_delivery_requires_and_snapshots_address_but_pickup_rejects_address(self):
        missing = self.checkout(payload=self.checkout_payload(
            fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
        ), key="missing-address")
        self.assertEqual(missing.status_code, 400)
        self.assertIn("delivery_address", missing.data)

        pickup_with_address = self.checkout(payload=self.checkout_payload(
            delivery_address={"address_line": "1 Main", "area": "Central", "city": "Bengaluru",
                              "state": "Karnataka", "pincode": "560001"},
        ), key="pickup-address")
        self.assertEqual(pickup_with_address.status_code, 400)

        address = {
            "recipient_name": "Receiver Snapshot",
            "address_line": "42 Checkout Lane",
            "area": "Old Area",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560042",
            "landmark": "Old Landmark",
            "delivery_notes": "Call on arrival",
        }
        response = self.checkout(payload=self.checkout_payload(
            fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
            delivery_address=address,
        ), key="delivery-address")
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.delivery_address.address_line, "42 Checkout Lane")
        self.assertEqual(order.delivery_address.recipient_name, "Receiver Snapshot")
        self.assertEqual(order.delivery_charge_snapshot, Decimal("25.00"))
        self.assertEqual(order.total_amount, Decimal("55.00"))

        Shop.objects.filter(pk=self.shop.pk).update(is_home_delivery_enabled=False)
        unavailable = self.checkout(payload=self.checkout_payload(
            fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
            delivery_address=address,
        ), key="delivery-disabled")
        self.assertEqual(unavailable.status_code, 400)

    def test_checkout_validation_and_atomic_stock_failure_preserve_cart(self):
        missing_key = self.client.post(self.checkout_url, self.checkout_payload(), format="json")
        self.assertEqual(missing_key.status_code, 400)

        wrong_identity = self.checkout(payload=self.checkout_payload(whatsapp_number="+919123450099"), key="wrong-person")
        self.assertEqual(wrong_identity.status_code, 400)
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

        empty = Cart.objects.create(shop=self.shop)
        empty_response = self.checkout(payload=self.checkout_payload(cart_id=empty.pk), key="empty-cart")
        self.assertEqual(empty_response.status_code, 400)

        self.cart_item.quantity = Decimal("21.000")
        self.cart_item.save()
        insufficient = self.checkout(key="insufficient")
        self.assertEqual(insufficient.status_code, 400)
        self.assertFalse(Order.objects.filter(idempotency_key="insufficient").exists())
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("20.000"))
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))

        self.cart_item.quantity = Decimal("1.000")
        self.cart_item.save()
        self.product.is_available = False
        self.product.save()
        unavailable = self.checkout(key="unavailable")
        self.assertEqual(unavailable.status_code, 400)
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

    def test_checkout_rejects_cart_from_another_shop(self):
        other_product = ShopProduct.objects.create(
            shop=self.other_shop,
            name="Other Apples",
            price=Decimal("10.00"),
            is_visible=True,
            is_available=True,
        )
        other_cart = Cart.objects.create(shop=self.other_shop)
        CartItem.objects.create(cart=other_cart, product=other_product, quantity=Decimal("1.000"))
        response = self.checkout(
            payload=self.checkout_payload(cart_id=other_cart.pk, whatsapp_number="+919123450005"),
            key="other-shop-cart",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Order.objects.filter(idempotency_key="other-shop-cart").exists())

    def test_checkout_retry_returns_existing_order_without_duplicate_reservation(self):
        first = self.checkout(key="retry-checkout")
        second = self.checkout(key="retry-checkout")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Order.objects.filter(shop=self.shop, idempotency_key="retry-checkout").count(), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("3.000"))

    def test_variant_checkout_uses_variant_price_and_reserves_variant_stock(self):
        CartItem.objects.all().delete()
        variant_cart = Cart.objects.create(shop=self.shop)
        CartItem.objects.create(cart=variant_cart, product=self.variant_product, variant=self.variant,
                                quantity=Decimal("2.000"))
        response = self.checkout(payload=self.checkout_payload(cart_id=variant_cart.pk,
                                    whatsapp_number="+919123450002", customer_name="Variant Buyer"),
                                 key="variant-checkout")
        self.assertEqual(response.status_code, 201, response.data)
        item = Order.objects.get(pk=response.data["id"]).items.get()
        self.assertEqual(item.product_name_snapshot, "Milk")
        self.assertEqual(item.variant_name_snapshot, "1 Litre")
        self.assertEqual(item.unit_price_snapshot, Decimal("30.00"))
        self.variant_stock.refresh_from_db()
        self.assertEqual(self.variant_stock.quantity, Decimal("10.000"))
        self.assertEqual(self.variant_stock.reserved_quantity, Decimal("2.000"))

    def test_merchant_partial_acceptance_recalculates_totals_and_inventory(self):
        order = self.place_order(
            payload=self.checkout_payload(
                fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
                delivery_address={
                    "address_line": "42 Checkout Lane",
                    "area": "Central",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "pincode": "560042",
                },
            ),
        )
        item = order.items.get()
        merchant = self.merchant_client()
        invalid = merchant.post(
            reverse("merchant-order-accept", args=[order.pk]),
            {"items": [{"item_id": item.pk, "quantity": "3.001"}]},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400, invalid.data)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("3.000"))

        response = merchant.post(
            reverse("merchant-order-accept", args=[order.pk]),
            {"items": [{"item_id": item.pk, "quantity": "1.250"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("whatsapp_action_link", response.data)
        self.assertIsNotNone(response.data["whatsapp_action_link"])
        self.assertTrue(response.data["whatsapp_action_link"].startswith("https://wa.me/"))
        self.assertIn("quantity%20adjust", response.data["whatsapp_action_link"])
        order.refresh_from_db()
        item.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(order.status, Order.Status.ACCEPTED)
        self.assertEqual(item.ordered_quantity, Decimal("3.000"))
        self.assertEqual(item.quantity, Decimal("1.250"))
        self.assertEqual(item.line_total, Decimal("12.50"))
        self.assertEqual(order.items_subtotal, Decimal("12.50"))
        self.assertEqual(order.total_amount, Decimal("37.50"))
        self.assertEqual(self.stock.quantity, Decimal("18.750"))
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))

        invalid = merchant.post(
            reverse("merchant-order-accept", args=[order.pk]),
            {"items": [{"item_id": item.pk, "quantity": "3.001"}]},
            format="json",
        )
        self.assertEqual(invalid.status_code, 200)  # already accepted is idempotent; no new adjustment
        self.assertEqual(order_item_quantity(order.pk), Decimal("1.250"))

    def test_merchant_rejection_and_eligible_cancellation_release_and_restore_stock(self):
        rejected = self.place_order(key="reject-me")
        response = self.merchant_client().post(
            reverse("merchant-order-reject", args=[rejected.pk]), {"rejection_note": "Unavailable"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("whatsapp_action_link", response.data)
        self.assertIsNotNone(response.data["whatsapp_action_link"])
        self.assertTrue(response.data["whatsapp_action_link"].startswith("https://wa.me/"))
        self.assertIn("nahi%20kar%20pa%20rahe", response.data["whatsapp_action_link"])
        rejected.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(rejected.status, Order.Status.REJECTED)
        self.assertEqual(rejected.rejection_reason_code, "MERCHANT_REJECTED")
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))

        accepted = self.place_order(key="cancel-after-accept")
        item = accepted.items.get()
        response = self.merchant_client().post(
            reverse("merchant-order-accept", args=[accepted.pk]), {}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("whatsapp_action_link", response.data)
        self.assertIsNotNone(response.data["whatsapp_action_link"])
        self.assertTrue(response.data["whatsapp_action_link"].startswith("https://wa.me/"))
        self.assertIn("accept%20kar%20liya", response.data["whatsapp_action_link"])
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("17.000"))
        response = self.merchant_client().post(
            reverse("merchant-order-cancel", args=[accepted.pk]), {"rejection_note": "Customer called"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("whatsapp_action_link", response.data)
        self.assertIsNotNone(response.data["whatsapp_action_link"])
        self.assertTrue(response.data["whatsapp_action_link"].startswith("https://wa.me/"))
        self.assertIn("nahi%20kar%20pa%20rahe", response.data["whatsapp_action_link"])
        accepted.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(accepted.status, Order.Status.REJECTED)
        self.assertEqual(self.stock.quantity, Decimal("20.000"))
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))

        preparing = self.place_order(key="cannot-cancel-preparing")
        self.merchant_client().post(reverse("merchant-order-accept", args=[preparing.pk]), {}, format="json")
        self.merchant_client().post(reverse("merchant-order-prepare", args=[preparing.pk]), {}, format="json")
        denied = self.merchant_client().post(
            reverse("merchant-order-cancel", args=[preparing.pk]), {}, format="json"
        )
        self.assertEqual(denied.status_code, 409)

    def test_pending_expiry_rejects_order_and_releases_inventory(self):
        order = self.place_order(key="expired-order")
        Order.objects.filter(pk=order.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.merchant_client().get(reverse("merchant-order-detail", args=[order.pk]))
        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertEqual(order.rejection_reason_code, "TIMEOUT_EXPIRED")
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))

    def test_configurable_shop_timeout_and_expiry_calculation(self):
        # Configure shop with custom timeout (e.g., 45 minutes)
        self.shop.pending_order_timeout_minutes = 45
        self.shop.save(update_fields=["pending_order_timeout_minutes"])

        before = timezone.now()
        order = self.place_order(key="custom-timeout-order")
        after = timezone.now()

        # Verify expires_at is roughly 45 minutes from creation
        self.assertIsNotNone(order.expires_at)
        expected_min = before + timedelta(minutes=45)
        expected_max = after + timedelta(minutes=45)
        self.assertTrue(expected_min <= order.expires_at <= expected_max)

        # Verify merchant can configure timeout via Shop update API
        merchant = self.merchant_client()
        resp = merchant.patch(reverse("shops:shop-me"), {"pending_order_timeout_minutes": 20}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.pending_order_timeout_minutes, 20)

        # Invalid timeout (0 or negative) is rejected
        resp_bad = merchant.patch(reverse("shops:shop-me"), {"pending_order_timeout_minutes": 0}, format="json")
        self.assertEqual(resp_bad.status_code, 400)

    def test_merchant_cannot_accept_order_after_expiry(self):
        order = self.place_order(key="expired-accept-order")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("3.000"))

        # Fast forward past expires_at
        Order.objects.filter(pk=order.pk).update(expires_at=timezone.now() - timedelta(seconds=1))

        # Attempt to accept expired order
        merchant = self.merchant_client()
        response = merchant.post(reverse("merchant-order-accept", args=[order.pk]), {}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data.get("detail"),
            "The pending Order expired and was rejected; reserved stock was released.",
        )

        # Verify order transitioned to REJECTED outcome and reservation released
        order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertEqual(order.rejection_actor, Order.RejectionActor.SYSTEM)
        self.assertEqual(order.rejection_reason_code, "TIMEOUT_EXPIRED")
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))
        self.assertEqual(self.stock.quantity, Decimal("20.000"))

        # Subsequent accept attempt on already-expired/rejected order is also blocked
        second_resp = merchant.post(reverse("merchant-order-accept", args=[order.pk]), {}, format="json")
        self.assertEqual(second_resp.status_code, 409)
        self.assertIn("Only PENDING Orders can be accepted", second_resp.data.get("detail", ""))

    def test_scheduled_worker_expires_overdue_orders_and_releases_reservations(self):
        from orders.services import expire_overdue_pending_orders

        # Order 1: overdue
        overdue_order = self.place_order(key="worker-overdue")
        Order.objects.filter(pk=overdue_order.pk).update(expires_at=timezone.now() - timedelta(minutes=5))

        # Order 2: still valid pending (future expiry)
        valid_order = self.place_order(key="worker-valid")
        Order.objects.filter(pk=valid_order.pk).update(expires_at=timezone.now() + timedelta(minutes=10))

        # Stock has reservations for both (3.000 + 3.000 = 6.000)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("6.000"))

        # Run worker sweep
        expired_count = expire_overdue_pending_orders(batch_size=10)
        self.assertEqual(expired_count, 1)

        # Overdue order is expired and reservation released
        overdue_order.refresh_from_db()
        self.assertEqual(overdue_order.status, Order.Status.REJECTED)
        self.assertEqual(overdue_order.rejection_actor, Order.RejectionActor.SYSTEM)
        self.assertEqual(overdue_order.rejection_reason_code, "TIMEOUT_EXPIRED")

        # Valid order is still PENDING
        valid_order.refresh_from_db()
        self.assertEqual(valid_order.status, Order.Status.PENDING)

        # Stock reservation released exactly for overdue order (6.000 - 3.000 = 3.000)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("3.000"))

    def test_expire_pending_orders_management_command(self):
        from io import StringIO
        from django.core.management import call_command

        order = self.place_order(key="command-order")
        Order.objects.filter(pk=order.pk).update(expires_at=timezone.now() - timedelta(minutes=2))

        out = StringIO()
        call_command("expire_pending_orders", batch_size=10, stdout=out)
        self.assertIn("Successfully expired 1 overdue pending order(s)", out.getvalue())

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertEqual(order.rejection_reason_code, "TIMEOUT_EXPIRED")

    def test_expiry_worker_idempotent_and_releases_exactly_once(self):
        from orders.services import expire_overdue_pending_orders

        order = self.place_order(key="idempotent-expiry-order")
        Order.objects.filter(pk=order.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("3.000"))

        # First run expires and releases
        count1 = expire_overdue_pending_orders(batch_size=10)
        self.assertEqual(count1, 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))

        # Second run is idempotent (0 orders processed, stock remains untouched)
        count2 = expire_overdue_pending_orders(batch_size=10)
        self.assertEqual(count2, 0)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))
        self.assertEqual(self.stock.quantity, Decimal("20.000"))

    def test_payment_and_canonical_state_machine_constraints(self):
        order = self.place_order(key="state-machine")
        merchant = self.merchant_client()
        for action in ("prepare", "ready", "complete"):
            response = merchant.post(reverse(f"merchant-order-{action}", args=[order.pk]), {}, format="json")
            self.assertEqual(response.status_code, 409, (action, response.data))

        resp_accept = merchant.post(reverse("merchant-order-accept", args=[order.pk]), {}, format="json")
        self.assertIn("whatsapp_action_link", resp_accept.data)
        self.assertIn("accept%20kar%20liya", resp_accept.data["whatsapp_action_link"])

        resp_prep = merchant.post(reverse("merchant-order-prepare", args=[order.pk]), {}, format="json")
        self.assertIn("whatsapp_action_link", resp_prep.data)
        self.assertIn("pack%20hona%20shuru", resp_prep.data["whatsapp_action_link"])

        resp_ready = merchant.post(reverse("merchant-order-ready", args=[order.pk]), {}, format="json")
        self.assertIn("whatsapp_action_link", resp_ready.data)
        self.assertIn("ready%20hai", resp_ready.data["whatsapp_action_link"])

        unpaid_complete = merchant.post(reverse("merchant-order-complete", args=[order.pk]), {}, format="json")
        self.assertEqual(unpaid_complete.status_code, 409)
        paid = merchant.post(
            reverse("merchant-order-payment-status", args=[order.pk]), {"payment_status": "PAID"}, format="json"
        )
        self.assertEqual(paid.status_code, 200, paid.data)
        completed = merchant.post(reverse("merchant-order-complete", args=[order.pk]), {}, format="json")
        self.assertEqual(completed.status_code, 200, completed.data)
        self.assertIn("whatsapp_action_link", completed.data)
        self.assertIn("deliver%20ho%20gaya%20hai", completed.data["whatsapp_action_link"])
        self.assertIn("thank%20you", completed.data["whatsapp_action_link"])
        self.assertIn(self.shop.public_slug, completed.data["whatsapp_action_link"])
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)

        downgrade = merchant.post(
            reverse("merchant-order-payment-status", args=[order.pk]), {"payment_status": "UNPAID"}, format="json"
        )
        self.assertEqual(downgrade.status_code, 409)
        self.assertNotIn("CANCELLED", Order.Status.values)
        self.assertNotIn("EXPIRED", Order.Status.values)

    def test_merchant_order_list_detail_are_shop_scoped(self):
        own = self.place_order(key="own-order")
        other_customer = Customer.objects.create(
            shop=self.other_shop, name="Other Customer", whatsapp_number="+919123450003"
        )
        other = Order.objects.create(
            shop=self.other_shop,
            customer=other_customer,
            customer_name_snapshot="Other Customer",
            customer_phone_snapshot=other_customer.whatsapp_number,
            fulfillment_type=Order.FulfillmentType.PICKUP,
        )
        merchant = self.merchant_client()
        listing = merchant.get(reverse("merchant-order-list"))
        self.assertEqual(listing.status_code, 200)
        returned_ids = {entry["id"] for entry in listing.data["results"]} if isinstance(listing.data, dict) else {
            entry["id"] for entry in listing.data
        }
        self.assertIn(own.pk, returned_ids)
        self.assertNotIn(other.pk, returned_ids)
        self.assertEqual(merchant.get(reverse("merchant-order-detail", args=[other.pk])).status_code, 404)
        self.assertEqual(self.merchant_client(self.other_user).get(
            reverse("merchant-order-detail", args=[own.pk])
        ).status_code, 404)

    def test_customer_pending_cancellation_requires_profile_confirmation_origin_and_csrf(self):
        order = self.place_order(key="customer-cancel")
        session, secret = CustomerSession.objects.issue_for_profile(self.customer)
        url = reverse("customer-order-cancellation", args=[order.pk])

        no_session = self.client.post(url, {"confirmed": True}, format="json")
        self.assertEqual(no_session.status_code, 401)
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["customer_session"] = secret
        no_origin = client.post(url, {"confirmed": True}, format="json")
        self.assertEqual(no_origin.status_code, 403)
        csrf_secret = "a" * 32
        client.cookies["csrftoken"] = csrf_secret
        no_confirmation = client.post(
            url, {"confirmed": False}, format="json", HTTP_ORIGIN="http://testserver",
            HTTP_X_CSRFTOKEN=csrf_secret,
        )
        self.assertEqual(no_confirmation.status_code, 400)
        del client.cookies["csrftoken"]
        no_csrf = client.post(
            url, {"confirmed": True}, format="json", HTTP_ORIGIN="http://testserver"
        )
        self.assertEqual(no_csrf.status_code, 403)

        client.cookies["csrftoken"] = csrf_secret
        response = client.post(
            url,
            {"confirmed": True},
            format="json",
            HTTP_ORIGIN="http://testserver",
            HTTP_X_CSRFTOKEN=csrf_secret,
        )
        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertEqual(order.rejection_actor, Order.RejectionActor.CUSTOMER)
        self.assertEqual(order.rejection_reason_code, "CUSTOMER_CANCELLED")
        self.assertEqual(self.stock.reserved_quantity, Decimal("0.000"))
        self.assertIsNotNone(session.pk)

    def test_customer_session_cannot_cancel_another_profile_or_non_pending_order(self):
        order = self.place_order(key="customer-scope")
        other_customer = Customer.objects.create(
            shop=self.shop, name="Another Customer", whatsapp_number="+919123450004"
        )
        _, secret = CustomerSession.objects.issue_for_profile(other_customer)
        client = APIClient()
        client.cookies["customer_session"] = secret
        response = client.post(
            reverse("customer-order-cancellation", args=[order.pk]),
            {"confirmed": True},
            format="json",
            HTTP_ORIGIN="http://testserver",
        )
        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)


def order_item_quantity(order_id):
    return Order.objects.get(pk=order_id).items.get().quantity


class OrderPostgreSQLConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            username="concurrent-order-merchant",
            email="concurrent-order-merchant@example.com",
            mobile_number="+919876540010",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        self.merchant = Merchant.objects.create(user=self.user, status=Merchant.Status.ACTIVE)
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Concurrent Shop",
            address_line="10 Test Road",
            area="Central",
            city="Bengaluru",
            state="Karnataka",
            pincode="560010",
            contact_number=self.user.mobile_number,
        )
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Limited Stock",
            price=Decimal("5.00"),
            is_visible=True,
            is_available=True,
        )
        self.stock = InventoryItem.objects.get(shop=self.shop, product=self.product, variant__isnull=True)
        self.stock.quantity = Decimal("10.000")
        self.stock.save()
        self.second_product = ShopProduct.objects.create(
            shop=self.shop,
            name="Second Limited Stock",
            price=Decimal("8.00"),
            is_visible=True,
            is_available=True,
        )
        self.second_stock = InventoryItem.objects.get(
            shop=self.shop, product=self.second_product, variant__isnull=True
        )
        self.second_stock.quantity = Decimal("10.000")
        self.second_stock.save()

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_reservations_cannot_oversell_inventory(self):
        barrier = Barrier(2)

        def reserve():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    reserve_order_creation_stock_for_test(self.shop.pk, self.product.pk, Decimal("7.000"))
                    return "reserved"
                except DjangoValidationError:
                    return "insufficient"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: reserve(), range(2)))

        self.assertCountEqual(results, ["reserved", "insufficient"])
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("10.000"))
        self.assertEqual(self.stock.reserved_quantity, Decimal("7.000"))
        self.assertGreaterEqual(self.stock.quantity, self.stock.reserved_quantity)

    @skipUnlessDBFeature("has_select_for_update")
    def test_reversed_multi_item_checkouts_use_deadlock_safe_lock_order(self):
        from inventory.services import reserve_order_creation_stock

        barrier = Barrier(2)
        target_ids = [self.product.pk, self.second_product.pk]

        def reserve_batch(reverse_targets):
            close_old_connections()
            try:
                shop = Shop.objects.get(pk=self.shop.pk)
                products = {p.pk: p for p in ShopProduct.objects.filter(pk__in=target_ids)}
                ordered_ids = list(reversed(target_ids)) if reverse_targets else target_ids
                entries = [(products[product_id], Decimal("2.000")) for product_id in ordered_ids]
                barrier.wait(timeout=10)
                return reserve_order_creation_stock(shop, entries)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve_batch, [False, True]))

        self.assertEqual([len(result) for result in results], [2, 2])
        self.stock.refresh_from_db()
        self.second_stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("4.000"))
        self.assertEqual(self.second_stock.reserved_quantity, Decimal("4.000"))

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_same_idempotency_key_creates_one_order_and_one_reservation(self):
        carts = []
        for suffix in ("11", "12"):
            customer = Customer.objects.create(
                shop=self.shop,
                name=f"Concurrent Customer {suffix}",
                whatsapp_number=f"+9191234500{suffix}",
            )
            cart = Cart.objects.create(shop=self.shop, customer=customer)
            CartItem.objects.create(cart=cart, product=self.product, quantity=Decimal("2.000"))
            carts.append((cart.pk, customer.whatsapp_number, customer.name))
        barrier = Barrier(2)

        def submit(entry):
            close_old_connections()
            try:
                cart_id, phone, name = entry
                barrier.wait(timeout=10)
                order, created = create_order(
                    self.shop,
                    {
                        "cart_id": cart_id,
                        "customer_name": name,
                        "whatsapp_number": phone,
                        "fulfillment_type": Order.FulfillmentType.PICKUP,
                    },
                    "same-concurrent-checkout-key",
                )
                return order.pk, created
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, carts))

        self.assertEqual(len({order_id for order_id, _ in results}), 1)
        self.assertCountEqual([created for _, created in results], [True, False])
        self.assertEqual(Order.objects.filter(shop=self.shop, idempotency_key="same-concurrent-checkout-key").count(), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("10.000"))
        self.assertEqual(self.stock.reserved_quantity, Decimal("2.000"))


def reserve_order_creation_stock_for_test(shop_id, product_id, quantity):
    from inventory.services import reserve_order_creation_stock

    shop = Shop.objects.get(pk=shop_id)
    product = ShopProduct.objects.get(pk=product_id)
    return reserve_order_creation_stock(shop, [(product, quantity)])
