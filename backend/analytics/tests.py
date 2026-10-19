from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import MasterCategory, ProductVariant, ShopProduct
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from shops.models import Shop
from users.models import Merchant, User


class AnalyticsBaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        # Create Merchant 1 and Shop 1 (Primary tenant)
        self.user1 = User.objects.create_user(
            username="merchant_one",
            email="merchant_one@example.com",
            password="testpassword123",
            role=User.Role.MERCHANT,
            mobile_number="+919876543210",
        )
        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop1 = Shop.objects.create(
            merchant=self.merchant1,
            name="Shop One",
            address_line="123 Market St",
            area="Downtown",
            city="Metropolis",
            state="Central",
            pincode="123456",
            contact_number="+919876543210",
            status=Shop.Status.ACTIVE,
        )

        # Create Merchant 2 and Shop 2 (Isolated tenant)
        self.user2 = User.objects.create_user(
            username="merchant_two",
            email="merchant_two@example.com",
            password="testpassword123",
            role=User.Role.MERCHANT,
            mobile_number="+919876543211",
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop2 = Shop.objects.create(
            merchant=self.merchant2,
            name="Shop Two",
            address_line="456 High St",
            area="Uptown",
            city="Metropolis",
            state="Central",
            pincode="123457",
            contact_number="+919876543211",
            status=Shop.Status.ACTIVE,
        )

        # Create Super Admin user
        self.super_admin = User.objects.create_user(
            username="super_admin",
            email="super_admin@example.com",
            password="testpassword123",
            role=User.Role.SUPER_ADMIN,
            mobile_number="+919876543299",
        )

        # Create Customer 1 in Shop 1
        self.customer1 = Customer.objects.create(
            shop=self.shop1,
            name="Alice Customer",
            whatsapp_number="+919999900001",
        )

        # Create Customer 2 in Shop 1
        self.customer2 = Customer.objects.create(
            shop=self.shop1,
            name="Bob Customer",
            whatsapp_number="+919999900002",
        )

        # Create Customer in Shop 2 with same phone as Customer 1 (verifies shop isolation)
        self.customer_shop2 = Customer.objects.create(
            shop=self.shop2,
            name="Alice Shop2",
            whatsapp_number="+919999900001",
        )

        # Create Products for Shop 1
        self.category = MasterCategory.objects.create(name="Groceries")
        self.prod1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Milk",
            price=Decimal("60.00"),
            sku="MILK-001",
        )
        self.prod2 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Whole Wheat Bread",
            price=Decimal("40.00"),
            sku="BREAD-001",
        )
        self.prod3 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Farm Eggs 12pk",
            price=Decimal("90.00"),
            sku="EGGS-001",
        )

        # Create Product for Shop 2
        self.prod_shop2 = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop2 Exotic Tea",
            price=Decimal("200.00"),
            sku="TEA-002",
        )


