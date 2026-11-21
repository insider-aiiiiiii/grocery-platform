from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from config.test_clients import TokenAPIClient as APIClient

from cart.models import Cart, CartItem
from catalog.models import ShopProduct
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order
from shops.models import Shop
from users.models import Merchant, User


class OrderOverrideAndArchivingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merchant_user = User.objects.create_user(
            username="override-merchant",
            email="override-merchant@example.com",
            mobile_number="+919876540099",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        self.merchant = Merchant.objects.create(user=self.merchant_user, status=Merchant.Status.ACTIVE)
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Override Dukaan",
            address_line="10 MG Road",
            area="Koramangala",
            city="Bengaluru",
            state="Karnataka",
            pincode="560034",
            contact_number=self.merchant_user.mobile_number,
            delivery_charge=Decimal("20.00"),
        )
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Fresh Milk",
            sku="MLK-01",
            price=Decimal("50.00"),
            is_visible=True,
            is_available=True,
        )
        self.stock = InventoryItem.objects.get(shop=self.shop, product=self.product, variant__isnull=True)
        self.stock.quantity = Decimal("100.000")
        self.stock.save()

        self.customer = Customer.objects.create(
            shop=self.shop,
            name="Ramesh Kumar",
            whatsapp_number="+919876543210",
        )

        self.client.force_authenticate(user=self.merchant_user)
        self.checkout_url = reverse("public-order-checkout", args=[self.shop.public_slug])

    def _create_order(self, fulfillment=Order.FulfillmentType.PICKUP, key="key-1"):
        cart = Cart.objects.create(shop=self.shop, customer=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=Decimal("2.000"))
        client = APIClient()
        payload = {
            "cart_id": cart.pk,
            "customer_name": "Ramesh Kumar",
            "whatsapp_number": self.customer.whatsapp_number,
            "fulfillment_type": fulfillment,
        }
        if fulfillment == Order.FulfillmentType.HOME_DELIVERY:
            payload["delivery_address"] = {
                "recipient_name": "Ramesh Kumar",
                "recipient_phone": self.customer.whatsapp_number,
                "address_line": "123 Green Avenue",
                "area": "Indiranagar",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560038",
            }
        res = client.post(self.checkout_url, payload, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(res.status_code, 201)
        return Order.objects.get(pk=res.data["id"])

    def test_direct_mark_as_done_from_pending_unpaid(self):
        """Merchants can mark an unpaid PENDING order directly as COMPLETED, auto-deducting stock."""
        order = self._create_order(fulfillment=Order.FulfillmentType.PICKUP, key="direct-done-pending")
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_status, Order.PaymentStatus.UNPAID)

        # Inventory check: 2 reserved, 98 available
        stock = InventoryItem.objects.get(pk=self.stock.pk)
        self.assertEqual(stock.reserved_quantity, Decimal("2.000"))

        url = reverse("merchant-order-complete", args=[order.pk])
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertIsNotNone(order.completed_at)
        self.assertIsNotNone(order.accepted_at)

        # Stock is permanently deducted (reserved -> 0, quantity -> 98)
        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, Decimal("0.000"))
        self.assertEqual(stock.quantity, Decimal("98.000"))

    def test_direct_mark_as_done_from_preparing_unpaid_delivery(self):
        """Home delivery order in PREPARING can be marked done directly without paying online."""
        order = self._create_order(fulfillment=Order.FulfillmentType.HOME_DELIVERY, key="delivery-done")
        self.client.post(reverse("merchant-order-accept", args=[order.pk]), {}, format="json")
        self.client.post(reverse("merchant-order-prepare", args=[order.pk]), {}, format="json")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PREPARING)
        self.assertEqual(order.payment_status, Order.PaymentStatus.UNPAID)

        url = reverse("merchant-order-complete", args=[order.pk])
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)

    def test_cancel_override_from_pending_releases_stock(self):
        """Cancelling a PENDING order releases reserved stock without requiring a rejection note."""
        order = self._create_order(key="cancel-pending")
        stock = InventoryItem.objects.get(pk=self.stock.pk)
        self.assertEqual(stock.reserved_quantity, Decimal("2.000"))

        url = reverse("merchant-order-cancel", args=[order.pk])
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertEqual(order.rejection_reason_code, "MERCHANT_CANCELLED")

        stock.refresh_from_db()
        self.assertEqual(stock.reserved_quantity, Decimal("0.000"))
        self.assertEqual(stock.quantity, Decimal("100.000"))

    def test_cancel_override_from_ready_restores_stock(self):
        """Cancelling an order in READY status restores deducted stock to shop inventory."""
        order = self._create_order(key="cancel-ready")
        self.client.post(reverse("merchant-order-accept", args=[order.pk]), {}, format="json")
        self.client.post(reverse("merchant-order-prepare", args=[order.pk]), {}, format="json")
        self.client.post(reverse("merchant-order-ready", args=[order.pk]), {}, format="json")

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.READY)
        stock = InventoryItem.objects.get(pk=self.stock.pk)
        self.assertEqual(stock.quantity, Decimal("98.000"))

        url = reverse("merchant-order-cancel", args=[order.pk])
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)

        stock.refresh_from_db()
        self.assertEqual(stock.quantity, Decimal("100.000"))

    def test_incoming_orders_view_midnight_settlement_and_cap(self):
        """Incoming orders view (?view=incoming) retains active orders and today's terminal orders up to 50."""
        # 1. Create an active order
        active_order = self._create_order(key="active-1")

        # 2. Create today's completed order
        today_completed = self._create_order(key="today-completed")
        self.client.post(reverse("merchant-order-complete", args=[today_completed.pk]), {}, format="json")

        # 3. Create a yesterday completed order (simulating past midnight)
        yesterday_completed = self._create_order(key="yesterday-completed")
        self.client.post(reverse("merchant-order-complete", args=[yesterday_completed.pk]), {}, format="json")
        past_time = timezone.now() - timedelta(days=2)
        Order.objects.filter(pk=yesterday_completed.pk).update(created_at=past_time, updated_at=past_time)

        # Query incoming orders
        url = reverse("merchant-order-list")
        res = self.client.get(f"{url}?view=incoming")
        self.assertEqual(res.status_code, 200)

        returned_ids = [o["id"] for o in res.data]
        self.assertIn(active_order.pk, returned_ids)
        self.assertIn(today_completed.pk, returned_ids)
        self.assertNotIn(yesterday_completed.pk, returned_ids)

        # Query order history (without view=incoming)
        history_res = self.client.get(url)
        history_ids = [o["id"] for o in history_res.data]
        self.assertIn(yesterday_completed.pk, history_ids)

    def test_own_merchant_cannot_place_order_in_own_shop(self):
        """A merchant cannot place customer orders at their own shop using their merchant number."""
        cart = Cart.objects.create(shop=self.shop)
        CartItem.objects.create(cart=cart, product=self.product, quantity=Decimal("1.000"))
        client = APIClient()
        payload = {
            "cart_id": cart.pk,
            "customer_name": "Self Merchant",
            "whatsapp_number": self.merchant_user.mobile_number,
            "fulfillment_type": Order.FulfillmentType.PICKUP,
        }
        res = client.post(self.checkout_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="self-order-attempt")
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot place customer orders in their own shop", str(res.json()))

    def test_other_merchant_can_place_order_in_shop(self):
        """Another merchant registered on the platform CAN place an order at this shop."""
        other_user = User.objects.create_user(
            username="other-platform-merchant",
            email="other-platform-merchant@example.com",
            mobile_number="+919876549999",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        Merchant.objects.create(user=other_user, status=Merchant.Status.ACTIVE)

        cart = Cart.objects.create(shop=self.shop)
        CartItem.objects.create(cart=cart, product=self.product, quantity=Decimal("1.000"))
        client = APIClient()
        payload = {
            "cart_id": cart.pk,
            "customer_name": "Other Merchant Shopper",
            "whatsapp_number": other_user.mobile_number,
            "fulfillment_type": Order.FulfillmentType.PICKUP,
        }
        res = client.post(self.checkout_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="other-merchant-order")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["customer_phone"], other_user.mobile_number)
