"""GP-QA-3: checkout must stay cheap in database round trips.

Against a remote database every query costs a network round trip, so the number of
queries a checkout makes is its latency. These tests pin that budget and the
behavior the optimisations must preserve.
"""

from decimal import Decimal

from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from cart.models import CartItem
from notifications.models import NotificationOutbox
from orders.models import Order
from orders.test_lifecycle import OrderLifecycleAPITests

# Measured at 33 for a one-item checkout (it was ~126 before GP-QA-3). Leave headroom
# for small additions, but fail loudly if per-model constraint validation comes back.
SINGLE_ITEM_QUERY_BUDGET = 40


class CheckoutQueryBudgetTests(TestCase):
    setUp = OrderLifecycleAPITests.setUp
    checkout_payload = OrderLifecycleAPITests.checkout_payload
    checkout = OrderLifecycleAPITests.checkout

    def test_single_item_checkout_stays_within_query_budget(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.checkout(key="budget-1")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertLessEqual(len(ctx), SINGLE_ITEM_QUERY_BUDGET, [q["sql"][:80] for q in ctx.captured_queries])
        constraint_checks = [q for q in ctx.captured_queries if q["sql"].startswith('SELECT 1 AS "_check"')]
        self.assertEqual(constraint_checks, [], "model save() must not validate constraints via queries")

    def test_extra_cart_lines_do_not_multiply_queries_per_constraint(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, product=self.variant_product, quantity=Decimal("2.000"))

        with CaptureQueriesContext(connection) as ctx:
            response = self.checkout(key="budget-2")

        self.assertEqual(response.status_code, 201, response.data)
        # A second line adds only its own reads/locks/writes, not a constraint-check fan-out.
        self.assertLessEqual(len(ctx), SINGLE_ITEM_QUERY_BUDGET + 12)


class CheckoutTotalsAndItemsTests(TestCase):
    setUp = OrderLifecycleAPITests.setUp
    checkout_payload = OrderLifecycleAPITests.checkout_payload
    checkout = OrderLifecycleAPITests.checkout

    def test_totals_items_and_notification_match_for_multi_line_home_delivery(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, product=self.variant_product, quantity=Decimal("2.000"))
        payload = self.checkout_payload(
            fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
            delivery_address={
                "address_line": "12 Park Street",
                "area": "Central",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001",
            },
        )

        response = self.checkout(payload, key="totals-1")

        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])
        # 3 x 10.00 + 2 x 30.00 = 90.00 items, plus the 25.00 fixed delivery charge.
        self.assertEqual(order.items_subtotal, Decimal("90.00"))
        self.assertEqual(order.total_amount, Decimal("115.00"))
        self.assertEqual(response.data["items_subtotal"], "90.00")
        self.assertEqual(response.data["total_amount"], "115.00")
        self.assertEqual(order.items.count(), 2)
        self.assertEqual([i["line_total"] for i in response.data["items"]], ["30.00", "60.00"])
        self.assertEqual(response.data["delivery_address"]["address_line"], "12 Park Street")
        self.assertEqual(response.data["whatsapp_notification_links"] is not None, True)
        outbox = NotificationOutbox.objects.get(order_id=order.pk)
        self.assertEqual(outbox.template_context["item_count"], 2)
        self.assertEqual(outbox.template_context["total_amount"], "115.00")
        self.assertFalse(self.cart.items.exists())

    def test_stock_is_reserved_for_every_line(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, product=self.variant_product, quantity=Decimal("2.000"))

        self.assertEqual(self.checkout(key="stock-1").status_code, 201)

        self.stock.refresh_from_db()
        self.variant_stock.refresh_from_db()
        self.assertEqual(self.stock.reserved_quantity, Decimal("3.000"))
        self.assertEqual(self.variant_stock.reserved_quantity, Decimal("2.000"))


class DatabaseStillEnforcesConstraintsTests(TestCase):
    """Skipping Python-side constraint validation must not weaken data integrity."""

    setUp = OrderLifecycleAPITests.setUp

    def test_inventory_cannot_reserve_more_than_on_hand(self):
        self.stock.reserved_quantity = self.stock.quantity + Decimal("1.000")

        with self.assertRaises(Exception):
            with transaction.atomic():
                self.stock.save()

    def test_negative_order_amount_is_rejected_by_the_database(self):
        order = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            customer_name_snapshot="X",
            customer_phone_snapshot="+919123450001",
            items_subtotal=Decimal("0.00"),
            total_amount=Decimal("0.00"),
        )
        order.total_amount = Decimal("-5.00")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                order.save()