class MerchantAnalyticsAuthenticationAndPermissionTests(AnalyticsBaseTestCase):
    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must be rejected with 401."""
        urls = [
            reverse("analytics:merchant-analytics-overview"),
            reverse("analytics:merchant-analytics-top-products"),
            reverse("analytics:merchant-analytics-low-stock"),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_forbidden_from_merchant_analytics(self):
        """Super Admin cannot access merchant-scoped analytics."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_merchant_forbidden(self):
        """Inactive merchant is forbidden."""
        self.merchant1.status = Merchant.Status.DEACTIVATED
        self.merchant1.save()
        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_merchant_with_deactivated_shop_rejected(self):
        """Merchant whose shop is deactivated cannot access analytics."""
        self.shop1.status = Shop.Status.DEACTIVATED
        self.shop1.save()
        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_merchant_without_shop_rejected(self):
        """Merchant without a shop is rejected with 404."""
        user_no_shop = User.objects.create_user(
            username="merchant_no_shop",
            email="no_shop@example.com",
            password="testpassword123",
            role=User.Role.MERCHANT,
            mobile_number="+919876543999",
        )
        Merchant.objects.create(
            user=user_no_shop,
            status=Merchant.Status.ACTIVE,
        )
        self.client.force_authenticate(user=user_no_shop)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class MerchantAnalyticsTenantIsolationTests(AnalyticsBaseTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()

        # Create Order in Shop 1 (Completed, total 100.00)
        self.order1 = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("100.00"),
            items_subtotal=Decimal("100.00"),
            customer_name_snapshot="Alice Customer",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=self.order1,
            product=self.prod1,
            product_name_snapshot=self.prod1.name,
            sku_snapshot=self.prod1.sku,
            ordered_quantity=Decimal("2.000"),
            quantity=Decimal("2.000"),
            unit_price_snapshot=Decimal("50.00"),
            line_total=Decimal("100.00"),
        )

        # Create Order in Shop 2 (Completed, total 500.00)
        self.order2 = Order.objects.create(
            shop=self.shop2,
            customer=self.customer_shop2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("500.00"),
            items_subtotal=Decimal("500.00"),
            customer_name_snapshot="Alice Shop2",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=self.order2,
            product=self.prod_shop2,
            product_name_snapshot=self.prod_shop2.name,
            sku_snapshot=self.prod_shop2.sku,
            ordered_quantity=Decimal("5.000"),
            quantity=Decimal("5.000"),
            unit_price_snapshot=Decimal("100.00"),
            line_total=Decimal("500.00"),
        )

        # Make prod2 and prod3 in Shop 1 in-stock so only prod1 is out of stock
        inv_prod2 = InventoryItem.objects.get(shop=self.shop1, product=self.prod2)
        inv_prod2.quantity = Decimal("10.000")
        inv_prod2.save()

        inv_prod3 = InventoryItem.objects.get(shop=self.shop1, product=self.prod3)
        inv_prod3.quantity = Decimal("10.000")
        inv_prod3.save()

        # Make Shop 2's item out of stock
        inv2 = InventoryItem.objects.get(shop=self.shop2, product=self.prod_shop2)
        inv2.quantity = Decimal("0.000")
        inv2.save()

    def test_merchant1_sees_only_shop1_metrics(self):
        """Merchant 1 sees strictly Shop 1 metrics; Shop 2 data is completely isolated."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["orders"]["total_orders"], 1)
        self.assertEqual(data["orders"]["completed_orders"], 1)
        self.assertEqual(data["sales"]["realized_sales"], "100.00")
        self.assertEqual(data["sales"]["average_order_value"], "100.00")
        self.assertEqual(data["customers"]["ordering_customers"], 1)
        self.assertEqual(data["inventory"]["out_of_stock_items_count"], 1)  # prod1 starts with 0 stock

        # Top products for Shop 1 contains only Shop 1's products
        top_prods = data["top_products"]
        self.assertEqual(len(top_prods), 1)
        self.assertEqual(top_prods[0]["product_id"], self.prod1.id)
        self.assertEqual(top_prods[0]["product_name"], "Organic Milk")

    def test_merchant2_sees_only_shop2_metrics(self):
        """Merchant 2 sees strictly Shop 2 metrics."""
        self.client.force_authenticate(user=self.user2)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["orders"]["total_orders"], 1)
        self.assertEqual(data["orders"]["completed_orders"], 1)
        self.assertEqual(data["sales"]["realized_sales"], "500.00")
        self.assertEqual(data["sales"]["average_order_value"], "500.00")
        self.assertEqual(data["customers"]["ordering_customers"], 1)

        top_prods = data["top_products"]
        self.assertEqual(len(top_prods), 1)
        self.assertEqual(top_prods[0]["product_id"], self.prod_shop2.id)
        self.assertEqual(top_prods[0]["product_name"], "Shop2 Exotic Tea")

    def test_client_provided_shop_id_param_is_ignored(self):
        """Providing shop_id query parameter cannot bypass tenant boundaries."""
        self.client.force_authenticate(user=self.user1)
        # Attempt to inject shop2's ID
        res = self.client.get(reverse("analytics:merchant-analytics-overview"), {"shop_id": self.shop2.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Still returns Shop 1's realized sales
        self.assertEqual(res.data["sales"]["realized_sales"], "100.00")


class MerchantAnalyticsFormulasAndMetricsTests(AnalyticsBaseTestCase):
    def test_order_status_distribution_and_realized_sales(self):
        """
        Total orders counts all statuses.
        Realized sales strictly counts COMPLETED orders.
        Pending, preparing, and rejected orders do NOT count towards realized sales.
        """
        # Completed order (50.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("50.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # Another Completed order (150.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("150.00"),
            customer_name_snapshot="Bob",
            customer_phone_snapshot="+919999900002",
        )
        # Pending order (80.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.PENDING,
            total_amount=Decimal("80.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # Accepted order (120.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer2,
            status=Order.Status.ACCEPTED,
            total_amount=Decimal("120.00"),
            customer_name_snapshot="Bob",
            customer_phone_snapshot="+919999900002",
        )
        # Rejected order (200.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.REJECTED,
            total_amount=Decimal("200.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        orders = data["orders"]
        self.assertEqual(orders["total_orders"], 5)
        self.assertEqual(orders["completed_orders"], 2)
        self.assertEqual(orders["rejected_orders"], 1)
        self.assertEqual(orders["status_distribution"]["PENDING"], 1)
        self.assertEqual(orders["status_distribution"]["ACCEPTED"], 1)
        self.assertEqual(orders["status_distribution"]["PREPARING"], 0)
        self.assertEqual(orders["status_distribution"]["READY"], 0)
        self.assertEqual(orders["status_distribution"]["COMPLETED"], 2)
        self.assertEqual(orders["status_distribution"]["REJECTED"], 1)

        # Sales: 50.00 + 150.00 = 200.00 (pending, accepted, rejected excluded)
        sales = data["sales"]
        self.assertEqual(sales["realized_sales"], "200.00")
        # AOV: 200.00 / 2 = 100.00
        self.assertEqual(sales["average_order_value"], "100.00")

    def test_average_order_value_with_zero_completed_orders(self):
        """AOV returns '0.00' when there are no completed orders."""
        # Only pending and rejected orders
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.PENDING,
            total_amount=Decimal("75.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.REJECTED,
            total_amount=Decimal("150.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["sales"]["realized_sales"], "0.00")
        self.assertEqual(res.data["sales"]["average_order_value"], "0.00")

    def test_top_selling_products_ranking_and_snapshot_preservation(self):
        """
        Top selling products ranked by units sold on completed orders.
        Snapshot names/SKUs are preserved even if live product is renamed.
        """
        order1 = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("300.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # 5 units of Bread
        OrderItem.objects.create(
            order=order1,
            product=self.prod2,
            product_name_snapshot="Whole Wheat Bread",
            sku_snapshot="BREAD-001",
            ordered_quantity=Decimal("5.000"),
            quantity=Decimal("5.000"),
            unit_price_snapshot=Decimal("40.00"),
            line_total=Decimal("200.00"),
        )
        # 2 units of Milk
        OrderItem.objects.create(
            order=order1,
            product=self.prod1,
            product_name_snapshot="Organic Milk",
            sku_snapshot="MILK-001",
            ordered_quantity=Decimal("2.000"),
            quantity=Decimal("2.000"),
            unit_price_snapshot=Decimal("50.00"),
            line_total=Decimal("100.00"),
        )

        # In-progress order item (MUST NOT be counted in top products)
        order_pending = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.PENDING,
            total_amount=Decimal("900.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=order_pending,
            product=self.prod3,
            product_name_snapshot="Farm Eggs 12pk",
            sku_snapshot="EGGS-001",
            ordered_quantity=Decimal("10.000"),
            quantity=Decimal("10.000"),
            unit_price_snapshot=Decimal("90.00"),
            line_total=Decimal("900.00"),
        )

        # Rename live product to verify snapshot preservation
        self.prod2.name = "Artisan Sourdough Bread"
        self.prod2.save()

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-top-products"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        top_prods = res.data["top_products"]
        self.assertEqual(len(top_prods), 2)

        # First is Bread (5 units)
        self.assertEqual(top_prods[0]["product_id"], self.prod2.id)
        self.assertEqual(top_prods[0]["product_name"], "Whole Wheat Bread")  # Snapshot preserved
        self.assertEqual(top_prods[0]["units_sold"], "5.000")
        self.assertEqual(top_prods[0]["total_revenue"], "200.00")

        # Second is Milk (2 units)
        self.assertEqual(top_prods[1]["product_id"], self.prod1.id)
        self.assertEqual(top_prods[1]["product_name"], "Organic Milk")
        self.assertEqual(top_prods[1]["units_sold"], "2.000")
        self.assertEqual(top_prods[1]["total_revenue"], "100.00")

    def test_customer_metrics_ordering_and_returning(self):
        """
        ordering_customers: distinct customers who completed orders in the period.
        returning_customers: shop customers with >= 2 lifetime completed orders.
        """
        # Customer 1 completes Order 1
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("50.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # Customer 1 completes Order 2 -> Customer 1 is now a RETURNING customer
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("75.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # Customer 2 completes Order 3 -> Customer 2 has 1 completed order (not returning)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("60.00"),
            customer_name_snapshot="Bob",
            customer_phone_snapshot="+919999900002",
        )

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        customers_data = res.data["customers"]
        # Both Alice and Bob completed orders in the period
        self.assertEqual(customers_data["ordering_customers"], 2)
        # Only Alice has >= 2 completed orders
        self.assertEqual(customers_data["returning_customers"], 1)

    def test_low_stock_endpoint_returns_only_out_of_stock_items(self):
        """Low stock returns items with available_quantity <= 0.000."""
        # prod1, prod2, prod3 started with 0 stock
        # Add stock to prod1 so it is in stock
        inv1 = InventoryItem.objects.get(shop=self.shop1, product=self.prod1)
        inv1.quantity = Decimal("10.000")
        inv1.save()

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-low-stock"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        # prod2 and prod3 are out of stock
        self.assertEqual(data["out_of_stock_items_count"], 2)
        product_ids = [item["product_id"] for item in data["items"]]
        self.assertNotIn(self.prod1.id, product_ids)
        self.assertIn(self.prod2.id, product_ids)
        self.assertIn(self.prod3.id, product_ids)


class MerchantAnalyticsDateRangeFilteringTests(AnalyticsBaseTestCase):
    def test_custom_period_filtering(self):
        """Custom date filtering evaluates inclusive start and end dates."""
        today = timezone.now().date()
        past_date = today - timedelta(days=5)

        # Order created today (Completed 100.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("100.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )

        # Order created in the past (Completed 200.00)
        past_order = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("200.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # Backdate created_at directly
        Order.objects.filter(id=past_order.id).update(
            created_at=datetime.combine(past_date, datetime.min.time(), tzinfo=dt_timezone.utc)
        )

        self.client.force_authenticate(user=self.user1)

        # Query period=today (only today's order)
        res_today = self.client.get(reverse("analytics:merchant-analytics-overview"), {"period": "today"})
        self.assertEqual(res_today.status_code, status.HTTP_200_OK)
        self.assertEqual(res_today.data["orders"]["total_orders"], 1)
        self.assertEqual(res_today.data["sales"]["realized_sales"], "100.00")

        # Query custom range covering past_date only
        res_past = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "period": "custom",
            "start_date": past_date.isoformat(),
            "end_date": past_date.isoformat(),
        })
        self.assertEqual(res_past.status_code, status.HTTP_200_OK)
        self.assertEqual(res_past.data["orders"]["total_orders"], 1)
        self.assertEqual(res_past.data["sales"]["realized_sales"], "200.00")

        # Query custom range covering both dates
        res_both = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "period": "custom",
            "start_date": past_date.isoformat(),
            "end_date": today.isoformat(),
        })
        self.assertEqual(res_both.status_code, status.HTTP_200_OK)
        self.assertEqual(res_both.data["orders"]["total_orders"], 2)
        self.assertEqual(res_both.data["sales"]["realized_sales"], "300.00")

    def test_custom_period_validation_errors(self):
        """Invalid query parameters return 400 Bad Request."""
        self.client.force_authenticate(user=self.user1)

        # Missing end_date
        res = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "period": "custom",
            "start_date": "2026-10-01",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # start_date > end_date
        res = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "period": "custom",
            "start_date": "2026-10-20",
            "end_date": "2026-10-10",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid date format
        res = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "period": "custom",
            "start_date": "not-a-date",
            "end_date": "2026-10-20",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Unsupported period name
        res = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "period": "last_century",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class MerchantAnalyticsEndpointsAliasTests(AnalyticsBaseTestCase):
    def test_shops_me_analytics_alias_routes_work_identically(self):
        """Verify that /api/v1/shops/me/analytics/ routes return the exact same analytics data."""
        self.client.force_authenticate(user=self.user1)

        res_direct = self.client.get("/api/v1/analytics/")
        res_alias = self.client.get("/api/v1/shops/me/analytics/")
        self.assertEqual(res_direct.status_code, status.HTTP_200_OK)
        self.assertEqual(res_alias.status_code, status.HTTP_200_OK)
        self.assertEqual(res_direct.data, res_alias.data)

        res_top_direct = self.client.get("/api/v1/analytics/top-products/")
        res_top_alias = self.client.get("/api/v1/shops/me/analytics/top-products/")
        self.assertEqual(res_top_direct.status_code, status.HTTP_200_OK)
        self.assertEqual(res_top_alias.status_code, status.HTTP_200_OK)
        self.assertEqual(res_top_direct.data, res_top_alias.data)

        res_low_direct = self.client.get("/api/v1/analytics/low-stock/")
        res_low_alias = self.client.get("/api/v1/shops/me/analytics/low-stock/")
        self.assertEqual(res_low_direct.status_code, status.HTTP_200_OK)
        self.assertEqual(res_low_alias.status_code, status.HTTP_200_OK)
        self.assertEqual(res_low_direct.data, res_low_alias.data)


class PlatformAnalyticsAuthenticationAndAuthorizationTests(AnalyticsBaseTestCase):
    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must be rejected with 401."""
        urls = [
            reverse("analytics:platform-analytics-overview"),
            reverse("analytics:platform-analytics-overview-alias"),
            reverse("analytics:platform-analytics-top-products"),
            reverse("analytics:platform-analytics-top-shops"),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_merchant_forbidden_from_platform_analytics(self):
        """Active merchants are forbidden from platform-level analytics (403)."""
        self.client.force_authenticate(user=self.user1)
        urls = [
            reverse("analytics:platform-analytics-overview"),
            reverse("analytics:platform-analytics-top-products"),
            reverse("analytics:platform-analytics-top-shops"),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_super_admin_rejected_from_platform_analytics(self):
        """Inactive super admin is rejected."""
        inactive_admin = User.objects.create_user(
            username="inactive_admin",
            email="inactive_admin@example.com",
            password="testpassword123",
            role=User.Role.SUPER_ADMIN,
            mobile_number="+919999988888",
            is_active=False,
        )
        self.client.force_authenticate(user=inactive_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"))
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_super_admin_authorized_for_platform_analytics(self):
        """Super Admin user is authorized and receives 200 OK."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class PlatformAnalyticsCrossShopAggregationTests(AnalyticsBaseTestCase):
    def setUp(self):
        super().setUp()

        # Give stock to prod2 and prod3 so only prod1 in shop1 is out of stock
        inv_prod2 = InventoryItem.objects.get(shop=self.shop1, product=self.prod2)
        inv_prod2.quantity = Decimal("10.000")
        inv_prod2.save()

        inv_prod3 = InventoryItem.objects.get(shop=self.shop1, product=self.prod3)
        inv_prod3.quantity = Decimal("10.000")
        inv_prod3.save()

        # In Shop 2, give prod_shop2 0 stock (out of stock)
        inv_shop2 = InventoryItem.objects.get(shop=self.shop2, product=self.prod_shop2)
        inv_shop2.quantity = Decimal("0.000")
        inv_shop2.save()

        # Shop 1: Completed Order (100.00)
        self.order_s1_comp = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("100.00"),
            items_subtotal=Decimal("100.00"),
            customer_name_snapshot="Alice Customer",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=self.order_s1_comp,
            product=self.prod1,
            product_name_snapshot="Organic Milk",
            sku_snapshot="MILK-001",
            ordered_quantity=Decimal("2.000"),
            quantity=Decimal("2.000"),
            unit_price_snapshot=Decimal("50.00"),
            line_total=Decimal("100.00"),
        )

        # Shop 1: Pending Order (50.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer2,
            status=Order.Status.PENDING,
            total_amount=Decimal("50.00"),
            customer_name_snapshot="Bob Customer",
            customer_phone_snapshot="+919999900002",
        )

        # Shop 2: Completed Order (300.00)
        self.order_s2_comp = Order.objects.create(
            shop=self.shop2,
            customer=self.customer_shop2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("300.00"),
            items_subtotal=Decimal("300.00"),
            customer_name_snapshot="Alice Shop2",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=self.order_s2_comp,
            product=self.prod_shop2,
            product_name_snapshot="Shop2 Exotic Tea",
            sku_snapshot="TEA-002",
            ordered_quantity=Decimal("3.000"),
            quantity=Decimal("3.000"),
            unit_price_snapshot=Decimal("100.00"),
            line_total=Decimal("300.00"),
        )

        # Shop 2: Rejected Order (80.00)
        Order.objects.create(
            shop=self.shop2,
            customer=self.customer_shop2,
            status=Order.Status.REJECTED,
            total_amount=Decimal("80.00"),
            customer_name_snapshot="Alice Shop2",
            customer_phone_snapshot="+919999900001",
        )

    def test_platform_overview_aggregates_across_all_shops(self):
        """Platform overview aggregates metrics across all registered shops."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data

        # Shops metrics
        self.assertEqual(data["shops"]["total_shops"], 2)
        self.assertEqual(data["shops"]["active_shops"], 2)
        self.assertEqual(data["shops"]["deactivated_shops"], 0)

        # Orders metrics
        orders = data["orders"]
        self.assertEqual(orders["total_orders"], 4)
        self.assertEqual(orders["completed_orders"], 2)
        self.assertEqual(orders["rejected_orders"], 1)
        self.assertEqual(orders["status_distribution"]["PENDING"], 1)
        self.assertEqual(orders["status_distribution"]["COMPLETED"], 2)
        self.assertEqual(orders["status_distribution"]["REJECTED"], 1)

        # Sales metrics: 100.00 + 300.00 = 400.00
        sales = data["sales"]
        self.assertEqual(sales["realized_sales"], "400.00")
        self.assertEqual(sales["average_order_value"], "200.00")  # 400 / 2

        # Customers metrics: 2 distinct ordering customers
        self.assertEqual(data["customers"]["ordering_customers"], 2)

        # Inventory metrics: 2 items out of stock across platform (prod1 in shop1, prod_shop2 in shop2)
        self.assertEqual(data["inventory"]["out_of_stock_items_count"], 2)

        # Top products: includes products from both shops
        top_prods = data["top_products"]
        self.assertEqual(len(top_prods), 2)
        # 1st is Tea (3.000 units), 2nd is Milk (2.000 units)
        self.assertEqual(top_prods[0]["product_id"], self.prod_shop2.id)
        self.assertEqual(top_prods[0]["units_sold"], "3.000")
        self.assertEqual(top_prods[1]["product_id"], self.prod1.id)
        self.assertEqual(top_prods[1]["units_sold"], "2.000")

        # Top shops: Shop 2 (300.00) first, Shop 1 (100.00) second
        top_shops = data["top_shops"]
        self.assertEqual(len(top_shops), 2)
        self.assertEqual(top_shops[0]["shop_id"], self.shop2.id)
        self.assertEqual(top_shops[0]["realized_sales"], "300.00")
        self.assertEqual(top_shops[1]["shop_id"], self.shop1.id)
        self.assertEqual(top_shops[1]["realized_sales"], "100.00")

    def test_platform_analytics_preserves_customer_privacy(self):
        """Platform analytics payloads strictly omit customer PII."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        response_str = str(res.data)
        # Verify no customer names or WhatsApp numbers leak into platform analytics
        self.assertNotIn("Alice Customer", response_str)
        self.assertNotIn("Bob Customer", response_str)
        self.assertNotIn("+919999900001", response_str)
        self.assertNotIn("+919999900002", response_str)


class PlatformAnalyticsShopFilteringTests(AnalyticsBaseTestCase):
    def setUp(self):
        super().setUp()

        # Shop 1 completed order (150.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("150.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )

        # Shop 2 completed order (350.00)
        Order.objects.create(
            shop=self.shop2,
            customer=self.customer_shop2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("350.00"),
            customer_name_snapshot="Alice Shop2",
            customer_phone_snapshot="+919999900001",
        )

    def test_super_admin_can_filter_platform_analytics_by_shop_id(self):
        """Super Admin can provide shop_id to scope platform overview to a specific shop."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"), {
            "shop_id": self.shop1.id,
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data.get("filtered_shop_id"), self.shop1.id)
        self.assertEqual(data["shops"]["total_shops"], 1)
        self.assertEqual(data["orders"]["total_orders"], 1)
        self.assertEqual(data["orders"]["completed_orders"], 1)
        self.assertEqual(data["sales"]["realized_sales"], "150.00")
        self.assertEqual(data["sales"]["average_order_value"], "150.00")

    def test_filtering_by_non_existent_shop_id_returns_404(self):
        """Filtering by a non-existent shop_id returns 404."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"), {
            "shop_id": 999999,
        })
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data.get("code"), "SHOP_NOT_FOUND")

    def test_filtering_by_invalid_shop_id_returns_400(self):
        """Filtering by an invalid shop_id format returns 400."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"), {
            "shop_id": "invalid-id",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class PlatformAnalyticsTopProductsAndShopsEndpointTests(AnalyticsBaseTestCase):
    def setUp(self):
        super().setUp()

        order1 = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("200.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=order1,
            product=self.prod1,
            product_name_snapshot="Organic Milk",
            sku_snapshot="MILK-001",
            ordered_quantity=Decimal("4.000"),
            quantity=Decimal("4.000"),
            unit_price_snapshot=Decimal("50.00"),
            line_total=Decimal("200.00"),
        )

        order2 = Order.objects.create(
            shop=self.shop2,
            customer=self.customer_shop2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("600.00"),
            customer_name_snapshot="Alice Shop2",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=order2,
            product=self.prod_shop2,
            product_name_snapshot="Shop2 Exotic Tea",
            sku_snapshot="TEA-002",
            ordered_quantity=Decimal("6.000"),
            quantity=Decimal("6.000"),
            unit_price_snapshot=Decimal("100.00"),
            line_total=Decimal("600.00"),
        )

    def test_platform_top_products_endpoint(self):
        """Top products endpoint aggregates across all shops with limit support."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-top-products"), {"limit": 1})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        top_prods = res.data["top_products"]
        self.assertEqual(len(top_prods), 1)
        self.assertEqual(top_prods[0]["product_id"], self.prod_shop2.id)
        self.assertEqual(top_prods[0]["units_sold"], "6.000")

    def test_platform_top_shops_endpoint(self):
        """Top shops endpoint ranks shops by realized sales on completed orders."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-top-shops"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        top_shops = res.data["top_shops"]
        self.assertEqual(len(top_shops), 2)
        self.assertEqual(top_shops[0]["shop_id"], self.shop2.id)
        self.assertEqual(top_shops[0]["realized_sales"], "600.00")
        self.assertEqual(top_shops[1]["shop_id"], self.shop1.id)
        self.assertEqual(top_shops[1]["realized_sales"], "200.00")


class PlatformAnalyticsZeroBaselineTests(AnalyticsBaseTestCase):
    def test_zero_orders_baseline_evaluates_cleanly(self):
        """When platform has zero orders, overview evaluates cleanly with 0.00 values."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["orders"]["total_orders"], 0)
        self.assertEqual(data["orders"]["completed_orders"], 0)
        self.assertEqual(data["sales"]["realized_sales"], "0.00")
        self.assertEqual(data["sales"]["average_order_value"], "0.00")
        self.assertEqual(data["customers"]["ordering_customers"], 0)
        self.assertEqual(data["top_products"], [])
        self.assertEqual(data["top_shops"], [])


class AnalyticsQueryEfficiencyAndIndexTests(AnalyticsBaseTestCase):
    def setUp(self):
        super().setUp()
        # Create completed orders in Shop 1
        for i in range(3):
            order = Order.objects.create(
                shop=self.shop1,
                customer=self.customer1,
                status=Order.Status.COMPLETED,
                payment_status=Order.PaymentStatus.PAID,
                total_amount=Decimal("100.00"),
                customer_name_snapshot="Alice",
                customer_phone_snapshot="+919999900001",
            )
            OrderItem.objects.create(
                order=order,
                product=self.prod1,
                product_name_snapshot="Organic Milk",
                sku_snapshot="MILK-001",
                ordered_quantity=Decimal("1.000"),
                quantity=Decimal("1.000"),
                unit_price_snapshot=Decimal("100.00"),
                line_total=Decimal("100.00"),
            )

    def test_merchant_overview_bounded_query_efficiency(self):
        """Merchant overview executes within a fixed, small number of queries with no N+1."""
        self.client.force_authenticate(user=self.user1)
        # Expected queries:
        # 1. Shop lookup
        # 2. Orders & ordering_customers combined aggregate
        # 3. Returning customers count
        # 4. Top products values + annotate
        # 5. Out of stock inventory count
        with self.assertNumQueries(5):
            res = self.client.get(reverse("analytics:merchant-analytics-overview"))
            self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_platform_overview_bounded_query_efficiency(self):
        """Platform overview executes within a fixed, small number of queries with no N+1."""
        self.client.force_authenticate(user=self.super_admin)
        # Expected queries:
        # 1. Total shops count
        # 2. Active shops count
        # 3. Deactivated shops count
        # 4. Orders & ordering_customers combined aggregate
        # 5. Top products values + annotate
        # 6. Top shops values + annotate
        # 7. Platform out-of-stock count
        with self.assertNumQueries(7):
            res = self.client.get(reverse("analytics:platform-analytics-overview"))
            self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_merchant_low_stock_single_query_efficiency(self):
        """Low stock list executes exactly 1 query joining product and variant."""
        self.client.force_authenticate(user=self.user1)
        # 1 query for shop lookup, 1 query for low_stock_items with select_related
        with self.assertNumQueries(2):
            res = self.client.get(reverse("analytics:merchant-analytics-low-stock"))
            self.assertEqual(res.status_code, status.HTTP_200_OK)


class AnalyticsControlledFixtureSetup(AnalyticsBaseTestCase):
    """
    Sets up 3 controlled shops with multi-tenant inventory, products, and customers
    for permutation testing across all scenarios.
    """

    def setUp(self):
        super().setUp()

        # Create Merchant 3 and Shop 3 (Deactivated shop for platform testing)
        self.user3 = User.objects.create_user(
            username="merchant_three",
            email="merchant_three@example.com",
            password="testpassword123",
            role=User.Role.MERCHANT,
            mobile_number="+919876543212",
        )
        self.merchant3 = Merchant.objects.create(
            user=self.user3,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop3 = Shop.objects.create(
            merchant=self.merchant3,
            name="Shop Three Deactivated",
            address_line="789 Industrial Way",
            area="Suburbs",
            city="Metropolis",
            state="Central",
            pincode="123458",
            contact_number="+919876543212",
            status=Shop.Status.DEACTIVATED,
        )
        self.customer3 = Customer.objects.create(
            shop=self.shop3,
            name="Carol Deactivated Customer",
            whatsapp_number="+919999900003",
        )
        self.prod_shop3 = ShopProduct.objects.create(
            shop=self.shop3,
            name="Shop3 Heritage Apples",
            price=Decimal("120.00"),
            sku="APPLES-003",
        )

        # Set stock for prod2 and prod3 in shop1 so only prod1 starts with 0 stock
        inv2 = InventoryItem.objects.get(shop=self.shop1, product=self.prod2)
        inv2.quantity = Decimal("20.000")
        inv2.save()

        inv3 = InventoryItem.objects.get(shop=self.shop1, product=self.prod3)
        inv3.quantity = Decimal("20.000")
        inv3.save()

        # Set stock for shop2 prod
        inv_s2 = InventoryItem.objects.get(shop=self.shop2, product=self.prod_shop2)
        inv_s2.quantity = Decimal("15.000")
        inv_s2.save()


class AnalyticsOrderLifecycleFormulaTests(AnalyticsControlledFixtureSetup):
    def test_all_order_lifecycle_states_and_formula_inclusions(self):
        """
        Tests order counting and monetary inclusion across all 6 lifecycle states:
        - PENDING, ACCEPTED, PREPARING, READY, COMPLETED, REJECTED.
        - Verifies that realized_sales and average_order_value strictly isolate COMPLETED orders.
        """
        now = timezone.now()

        # 1 PENDING order (50.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.PENDING,
            total_amount=Decimal("50.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # 1 ACCEPTED order (60.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.ACCEPTED,
            total_amount=Decimal("60.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # 1 PREPARING order (70.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.PREPARING,
            total_amount=Decimal("70.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # 1 READY order (80.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.READY,
            total_amount=Decimal("80.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # 2 COMPLETED orders (120.50 + 79.50 = 200.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("120.50"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("79.50"),
            customer_name_snapshot="Bob",
            customer_phone_snapshot="+919999900002",
        )
        # 3 REJECTED orders (simulating customer cancellation, merchant cancellation, and expiry)
        for amount in [Decimal("30.00"), Decimal("40.00"), Decimal("45.00")]:
            Order.objects.create(
                shop=self.shop1,
                customer=self.customer1,
                status=Order.Status.REJECTED,
                total_amount=amount,
                customer_name_snapshot="Alice",
                customer_phone_snapshot="+919999900001",
            )

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        orders = res.data["orders"]
        # Total: 1 PENDING + 1 ACCEPTED + 1 PREPARING + 1 READY + 2 COMPLETED + 3 REJECTED = 9
        self.assertEqual(orders["total_orders"], 9)
        self.assertEqual(orders["completed_orders"], 2)
        self.assertEqual(orders["rejected_orders"], 3)

        dist = orders["status_distribution"]
        self.assertEqual(dist[Order.Status.PENDING], 1)
        self.assertEqual(dist[Order.Status.ACCEPTED], 1)
        self.assertEqual(dist[Order.Status.PREPARING], 1)
        self.assertEqual(dist[Order.Status.READY], 1)
        self.assertEqual(dist[Order.Status.COMPLETED], 2)
        self.assertEqual(dist[Order.Status.REJECTED], 3)

        # Sales: strictly 120.50 + 79.50 = 200.00
        sales = res.data["sales"]
        self.assertEqual(sales["realized_sales"], "200.00")
        self.assertEqual(sales["average_order_value"], "100.00")  # 200.00 / 2


class AnalyticsDateTimeBoundaryPermutationTests(AnalyticsControlledFixtureSetup):
    def test_utc_inclusive_boundaries_and_preset_permutations(self):
        """
        Tests exact UTC timestamp boundaries:
        - Orders at 00:00:00 and 23:59:59.999999 of today are included.
        - Orders microsecond before/after are excluded from today.
        """
        now = timezone.now()
        today = now.date()

        # Start of today (00:00:00 UTC)
        dt_today_start = datetime.combine(today, datetime.min.time(), tzinfo=dt_timezone.utc)
        o_start = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("100.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        Order.objects.filter(id=o_start.id).update(created_at=dt_today_start)

        # End of today (23:59:59.999999 UTC)
        dt_today_end = datetime.combine(today, datetime.max.time(), tzinfo=dt_timezone.utc)
        o_end = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("150.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        Order.objects.filter(id=o_end.id).update(created_at=dt_today_end)

        # Yesterday 23:59:59 UTC
        yesterday = today - timedelta(days=1)
        dt_yesterday = datetime.combine(yesterday, datetime.max.time(), tzinfo=dt_timezone.utc)
        o_yesterday = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("80.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        Order.objects.filter(id=o_yesterday.id).update(created_at=dt_yesterday)

        # Tomorrow 00:00:00.000001 UTC
        tomorrow = today + timedelta(days=1)
        dt_tomorrow = datetime.combine(tomorrow, datetime.min.time(), tzinfo=dt_timezone.utc)
        o_tomorrow = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("90.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        Order.objects.filter(id=o_tomorrow.id).update(created_at=dt_tomorrow)

        self.client.force_authenticate(user=self.user1)

        # 1. Query period=today (default) -> strictly o_start and o_end
        res_today = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res_today.status_code, status.HTTP_200_OK)
        self.assertEqual(res_today.data["orders"]["total_orders"], 2)
        self.assertEqual(res_today.data["sales"]["realized_sales"], "250.00")  # 100 + 150

        # 2. Query period=yesterday -> strictly o_yesterday
        res_yesterday = self.client.get(reverse("analytics:merchant-analytics-overview"), {"period": "yesterday"})
        self.assertEqual(res_yesterday.status_code, status.HTTP_200_OK)
        self.assertEqual(res_yesterday.data["orders"]["total_orders"], 1)
        self.assertEqual(res_yesterday.data["sales"]["realized_sales"], "80.00")

        # 3. Query custom date range spanning yesterday and today
        res_custom = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "period": "custom",
            "start_date": yesterday.isoformat(),
            "end_date": today.isoformat(),
        })
        self.assertEqual(res_custom.status_code, status.HTTP_200_OK)
        self.assertEqual(res_custom.data["orders"]["total_orders"], 3)  # o_yesterday + o_start + o_end
        self.assertEqual(res_custom.data["sales"]["realized_sales"], "330.00")  # 80 + 100 + 150


class AnalyticsMultiTenantIsolationPermutationTests(AnalyticsControlledFixtureSetup):
    def test_customer_phone_number_collision_remains_strictly_isolated(self):
        """
        Customer phone collision:
        - Customer A in Shop 1: whatsapp_number="+919999900001" (2 completed orders -> returning)
        - Customer B in Shop 2: whatsapp_number="+919999900001" (1 completed order -> not returning)
        Asserts that customer identities and returning status are NEVER merged across shops.
        """
        # Shop 1: Customer 1 places 2 completed orders
        for amt in [Decimal("100.00"), Decimal("150.00")]:
            Order.objects.create(
                shop=self.shop1,
                customer=self.customer1,
                status=Order.Status.COMPLETED,
                payment_status=Order.PaymentStatus.PAID,
                total_amount=amt,
                customer_name_snapshot="Alice Customer",
                customer_phone_snapshot="+919999900001",
            )

        # Shop 2: Customer Shop2 (same phone "+919999900001") places 1 completed order
        Order.objects.create(
            shop=self.shop2,
            customer=self.customer_shop2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("300.00"),
            customer_name_snapshot="Alice Shop2",
            customer_phone_snapshot="+919999900001",
        )

        # Query Shop 1
        self.client.force_authenticate(user=self.user1)
        res_shop1 = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res_shop1.status_code, status.HTTP_200_OK)
        # Shop 1 has 1 ordering customer, 1 returning customer (>= 2 completed orders)
        self.assertEqual(res_shop1.data["customers"]["ordering_customers"], 1)
        self.assertEqual(res_shop1.data["customers"]["returning_customers"], 1)
        self.assertEqual(res_shop1.data["sales"]["realized_sales"], "250.00")

        # Query Shop 2
        self.client.force_authenticate(user=self.user2)
        res_shop2 = self.client.get(reverse("analytics:merchant-analytics-overview"))
        self.assertEqual(res_shop2.status_code, status.HTTP_200_OK)
        # Shop 2 has 1 ordering customer, 0 returning customers (< 2 completed orders in Shop 2)
        self.assertEqual(res_shop2.data["customers"]["ordering_customers"], 1)
        self.assertEqual(res_shop2.data["customers"]["returning_customers"], 0)
        self.assertEqual(res_shop2.data["sales"]["realized_sales"], "300.00")

    def test_parameter_tampering_attempt_ignored(self):
        """Merchant attempting to pass ?shop_id=<shop2.id> receives strictly Shop 1 data."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-overview"), {
            "shop_id": self.shop2.id,
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should not reveal Shop 2 info
        self.assertNotIn("Shop2 Exotic Tea", str(res.data))


class AnalyticsSuperAdminAggregationPermutationTests(AnalyticsControlledFixtureSetup):
    def test_super_admin_aggregates_across_active_and_deactivated_shops(self):
        """
        Super admin platform overview aggregates across Shop 1, Shop 2, and Shop 3.
        Verifies deactivated shops are counted in deactivated_shops and their historical orders contribute.
        """
        # Shop 1 completed order (100.00)
        Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("100.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        # Shop 2 completed order (200.00)
        Order.objects.create(
            shop=self.shop2,
            customer=self.customer_shop2,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("200.00"),
            customer_name_snapshot="Alice Shop2",
            customer_phone_snapshot="+919999900001",
        )
        # Shop 3 (deactivated shop) completed order (300.00)
        Order.objects.create(
            shop=self.shop3,
            customer=self.customer3,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("300.00"),
            customer_name_snapshot="Carol",
            customer_phone_snapshot="+919999900003",
        )

        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get(reverse("analytics:platform-analytics-overview"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        # Shop metrics: 3 total, 2 active, 1 deactivated
        self.assertEqual(data["shops"]["total_shops"], 3)
        self.assertEqual(data["shops"]["active_shops"], 2)
        self.assertEqual(data["shops"]["deactivated_shops"], 1)

        # Orders & Sales: 100 + 200 + 300 = 600.00
        self.assertEqual(data["orders"]["total_orders"], 3)
        self.assertEqual(data["orders"]["completed_orders"], 3)
        self.assertEqual(data["sales"]["realized_sales"], "600.00")
        self.assertEqual(data["sales"]["average_order_value"], "200.00")  # 600 / 3

        # Scoped query for Shop 3
        res_s3 = self.client.get(reverse("analytics:platform-analytics-overview"), {
            "shop_id": self.shop3.id,
        })
        self.assertEqual(res_s3.status_code, status.HTTP_200_OK)
        self.assertEqual(res_s3.data["shops"]["total_shops"], 1)
        self.assertEqual(res_s3.data["shops"]["deactivated_shops"], 1)
        self.assertEqual(res_s3.data["sales"]["realized_sales"], "300.00")


class AnalyticsHistoricalSnapshotImmutabilityTests(AnalyticsControlledFixtureSetup):
    def test_top_products_preserves_historical_snapshots_after_catalog_mutation(self):
        """
        When a catalog product is mutated (renamed, SKU changed, or deleted),
        the top products reporting remains frozen and immutable using OrderItem snapshots.
        """
        order = Order.objects.create(
            shop=self.shop1,
            customer=self.customer1,
            status=Order.Status.COMPLETED,
            payment_status=Order.PaymentStatus.PAID,
            total_amount=Decimal("500.00"),
            customer_name_snapshot="Alice",
            customer_phone_snapshot="+919999900001",
        )
        OrderItem.objects.create(
            order=order,
            product=self.prod1,
            product_name_snapshot="Original Organic Milk 1L",
            sku_snapshot="MILK-ORIG-001",
            ordered_quantity=Decimal("10.000"),
            quantity=Decimal("10.000"),
            unit_price_snapshot=Decimal("50.00"),
            line_total=Decimal("500.00"),
        )

        # Mutate catalog product
        self.prod1.name = "Mutated Skimmed Milk"
        self.prod1.sku = "MUTATED-SKU"
        self.prod1.price = Decimal("999.00")
        self.prod1.save()

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-top-products"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        top_prods = res.data["top_products"]
        self.assertEqual(len(top_prods), 1)
        # Snapshot preserved
        self.assertEqual(top_prods[0]["product_name"], "Original Organic Milk 1L")
        self.assertEqual(top_prods[0]["sku"], "MILK-ORIG-001")
        self.assertEqual(top_prods[0]["units_sold"], "10.000")
        self.assertEqual(top_prods[0]["total_revenue"], "500.00")


class AnalyticsInventoryOutOfStockPermutationTests(AnalyticsControlledFixtureSetup):
    def test_out_of_stock_permutations_and_zero_threshold_adherence(self):
        """
        Permutations for low-stock / out-of-stock evaluation:
        - quantity=0, reserved=0 -> available=0 (OUT OF STOCK)
        - quantity=5, reserved=5 -> available=0 (OUT OF STOCK via reservation)
        - quantity=5, reserved=4 -> available=1 (IN STOCK)
        - quantity=1, reserved=0 -> available=1 (IN STOCK, verifies no arbitrary threshold like < 5)
        """
        # Item 1: Exact 0 stock (prod1)
        inv1 = InventoryItem.objects.get(shop=self.shop1, product=self.prod1)
        inv1.quantity = Decimal("0.000")
        inv1.reserved_quantity = Decimal("0.000")
        inv1.save()

        # Item 2: Fully reserved stock (prod2)
        inv2 = InventoryItem.objects.get(shop=self.shop1, product=self.prod2)
        inv2.quantity = Decimal("5.000")
        inv2.reserved_quantity = Decimal("5.000")
        inv2.save()

        # Item 3: Available stock = 1 (prod3) -> MUST NOT be in out-of-stock list
        inv3 = InventoryItem.objects.get(shop=self.shop1, product=self.prod3)
        inv3.quantity = Decimal("1.000")
        inv3.reserved_quantity = Decimal("0.000")
        inv3.save()

        self.client.force_authenticate(user=self.user1)
        res = self.client.get(reverse("analytics:merchant-analytics-low-stock"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["out_of_stock_items_count"], 2)
        out_of_stock_pids = [item["product_id"] for item in data["items"]]
        self.assertIn(self.prod1.id, out_of_stock_pids)
        self.assertIn(self.prod2.id, out_of_stock_pids)
        # prod3 with available=1 is NOT included
        self.assertNotIn(self.prod3.id, out_of_stock_pids)



