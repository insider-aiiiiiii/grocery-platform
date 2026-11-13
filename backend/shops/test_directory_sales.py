"""GP-QA-3: the Super Admin tenant directory reports real 30-day realized sales (ADR 0006)."""

from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from orders.models import Order
from shops.models import Shop
from shops.serializers import format_rupees
from users.models import Merchant, User

DIRECTORY_URL = "/api/v1/shops/admin/directory/"


class FormatRupeesTests(SimpleTestCase):
    def test_indian_grouping_and_paise(self):
        self.assertEqual(format_rupees(0), "₹0")
        self.assertEqual(format_rupees(None), "₹0")
        self.assertEqual(format_rupees(Decimal("165.00")), "₹165")
        self.assertEqual(format_rupees(Decimal("60.50")), "₹60.50")
        self.assertEqual(format_rupees(Decimal("1234.00")), "₹1,234")
        self.assertEqual(format_rupees(Decimal("123456.00")), "₹1,23,456")
        self.assertEqual(format_rupees(Decimal("12345678.25")), "₹1,23,45,678.25")


class TenantDirectorySalesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="dir-admin", email="dir-admin@example.com", mobile_number="+919800000001",
            role=User.Role.SUPER_ADMIN, password="test-password-123",
        )
        self.shop_a = self._shop("a", "+919800000002")
        self.shop_b = self._shop("b", "+919800000003")
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def _shop(self, key, mobile):
        user = User.objects.create_user(
            username=f"dir-m-{key}", email=f"dir-m-{key}@example.com", mobile_number=mobile,
            role=User.Role.MERCHANT, password="test-password-123",
        )
        merchant = Merchant.objects.create(user=user, status=Merchant.Status.ACTIVE)
        return Shop.objects.create(
            merchant=merchant, name=f"Dir Shop {key}", address_line="1 Road", area="Area",
            city="Indore", state="MP", pincode="452001", contact_number=mobile,
        )

    def _order(self, shop, amount, status=Order.Status.COMPLETED, days_ago=0):
        customer, _ = Customer.objects.get_or_create(
            shop=shop, whatsapp_number="+919123450001", defaults={"name": "C"}
        )
        order = Order.objects.create(
            shop=shop, customer=customer, status=status,
            payment_status=Order.PaymentStatus.PAID if status == Order.Status.COMPLETED else Order.PaymentStatus.UNPAID,
            fulfillment_type=Order.FulfillmentType.PICKUP, customer_name_snapshot="C",
            customer_phone_snapshot="+919123450001", items_subtotal=Decimal(amount), total_amount=Decimal(amount),
        )
        if days_ago:
            Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
        return order

    def _volumes(self):
        response = self.client.get(DIRECTORY_URL)
        self.assertEqual(response.status_code, 200, response.data)
        return {row["name"]: row["monthly_volume"] for row in response.data if row["shop_id"]}

    def test_sums_only_completed_orders_in_the_last_30_days_per_shop(self):
        self._order(self.shop_a, "100.00")
        self._order(self.shop_a, "65.50", days_ago=29)
        self._order(self.shop_a, "999.00", days_ago=31)                       # outside the window
        self._order(self.shop_a, "500.00", status=Order.Status.PENDING)       # not completed
        self._order(self.shop_a, "700.00", status=Order.Status.REJECTED)      # not completed
        self._order(self.shop_b, "1234.00")                                   # other shop

        volumes = self._volumes()

        self.assertEqual(volumes["Dir Shop a"], "₹165.50")
        self.assertEqual(volumes["Dir Shop b"], "₹1,234")

    def test_shop_without_orders_shows_zero(self):
        self.assertEqual(self._volumes()["Dir Shop a"], "₹0")

    def test_directory_query_count_does_not_grow_with_the_number_of_shops(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self._order(self.shop_a, "10.00")
        with CaptureQueriesContext(connection) as before:
            self.assertEqual(self.client.get(DIRECTORY_URL).status_code, 200)

        for key, mobile in (("c", "+919800000004"), ("d", "+919800000005"), ("e", "+919800000006")):
            self._order(self._shop(key, mobile), "5.00")
        with CaptureQueriesContext(connection) as after:
            self.assertEqual(self.client.get(DIRECTORY_URL).status_code, 200)

        self.assertEqual(len(after), len(before), "directory must not run per-shop queries")

    def test_catalog_items_count_still_correct(self):
        from catalog.models import ShopProduct

        for n in range(3):
            ShopProduct.objects.create(shop=self.shop_a, name=f"P{n}", sku=f"S{n}", price=Decimal("1.00"),
                                       is_visible=True, is_available=True)
        rows = {r["name"]: r["catalog_items_count"] for r in self.client.get(DIRECTORY_URL).data if r["shop_id"]}
        self.assertEqual(rows["Dir Shop a"], 3)
        self.assertEqual(rows["Dir Shop b"], 0)
