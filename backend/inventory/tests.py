from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from catalog.models import MasterCategory, MasterProduct, ProductVariant, ShopProduct
from shops.models import Shop
from users.models import Merchant, User
from cart.models import Cart, CartItem
from .models import InventoryItem, quantize_quantity
from .services import (
    add_stock,
    adjust_stock,
    deduct_order_acceptance_stock,
    deduct_order_items_stock,
    deduct_order_stock,
    get_product_stock,
    get_variant_stock,
    initialize_product_stock,
    initialize_variant_stock,
    reduce_and_accept_order_items_stock,
    reduce_and_accept_order_stock,
    release_order_items_stock,
    release_order_stock,
    reserve_order_creation_stock,
    reserve_order_items_stock,
    reserve_order_stock,
    restore_cancelled_order_stock,
    restore_order_items_stock,
    set_exact_stock,
    set_stock,
    subtract_stock,
    update_exact_stock,
)



class InventoryBaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
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
        )

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
        )


class InventoryItemModelTests(InventoryBaseTestCase):
    def test_newly_created_product_starts_with_zero_stock(self):
        """A newly created Shop Product automatically initializes with 0.000 stock."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Fresh Apples",
            price=Decimal("120.00"),
        )
        item = InventoryItem.objects.filter(shop=self.shop1, product=product, variant__isnull=True).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, Decimal("0.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))
        self.assertTrue(item.is_out_of_stock)

    def test_newly_created_variant_starts_with_zero_stock_and_replaces_product_level_stock(self):
        """
        When variants are added to a product, variant stock is created with 0.000 stock
        and the obsolete independent product-level balance is removed.
        """
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Basmati Rice",
            price=Decimal("100.00"),
        )
        self.assertTrue(InventoryItem.objects.filter(product=product, variant__isnull=True).exists())

        variant1 = ProductVariant.objects.create(
            product=product,
            name="1 kg",
            price=Decimal("100.00"),
        )
        variant2 = ProductVariant.objects.create(
            product=product,
            name="5 kg",
            price=Decimal("480.00"),
        )

        # Authoritative variant items exist with stock 0.000
        item1 = InventoryItem.objects.filter(variant=variant1).first()
        item2 = InventoryItem.objects.filter(variant=variant2).first()
        self.assertIsNotNone(item1)
        self.assertIsNotNone(item2)
        self.assertEqual(item1.quantity, Decimal("0.000"))
        self.assertEqual(item2.quantity, Decimal("0.000"))

        # Obsolete product-level stock item is removed
        self.assertFalse(InventoryItem.objects.filter(product=product, variant__isnull=True).exists())

    def test_preserve_decimal_quantities(self):
        """Preserves decimal quantities accurately (e.g. 1.250 kg, 0.750 L)."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Loose Potatoes",
            price=Decimal("30.00"),
        )
        item = InventoryItem.objects.get(product=product, variant__isnull=True)
        item.set_quantity(Decimal("15.750"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("15.750"))
        self.assertEqual(item.available_quantity, Decimal("15.750"))

    def test_non_negative_quantity_validation_and_check_constraint(self):
        """Stock quantity cannot become negative."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Carrots",
            price=Decimal("40.00"),
        )
        item = InventoryItem.objects.get(product=product, variant__isnull=True)
        with self.assertRaises(ValidationError):
            item.set_quantity(Decimal("-5.000"))

        with self.assertRaises(ValidationError):
            item.quantity = Decimal("-1.000")
            item.save()

    def test_reserved_quantity_cannot_exceed_total_quantity(self):
        """Reserved stock cannot exceed total on-hand stock."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Oranges",
            price=Decimal("80.00"),
        )
        item = InventoryItem.objects.get(product=product, variant__isnull=True)
        item.set_quantity(Decimal("10.000"))

        with self.assertRaises(ValidationError):
            item.reserve_stock(Decimal("15.000"))

    def test_tenant_boundary_validation(self):
        """Inventory item must belong to the same shop as the product."""
        product2 = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop Two Bananas",
            price=Decimal("50.00"),
        )
        item = InventoryItem(
            shop=self.shop1,  # Shop 1 attempting to manage Shop 2 product
            product=product2,
            quantity=Decimal("10.000"),
        )
        with self.assertRaises(ValidationError) as cm:
            item.save()
        self.assertIn("shop", cm.exception.message_dict)

    def test_variant_must_belong_to_specified_product(self):
        """Variant in inventory item must belong to the specified product."""
        product_a = ShopProduct.objects.create(shop=self.shop1, name="Product A")
        product_b = ShopProduct.objects.create(shop=self.shop1, name="Product B")
        var_a = ProductVariant.objects.create(product=product_a, name="Var A")

        item = InventoryItem(
            shop=self.shop1,
            product=product_b,
            variant=var_a,
            quantity=Decimal("5.000"),
        )
        with self.assertRaises(ValidationError) as cm:
            item.save()
        self.assertIn("variant", cm.exception.message_dict)

    def test_variant_based_product_rejects_independent_product_level_record(self):
        """Direct creation of product-level record for a variant-based product is rejected."""
        product = ShopProduct.objects.create(shop=self.shop1, name="Milk")
        ProductVariant.objects.create(product=product, name="500ml")

        item = InventoryItem(
            shop=self.shop1,
            product=product,
            variant=None,
            quantity=Decimal("20.000"),
        )
        with self.assertRaises(ValidationError) as cm:
            item.save()
        self.assertIn("product", cm.exception.message_dict)

    def test_cascade_delete_on_product_and_variant_removal(self):
        """When a Catalog Product or Variant is removed, its Inventory record is removed with it."""
        product = ShopProduct.objects.create(shop=self.shop1, name="Seasonal Mango")
        var = ProductVariant.objects.create(product=product, name="1 Dozen")

        self.assertTrue(InventoryItem.objects.filter(variant=var).exists())

        # Removing variant removes inventory record
        var_id = var.id
        var.delete()
        self.assertFalse(InventoryItem.objects.filter(variant_id=var_id).exists())

        # Removing product removes all inventory records
        prod_id = product.id
        product.delete()
        self.assertFalse(InventoryItem.objects.filter(product_id=prod_id).exists())


