from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from analytics.services import get_merchant_analytics_overview
from catalog.models import ShopCategory, ShopProduct
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderDeliveryAddress, OrderItem
from shops.models import Shop
from users.models import Merchant, User


class SeedMerchantDemoCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="demo_seed_merchant",
            email="demo-seed-merchant@example.test",
            mobile_number="+919876543201",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Seed Test Shop",
            address_line="1 Market Road",
            area="Central",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=self.user.mobile_number,
        )

    def run_seed(self):
        call_command("seed_merchant_demo", username=self.user.username, verbosity=0)

    def test_seed_is_repeatable_and_preserves_unrelated_shop_data(self):
        unrelated = ShopProduct.objects.create(
            shop=self.shop,
            sku="MY-REAL-SKU",
            name="My existing product",
            price=Decimal("100.00"),
        )

        self.run_seed()
        first_product_ids = list(
            ShopProduct.objects.filter(shop=self.shop, sku__startswith="DEMO-SEED-")
            .order_by("sku")
            .values_list("id", flat=True)
        )
        self.run_seed()

        self.assertEqual(len(first_product_ids), 6)
        self.assertEqual(
            list(
                ShopProduct.objects.filter(shop=self.shop, sku__startswith="DEMO-SEED-")
                .order_by("sku")
                .values_list("id", flat=True)
            ),
            first_product_ids,
        )
        self.assertEqual(ShopProduct.objects.get(pk=unrelated.pk).name, "My existing product")
        self.assertEqual(ShopCategory.objects.filter(shop=self.shop, slug__startswith="demo-seed-").count(), 2)
        self.assertEqual(Customer.objects.filter(shop=self.shop, name__startswith="DEMO-SEED ").count(), 6)

        seeded_orders = Order.objects.filter(shop=self.shop, idempotency_key__startswith="demo-seed:")
        self.assertEqual(seeded_orders.count(), 6)
        self.assertSetEqual(set(seeded_orders.values_list("status", flat=True)), set(Order.Status.values))
        self.assertEqual(OrderItem.objects.filter(order__in=seeded_orders).count(), 6)
        self.assertEqual(OrderDeliveryAddress.objects.filter(order__in=seeded_orders).count(), 3)
        overview = get_merchant_analytics_overview(self.shop.id, {"period": "today"})
        self.assertEqual(overview["orders"]["total_orders"], 6)
        self.assertEqual(overview["orders"]["completed_orders"], 1)
        self.assertGreater(Decimal(overview["sales"]["realized_sales"]), Decimal("0.00"))
        self.assertTrue(overview["top_products"])
        self.assertTrue(
            InventoryItem.objects.filter(shop=self.shop, product__sku="DEMO-SEED-BANANA-001", quantity=0).exists()
        )
        pending = seeded_orders.get(status=Order.Status.PENDING)
        pending_item = pending.items.get()
        pending_stock = InventoryItem.objects.get(product=pending_item.product, variant=None)
        self.assertEqual(pending_stock.reserved_quantity, pending_item.quantity)

    def test_unknown_merchant_returns_clear_command_error(self):
        with self.assertRaisesMessage(CommandError, "No merchant account found"):
            call_command("seed_merchant_demo", username="missing-demo-merchant", verbosity=0)

    def test_inactive_merchant_is_rejected(self):
        self.merchant.status = Merchant.Status.DEACTIVATED
        self.merchant.save(update_fields=["status"])
        with self.assertRaisesMessage(CommandError, "is not active"):
            self.run_seed()
        self.assertFalse(ShopProduct.objects.filter(shop=self.shop, sku__startswith="DEMO-SEED-").exists())

    def test_merchant_without_shop_is_rejected(self):
        self.shop.delete()
        with self.assertRaisesMessage(CommandError, "does not have a shop yet"):
            self.run_seed()

    def test_order_seed_preserves_shop_tenant_relationships(self):
        self.run_seed()
        for order in Order.objects.filter(shop=self.shop, idempotency_key__startswith="demo-seed:"):
            self.assertEqual(order.customer.shop_id, self.shop.id)
            self.assertEqual(order.payment_status == Order.PaymentStatus.PAID, order.status == Order.Status.COMPLETED)
            if order.fulfillment_type == Order.FulfillmentType.HOME_DELIVERY:
                self.assertTrue(hasattr(order, "delivery_address"))
            else:
                self.assertFalse(OrderDeliveryAddress.objects.filter(order=order).exists())

    def test_seeded_products_are_listed_by_public_storefront_endpoint(self):
        self.run_seed()
        response = APIClient().get(f"/api/v1/shops/public/{self.shop.public_slug}/products/")
        self.assertEqual(response.status_code, 200)
        names = {item["name"] for item in response.data}
        self.assertIn("DEMO-SEED Kashmiri Apples", names)
        self.assertIn("DEMO-SEED Robusta Bananas", names)
        self.assertNotIn("DEMO-SEED Dish Soap", names)
