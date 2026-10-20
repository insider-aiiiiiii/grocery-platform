from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from catalog.models import MasterCategory, ProductVariant, ShopProduct
from customers.models import Customer
from orders.models import Order, OrderDeliveryAddress, OrderItem
from shops.models import Shop
from users.models import Merchant, User


class OrderModelTests(TestCase):
    """Unit and domain model tests for Order, OrderItem, and OrderDeliveryAddress."""

    def setUp(self):
        # Create merchant and active shop
        self.user = User.objects.create_user(
            username="merchant_order",
            email="merchant_order@test.com",
            mobile_number="+919876543210",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Fresh Corner Grocery",
            address_line="123 Market St",
            area="Koramangala",
            city="Bengaluru",
            state="Karnataka",
            pincode="560034",
            contact_number="+919876543210",
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("40.00"),
        )

        # Create another shop for multi-tenancy isolation tests
        self.other_user = User.objects.create_user(
            username="other_merchant",
            email="other_merchant@test.com",
            mobile_number="+919876543211",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.other_merchant = Merchant.objects.create(
            user=self.other_user,
        )
        self.other_shop = Shop.objects.create(
            merchant=self.other_merchant,
            name="Other Grocery",
            address_line="456 Other St",
            area="Indiranagar",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
            contact_number="+919876543211",
        )

        # Create customer for shop
        self.customer = Customer.objects.create(
            shop=self.shop,
            name="Rahul Sharma",
            whatsapp_number="+919123456789",
        )

        # Create catalog category and products
        self.category = MasterCategory.objects.create(name="Staples")
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Aashirvaad Atta",
            sku="ATT-001",
            price=Decimal("250.00"),
        )
        self.variant_product = ShopProduct.objects.create(
            shop=self.shop,
            name="Fortune Sunlite Oil",
        )
        self.variant = ProductVariant.objects.create(
            product=self.variant_product,
            name="1 Liter Pouch",
            sku="OIL-1L",
            price=Decimal("140.00"),
        )

    def create_order(self, **kwargs):
        kwargs.setdefault("fulfillment_type", Order.FulfillmentType.PICKUP)
        return Order.objects.create(**kwargs)

    def test_order_creation_with_snapshots(self):
        """Order successfully stores checkout-time customer, delivery, and financial snapshots."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
            delivery_fee_type_snapshot=Order.DeliveryFeeType.FIXED,
            delivery_charge_snapshot=Decimal("40.00"),
            items_subtotal=Decimal("390.00"),
            total_amount=Decimal("430.00"),
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_status, Order.PaymentStatus.UNPAID)
        self.assertEqual(order.customer_name_snapshot, "Rahul Sharma")
        self.assertEqual(order.customer_phone_snapshot, "+919123456789")
        self.assertEqual(order.delivery_charge_snapshot, Decimal("40.00"))
        self.assertEqual(order.items_subtotal, Decimal("390.00"))
        self.assertEqual(order.total_amount, Decimal("430.00"))
        self.assertTrue(order.is_pending)
        self.assertTrue(order.is_unpaid)
        self.assertTrue(order.is_home_delivery)
        self.assertFalse(order.is_expired)
        self.assertTrue(order.can_customer_cancel)
        OrderDeliveryAddress.objects.create(
            order=order,
            recipient_name="Rahul Sharma",
            recipient_phone="+919123456789",
            address_line="123 Market St",
            area="Koramangala",
            city="Bengaluru",
            state="Karnataka",
            pincode="560034",
        )

    def test_order_item_creation_and_frozen_snapshots(self):
        """Order item stores frozen catalog snapshots; later product edits do not affect it."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
        )

        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="Aashirvaad Atta",
            sku_snapshot="ATT-001",
            unit_snapshot="kg",
            ordered_quantity=Decimal("2.000"),
            quantity=Decimal("2.000"),
            unit_price_snapshot=Decimal("250.00"),
        )

        self.assertEqual(item.line_total, Decimal("500.00"))

        # Later modification of live catalog product
        self.product.name = "Aashirvaad Shudh Chakki Atta"
        self.product.price = Decimal("295.00")
        self.product.sku = "ATT-NEW-99"
        self.product.save()

        # Reload order item from database
        item.refresh_from_db()
        self.assertEqual(item.product_name_snapshot, "Aashirvaad Atta")
        self.assertEqual(item.unit_price_snapshot, Decimal("250.00"))
        self.assertEqual(item.sku_snapshot, "ATT-001")
        self.assertEqual(item.line_total, Decimal("500.00"))

    def test_home_delivery_address_snapshot(self):
        """Home delivery order requires and creates an immutable delivery address snapshot."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
        )

        address = OrderDeliveryAddress.objects.create(
            order=order,
            recipient_name="Rahul S",
            recipient_phone="+919123456789",
            address_line="Flat 402, Green Glen Layout",
            area="Bellandur",
            city="Bengaluru",
            state="Karnataka",
            pincode="560103",
            landmark="Near EcoSpace",
            delivery_notes="Leave at security desk",
        )

        self.assertEqual(order.delivery_address.pincode, "560103")
        self.assertEqual(address.city, "Bengaluru")

    def test_pickup_order_rejects_delivery_address(self):
        """Pickup orders must not have a delivery address."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            fulfillment_type=Order.FulfillmentType.PICKUP,
        )

        with self.assertRaises(ValidationError):
            OrderDeliveryAddress.objects.create(
                order=order,
                recipient_name="Rahul S",
                recipient_phone="+919123456789",
                address_line="123 Street",
                area="Area",
                city="City",
                state="State",
                pincode="123456",
            )

    def test_tenant_boundary_validation_customer_mismatch(self):
        """Order creation rejects customer belonging to a different shop."""
        other_customer = Customer.objects.create(
            shop=self.other_shop,
            name="Pooja Rao",
            whatsapp_number="+919888877777",
        )

        order = Order(
            shop=self.shop,
            customer=other_customer,
            customer_name_snapshot="Pooja Rao",
            customer_phone_snapshot="+919888877777",
        )
        with self.assertRaises(ValidationError) as ctx:
            order.clean()
        self.assertIn("customer", ctx.exception.message_dict)

    def test_tenant_boundary_validation_product_mismatch(self):
        """OrderItem rejects product belonging to a different shop."""
        other_product = ShopProduct.objects.create(
            shop=self.other_shop,
            name="External Milk",
            price=Decimal("30.00"),
        )
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
        )

        item = OrderItem(
            order=order,
            product=other_product,
            product_name_snapshot="External Milk",
            ordered_quantity=Decimal("1.000"),
            quantity=Decimal("1.000"),
            unit_price_snapshot=Decimal("30.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("product", ctx.exception.message_dict)

    def test_completed_order_requires_paid_status(self):
        """An order cannot be marked COMPLETED while UNPAID."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            status=Order.Status.READY,
            payment_status=Order.PaymentStatus.UNPAID,
        )

        # Transitioning to COMPLETED while UNPAID must fail validation
        order.status = Order.Status.COMPLETED
        with self.assertRaises(ValidationError) as ctx:
            order.clean()
        self.assertIn("payment_status", ctx.exception.message_dict)

        # Making it PAID allows COMPLETED
        order.payment_status = Order.PaymentStatus.PAID
        order.clean()  # Should pass without error
        order.save()
        self.assertEqual(order.status, Order.Status.COMPLETED)

    def test_no_cancelled_or_expired_state_in_model_choices(self):
        """Verifies strict invariant: NO CANCELLED or EXPIRED states exist in Order.Status."""
        statuses = [choice[0] for choice in Order.Status.choices]
        self.assertNotIn("CANCELLED", statuses)
        self.assertNotIn("EXPIRED", statuses)
        self.assertIn("REJECTED", statuses)
        self.assertIn("PENDING", statuses)
        self.assertIn("ACCEPTED", statuses)
        self.assertIn("PREPARING", statuses)
        self.assertIn("READY", statuses)
        self.assertIn("COMPLETED", statuses)

    def test_rejection_actor_and_reason_metadata(self):
        """Preserves semantic audit metadata for rejection, customer cancellation, and expiry."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            status=Order.Status.REJECTED,
            rejection_actor=Order.RejectionActor.CUSTOMER,
            rejection_reason_code="CUSTOMER_CANCELLED",
            rejection_note="Ordered by mistake",
            rejected_at=timezone.now(),
        )

        self.assertTrue(order.is_rejected)
        self.assertEqual(order.rejection_actor, "CUSTOMER")
        self.assertEqual(order.rejection_reason_code, "CUSTOMER_CANCELLED")
        self.assertEqual(order.rejection_note, "Ordered by mistake")

    def test_merchant_controlled_partial_quantity_adjustment(self):
        """Merchant reduces fulfillable quantity; recalculate_totals updates subtotal and total."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            fulfillment_type=Order.FulfillmentType.HOME_DELIVERY,
            delivery_charge_snapshot=Decimal("30.00"),
        )
        OrderDeliveryAddress.objects.create(
            order=order,
            recipient_name="Rahul Sharma",
            recipient_phone="+919123456789",
            address_line="123 Market St",
            area="Koramangala",
            city="Bengaluru",
            state="Karnataka",
            pincode="560034",
        )

        item1 = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="Aashirvaad Atta",
            ordered_quantity=Decimal("3.000"),
            quantity=Decimal("3.000"),
            unit_price_snapshot=Decimal("200.00"),
        )
        item2 = OrderItem.objects.create(
            order=order,
            product=self.variant_product,
            variant=self.variant,
            product_name_snapshot="Fortune Sunlite Oil",
            variant_name_snapshot="1 Liter Pouch",
            ordered_quantity=Decimal("2.000"),
            quantity=Decimal("2.000"),
            unit_price_snapshot=Decimal("150.00"),
        )

        order.recalculate_totals(save=True)
        # 3 * 200 = 600, 2 * 150 = 300 -> subtotal = 900; total = 900 + 30 = 930
        self.assertEqual(order.items_subtotal, Decimal("900.00"))
        self.assertEqual(order.total_amount, Decimal("930.00"))

        # Merchant manually reduces Atta from 3.000 to 1.000
        item1.quantity = Decimal("1.000")
        item1.save()
        self.assertEqual(item1.line_total, Decimal("200.00"))

        order.recalculate_totals(save=True)
        # 1 * 200 = 200, 2 * 150 = 300 -> subtotal = 500; total = 500 + 30 = 530
        self.assertEqual(order.items_subtotal, Decimal("500.00"))
        self.assertEqual(order.total_amount, Decimal("530.00"))

    def test_quantity_cannot_exceed_ordered_quantity(self):
        """Item quantity cannot exceed originally ordered quantity."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
        )

        item = OrderItem(
            order=order,
            product=self.product,
            product_name_snapshot="Aashirvaad Atta",
            ordered_quantity=Decimal("2.000"),
            quantity=Decimal("3.000"),
            unit_price_snapshot=Decimal("250.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.clean()
        self.assertIn("quantity", ctx.exception.message_dict)

    def test_catalog_deletion_does_not_delete_order_item(self):
        """Deleting a ShopProduct or ProductVariant sets FK to NULL but preserves OrderItem."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
        )

        item = OrderItem.objects.create(
            order=order,
            product=self.variant_product,
            variant=self.variant,
            product_name_snapshot="Fortune Sunlite Oil",
            variant_name_snapshot="1 Liter Pouch",
            sku_snapshot="OIL-1L",
            unit_snapshot="L",
            ordered_quantity=Decimal("1.000"),
            quantity=Decimal("1.000"),
            unit_price_snapshot=Decimal("140.00"),
        )

        # Delete product variant from catalog
        self.variant.delete()
        item.refresh_from_db()
        self.assertIsNone(item.variant)
        self.assertEqual(item.variant_name_snapshot, "1 Liter Pouch")
        self.assertEqual(item.unit_price_snapshot, Decimal("140.00"))

        # Delete parent product from catalog
        self.variant_product.delete()
        item.refresh_from_db()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name_snapshot, "Fortune Sunlite Oil")
        self.assertEqual(item.line_total, Decimal("140.00"))

    def test_customer_deletion_protected_by_order(self):
        """Deleting a customer with historical orders is protected and raises ProtectedError."""
        self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
        )

        with self.assertRaises(ProtectedError):
            self.customer.delete()

    def test_shop_deletion_cascades_orders(self):
        """Deleting a Shop permanently deletes all its Orders and OrderItems."""
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot="Aashirvaad Atta",
            ordered_quantity=Decimal("1.000"),
            quantity=Decimal("1.000"),
            unit_price_snapshot=Decimal("250.00"),
        )

        order_id = order.id
        self.shop.delete()
        self.assertFalse(Order.objects.filter(id=order_id).exists())
        self.assertFalse(OrderItem.objects.filter(order_id=order_id).exists())

    def test_idempotency_key_uniqueness_per_shop(self):
        """Idempotency key is unique per Shop; different shops can reuse key."""
        self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            idempotency_key="checkout-tok-12345",
        )

        # Same shop with duplicate key must fail unique constraint
        with self.assertRaises((IntegrityError, ValidationError)):
            self.create_order(
                shop=self.shop,
                customer=self.customer,
                customer_name_snapshot="Rahul Sharma",
                customer_phone_snapshot="+919123456789",
                idempotency_key="checkout-tok-12345",
            )

        # Different shop with same key succeeds
        other_customer = Customer.objects.create(
            shop=self.other_shop,
            name="Other Customer",
            whatsapp_number="+919777766666",
        )
        other_order = self.create_order(
            shop=self.other_shop,
            customer=other_customer,
            customer_name_snapshot="Other Customer",
            customer_phone_snapshot="+919777766666",
            idempotency_key="checkout-tok-12345",
        )
        self.assertIsNotNone(other_order.pk)

    def test_expiry_and_cancellation_helpers(self):
        """Tests is_expired, can_customer_cancel, and can_merchant_cancel helper properties."""
        now = timezone.now()
        order = self.create_order(
            shop=self.shop,
            customer=self.customer,
            customer_name_snapshot="Rahul Sharma",
            customer_phone_snapshot="+919123456789",
            status=Order.Status.PENDING,
            expires_at=now + timedelta(minutes=15),
        )

        self.assertFalse(order.is_expired)
        self.assertTrue(order.can_customer_cancel)
        self.assertFalse(order.can_merchant_cancel)

        # Expired order
        order.expires_at = now - timedelta(seconds=1)
        self.assertTrue(order.is_expired)
        self.assertFalse(order.can_customer_cancel)

        # Accepted order
        order.status = Order.Status.ACCEPTED
        order.expires_at = now + timedelta(minutes=15)
        self.assertFalse(order.can_customer_cancel)
        self.assertTrue(order.can_merchant_cancel)

        # Preparing order
        order.status = Order.Status.PREPARING
        self.assertFalse(order.can_customer_cancel)
        self.assertFalse(order.can_merchant_cancel)