class StockAdjustmentAndOrderFlowTests(InventoryBaseTestCase):
    def setUp(self):
        super().setUp()
        self.product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Sugar",
            price=Decimal("45.00"),
        )
        self.item = InventoryItem.objects.get(product=self.product, variant__isnull=True)

    def test_merchant_add_and_subtract_stock(self):
        """Merchant may add, subtract, and set exact stock."""
        # Set exact stock
        self.item.set_quantity(Decimal("50.000"))
        self.assertEqual(self.item.quantity, Decimal("50.000"))

        # Add stock
        self.item.add_stock(Decimal("25.500"))
        self.assertEqual(self.item.quantity, Decimal("75.500"))

        # Subtract stock
        self.item.subtract_stock(Decimal("10.500"))
        self.assertEqual(self.item.quantity, Decimal("65.000"))

        # Cannot subtract below zero
        with self.assertRaises(ValidationError):
            self.item.subtract_stock(Decimal("100.000"))

    def test_order_lifecycle_stock_flow(self):
        """
        Verifies:
        1. Order Created -> Required Quantity Reserved
        2. Merchant Accepts -> Reserved Quantity Becomes Deducted Stock
        3. Order Rejected -> Reserved Quantity Released
        4. Accepted Order Cancelled -> Deducted Quantity Restored
        """
        self.item.set_quantity(Decimal("100.000"))
        self.assertEqual(self.item.available_quantity, Decimal("100.000"))

        # Step 1: Order Created -> Reserve 20.000 units
        self.item.reserve_stock(Decimal("20.000"))
        self.assertEqual(self.item.quantity, Decimal("100.000"))
        self.assertEqual(self.item.reserved_quantity, Decimal("20.000"))
        self.assertEqual(self.item.available_quantity, Decimal("80.000"))

        # Step 2: Merchant Accepts -> 20.000 reserved becomes deducted stock
        self.item.deduct_reserved_stock(Decimal("20.000"))
        self.assertEqual(self.item.quantity, Decimal("80.000"))
        self.assertEqual(self.item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(self.item.available_quantity, Decimal("80.000"))

        # Step 3: Another Order Created -> Reserve 15.000 units, then Order Rejected -> Released
        self.item.reserve_stock(Decimal("15.000"))
        self.assertEqual(self.item.available_quantity, Decimal("65.000"))
        self.item.release_reserved_stock(Decimal("15.000"))
        self.assertEqual(self.item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(self.item.available_quantity, Decimal("80.000"))

        # Step 4: Accepted Order Cancelled -> Restores deducted quantity (e.g. 20.000)
        self.item.restore_deducted_stock(Decimal("20.000"))
        self.assertEqual(self.item.quantity, Decimal("100.000"))
        self.assertEqual(self.item.available_quantity, Decimal("100.000"))


class InventoryServiceTests(InventoryBaseTestCase):
    def test_non_variant_product_stock_service(self):
        """Non-variant product uses product-level stock with is_derived=False."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Green Tea",
            price=Decimal("150.00"),
        )
        item = InventoryItem.objects.get(product=product, variant__isnull=True)
        item.set_quantity(Decimal("25.000"))
        item.reserve_stock(Decimal("5.000"))

        stock_info = get_product_stock(product)
        self.assertFalse(stock_info["is_derived"])
        self.assertFalse(stock_info["has_variants"])
        self.assertEqual(stock_info["quantity"], Decimal("25.000"))
        self.assertEqual(stock_info["reserved_quantity"], Decimal("5.000"))
        self.assertEqual(stock_info["available_quantity"], Decimal("20.000"))
        self.assertFalse(stock_info["is_out_of_stock"])

    def test_variant_based_product_stock_is_authoritative_and_derived(self):
        """
        For a variant-based product:
        - Variant stock is authoritative.
        - Product-level stock is derived aggregate of variants (is_derived=True).
        - Direct changes to product-level stock are prohibited.
        """
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Whole Wheat Flour",
            price=Decimal("50.00"),
        )
        var_1kg = ProductVariant.objects.create(product=product, name="1 kg")
        var_5kg = ProductVariant.objects.create(product=product, name="5 kg")

        item_1kg = InventoryItem.objects.get(variant=var_1kg)
        item_5kg = InventoryItem.objects.get(variant=var_5kg)

        item_1kg.set_quantity(Decimal("30.000"))
        item_1kg.reserve_stock(Decimal("5.000"))

        item_5kg.set_quantity(Decimal("10.000"))
        item_5kg.reserve_stock(Decimal("2.000"))

        # Variant 1 stock check
        v1_stock = get_variant_stock(var_1kg)
        self.assertEqual(v1_stock["quantity"], Decimal("30.000"))
        self.assertEqual(v1_stock["available_quantity"], Decimal("25.000"))

        # Variant 2 stock check
        v2_stock = get_variant_stock(var_5kg)
        self.assertEqual(v2_stock["quantity"], Decimal("10.000"))
        self.assertEqual(v2_stock["available_quantity"], Decimal("8.000"))

        # Product derived aggregate check
        prod_stock = get_product_stock(product)
        self.assertTrue(prod_stock["is_derived"])
        self.assertTrue(prod_stock["has_variants"])
        self.assertEqual(prod_stock["quantity"], Decimal("40.000"))  # 30 + 10
        self.assertEqual(prod_stock["reserved_quantity"], Decimal("7.000"))  # 5 + 2
        self.assertEqual(prod_stock["available_quantity"], Decimal("33.000"))  # 40 - 7
        self.assertFalse(prod_stock["is_out_of_stock"])

        # Attempting to modify aggregate product stock directly is superseded and prohibited
        with self.assertRaises(ValidationError) as cm:
            adjust_stock(self.shop1, product, set_quantity=Decimal("50.000"))
        self.assertIn("superseded and not permitted", str(cm.exception))

    def test_adjust_stock_service_helper(self):
        """adjust_stock helper modifies stock correctly and enforces shop authorization."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Cooking Oil",
            price=Decimal("180.00"),
        )
        # Set quantity via service
        item = adjust_stock(self.shop1, product, set_quantity=Decimal("20.000"))
        self.assertEqual(item.quantity, Decimal("20.000"))

        # Add delta
        adjust_stock(self.shop1, product, delta=Decimal("5.500"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("25.500"))

        # Subtract delta
        adjust_stock(self.shop1, product, delta=Decimal("-3.500"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("22.000"))

        # Cross-tenant modification rejected
        with self.assertRaises(ValidationError):
            adjust_stock(self.shop2, product, set_quantity=Decimal("10.000"))


class OrderFlowStockLifecycleTests(InventoryBaseTestCase):
    def setUp(self):
        super().setUp()
        self.product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Honey",
            price=Decimal("350.00"),
        )
        adjust_stock(self.shop1, self.product, set_quantity=Decimal("50.000"))

    def test_full_order_acceptance_lifecycle(self):
        """
        Flow 1: Order Created -> Required Quantity Reserved -> Merchant Accepts -> Reserved Quantity Deducted.
        """
        # Step 1: Order Created: Reserve 10.500 units
        item = reserve_order_stock(self.shop1, self.product, Decimal("10.500"))
        self.assertEqual(item.quantity, Decimal("50.000"))
        self.assertEqual(item.reserved_quantity, Decimal("10.500"))
        self.assertEqual(item.available_quantity, Decimal("39.500"))

        # Step 2: Merchant Accepts: 10.500 units deducted from on-hand stock
        item = deduct_order_stock(self.shop1, self.product, Decimal("10.500"))
        self.assertEqual(item.quantity, Decimal("39.500"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("39.500"))

    def test_order_rejection_or_cancellation_releases_reserved_stock(self):
        """
        Flow 2: Order Created -> Quantity Reserved -> Order Rejected/Expired/Cancelled by customer -> Released.
        """
        item = reserve_order_stock(self.shop1, self.product, Decimal("15.000"))
        self.assertEqual(item.available_quantity, Decimal("35.000"))

        # Order Rejected or Expired or Cancelled while PENDING -> release reserved quantity
        item = release_order_stock(self.shop1, self.product, Decimal("15.000"))
        self.assertEqual(item.quantity, Decimal("50.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("50.000"))

    def test_cancellation_after_acceptance_restores_deducted_stock(self):
        """
        Flow 3: Order Accepted -> Deducted -> Cancelled before preparation -> Deducted quantity restored.
        """
        reserve_order_stock(self.shop1, self.product, Decimal("20.000"))
        deduct_order_stock(self.shop1, self.product, Decimal("20.000"))

        item = InventoryItem.objects.get(product=self.product, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("30.000"))
        self.assertEqual(item.available_quantity, Decimal("30.000"))

        # Merchant cancels accepted order before PREPARING -> restore stock
        item = restore_cancelled_order_stock(self.shop1, self.product, Decimal("20.000"))
        self.assertEqual(item.quantity, Decimal("50.000"))
        self.assertEqual(item.available_quantity, Decimal("50.000"))

    def test_merchant_manual_fulfillment_reduction_before_acceptance(self):
        """
        Flow 4: Customer requested 5.000 units, but merchant only fulfills 3.000 units.
        The unfulfilled difference (2.000) is released, and 3.000 is deducted atomically.
        """
        # Customer placed order requesting 5.000 units (reserved)
        reserve_order_stock(self.shop1, self.product, Decimal("5.000"))
        item = InventoryItem.objects.get(product=self.product, variant__isnull=True)
        self.assertEqual(item.reserved_quantity, Decimal("5.000"))
        self.assertEqual(item.available_quantity, Decimal("45.000"))

        # Merchant manually reduces fulfillable quantity to 3.000 and accepts
        item = reduce_and_accept_order_stock(
            self.shop1,
            self.product,
            original_reserved=Decimal("5.000"),
            accepted_quantity=Decimal("3.000"),
        )
        # On-hand drops by accepted quantity (50 - 3 = 47)
        self.assertEqual(item.quantity, Decimal("47.000"))
        # Reserved drops to 0
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        # Available stock is now 47.000 (45 + 2 unfulfilled released)
        self.assertEqual(item.available_quantity, Decimal("47.000"))

    def test_insufficient_stock_rejection(self):
        """Reserving more than available stock raises ValidationError."""
        with self.assertRaises(ValidationError) as cm:
            reserve_order_stock(self.shop1, self.product, Decimal("60.000"))
        self.assertIn("Insufficient available stock", str(cm.exception))

    def test_reduce_and_accept_invalid_quantity(self):
        """Accepted quantity cannot exceed originally reserved quantity."""
        reserve_order_stock(self.shop1, self.product, Decimal("5.000"))
        with self.assertRaises(ValidationError) as cm:
            reduce_and_accept_order_stock(
                self.shop1,
                self.product,
                original_reserved=Decimal("5.000"),
                accepted_quantity=Decimal("6.000"),
            )
        self.assertIn("Accepted quantity cannot exceed", str(cm.exception))


class BatchOrderStockAtomicTests(InventoryBaseTestCase):
    def setUp(self):
        super().setUp()
        self.prod_a = ShopProduct.objects.create(shop=self.shop1, name="Item A")
        self.prod_b = ShopProduct.objects.create(shop=self.shop1, name="Item B")
        self.prod_c = ShopProduct.objects.create(shop=self.shop1, name="Item C")

        adjust_stock(self.shop1, self.prod_a, set_quantity=Decimal("10.000"))
        adjust_stock(self.shop1, self.prod_b, set_quantity=Decimal("20.000"))
        adjust_stock(self.shop1, self.prod_c, set_quantity=Decimal("5.000"))

    def test_batch_reservation_success(self):
        """All items in order reserved atomically."""
        items_and_qty = [
            (self.prod_a, Decimal("2.000")),
            (self.prod_b, Decimal("5.000")),
            (self.prod_c, Decimal("1.500")),
        ]
        reserve_order_items_stock(self.shop1, items_and_qty)

        item_a = InventoryItem.objects.get(product=self.prod_a, variant__isnull=True)
        item_b = InventoryItem.objects.get(product=self.prod_b, variant__isnull=True)
        item_c = InventoryItem.objects.get(product=self.prod_c, variant__isnull=True)

        self.assertEqual(item_a.reserved_quantity, Decimal("2.000"))
        self.assertEqual(item_b.reserved_quantity, Decimal("5.000"))
        self.assertEqual(item_c.reserved_quantity, Decimal("1.500"))

    def test_batch_reservation_rollback_when_one_item_insufficient(self):
        """
        When any single line item has insufficient stock, the entire order reservation
        rolls back atomically and no stock is reserved.
        """
        items_and_qty = [
            (self.prod_a, Decimal("2.000")),
            (self.prod_b, Decimal("5.000")),
            (self.prod_c, Decimal("10.000")),  # prod_c only has 5.000!
        ]
        with self.assertRaises(ValidationError) as cm:
            reserve_order_items_stock(self.shop1, items_and_qty)
        self.assertIn("Insufficient stock for 'Item C'", str(cm.exception))

        # Check atomicity: prod_a and prod_b must NOT have reserved stock!
        item_a = InventoryItem.objects.get(product=self.prod_a, variant__isnull=True)
        item_b = InventoryItem.objects.get(product=self.prod_b, variant__isnull=True)
        item_c = InventoryItem.objects.get(product=self.prod_c, variant__isnull=True)

        self.assertEqual(item_a.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item_b.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item_c.reserved_quantity, Decimal("0.000"))

    def test_batch_deduct_and_restore(self):
        """Multi-item deduction and restoration work atomically."""
        items_and_qty = [
            (self.prod_a, Decimal("4.000")),
            (self.prod_b, Decimal("10.000")),
        ]
        reserve_order_items_stock(self.shop1, items_and_qty)
        deduct_order_items_stock(self.shop1, items_and_qty)

        item_a = InventoryItem.objects.get(product=self.prod_a, variant__isnull=True)
        item_b = InventoryItem.objects.get(product=self.prod_b, variant__isnull=True)
        self.assertEqual(item_a.quantity, Decimal("6.000"))
        self.assertEqual(item_b.quantity, Decimal("10.000"))

        # Restore
        restore_order_items_stock(self.shop1, items_and_qty)
        item_a.refresh_from_db()
        item_b.refresh_from_db()
        self.assertEqual(item_a.quantity, Decimal("10.000"))
        self.assertEqual(item_b.quantity, Decimal("20.000"))


class DecimalQuantityEdgeCasesTests(InventoryBaseTestCase):
    def test_quantize_quantity_helper(self):
        """Tests exact 3 decimal place quantization and validation."""
        self.assertEqual(quantize_quantity("1.250"), Decimal("1.250"))
        self.assertEqual(quantize_quantity("0.001"), Decimal("0.001"))
        self.assertEqual(quantize_quantity(5), Decimal("5.000"))
        self.assertEqual(quantize_quantity("10.5"), Decimal("10.500"))

        # Rejects more than 3 decimal places
        with self.assertRaises(ValidationError) as cm:
            quantize_quantity("1.2345")
        self.assertIn("cannot have more than 3 decimal places", str(cm.exception))

        # Rejects negative values
        with self.assertRaises(ValidationError) as cm:
            quantize_quantity("-0.001")
        self.assertIn("cannot be negative", str(cm.exception))

    def test_boundary_zero_stock_quantities(self):
        """Zero stock quantity is permitted, exactly 0.000."""
        product = ShopProduct.objects.create(shop=self.shop1, name="Out of Stock Item")
        item = InventoryItem.objects.get(product=product, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))
        self.assertTrue(item.is_out_of_stock)


class AntiBloatVerificationTests(TestCase):
    def test_no_persistent_movement_ledger_or_low_stock_threshold(self):
        """
        Verifies compliance with Section 11 and Section 8 of inventory.md:
        - The MVP stores current stock state and does not maintain a persistent inventory movement/history ledger.
        - The MVP has no low-stock threshold.
        """
        # Ensure InventoryItem has no low_stock_threshold field
        field_names = [f.name for f in InventoryItem._meta.get_fields()]
        self.assertNotIn("low_stock_threshold", field_names)
        self.assertNotIn("threshold", field_names)
        self.assertNotIn("min_stock", field_names)

        # Ensure no movement or ledger models exist in the inventory app
        from django.apps import apps
        inventory_models = apps.get_app_config("inventory").get_models()
        model_names = [m.__name__ for m in inventory_models]
        self.assertEqual(model_names, ["InventoryItem"])


class DatabaseConstraintsAndIntegrityTests(InventoryBaseTestCase):
    """
    Dedicated tests verifying database-level constraints (CheckConstraint, UniqueConstraint),
    model clean() validations for Shop isolation and Catalog references, and cascade behaviors.
    """

    def setUp(self):
        super().setUp()
        self.product1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Sugar",
            price=Decimal("45.00"),
        )
        self.product2 = ShopProduct.objects.create(
            shop=self.shop2,
            name="Flour",
            price=Decimal("50.00"),
        )

    def test_db_check_constraint_rejects_negative_quantity_on_raw_insert(self):
        """Database CheckConstraint rejects negative quantity even when bypassing full_clean()."""
        with self.assertRaises(IntegrityError):
            InventoryItem.objects.bulk_create([
                InventoryItem(
                    shop=self.shop1,
                    product=self.product1,
                    variant=None,
                    quantity=Decimal("-1.000"),
                    reserved_quantity=Decimal("0.000"),
                )
            ])

    def test_db_check_constraint_rejects_negative_reserved_quantity_on_raw_insert(self):
        """Database CheckConstraint rejects negative reserved_quantity on raw insert."""
        with self.assertRaises(IntegrityError):
            InventoryItem.objects.bulk_create([
                InventoryItem(
                    shop=self.shop1,
                    product=self.product1,
                    variant=None,
                    quantity=Decimal("10.000"),
                    reserved_quantity=Decimal("-2.000"),
                )
            ])

    def test_db_check_constraint_rejects_reserved_greater_than_quantity_on_raw_insert(self):
        """Database CheckConstraint rejects reserved_quantity > quantity on raw insert."""
        with self.assertRaises(IntegrityError):
            InventoryItem.objects.bulk_create([
                InventoryItem(
                    shop=self.shop1,
                    product=self.product1,
                    variant=None,
                    quantity=Decimal("5.000"),
                    reserved_quantity=Decimal("6.000"),
                )
            ])

    def test_db_unique_constraint_rejects_duplicate_product_stock_on_raw_insert(self):
        """Database UniqueConstraint rejects duplicate (shop, product) records where variant is null."""
        # Initial item was already created by signal on ShopProduct creation
        self.assertTrue(InventoryItem.objects.filter(shop=self.shop1, product=self.product1, variant__isnull=True).exists())

        # Attempting to bulk_create a second product-level record for the same shop & product
        with self.assertRaises(IntegrityError):
            InventoryItem.objects.bulk_create([
                InventoryItem(
                    shop=self.shop1,
                    product=self.product1,
                    variant=None,
                    quantity=Decimal("10.000"),
                )
            ])

    def test_db_unique_constraint_rejects_duplicate_variant_stock_on_raw_insert(self):
        """Database UniqueConstraint rejects duplicate (shop, variant) records."""
        variant = ProductVariant.objects.create(product=self.product1, name="1 kg")
        self.assertTrue(InventoryItem.objects.filter(shop=self.shop1, variant=variant).exists())

        # Attempting to bulk_create a second variant-level record for the same shop & variant
        with self.assertRaises(IntegrityError):
            InventoryItem.objects.bulk_create([
                InventoryItem(
                    shop=self.shop1,
                    product=self.product1,
                    variant=variant,
                    quantity=Decimal("5.000"),
                )
            ])

    def test_shop_isolation_rejects_cross_shop_product_assignment(self):
        """InventoryItem cannot reference a product belonging to a different shop."""
        item = InventoryItem(
            shop=self.shop1,
            product=self.product2,  # belongs to shop2!
            variant=None,
            quantity=Decimal("10.000"),
        )
        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn("shop", cm.exception.message_dict)

    def test_shop_isolation_rejects_cross_shop_variant_assignment(self):
        """InventoryItem cannot reference a variant whose product belongs to a different shop."""
        var2 = ProductVariant.objects.create(product=self.product2, name="500g")
        item = InventoryItem(
            shop=self.shop1,
            product=self.product2,
            variant=var2,
            quantity=Decimal("10.000"),
        )
        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn("shop", cm.exception.message_dict)

    def test_valid_product_reference_rejects_mismatched_variant(self):
        """Variant must belong to the specified product in InventoryItem."""
        var1 = ProductVariant.objects.create(product=self.product1, name="1 kg")
        product_other = ShopProduct.objects.create(shop=self.shop1, name="Tea")

        item = InventoryItem(
            shop=self.shop1,
            product=product_other,
            variant=var1,  # belongs to product1, not product_other!
            quantity=Decimal("5.000"),
        )
        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn("variant", cm.exception.message_dict)

    def test_finalized_relationship_to_catalog_cascading_deletion(self):
        """
        When a Shop, ShopProduct, or ProductVariant is removed from the Catalog,
        its Inventory records are cascade-deleted per Section 6 of inventory.md.
        """
        product = ShopProduct.objects.create(shop=self.shop1, name="Seasonal Dates")
        var = ProductVariant.objects.create(product=product, name="500g Box")

        var_id = var.id
        prod_id = product.id

        self.assertTrue(InventoryItem.objects.filter(variant_id=var_id).exists())

        # 1. Variant deletion cascades to its InventoryItem
        var.delete()
        self.assertFalse(InventoryItem.objects.filter(variant_id=var_id).exists())

        # 2. Product deletion cascades to its InventoryItems
        product.delete()
        self.assertFalse(InventoryItem.objects.filter(product_id=prod_id).exists())

        # 3. Shop deletion cascades to all its InventoryItems
        temp_user = User.objects.create_user(
            username="merchant_temp",
            email="merchant_temp@example.com",
            password="testpassword123",
            role=User.Role.MERCHANT,
            mobile_number="+919876543999",
        )
        temp_merchant = Merchant.objects.create(
            user=temp_user,
            status=Merchant.Status.ACTIVE,
        )
        shop_test = Shop.objects.create(
            merchant=temp_merchant,
            name="Temporary Shop",
            address_line="789 Lane",
            area="Area",
            city="City",
            state="State",
            pincode="123458",
            contact_number="+919876543999",
        )
        prod_temp = ShopProduct.objects.create(shop=shop_test, name="Temp Item")
        temp_shop_id = shop_test.id

        self.assertTrue(InventoryItem.objects.filter(shop_id=temp_shop_id).exists())
        shop_test.delete()
        self.assertFalse(InventoryItem.objects.filter(shop_id=temp_shop_id).exists())


class StockInitializationAndGranularityTests(InventoryBaseTestCase):
    """
    Dedicated verification for task INV-004:
    - Newly created Shop Products and Variants initialize stock strictly at zero (0.000).
    - Creation flows (ORM, from_master_product, API) cannot establish positive stock.
    - Product/Variant granularity is strictly respected.
    """

    def test_new_shop_product_starts_with_zero_stock(self):
        """Direct ShopProduct creation initializes InventoryItem with quantity 0.000 and out-of-stock."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Green Tea",
            price=Decimal("150.00"),
        )
        item = InventoryItem.objects.filter(shop=self.shop1, product=product, variant__isnull=True).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, Decimal("0.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))
        self.assertTrue(item.is_out_of_stock)

        stock_info = get_product_stock(product)
        self.assertEqual(stock_info["quantity"], Decimal("0.000"))
        self.assertEqual(stock_info["reserved_quantity"], Decimal("0.000"))
        self.assertEqual(stock_info["available_quantity"], Decimal("0.000"))
        self.assertFalse(stock_info["has_variants"])
        self.assertFalse(stock_info["is_derived"])
        self.assertTrue(stock_info["is_out_of_stock"])

    def test_new_variant_starts_with_zero_stock(self):
        """Direct ProductVariant creation initializes variant-level InventoryItem at zero."""
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Sunflower Oil",
            price=Decimal("180.00"),
        )
        variant = ProductVariant.objects.create(
            product=product,
            name="1 Litre Pouch",
            price=Decimal("180.00"),
        )
        item = InventoryItem.objects.filter(shop=self.shop1, product=product, variant=variant).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, Decimal("0.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))
        self.assertTrue(item.is_out_of_stock)

        var_stock = get_variant_stock(variant)
        self.assertEqual(var_stock["quantity"], Decimal("0.000"))
        self.assertEqual(var_stock["available_quantity"], Decimal("0.000"))
        self.assertTrue(var_stock["is_out_of_stock"])

        # Derived product stock is also zero
        prod_stock = get_product_stock(product)
        self.assertEqual(prod_stock["quantity"], Decimal("0.000"))
        self.assertTrue(prod_stock["has_variants"])
        self.assertTrue(prod_stock["is_derived"])
        self.assertTrue(prod_stock["is_out_of_stock"])

    def test_from_master_product_starts_at_zero_stock(self):
        """Selecting from Master Catalog via factory initializes stock strictly at zero."""
        master_category = MasterCategory.objects.create(
            name="Dairy",
            slug="dairy",
            description="Dairy and eggs",
        )
        master_product = MasterProduct.objects.create(
            name="Pasteurized Whole Milk 500ml",
            category=master_category,
            brand="Amul",
            description="Fresh dairy milk",
        )
        shop_product = ShopProduct.from_master_product(
            self.shop1,
            master_product,
            price=Decimal("32.00"),
        )
        item = InventoryItem.objects.filter(shop=self.shop1, product=shop_product, variant__isnull=True).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, Decimal("0.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))
        self.assertTrue(item.is_out_of_stock)

    def test_api_creation_flow_ignores_positive_stock_payload(self):
        """
        Submitting stock/quantity fields in REST API product creation payload does not establish
        positive stock. Stock starts strictly at 0.000.
        """
        api_client = APIClient()
        login_res = api_client.post(
            reverse("auth-login"),
            {"mobile_number": self.user1.mobile_number, "password": "testpassword123"},
            format="json",
        )
        self.assertEqual(login_res.status_code, 200)
        token = login_res.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        create_res = api_client.post(
            reverse("catalog:merchant-product-list"),
            {
                "name": "API Created Biscuits",
                "price": "25.00",
                "stock": 100,
                "quantity": 100,
                "initial_stock": 50,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, 201)
        product_id = create_res.data["id"]

        product = ShopProduct.objects.get(id=product_id)
        item = InventoryItem.objects.filter(product=product, variant__isnull=True).first()
        self.assertIsNotNone(item)
        self.assertEqual(item.quantity, Decimal("0.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))

    def test_adding_variant_to_stocked_product_starts_variant_at_zero_and_supersedes_parent(self):
        """
        When a variant is added to a product that had positive product-level stock:
        - The variant starts at 0.000 (does not inherit parent stock).
        - The parent's obsolete non-variant record is removed.
        - Aggregate product stock resets to 0.000.
        """
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Wheat Flour",
            price=Decimal("45.00"),
        )
        # Establish positive product-level stock before variants exist
        adjust_stock(self.shop1, product, set_quantity=Decimal("50.000"))
        self.assertEqual(get_product_stock(product)["quantity"], Decimal("50.000"))
        self.assertFalse(get_product_stock(product)["has_variants"])

        # Add first variant
        variant1 = ProductVariant.objects.create(
            product=product,
            name="1 kg Bag",
            price=Decimal("45.00"),
        )

        # Variant 1 starts strictly at 0.000
        var1_stock = get_variant_stock(variant1)
        self.assertEqual(var1_stock["quantity"], Decimal("0.000"))
        self.assertEqual(var1_stock["available_quantity"], Decimal("0.000"))

        # Obsolete non-variant record is gone
        self.assertFalse(InventoryItem.objects.filter(product=product, variant__isnull=True).exists())

        # Product-level aggregate is now 0.000
        prod_stock = get_product_stock(product)
        self.assertEqual(prod_stock["quantity"], Decimal("0.000"))
        self.assertTrue(prod_stock["has_variants"])
        self.assertTrue(prod_stock["is_derived"])
        self.assertTrue(prod_stock["is_out_of_stock"])

    def test_subsequent_variants_initialize_independently_at_zero(self):
        """
        When a product has an existing variant with positive stock, adding a new variant
        initializes the new variant strictly at 0.000 without inheriting positive sibling stock.
        """
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Basmati Rice Gold",
            price=Decimal("90.00"),
        )
        var1 = ProductVariant.objects.create(product=product, name="1 kg")
        var2 = ProductVariant.objects.create(product=product, name="5 kg")

        # Adjust variant 1 to 20.000 stock; variant 2 remains 0.000
        adjust_stock(self.shop1, var1, set_quantity=Decimal("20.000"))
        self.assertEqual(get_variant_stock(var1)["quantity"], Decimal("20.000"))
        self.assertEqual(get_variant_stock(var2)["quantity"], Decimal("0.000"))
        self.assertEqual(get_product_stock(product)["quantity"], Decimal("20.000"))

        # Add variant 3
        var3 = ProductVariant.objects.create(product=product, name="10 kg")

        # Variant 3 must be initialized at 0.000 (does not inherit 20.000)
        self.assertEqual(get_variant_stock(var3)["quantity"], Decimal("0.000"))
        self.assertTrue(get_variant_stock(var3)["is_out_of_stock"])

        # Product aggregate stock remains 20.000 (20 + 0 + 0)
        self.assertEqual(get_product_stock(product)["quantity"], Decimal("20.000"))

    def test_new_product_and_variant_cannot_be_reserved_due_to_zero_stock(self):
        """Zero initial stock prevents reservations or orders immediately upon creation."""
        product = ShopProduct.objects.create(shop=self.shop1, name="Honey")
        variant = ProductVariant.objects.create(product=product, name="250g Jar")

        with self.assertRaises(ValidationError) as cm:
            reserve_order_stock(self.shop1, variant, quantity=Decimal("1.000"))
        self.assertIn("Insufficient available stock", str(cm.exception))

    def test_initialize_product_stock_service_raises_on_variant_product(self):
        """Calling initialize_product_stock on a variant-based product raises ValidationError."""
        product = ShopProduct.objects.create(shop=self.shop1, name="Variant Product")
        ProductVariant.objects.create(product=product, name="Var 1")

        with self.assertRaises(ValidationError) as cm:
            initialize_product_stock(product)
        self.assertIn("Variant-based products cannot have an independent product-level inventory record", str(cm.exception))

    def test_initialize_variant_stock_service_removes_obsolete_parent_record(self):
        """Calling initialize_variant_stock directly removes obsolete non-variant parent record."""
        product = ShopProduct.objects.create(shop=self.shop1, name="Service Test Item")
        # Ensure product-level item exists
        self.assertTrue(InventoryItem.objects.filter(product=product, variant__isnull=True).exists())

        variant = ProductVariant(product=product, name="Pack")
        variant.save()  # signal calls initialize_variant_stock

        self.assertFalse(InventoryItem.objects.filter(product=product, variant__isnull=True).exists())
        var_item = InventoryItem.objects.filter(product=product, variant=variant).first()
        self.assertIsNotNone(var_item)
        self.assertEqual(var_item.quantity, Decimal("0.000"))


class MerchantStockAddSubtractTests(InventoryBaseTestCase):
    """
    Test suite for Task INV-005: Merchant stock add and subtract operations.
    Validates Shop authorization, prevents negative resulting stock, prevents
    reducing below reserved stock, enforces MVP no-reason/no-movement policy.
    """

    def setUp(self):
        super().setUp()
        self.product1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Milk 1L",
            price=Decimal("60.00"),
        )
        self.variant_product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Premium Basmati Rice",
            price=Decimal("120.00"),
        )
        self.variant_1kg = ProductVariant.objects.create(
            product=self.variant_product,
            name="1 kg Pouch",
        )
        self.variant_5kg = ProductVariant.objects.create(
            product=self.variant_product,
            name="5 kg Bag",
        )

        # Shop 2 product and variant for cross-tenant testing
        self.shop2_product = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop 2 Olive Oil",
            price=Decimal("500.00"),
        )
        self.shop2_variant_product = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop 2 Salt",
            price=Decimal("20.00"),
        )
        self.shop2_variant = ProductVariant.objects.create(
            product=self.shop2_variant_product,
            name="1 kg",
        )

    def test_merchant_add_stock_non_variant_product(self):
        """Active shop owner merchant successfully adds stock to a non-variant product."""
        # Initial stock is 0.000
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("0.000"))

        item = add_stock(self.shop1, self.product1, Decimal("25.500"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("25.500"))
        self.assertEqual(item.available_quantity, Decimal("25.500"))

        # Add additional stock with user actor
        item = add_stock(self.shop1, self.product1, Decimal("10.250"), actor=self.user1)
        self.assertEqual(item.quantity, Decimal("35.750"))
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("35.750"))

    def test_merchant_add_stock_variant(self):
        """Active shop owner merchant adds stock to a variant; derived product aggregate updates."""
        item1 = add_stock(self.shop1, self.variant_1kg, Decimal("15.000"), actor=self.merchant1)
        item5 = add_stock(self.shop1, self.variant_5kg, Decimal("5.000"), actor=self.merchant1)

        self.assertEqual(item1.quantity, Decimal("15.000"))
        self.assertEqual(item5.quantity, Decimal("5.000"))
        self.assertEqual(get_variant_stock(self.variant_1kg)["quantity"], Decimal("15.000"))
        self.assertEqual(get_variant_stock(self.variant_5kg)["quantity"], Decimal("5.000"))

        # Parent product aggregate stock is derived: 15 + 5 = 20.000
        parent_stock = get_product_stock(self.variant_product)
        self.assertEqual(parent_stock["quantity"], Decimal("20.000"))
        self.assertTrue(parent_stock["is_derived"])

    def test_merchant_subtract_stock_non_variant_product(self):
        """Active shop owner merchant subtracts stock from a non-variant product."""
        add_stock(self.shop1, self.product1, Decimal("50.000"), actor=self.merchant1)

        item = subtract_stock(self.shop1, self.product1, Decimal("18.500"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("31.500"))
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("31.500"))

    def test_merchant_subtract_stock_variant(self):
        """Active shop owner merchant subtracts stock from a variant; derived aggregate updates."""
        add_stock(self.shop1, self.variant_1kg, Decimal("30.000"), actor=self.merchant1)
        add_stock(self.shop1, self.variant_5kg, Decimal("10.000"), actor=self.merchant1)

        item = subtract_stock(self.shop1, self.variant_1kg, Decimal("12.000"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("18.000"))

        parent_stock = get_product_stock(self.variant_product)
        self.assertEqual(parent_stock["quantity"], Decimal("28.000"))  # 18 + 10

    def test_subtract_stock_cannot_reduce_below_zero(self):
        """Subtracting more stock than available balance raises ValidationError."""
        add_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant1)

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.product1, Decimal("10.001"), actor=self.merchant1)
        self.assertIn("Cannot subtract stock below zero.", str(cm.exception))

        # Balance remains unaffected
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("10.000"))

    def test_subtract_stock_cannot_reduce_below_reserved_quantity(self):
        """Subtracting stock cannot reduce total quantity below currently reserved quantity."""
        add_stock(self.shop1, self.product1, Decimal("20.000"), actor=self.merchant1)
        # Reserve 8.000
        reserve_order_stock(self.shop1, self.product1, Decimal("8.000"))

        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("20.000"))
        self.assertEqual(item.reserved_quantity, Decimal("8.000"))
        self.assertEqual(item.available_quantity, Decimal("12.000"))

        # Subtracting 15.000 would leave quantity at 5.000, which is < reserved 8.000
        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.product1, Decimal("15.000"), actor=self.merchant1)
        self.assertIn("Cannot subtract stock below reserved quantity.", str(cm.exception))

        # Subtracting 12.000 leaves exactly 8.000 == reserved 8.000, which is valid
        item = subtract_stock(self.shop1, self.product1, Decimal("12.000"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("8.000"))
        self.assertEqual(item.reserved_quantity, Decimal("8.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))

    def test_add_and_subtract_reject_non_positive_quantity(self):
        """Adding or subtracting zero or negative quantities is strictly rejected."""
        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("0.000"), actor=self.merchant1)
        self.assertIn("Quantity to add must be greater than zero.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("-5.000"), actor=self.merchant1)
        self.assertIn("Quantity to add must be greater than zero.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.product1, Decimal("0.000"), actor=self.merchant1)
        self.assertIn("Quantity to subtract must be greater than zero.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.product1, Decimal("-5.000"), actor=self.merchant1)
        self.assertIn("Quantity to subtract must be greater than zero.", str(cm.exception))

    def test_cross_shop_target_rejection(self):
        """Attempting to add or subtract stock on a product/variant belonging to another shop is rejected."""
        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.shop2_product, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Target product does not belong to the authorized shop.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.shop2_variant, Decimal("5.000"), actor=self.merchant1)
        self.assertIn("Target variant does not belong to the authorized shop.", str(cm.exception))

    def test_unauthorized_merchant_rejection(self):
        """Merchant from Shop 2 cannot modify inventory for Shop 1."""
        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant2)
        self.assertIn("Merchant is not authorized to modify inventory for this shop.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.product1, Decimal("5.000"), actor=self.user2)
        self.assertIn("Merchant is not authorized to modify inventory for this shop.", str(cm.exception))

    def test_super_admin_explicitly_rejected(self):
        """Super Admin is strictly prohibited from modifying Merchant inventory per Section 3."""
        admin_user = User.objects.create_user(
            username="superadmin_test",
            email="admin@example.com",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )

        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("10.000"), actor=admin_user)
        self.assertIn("Super Admin is not authorized to modify Merchant inventory.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.product1, Decimal("5.000"), actor=admin_user)
        self.assertIn("Super Admin is not authorized to modify Merchant inventory.", str(cm.exception))

    def test_customer_actor_rejected(self):
        """Customer actor or non-user/merchant actor cannot modify merchant inventory."""
        from customers.models import Customer

        customer = Customer.objects.create(
            shop=self.shop1,
            name="Alice Customer",
            whatsapp_number="+919123456789",
        )

        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("5.000"), actor=customer)
        self.assertIn("Invalid actor for inventory modification.", str(cm.exception))

    def test_deactivated_or_suspended_shop_rejection(self):
        """Cannot modify inventory for a deactivated or suspended shop."""
        self.shop1.status = Shop.Status.DEACTIVATED
        self.shop1.save()

        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Cannot modify inventory for a deactivated or suspended shop.", str(cm.exception))

        self.shop1.status = Shop.Status.SUSPENDED
        self.shop1.save()

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.product1, Decimal("5.000"), actor=self.merchant1)
        self.assertIn("Cannot modify inventory for a deactivated or suspended shop.", str(cm.exception))

    def test_inactive_merchant_rejection(self):
        """Deactivated or non-active merchant cannot modify inventory."""
        self.merchant1.status = Merchant.Status.DEACTIVATED
        self.merchant1.save()

        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Only active merchants can modify shop inventory.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.user1)
        self.assertIn("Only active merchants can modify shop inventory.", str(cm.exception))

    def test_variant_based_parent_product_manual_adjustment_rejected(self):
        """Attempting to add or subtract stock directly on a parent variant-based product is rejected."""
        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.variant_product, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            subtract_stock(self.shop1, self.variant_product, Decimal("5.000"), actor=self.merchant1)
        self.assertIn("Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted.", str(cm.exception))

    def test_decimal_precision_preservation(self):
        """Decimal quantities preserve 3 decimal places and reject >3 decimal places."""
        item = add_stock(self.shop1, self.product1, Decimal("12.345"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("12.345"))

        item = subtract_stock(self.shop1, self.product1, Decimal("2.345"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("10.000"))

        with self.assertRaises(ValidationError) as cm:
            add_stock(self.shop1, self.product1, "12.3456", actor=self.merchant1)
        self.assertIn("Quantity cannot have more than 3 decimal places.", str(cm.exception))

    def test_no_adjustment_reason_or_movement_history_mvp(self):
        """MVP strictly enforces no adjustment reason argument and no movement history ledger."""
        import inspect
        from django.apps import apps

        add_params = inspect.signature(add_stock).parameters
        sub_params = inspect.signature(subtract_stock).parameters
        self.assertNotIn("reason", add_params)
        self.assertNotIn("reason", sub_params)

        inventory_models = [m.__name__.lower() for m in apps.get_app_config("inventory").get_models()]
        self.assertNotIn("movement", inventory_models)
        self.assertNotIn("inventorymovement", inventory_models)
        self.assertNotIn("stockmovement", inventory_models)
        self.assertNotIn("history", inventory_models)


class MerchantExactStockUpdateTests(InventoryBaseTestCase):
    """
    Test suite for Task INV-006: Merchant exact-quantity stock updates.
    Validates Shop ownership, non-negative decimal quantity, reserved-stock rules,
    variant granularity, and MVP no-reason/no-movement policy.
    """

    def setUp(self):
        super().setUp()
        self.product1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Whole Wheat Flour 5kg",
            price=Decimal("250.00"),
        )
        self.variant_product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Cold Pressed Coconut Oil",
            price=Decimal("180.00"),
        )
        self.variant_500ml = ProductVariant.objects.create(
            product=self.variant_product,
            name="500 ml Bottle",
        )
        self.variant_1l = ProductVariant.objects.create(
            product=self.variant_product,
            name="1 Litre Bottle",
        )

        # Shop 2 product and variant for cross-tenant testing
        self.shop2_product = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop 2 Mustard Oil",
            price=Decimal("150.00"),
        )
        self.shop2_variant_product = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop 2 Sugar",
            price=Decimal("45.00"),
        )
        self.shop2_variant = ProductVariant.objects.create(
            product=self.shop2_variant_product,
            name="1 kg Bag",
        )

    def test_merchant_set_exact_stock_non_variant_product(self):
        """Active shop owner merchant sets exact stock on a non-variant product."""
        # Initial stock is 0.000
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("0.000"))

        item = set_stock(self.shop1, self.product1, Decimal("45.500"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("45.500"))
        self.assertEqual(item.available_quantity, Decimal("45.500"))
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("45.500"))

        # Update to another exact quantity (e.g. 12.000) using User actor
        item = set_stock(self.shop1, self.product1, Decimal("12.000"), actor=self.user1)
        self.assertEqual(item.quantity, Decimal("12.000"))
        self.assertEqual(item.available_quantity, Decimal("12.000"))
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("12.000"))

    def test_merchant_set_exact_stock_to_zero(self):
        """Setting exact stock to 0.000 succeeds when reserved quantity is zero and marks out of stock."""
        # First set stock to 15.000
        set_stock(self.shop1, self.product1, Decimal("15.000"), actor=self.merchant1)
        self.assertFalse(get_product_stock(self.product1)["is_out_of_stock"])

        # Set exact stock to 0.000
        item = set_stock(self.shop1, self.product1, Decimal("0.000"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))
        self.assertTrue(item.is_out_of_stock)

        stock_info = get_product_stock(self.product1)
        self.assertEqual(stock_info["quantity"], Decimal("0.000"))
        self.assertEqual(stock_info["available_quantity"], Decimal("0.000"))
        self.assertTrue(stock_info["is_out_of_stock"])

    def test_merchant_set_exact_stock_variant(self):
        """Setting exact stock on variants updates authoritative balances and parent derived aggregate."""
        item_500ml = set_stock(self.shop1, self.variant_500ml, Decimal("25.000"), actor=self.merchant1)
        item_1l = set_stock(self.shop1, self.variant_1l, Decimal("10.000"), actor=self.merchant1)

        self.assertEqual(item_500ml.quantity, Decimal("25.000"))
        self.assertEqual(item_1l.quantity, Decimal("10.000"))

        self.assertEqual(get_variant_stock(self.variant_500ml)["quantity"], Decimal("25.000"))
        self.assertEqual(get_variant_stock(self.variant_1l)["quantity"], Decimal("10.000"))

        parent_stock = get_product_stock(self.variant_product)
        self.assertEqual(parent_stock["quantity"], Decimal("35.000"))
        self.assertTrue(parent_stock["is_derived"])

    def test_set_exact_stock_rejects_negative_quantity(self):
        """Setting negative exact quantity is strictly rejected."""
        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("-1.000"), actor=self.merchant1)
        self.assertIn("Quantity cannot be negative.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, "-0.001", actor=self.merchant1)
        self.assertIn("Quantity cannot be negative.", str(cm.exception))

        # Balance remains 0.000
        self.assertEqual(get_product_stock(self.product1)["quantity"], Decimal("0.000"))

    def test_set_exact_stock_cannot_bypass_reserved_stock(self):
        """Cannot set exact stock lower than currently reserved quantity."""
        set_stock(self.shop1, self.product1, Decimal("20.000"), actor=self.merchant1)
        reserve_order_stock(self.shop1, self.product1, Decimal("8.000"))

        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("20.000"))
        self.assertEqual(item.reserved_quantity, Decimal("8.000"))
        self.assertEqual(item.available_quantity, Decimal("12.000"))

        # Setting exact stock to 7.999 is strictly rejected
        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("7.999"), actor=self.merchant1)
        self.assertIn("Cannot set quantity lower than currently reserved quantity.", str(cm.exception))

        # Setting exact stock to 0.000 while reservations exist is strictly rejected
        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("0.000"), actor=self.merchant1)
        self.assertIn("Cannot set quantity lower than currently reserved quantity.", str(cm.exception))

        # Stock remains unchanged
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("20.000"))

    def test_set_exact_stock_equal_to_reserved_stock_succeeds(self):
        """Setting exact stock equal to reserved quantity succeeds and leaves available quantity at zero."""
        set_stock(self.shop1, self.product1, Decimal("20.000"), actor=self.merchant1)
        reserve_order_stock(self.shop1, self.product1, Decimal("8.000"))

        # Setting exact quantity to exactly 8.000
        item = set_stock(self.shop1, self.product1, Decimal("8.000"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("8.000"))
        self.assertEqual(item.reserved_quantity, Decimal("8.000"))
        self.assertEqual(item.available_quantity, Decimal("0.000"))
        self.assertTrue(item.is_out_of_stock)

        # Increasing exact stock above reserved quantity restores availability
        item = set_stock(self.shop1, self.product1, Decimal("15.000"), actor=self.merchant1)
        self.assertEqual(item.quantity, Decimal("15.000"))
        self.assertEqual(item.reserved_quantity, Decimal("8.000"))
        self.assertEqual(item.available_quantity, Decimal("7.000"))
        self.assertFalse(item.is_out_of_stock)

    def test_set_exact_stock_rejects_excess_decimal_places(self):
        """Quantities with more than 3 decimal places are rejected."""
        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, "10.1234", actor=self.merchant1)
        self.assertIn("Quantity cannot have more than 3 decimal places.", str(cm.exception))

    def test_set_exact_stock_cross_shop_target_rejection(self):
        """Setting stock on products/variants belonging to another shop is rejected."""
        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.shop2_product, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Target product does not belong to the authorized shop.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.shop2_variant, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Target variant does not belong to the authorized shop.", str(cm.exception))

    def test_set_exact_stock_unauthorized_merchant_rejection(self):
        """Merchant 2 cannot modify inventory for Shop 1."""
        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant2)
        self.assertIn("Merchant is not authorized to modify inventory for this shop.", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.user2)
        self.assertIn("Merchant is not authorized to modify inventory for this shop.", str(cm.exception))

    def test_set_exact_stock_super_admin_explicitly_rejected(self):
        """Super Admin is strictly prohibited from modifying Merchant inventory per Section 3."""
        admin_user = User.objects.create_user(
            username="superadmin_inv006",
            email="admin_inv006@example.com",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("10.000"), actor=admin_user)
        self.assertIn("Super Admin is not authorized to modify Merchant inventory.", str(cm.exception))

    def test_set_exact_stock_invalid_actor_rejected(self):
        """Customer profile or invalid actor cannot modify merchant inventory."""
        from customers.models import Customer

        customer = Customer.objects.create(
            shop=self.shop1,
            name="Bob Customer",
            whatsapp_number="+919876543201",
        )

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("10.000"), actor=customer)
        self.assertIn("Invalid actor for inventory modification.", str(cm.exception))

    def test_set_exact_stock_deactivated_or_suspended_shop_rejection(self):
        """Cannot modify inventory for a deactivated or suspended shop."""
        self.shop1.status = Shop.Status.DEACTIVATED
        self.shop1.save()

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Cannot modify inventory for a deactivated or suspended shop.", str(cm.exception))

        self.shop1.status = Shop.Status.SUSPENDED
        self.shop1.save()

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Cannot modify inventory for a deactivated or suspended shop.", str(cm.exception))

    def test_set_exact_stock_inactive_merchant_rejection(self):
        """Deactivated merchant cannot modify inventory."""
        self.merchant1.status = Merchant.Status.DEACTIVATED
        self.merchant1.save()

        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.product1, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Only active merchants can modify shop inventory.", str(cm.exception))

    def test_set_exact_stock_variant_based_parent_product_rejected(self):
        """Attempting to set exact stock directly on a parent variant-based product is rejected."""
        with self.assertRaises(ValidationError) as cm:
            set_stock(self.shop1, self.variant_product, Decimal("10.000"), actor=self.merchant1)
        self.assertIn("Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted.", str(cm.exception))

    def test_set_stock_aliases_and_anti_bloat_mvp(self):
        """update_exact_stock and set_exact_stock work identically; no reason or movement tables exist."""
        import inspect
        from django.apps import apps

        # Test aliases work identically
        item1 = update_exact_stock(self.shop1, self.product1, Decimal("30.000"), actor=self.merchant1)
        self.assertEqual(item1.quantity, Decimal("30.000"))

        item2 = set_exact_stock(self.shop1, self.product1, Decimal("22.000"), actor=self.merchant1)
        self.assertEqual(item2.quantity, Decimal("22.000"))

        # Anti-bloat signature check
        set_params = inspect.signature(set_stock).parameters
        self.assertNotIn("reason", set_params)

        # Anti-bloat models check
        inventory_models = [m.__name__.lower() for m in apps.get_app_config("inventory").get_models()]
        self.assertNotIn("movement", inventory_models)
        self.assertNotIn("inventorymovement", inventory_models)
        self.assertNotIn("stockmovement", inventory_models)
        self.assertNotIn("history", inventory_models)


class MerchantInventoryAPITests(InventoryBaseTestCase):
    """
    Test suite for Task INV-007: Merchant inventory retrieval and update APIs.
    Validates standardized DRF API patterns, approved visibility values,
    strict Shop isolation, negative stock prevention, and variant granularity.
    """

    def setUp(self):
        super().setUp()
        # Non-variant product in Shop 1
        self.product1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Whole Wheat Flour",
            sku="FLOUR-01",
            price=Decimal("250.00"),
        )
        # Variant product in Shop 1
        self.var_product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Cold Pressed Coconut Oil",
            sku="OIL-01",
            price=Decimal("180.00"),
        )
        self.variant_500ml = ProductVariant.objects.create(
            product=self.var_product,
            name="500 ml Bottle",
            sku="OIL-500ML",
        )
        self.variant_1l = ProductVariant.objects.create(
            product=self.var_product,
            name="1 Litre Bottle",
            sku="OIL-1L",
        )

        # Products in Shop 2 for cross-tenant testing
        self.shop2_product = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop 2 Olive Oil",
            sku="SH2-OIL",
            price=Decimal("500.00"),
        )
        self.shop2_var_product = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop 2 Sugar",
            sku="SH2-SUGAR",
            price=Decimal("45.00"),
        )
        self.shop2_variant = ProductVariant.objects.create(
            product=self.shop2_var_product,
            name="1 kg Bag",
            sku="SH2-SUGAR-1KG",
        )

        # Super Admin user for security testing
        self.super_admin_user = User.objects.create_user(
            username="super_admin_inv007",
            email="superadmin007@example.com",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )

    def _get_authenticated_client(self, user, mobile_number, password="testpassword123"):
        client = APIClient()
        login_res = client.post(
            reverse("auth-login"),
            {"mobile_number": mobile_number, "password": password},
            format="json",
        )
        self.assertEqual(login_res.status_code, 200, f"Login failed for {mobile_number}: {login_res.data}")
        token = login_res.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def _get_super_admin_client(self):
        client = APIClient()
        login_res = client.post(
            reverse("auth-super-admin-login"),
            {"identifier": self.super_admin_user.email, "password": "adminpassword123"},
            format="json",
        )
        self.assertEqual(login_res.status_code, 200, f"Super Admin login failed: {login_res.data}")
        token = login_res.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def test_merchant_list_inventory_returns_only_own_shop_items(self):
        """Merchant inventory list returns only items belonging to their own Shop."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)

        # Test primary route: /api/v1/inventory/
        res = client1.get(reverse("inventory:merchant-inventory-list"))
        self.assertEqual(res.status_code, 200)

        data = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        self.assertGreater(len(data), 0)

        # All items must belong to Shop 1 (product1, variant_500ml, variant_1l)
        returned_products = [item["product"] for item in data]
        self.assertIn(self.product1.id, returned_products)
        self.assertIn(self.var_product.id, returned_products)
        self.assertNotIn(self.shop2_product.id, returned_products)
        self.assertNotIn(self.shop2_var_product.id, returned_products)

        # Test shop convenience route: /api/v1/shops/me/inventory/
        res_me = client1.get("/api/v1/shops/me/inventory/")
        self.assertEqual(res_me.status_code, 200)

    def test_merchant_retrieve_item_detail(self):
        """Merchant retrieves an inventory item with approved visibility attributes."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)

        res = client1.get(reverse("inventory:merchant-inventory-detail", kwargs={"pk": item.pk}))
        self.assertEqual(res.status_code, 200)

        expected_fields = [
            "id",
            "product",
            "product_name",
            "variant",
            "variant_name",
            "sku",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "is_out_of_stock",
            "has_variants",
        ]
        for field in expected_fields:
            self.assertIn(field, res.data, f"Field '{field}' missing from response")

        self.assertEqual(res.data["product_name"], "Organic Whole Wheat Flour")
        self.assertEqual(res.data["sku"], "FLOUR-01")
        self.assertEqual(Decimal(str(res.data["quantity"])), Decimal("0.000"))
        self.assertEqual(Decimal(str(res.data["reserved_quantity"])), Decimal("0.000"))
        self.assertEqual(Decimal(str(res.data["available_quantity"])), Decimal("0.000"))
        self.assertTrue(res.data["is_out_of_stock"])

    def test_merchant_cannot_retrieve_another_shop_item(self):
        """Merchant cannot retrieve an inventory item belonging to another Shop (returns 404)."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        shop2_item = InventoryItem.objects.get(product=self.shop2_product, variant__isnull=True)

        res = client1.get(reverse("inventory:merchant-inventory-detail", kwargs={"pk": shop2_item.pk}))
        self.assertEqual(res.status_code, 404)

    def test_merchant_set_exact_stock_api(self):
        """Merchant sets exact stock via PATCH and via /set-stock/ action."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)

        # 1. Standard PATCH /api/v1/inventory/<id>/ with quantity
        res = client1.patch(
            reverse("inventory:merchant-inventory-detail", kwargs={"pk": item.pk}),
            {"quantity": "50.000"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Decimal(str(res.data["quantity"])), Decimal("50.000"))
        self.assertEqual(Decimal(str(res.data["available_quantity"])), Decimal("50.000"))
        self.assertFalse(res.data["is_out_of_stock"])

        # 2. Detail action POST /api/v1/inventory/<id>/set-stock/
        res_action = client1.post(
            reverse("inventory:merchant-inventory-set-stock-action", kwargs={"pk": item.pk}),
            {"quantity": "25.000"},
            format="json",
        )
        self.assertEqual(res_action.status_code, 200)
        self.assertEqual(Decimal(str(res_action.data["quantity"])), Decimal("25.000"))

    def test_merchant_add_and_subtract_stock_actions(self):
        """Merchant adds and subtracts stock via dedicated detail action endpoints."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)

        # Add 30.000
        res_add = client1.post(
            reverse("inventory:merchant-inventory-add-stock-action", kwargs={"pk": item.pk}),
            {"quantity": "30.000"},
            format="json",
        )
        self.assertEqual(res_add.status_code, 200)
        self.assertEqual(Decimal(str(res_add.data["quantity"])), Decimal("30.000"))

        # Subtract 10.500
        res_sub = client1.post(
            reverse("inventory:merchant-inventory-subtract-stock-action", kwargs={"pk": item.pk}),
            {"quantity": "10.500"},
            format="json",
        )
        self.assertEqual(res_sub.status_code, 200)
        self.assertEqual(Decimal(str(res_sub.data["quantity"])), Decimal("19.500"))
        self.assertEqual(Decimal(str(res_sub.data["available_quantity"])), Decimal("19.500"))

    def test_subtract_below_zero_returns_400_bad_request(self):
        """Subtracting more stock than on-hand balance returns 400 Bad Request."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)
        set_stock(self.shop1, self.product1, Decimal("10.000"))

        res = client1.post(
            reverse("inventory:merchant-inventory-subtract-stock-action", kwargs={"pk": item.pk}),
            {"quantity": "10.001"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Cannot subtract stock below zero.", str(res.data))

    def test_update_below_reserved_stock_returns_400_bad_request(self):
        """Setting or subtracting stock below reserved quantity returns 400 Bad Request."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)
        set_stock(self.shop1, self.product1, Decimal("20.000"))
        reserve_order_stock(self.shop1, self.product1, Decimal("8.000"))

        # Setting exact stock to 5.000 (< reserved 8.000)
        res_set = client1.post(
            reverse("inventory:merchant-inventory-set-stock-action", kwargs={"pk": item.pk}),
            {"quantity": "5.000"},
            format="json",
        )
        self.assertEqual(res_set.status_code, 400)
        self.assertIn("Cannot set quantity lower than currently reserved quantity.", str(res_set.data))

        # Subtracting 15.000 (leaves 5.000 < reserved 8.000)
        res_sub = client1.post(
            reverse("inventory:merchant-inventory-subtract-stock-action", kwargs={"pk": item.pk}),
            {"quantity": "15.000"},
            format="json",
        )
        self.assertEqual(res_sub.status_code, 400)
        self.assertIn("Cannot subtract stock below reserved quantity.", str(res_sub.data))

    def test_negative_quantity_returns_400_bad_request(self):
        """Submitting negative quantities returns 400 Bad Request."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)

        res = client1.patch(
            reverse("inventory:merchant-inventory-detail", kwargs={"pk": item.pk}),
            {"quantity": "-5.000"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_excess_decimal_places_returns_400_bad_request(self):
        """Submitting quantities with >3 decimal places returns 400 Bad Request."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)

        res = client1.patch(
            reverse("inventory:merchant-inventory-detail", kwargs={"pk": item.pk}),
            {"quantity": "10.1234"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_super_admin_cannot_access_or_modify_merchant_inventory_api(self):
        """Super Admin cannot access or modify Merchant inventory APIs per Section 3."""
        admin_client = self._get_super_admin_client()

        res_list = admin_client.get(reverse("inventory:merchant-inventory-list"))
        self.assertEqual(res_list.status_code, 403)

        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)
        res_update = admin_client.patch(
            reverse("inventory:merchant-inventory-detail", kwargs={"pk": item.pk}),
            {"quantity": "50.000"},
            format="json",
        )
        self.assertEqual(res_update.status_code, 403)

    def test_customer_or_unauthenticated_cannot_access_api(self):
        """Anonymous callers are rejected with 401 Unauthorized."""
        anon_client = APIClient()
        res = anon_client.get(reverse("inventory:merchant-inventory-list"))
        self.assertEqual(res.status_code, 401)

    def test_deactivated_shop_returns_403_forbidden(self):
        """Deactivated shop returns 403 Forbidden with SHOP_INACTIVE."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        self.shop1.status = Shop.Status.DEACTIVATED
        self.shop1.save()

        res = client1.get(reverse("inventory:merchant-inventory-list"))
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data.get("code"), "SHOP_INACTIVE")

    def test_product_scoped_inventory_endpoint(self):
        """Product-scoped endpoint returns stock details and allows non-variant stock updates."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)

        # 1. Non-variant product stock retrieval
        res_non_var = client1.get(
            reverse("inventory:merchant-inventory-product-stock", kwargs={"product_id": self.product1.pk})
        )
        self.assertEqual(res_non_var.status_code, 200)
        self.assertEqual(res_non_var.data["product_id"], self.product1.pk)
        self.assertFalse(res_non_var.data["has_variants"])

        # Update non-variant product stock via POST
        res_update = client1.post(
            reverse("inventory:merchant-inventory-product-stock", kwargs={"product_id": self.product1.pk}),
            {"quantity": "40.000"},
            format="json",
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(Decimal(str(res_update.data["quantity"])), Decimal("40.000"))

        # 2. Variant-based product stock retrieval
        set_stock(self.shop1, self.variant_500ml, Decimal("15.000"))
        set_stock(self.shop1, self.variant_1l, Decimal("10.000"))

        res_var = client1.get(
            reverse("inventory:merchant-inventory-product-stock", kwargs={"product_id": self.var_product.pk})
        )
        self.assertEqual(res_var.status_code, 200)
        self.assertTrue(res_var.data["has_variants"])
        self.assertTrue(res_var.data["is_derived"])
        self.assertEqual(Decimal(str(res_var.data["quantity"])), Decimal("25.000"))
        self.assertEqual(len(res_var.data["variants"]), 2)

    def test_variant_scoped_inventory_endpoint(self):
        """Variant-scoped endpoint returns variant stock and allows variant stock updates."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)

        # GET variant stock
        res = client1.get(
            reverse("inventory:merchant-inventory-variant-stock", kwargs={"variant_id": self.variant_500ml.pk})
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["variant_id"], self.variant_500ml.pk)

        # POST update variant stock
        res_update = client1.post(
            reverse("inventory:merchant-inventory-variant-stock", kwargs={"variant_id": self.variant_500ml.pk}),
            {"action": "set", "quantity": "35.000"},
            format="json",
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(Decimal(str(res_update.data["quantity"])), Decimal("35.000"))

        # Derived aggregate updates
        parent_stock = get_product_stock(self.var_product)
        self.assertEqual(parent_stock["quantity"], Decimal("35.000"))

    def test_variant_based_parent_product_direct_stock_modification_rejected(self):
        """Direct stock modification on a variant-based parent product is strictly rejected."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)

        res = client1.post(
            reverse("inventory:merchant-inventory-product-stock", kwargs={"product_id": self.var_product.pk}),
            {"quantity": "100.000"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted.", str(res.data))

    def test_direct_create_and_destroy_not_allowed(self):
        """Direct POST to /inventory/ and DELETE to /inventory/<id>/ are not allowed (405)."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)

        res_post = client1.post(reverse("inventory:merchant-inventory-list"), {"quantity": "10.000"}, format="json")
        self.assertEqual(res_post.status_code, 405)

        res_delete = client1.delete(reverse("inventory:merchant-inventory-detail", kwargs={"pk": item.pk}))
        self.assertEqual(res_delete.status_code, 405)

    def test_no_thresholds_or_movement_history_exposed(self):
        """Response payloads never expose low-stock thresholds, alerts, or movement history ledgers."""
        client1 = self._get_authenticated_client(self.user1, self.user1.mobile_number)
        item = InventoryItem.objects.get(product=self.product1, variant__isnull=True)

        res_detail = client1.get(reverse("inventory:merchant-inventory-detail", kwargs={"pk": item.pk}))
        data = res_detail.data

        forbidden_keys = [
            "low_stock_threshold",
            "threshold",
            "alert",
            "movements",
            "movement_history",
            "history",
            "reason",
        ]
        for key in forbidden_keys:
            self.assertNotIn(key, data, f"Forbidden key '{key}' exposed in API response")


class OrderCreationInventoryReservationIntegrationTests(InventoryBaseTestCase):
    """
    INV-008: Integration of Inventory Reservation with Order Creation.

    Pillars verified:
    1. Order creation reserves requested quantities; checkout does NOT deduct stock.
    2. Multi-item batch and Cart instance reservation integration.
    3. Insufficient stock rejects checkout without automatic quantity reduction or clamping.
    4. Merchant-controlled partial-quantity adjustment (single and multi-item) releases
       the unfulfilled difference and deducts the accepted quantity.
    5. Zero customer confirmation workflows invented (merchant directly controls adjustment).
    6. Shop isolation and multi-tenant security boundary enforcement.
    """

    def setUp(self):
        super().setUp()
        # Non-variant products for Shop 1
        self.prod1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Basmati Rice",
            price=Decimal("150.00"),
        )
        adjust_stock(self.shop1, self.prod1, set_quantity=Decimal("50.000"))

        self.prod2 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Cold Pressed Mustard Oil",
            price=Decimal("220.00"),
        )
        adjust_stock(self.shop1, self.prod2, set_quantity=Decimal("20.000"))

        # Variant product for Shop 1
        self.var_prod = ShopProduct.objects.create(
            shop=self.shop1,
            name="Fresh Milk",
            price=Decimal("60.00"),
        )
        self.var_500ml = ProductVariant.objects.create(
            product=self.var_prod,
            name="500 ml",
            price=Decimal("30.00"),
        )
        self.var_1000ml = ProductVariant.objects.create(
            product=self.var_prod,
            name="1000 ml",
            price=Decimal("60.00"),
        )
        adjust_stock(self.shop1, self.var_500ml, set_quantity=Decimal("30.000"))
        adjust_stock(self.shop1, self.var_1000ml, set_quantity=Decimal("25.000"))

        # Shop 2 product for cross-shop isolation tests
        self.shop2_prod = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop Two Product",
            price=Decimal("99.00"),
        )
        adjust_stock(self.shop2, self.shop2_prod, set_quantity=Decimal("40.000"))

    def test_order_creation_reserves_stock_without_deducting_on_hand(self):
        """
        Pillar 1: Order creation reserves requested quantity.
        Checkout does NOT deduct stock: reserved_quantity increases, but
        on-hand quantity remains constant until Merchant acceptance.
        """
        # Initial state: 50.000 on hand, 0 reserved, 50.000 available
        item = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("50.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("50.000"))

        # Customer creates order with 12.500 kg
        reserved_items = reserve_order_creation_stock(
            self.shop1,
            [(self.prod1, Decimal("12.500"))],
        )

        item.refresh_from_db()
        self.assertEqual(len(reserved_items), 1)
        # CRITICAL INVARIANT: On-hand stock is NOT deducted at checkout!
        self.assertEqual(item.quantity, Decimal("50.000"))
        # Reserved stock is incremented by requested quantity
        self.assertEqual(item.reserved_quantity, Decimal("12.500"))
        # Available stock is reduced by reserved quantity
        self.assertEqual(item.available_quantity, Decimal("37.500"))

    def test_order_creation_reserves_variant_stock_without_deducting(self):
        """
        Pillar 1b: Variant stock is authoritative.
        Order creation reserves variant stock without deducting on-hand stock.
        """
        item_500 = InventoryItem.objects.get(variant=self.var_500ml)
        self.assertEqual(item_500.quantity, Decimal("30.000"))
        self.assertEqual(item_500.reserved_quantity, Decimal("0.000"))

        # Order creation reserves 8.000 units of 500ml variant
        reserve_order_creation_stock(
            self.shop1,
            [(self.var_500ml, Decimal("8.000"))],
        )

        item_500.refresh_from_db()
        # On-hand quantity unchanged (checkout does NOT deduct)
        self.assertEqual(item_500.quantity, Decimal("30.000"))
        self.assertEqual(item_500.reserved_quantity, Decimal("8.000"))
        self.assertEqual(item_500.available_quantity, Decimal("22.000"))

        # Aggregate product stock reflects the reservation
        agg = get_product_stock(self.var_prod)
        self.assertEqual(agg["quantity"], Decimal("55.000"))  # 30 + 25
        self.assertEqual(agg["reserved_quantity"], Decimal("8.000"))
        self.assertEqual(agg["available_quantity"], Decimal("47.000"))

    def test_order_creation_from_cart_instance(self):
        """
        Pillar 2: Order creation can accept a Cart instance directly.
        All cart items are extracted, shop-validated, and atomically reserved.
        """
        cart = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(cart=cart, product=self.prod1, quantity=Decimal("5.000"))
        CartItem.objects.create(cart=cart, product=self.var_prod, variant=self.var_1000ml, quantity=Decimal("4.000"))

        reserved = reserve_order_creation_stock(self.shop1, cart)
        self.assertEqual(len(reserved), 2)

        item1 = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        item_var = InventoryItem.objects.get(variant=self.var_1000ml)

        # Neither item has on-hand stock deducted
        self.assertEqual(item1.quantity, Decimal("50.000"))
        self.assertEqual(item1.reserved_quantity, Decimal("5.000"))
        self.assertEqual(item1.available_quantity, Decimal("45.000"))

        self.assertEqual(item_var.quantity, Decimal("25.000"))
        self.assertEqual(item_var.reserved_quantity, Decimal("4.000"))
        self.assertEqual(item_var.available_quantity, Decimal("21.000"))

    def test_insufficient_stock_fails_without_automatic_quantity_reduction(self):
        """
        Pillar 3: Rejection on insufficient stock without automatic reduction.
        The system does NOT automatically clamp or reduce quantities.
        """
        # prod2 has 20.000 available
        item2 = InventoryItem.objects.get(product=self.prod2, variant__isnull=True)
        self.assertEqual(item2.available_quantity, Decimal("20.000"))

        # Customer attempts to order 25.000 kg
        with self.assertRaises(ValidationError) as cm:
            reserve_order_creation_stock(
                self.shop1,
                [(self.prod2, Decimal("25.000"))],
            )
        self.assertIn("Insufficient stock for 'Cold Pressed Mustard Oil'", str(cm.exception))

        item2.refresh_from_db()
        # Verify no automatic quantity reduction occurred:
        # Stock state is completely untouched
        self.assertEqual(item2.quantity, Decimal("20.000"))
        self.assertEqual(item2.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item2.available_quantity, Decimal("20.000"))

    def test_multi_item_order_creation_atomic_rollback_on_failure(self):
        """
        Pillar 3b: If ANY line item in a multi-item order has insufficient stock,
        the entire order reservation transaction rolls back cleanly.
        """
        items_and_qty = [
            (self.prod1, Decimal("10.000")),       # 50 available -> sufficient
            (self.prod2, Decimal("30.000")),       # 20 available -> INSUFFICIENT!
            (self.var_500ml, Decimal("5.000")),    # 30 available -> sufficient
        ]

        with self.assertRaises(ValidationError) as cm:
            reserve_order_creation_stock(self.shop1, items_and_qty)
        self.assertIn("Insufficient stock for 'Cold Pressed Mustard Oil'", str(cm.exception))

        # Check atomicity: prod1 and var_500ml must have ZERO reserved quantity
        item1 = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        item2 = InventoryItem.objects.get(product=self.prod2, variant__isnull=True)
        item_var = InventoryItem.objects.get(variant=self.var_500ml)

        self.assertEqual(item1.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item2.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item_var.reserved_quantity, Decimal("0.000"))

    def test_merchant_controlled_partial_quantity_adjustment_single_item(self):
        """
        Pillar 4: Merchant-controlled partial-quantity adjustment.
        When customer requested 10.000, but merchant only fulfills 6.000 before acceptance:
        - The unfulfilled difference (4.000) is released back to available stock.
        - The accepted quantity (6.000) is deducted from on-hand stock.
        - No customer confirmation prompt/workflow is invented.
        """
        # Step 1: Order created (10.000 reserved)
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("10.000"))])
        item1 = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        self.assertEqual(item1.quantity, Decimal("50.000"))
        self.assertEqual(item1.reserved_quantity, Decimal("10.000"))
        self.assertEqual(item1.available_quantity, Decimal("40.000"))

        # Step 2: Merchant reviews order, reduces fulfillable quantity to 6.000, and accepts
        updated_item = reduce_and_accept_order_stock(
            self.shop1,
            self.prod1,
            original_reserved=Decimal("10.000"),
            accepted_quantity=Decimal("6.000"),
        )

        # On-hand stock is deducted by accepted amount: 50.000 - 6.000 = 44.000
        self.assertEqual(updated_item.quantity, Decimal("44.000"))
        # Reserved stock drops to 0.000
        self.assertEqual(updated_item.reserved_quantity, Decimal("0.000"))
        # Available stock is now 44.000 (40.000 original available + 4.000 unfulfilled released)
        self.assertEqual(updated_item.available_quantity, Decimal("44.000"))

    def test_merchant_controlled_partial_quantity_adjustment_multi_item(self):
        """
        Pillar 4b: Multi-item merchant partial-quantity adjustment.
        Atomically adjusts multiple items across an order before acceptance.
        """
        # Step 1: Order created with 2 items
        reserve_order_creation_stock(
            self.shop1,
            [
                (self.prod1, Decimal("10.000")),
                (self.prod2, Decimal("8.000")),
            ],
        )

        item1 = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        item2 = InventoryItem.objects.get(product=self.prod2, variant__isnull=True)
        self.assertEqual(item1.reserved_quantity, Decimal("10.000"))
        self.assertEqual(item2.reserved_quantity, Decimal("8.000"))

        # Step 2: Merchant adjusts:
        # Prod 1: requested 10.000 -> accepted 7.000 (3.000 released, 7.000 deducted)
        # Prod 2: requested 8.000 -> accepted 5.000 (3.000 released, 5.000 deducted)
        adjustments = [
            (self.prod1, Decimal("10.000"), Decimal("7.000")),
            (self.prod2, Decimal("8.000"), Decimal("5.000")),
        ]
        updated = reduce_and_accept_order_items_stock(self.shop1, adjustments)
        self.assertEqual(len(updated), 2)

        item1.refresh_from_db()
        item2.refresh_from_db()

        # Prod 1: on-hand 50 - 7 = 43.000, reserved 0, available 43.000
        self.assertEqual(item1.quantity, Decimal("43.000"))
        self.assertEqual(item1.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item1.available_quantity, Decimal("43.000"))

        # Prod 2: on-hand 20 - 5 = 15.000, reserved 0, available 15.000
        self.assertEqual(item2.quantity, Decimal("15.000"))
        self.assertEqual(item2.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item2.available_quantity, Decimal("15.000"))

    def test_merchant_partial_adjustment_invalid_quantities_rejected(self):
        """
        Pillar 4c: Validation rejects invalid partial adjustment quantities.
        - Accepted quantity cannot exceed originally reserved quantity.
        - Accepted quantity cannot be negative.
        """
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("10.000"))])

        # Exceeds originally reserved
        with self.assertRaises(ValidationError) as cm:
            reduce_and_accept_order_items_stock(
                self.shop1,
                [(self.prod1, Decimal("10.000"), Decimal("12.000"))],
            )
        self.assertIn("cannot exceed originally reserved quantity", str(cm.exception))

        # Negative accepted quantity
        with self.assertRaises(ValidationError) as cm:
            reduce_and_accept_order_items_stock(
                self.shop1,
                [(self.prod1, Decimal("10.000"), Decimal("-1.000"))],
            )
        self.assertIn("cannot be negative", str(cm.exception))

    def test_shop_isolation_order_creation_reservation(self):
        """
        Pillar 5: Shop isolation is strictly enforced.
        - Cannot reserve stock for another shop's products.
        - Cannot use a Cart belonging to Shop 2 to reserve in Shop 1.
        """
        # Attempt to reserve Shop 2 product within Shop 1 context
        with self.assertRaises(ValidationError) as cm:
            reserve_order_creation_stock(
                self.shop1,
                [(self.shop2_prod, Decimal("5.000"))],
            )
        self.assertIn("authorized shop", str(cm.exception))

        # Attempt to reserve using a Cart from Shop 2 within Shop 1 context
        cart_shop2 = Cart.objects.create(shop=self.shop2)
        CartItem.objects.create(cart=cart_shop2, product=self.shop2_prod, quantity=Decimal("2.000"))

        with self.assertRaises(ValidationError) as cm:
            reserve_order_creation_stock(self.shop1, cart_shop2)
        self.assertIn("Cart does not belong to the specified shop", str(cm.exception))

    def test_empty_cart_or_items_rejected(self):
        """Empty Cart or empty items sequence raises ValidationError."""
        empty_cart = Cart.objects.create(shop=self.shop1)
        with self.assertRaises(ValidationError) as cm:
            reserve_order_creation_stock(self.shop1, empty_cart)
        self.assertIn("Cannot reserve inventory for an empty cart", str(cm.exception))

        with self.assertRaises(ValidationError) as cm:
            reserve_order_creation_stock(self.shop1, [])
        self.assertIn("Cannot reserve inventory for an empty order item list", str(cm.exception))


class MerchantOrderAcceptanceStockDeductionIntegrationTests(InventoryBaseTestCase):
    """
    INV-009: Integration of stock deduction with Merchant Order acceptance.

    Pillars verified:
    1. Stock is deducted strictly on Merchant acceptance, NOT at checkout.
    2. Available and reserved stock semantics are preserved identically across acceptance.
    3. Merchant partial-quantity adjustments release unfulfilled differences and deduct accepted quantities.
    4. Multi-item batch acceptance executed atomically with deterministic lock ordering (ADR-0001, ADR-0003).
    5. Deductions exceeding reserved stock are strictly rejected.
    6. Merchant authorization is strictly enforced (Super Admin and cross-shop merchants rejected).
    7. Shop isolation prevents cross-shop deductions.
    """

    def setUp(self):
        super().setUp()
        self.prod1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Basmati Rice",
            price=Decimal("150.00"),
        )
        adjust_stock(self.shop1, self.prod1, set_quantity=Decimal("100.000"))

        self.prod2 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Cold Pressed Mustard Oil",
            price=Decimal("220.00"),
        )
        adjust_stock(self.shop1, self.prod2, set_quantity=Decimal("40.000"))

        # Variant product for Shop 1
        self.var_prod = ShopProduct.objects.create(
            shop=self.shop1,
            name="Fresh Milk",
            price=Decimal("60.00"),
        )
        self.var_500ml = ProductVariant.objects.create(
            product=self.var_prod,
            name="500 ml",
            price=Decimal("30.00"),
        )
        self.var_1000ml = ProductVariant.objects.create(
            product=self.var_prod,
            name="1000 ml",
            price=Decimal("60.00"),
        )
        adjust_stock(self.shop1, self.var_500ml, set_quantity=Decimal("30.000"))
        adjust_stock(self.shop1, self.var_1000ml, set_quantity=Decimal("25.000"))

        # Shop 2 product for cross-shop isolation tests
        self.shop2_prod = ShopProduct.objects.create(
            shop=self.shop2,
            name="Shop Two Product",
            price=Decimal("99.00"),
        )
        adjust_stock(self.shop2, self.shop2_prod, set_quantity=Decimal("50.000"))

    def test_stock_deduction_occurs_on_acceptance_not_at_checkout(self):
        """
        Pillar 1: Order creation reserves stock; acceptance deducts stock.
        On full acceptance:
        - quantity drops by accepted amount (reserved becomes deducted)
        - reserved_quantity drops to 0.000
        - available_quantity remains constant for other shoppers!
        """
        item = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("100.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("100.000"))

        # Step 1: Customer creates Order with 25.000 kg (Checkout stage)
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("25.000"))])
        item.refresh_from_db()

        # Checkout does NOT deduct stock
        self.assertEqual(item.quantity, Decimal("100.000"))
        self.assertEqual(item.reserved_quantity, Decimal("25.000"))
        self.assertEqual(item.available_quantity, Decimal("75.000"))

        # Step 2: Merchant accepts the Order (Acceptance stage)
        deducted = deduct_order_acceptance_stock(
            self.shop1,
            [(self.prod1, Decimal("25.000"))],
            actor=self.merchant1,
        )
        self.assertEqual(len(deducted), 1)

        item.refresh_from_db()
        # On-hand stock is officially deducted on acceptance: 100 - 25 = 75
        self.assertEqual(item.quantity, Decimal("75.000"))
        # Reserved stock drops to 0
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        # Available stock remains 75.000 (preserved available semantics)
        self.assertEqual(item.available_quantity, Decimal("75.000"))

    def test_variant_stock_acceptance_deduction_and_aggregate_semantics(self):
        """
        Pillar 1b: Variant stock deduction preserves authoritative variant
        and aggregate product stock semantics.
        """
        # Reserve 10.000 of 500ml variant
        reserve_order_creation_stock(self.shop1, [(self.var_500ml, Decimal("10.000"))])

        item_500 = InventoryItem.objects.get(variant=self.var_500ml)
        self.assertEqual(item_500.quantity, Decimal("30.000"))
        self.assertEqual(item_500.reserved_quantity, Decimal("10.000"))
        self.assertEqual(item_500.available_quantity, Decimal("20.000"))

        # Merchant accepts order
        deduct_order_acceptance_stock(
            self.shop1,
            [(self.var_500ml, Decimal("10.000"))],
            actor=self.merchant1,
        )

        item_500.refresh_from_db()
        self.assertEqual(item_500.quantity, Decimal("20.000"))
        self.assertEqual(item_500.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item_500.available_quantity, Decimal("20.000"))

        # Aggregate product stock derived from variants:
        # 500ml: 20 on hand; 1000ml: 25 on hand -> Total 45.000
        agg = get_product_stock(self.var_prod)
        self.assertEqual(agg["quantity"], Decimal("45.000"))
        self.assertEqual(agg["reserved_quantity"], Decimal("0.000"))
        self.assertEqual(agg["available_quantity"], Decimal("45.000"))

    def test_partial_quantity_acceptance_stock_deduction_semantics(self):
        """
        Pillar 2: Partial-quantity acceptance:
        - Customer requested 20.000 (reserved).
        - Merchant only fulfills 12.000 before acceptance.
        - Unfulfilled difference (8.000) is released back to available stock.
        - Accepted quantity (12.000) is deducted from on-hand stock.
        """
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("20.000"))])
        item = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("100.000"))
        self.assertEqual(item.reserved_quantity, Decimal("20.000"))
        self.assertEqual(item.available_quantity, Decimal("80.000"))

        # Merchant accepts partial quantity: original 20.000 -> accepted 12.000
        deduct_order_acceptance_stock(
            self.shop1,
            [(self.prod1, Decimal("20.000"), Decimal("12.000"))],
            actor=self.merchant1,
        )

        item.refresh_from_db()
        # On-hand drops by accepted 12.000: 100 - 12 = 88.000
        self.assertEqual(item.quantity, Decimal("88.000"))
        # Reserved drops to 0.000
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        # Available is 88.000 (80.000 original available + 8.000 released difference)
        self.assertEqual(item.available_quantity, Decimal("88.000"))

    def test_multi_item_order_acceptance_atomic_deduction(self):
        """
        Pillar 3: Multi-item batch acceptance executed atomically with
        deadlock-free deterministic lock sorting.
        """
        reserve_order_creation_stock(
            self.shop1,
            [
                (self.prod1, Decimal("15.000")),
                (self.prod2, Decimal("10.000")),
            ],
        )

        item1 = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        item2 = InventoryItem.objects.get(product=self.prod2, variant__isnull=True)
        self.assertEqual(item1.reserved_quantity, Decimal("15.000"))
        self.assertEqual(item2.reserved_quantity, Decimal("10.000"))

        # Merchant accepts both items
        deducted = deduct_order_acceptance_stock(
            self.shop1,
            [
                (self.prod1, Decimal("15.000")),
                (self.prod2, Decimal("10.000")),
            ],
            actor=self.merchant1,
        )
        self.assertEqual(len(deducted), 2)

        item1.refresh_from_db()
        item2.refresh_from_db()

        self.assertEqual(item1.quantity, Decimal("85.000"))
        self.assertEqual(item1.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item1.available_quantity, Decimal("85.000"))

        self.assertEqual(item2.quantity, Decimal("30.000"))
        self.assertEqual(item2.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item2.available_quantity, Decimal("30.000"))

    def test_deduct_more_than_reserved_rejected(self):
        """
        Pillar 4: Cannot deduct more than currently reserved stock.
        """
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("10.000"))])

        # Attempt to deduct 15.000 when only 10.000 is reserved
        with self.assertRaises(ValidationError) as cm:
            deduct_order_acceptance_stock(
                self.shop1,
                [(self.prod1, Decimal("15.000"))],
                actor=self.merchant1,
            )
        self.assertIn("Cannot deduct more than currently reserved stock", str(cm.exception))

        item = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        # Verify rollback: stock remains 100 on-hand, 10 reserved
        self.assertEqual(item.quantity, Decimal("100.000"))
        self.assertEqual(item.reserved_quantity, Decimal("10.000"))

    def test_deduct_negative_or_zero_quantity_rejected(self):
        """
        Pillar 4b: Deducting negative or zero quantity raises ValidationError.
        """
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("10.000"))])

        with self.assertRaises(ValidationError) as cm:
            deduct_order_acceptance_stock(
                self.shop1,
                [(self.prod1, Decimal("0.000"))],
                actor=self.merchant1,
            )
        self.assertIn("must be greater than zero", str(cm.exception))

    def test_merchant_authorization_enforced_on_acceptance(self):
        """
        Pillar 5: Merchant authorization enforcement:
        - Active owner merchant succeeds.
        - Super Admin is rejected (MVP rule).
        - Merchant from another shop is rejected.
        """
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("5.000"))])

        # Super Admin rejected
        super_admin = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="testpassword123",
            role=User.Role.SUPER_ADMIN,
        )
        with self.assertRaises(ValidationError) as cm:
            deduct_order_acceptance_stock(
                self.shop1,
                [(self.prod1, Decimal("5.000"))],
                actor=super_admin,
            )
        self.assertIn("Super Admin is not authorized", str(cm.exception))

        # Merchant of Shop 2 rejected for Shop 1
        with self.assertRaises(ValidationError) as cm:
            deduct_order_acceptance_stock(
                self.shop1,
                [(self.prod1, Decimal("5.000"))],
                actor=self.merchant2,
            )
        self.assertIn("not authorized to modify inventory for this shop", str(cm.exception))

    def test_cross_shop_product_deduction_rejected(self):
        """
        Pillar 6: Shop isolation prevents deducting products belonging to another shop.
        """
        with self.assertRaises(ValidationError) as cm:
            deduct_order_acceptance_stock(
                self.shop1,
                [(self.shop2_prod, Decimal("5.000"))],
                actor=self.merchant1,
            )
        self.assertIn("authorized shop", str(cm.exception))

    def test_order_container_duck_typing_acceptance(self):
        """
        Pillar 7: Duck-typed container/order object acceptance.
        """
        reserve_order_creation_stock(self.shop1, [(self.prod1, Decimal("8.000"))])

        # Simulate an Order object with items
        class DummyOrderItem:
            def __init__(self, product, ordered_quantity, accepted_quantity):
                self.product = product
                self.variant = None
                self.ordered_quantity = ordered_quantity
                self.accepted_quantity = accepted_quantity

        class DummyOrder:
            def __init__(self, shop, items):
                self.shop = shop
                self.shop_id = shop.id
                self._items = items

            class Manager:
                def __init__(self, items):
                    self._items = items
                def all(self):
                    return self._items

            @property
            def items(self):
                return self.Manager(self._items)

        order = DummyOrder(self.shop1, [DummyOrderItem(self.prod1, Decimal("8.000"), Decimal("8.000"))])
        deducted = deduct_order_acceptance_stock(self.shop1, order, actor=self.merchant1)
        self.assertEqual(len(deducted), 1)

        item = InventoryItem.objects.get(product=self.prod1, variant__isnull=True)
        self.assertEqual(item.quantity, Decimal("92.000"))
        self.assertEqual(item.reserved_quantity, Decimal("0.000"))
        self.assertEqual(item.available_quantity, Decimal("92.000"))








