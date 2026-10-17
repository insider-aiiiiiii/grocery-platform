from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from catalog.models import ProductVariant, ShopProduct
from customers.models import Customer
from shops.models import Shop
from users.models import Merchant, User

from .models import Cart, CartItem, validate_positive_quantity


class CartModelTests(TestCase):
    """Unit and domain tests for CART-001 Shop-scoped Cart and CartItem models."""

    def setUp(self):
        # Setup Merchant 1 and Shop 1
        self.user1 = User.objects.create_user(
            username="merchant_1",
            email="merchant1@example.com",
            mobile_number="+919876543211",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            status=Merchant.Status.ACTIVE,
        )
        self.shop1 = Shop.objects.create(
            merchant=self.merchant1,
            name="Alpha Groceries",
            address_line="100 First Street",
            area="North",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=self.user1.mobile_number,
        )

        # Setup Merchant 2 and Shop 2 (for multi-tenancy tests)
        self.user2 = User.objects.create_user(
            username="merchant_2",
            email="merchant2@example.com",
            mobile_number="+919876543212",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            status=Merchant.Status.ACTIVE,
        )
        self.shop2 = Shop.objects.create(
            merchant=self.merchant2,
            name="Beta Mart",
            address_line="200 Second Street",
            area="South",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            contact_number=self.user2.mobile_number,
        )

        # Shop 1 Catalog Products
        self.product1_s1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Fresh Milk 1L",
            price=Decimal("60.00"),
        )
        self.product2_s1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Basmati Rice",
            price=Decimal("120.00"),
        )
        self.variant1_s1 = ProductVariant.objects.create(
            product=self.product2_s1,
            name="1kg Pack",
            price=Decimal("130.00"),
        )
        self.variant2_s1 = ProductVariant.objects.create(
            product=self.product2_s1,
            name="5kg Pack",
            price=Decimal("600.00"),
        )

        # Shop 2 Catalog Products
        self.product1_s2 = ShopProduct.objects.create(
            shop=self.shop2,
            name="Organic Milk 1L",
            price=Decimal("75.00"),
        )
        self.variant1_s2 = ProductVariant.objects.create(
            product=self.product1_s2,
            name="Tetra Pack",
            price=Decimal("80.00"),
        )

        # Shop 1 Customer
        self.customer_s1 = Customer.objects.create(
            shop=self.shop1,
            name="Anand Sharma",
            whatsapp_number="+919876500001",
        )

        # Shop 2 Customer
        self.customer_s2 = Customer.objects.create(
            shop=self.shop2,
            name="Pooja Verma",
            whatsapp_number="+919876500002",
        )

    # 1. Cart creation and customer association
    def test_create_anonymous_cart(self):
        """Cart can exist anonymously without a Customer in a specific Shop."""
        cart = Cart.objects.create(shop=self.shop1)
        self.assertEqual(cart.shop, self.shop1)
        self.assertIsNone(cart.customer)
        self.assertIn("Anonymous", str(cart))
        self.assertIn(f"Shop: {self.shop1.id}", str(cart))

    def test_create_cart_with_same_shop_customer(self):
        """Cart can be associated with a Customer belonging to the same Shop."""
        cart = Cart.objects.create(shop=self.shop1, customer=self.customer_s1)
        self.assertEqual(cart.shop, self.shop1)
        self.assertEqual(cart.customer, self.customer_s1)
        self.assertIn(f"Customer: {self.customer_s1.id}", str(cart))

    def test_reject_cart_with_customer_from_different_shop(self):
        """Cart cannot be associated with a Customer from another Shop."""
        cart = Cart(shop=self.shop1, customer=self.customer_s2)
        with self.assertRaises(ValidationError) as ctx:
            cart.full_clean()
        self.assertIn("customer", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            cart.save()

    # 2. CartItem creation & multi-tenant isolation
    def test_add_cart_item_shop_product(self):
        """CartItem can reference a ShopProduct belonging to the Cart's Shop."""
        cart = Cart.objects.create(shop=self.shop1)
        item = CartItem.objects.create(
            cart=cart,
            product=self.product1_s1,
            quantity=Decimal("2.000"),
        )
        self.assertEqual(item.cart, cart)
        self.assertEqual(item.product, self.product1_s1)
        self.assertIsNone(item.variant)
        self.assertEqual(item.quantity, Decimal("2.000"))
        self.assertEqual(item.unit_price, Decimal("60.00"))
        self.assertEqual(item.line_total, Decimal("120.00"))

    def test_add_cart_item_with_variant(self):
        """CartItem can reference a ProductVariant belonging to the selected Product."""
        cart = Cart.objects.create(shop=self.shop1)
        item = CartItem.objects.create(
            cart=cart,
            product=self.product2_s1,
            variant=self.variant1_s1,
            quantity=Decimal("3.000"),
        )
        self.assertEqual(item.variant, self.variant1_s1)
        self.assertEqual(item.unit_price, Decimal("130.00"))
        self.assertEqual(item.line_total, Decimal("390.00"))
        self.assertIn("Variant: 1kg Pack", str(item))

    def test_reject_cart_item_from_different_shop_product(self):
        """Cart cannot contain products from a different Shop."""
        cart_s1 = Cart.objects.create(shop=self.shop1)
        item = CartItem(
            cart=cart_s1,
            product=self.product1_s2,  # belongs to shop2!
            quantity=Decimal("1.000"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("product", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            item.save()

    def test_reject_cart_item_with_variant_from_different_product(self):
        """CartItem cannot reference a variant that does not belong to the selected product."""
        cart = Cart.objects.create(shop=self.shop1)
        item = CartItem(
            cart=cart,
            product=self.product1_s1,  # Fresh Milk
            variant=self.variant1_s1,  # variant of Basmati Rice!
            quantity=Decimal("1.000"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("variant", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            item.save()

    def test_reject_cart_item_with_variant_from_different_shop(self):
        """CartItem cannot reference a variant from another Shop."""
        cart = Cart.objects.create(shop=self.shop1)
        item = CartItem(
            cart=cart,
            product=self.product1_s2,  # product from shop2
            variant=self.variant1_s2,  # variant from shop2
            quantity=Decimal("1.000"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("product", ctx.exception.message_dict)

    # 3. Quantity validation & precision
    def test_reject_non_positive_quantity(self):
        """Cart item quantity must be strictly greater than zero."""
        cart = Cart.objects.create(shop=self.shop1)

        # Zero quantity
        item_zero = CartItem(cart=cart, product=self.product1_s1, quantity=Decimal("0.000"))
        with self.assertRaises(ValidationError):
            item_zero.save()

        # Negative quantity
        item_neg = CartItem(cart=cart, product=self.product1_s1, quantity=Decimal("-1.500"))
        with self.assertRaises(ValidationError):
            item_neg.save()

    def test_quantity_check_constraint_at_database_level(self):
        """Database check constraint enforces quantity > 0 even if clean() is bypassed."""
        cart = Cart.objects.create(shop=self.shop1)
        with self.assertRaises(IntegrityError):
            CartItem.objects.bulk_create([
                CartItem(cart=cart, product=self.product1_s1, quantity=Decimal("0.000"))
            ])

    def test_reject_quantity_excessive_decimal_places(self):
        """Quantities with more than 3 decimal places are rejected."""
        cart = Cart.objects.create(shop=self.shop1)
        item = CartItem(cart=cart, product=self.product1_s1, quantity=Decimal("1.1234"))
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("3 decimal places", str(ctx.exception))

    def test_valid_decimal_quantities_and_quantization(self):
        """Valid quantities with up to 3 decimal places are correctly quantized and stored."""
        cart = Cart.objects.create(shop=self.shop1)
        item = CartItem.objects.create(
            cart=cart,
            product=self.product1_s1,
            quantity=Decimal("2.5"),
        )
        self.assertEqual(item.quantity, Decimal("2.500"))

        item2 = CartItem.objects.create(
            cart=cart,
            product=self.product2_s1,
            variant=self.variant1_s1,
            quantity="0.75",
        )
        self.assertEqual(item2.quantity, Decimal("0.750"))

    # 4. Uniqueness constraints
    def test_unique_constraint_same_product_no_variant(self):
        """Cannot add the same product without a variant more than once in the same cart."""
        cart = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("1.000"))

        # Validation at save/full_clean level
        with self.assertRaises((ValidationError, IntegrityError)):
            CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("2.000"))

        # Enforcement at database level
        with self.assertRaises(IntegrityError):
            CartItem.objects.bulk_create([
                CartItem(cart=cart, product=self.product1_s1, quantity=Decimal("3.000"))
            ])

    def test_unique_constraint_same_variant(self):
        """Cannot add the same variant more than once in the same cart."""
        cart = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(
            cart=cart,
            product=self.product2_s1,
            variant=self.variant1_s1,
            quantity=Decimal("1.000"),
        )

        # Validation at save/full_clean level
        with self.assertRaises((ValidationError, IntegrityError)):
            CartItem.objects.create(
                cart=cart,
                product=self.product2_s1,
                variant=self.variant1_s1,
                quantity=Decimal("2.000"),
            )

        # Enforcement at database level
        with self.assertRaises(IntegrityError):
            CartItem.objects.bulk_create([
                CartItem(cart=cart, product=self.product2_s1, variant=self.variant1_s1, quantity=Decimal("3.000"))
            ])

    def test_can_have_multiple_different_variants_of_same_product(self):
        """A cart can contain multiple distinct variants of the same product."""
        cart = Cart.objects.create(shop=self.shop1)
        item1 = CartItem.objects.create(
            cart=cart,
            product=self.product2_s1,
            variant=self.variant1_s1,
            quantity=Decimal("1.000"),
        )
        item2 = CartItem.objects.create(
            cart=cart,
            product=self.product2_s1,
            variant=self.variant2_s1,
            quantity=Decimal("2.000"),
        )
        self.assertEqual(cart.items.count(), 2)
        self.assertEqual(item1.variant, self.variant1_s1)
        self.assertEqual(item2.variant, self.variant2_s1)

    # 5. Cart helper properties
    def test_cart_helpers_count_quantity_subtotal(self):
        """Cart item_count, total_quantity, and subtotal reflect items accurately."""
        cart = Cart.objects.create(shop=self.shop1)
        # item 1: 2 * 60.00 = 120.00
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("2.000"))
        # item 2: 1.5 * 130.00 = 195.00
        CartItem.objects.create(
            cart=cart,
            product=self.product2_s1,
            variant=self.variant1_s1,
            quantity=Decimal("1.500"),
        )

        self.assertEqual(cart.item_count, 2)
        self.assertEqual(cart.total_quantity, Decimal("3.500"))
        self.assertEqual(cart.subtotal, Decimal("315.00"))

    # 6. Cascade behavior
    def test_shop_deletion_cascades_to_carts(self):
        """Deleting a Shop deletes its associated Carts and CartItems."""
        cart = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("1.000"))
        cart_id = cart.id

        self.shop1.delete()
        self.assertFalse(Cart.objects.filter(id=cart_id).exists())
        self.assertFalse(CartItem.objects.filter(cart_id=cart_id).exists())

    def test_customer_deletion_clears_customer_on_cart(self):
        """Deleting a Customer sets cart.customer to None without deleting the Cart."""
        cart = Cart.objects.create(shop=self.shop1, customer=self.customer_s1)
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("1.000"))

        self.customer_s1.delete()
        cart.refresh_from_db()
        self.assertIsNone(cart.customer)
        self.assertEqual(cart.items.count(), 1)

    # 7. Invariant check: No persistent Order relationship
    def test_no_persistent_order_relationship(self):
        """Verify that Cart and CartItem have no foreign keys or fields referencing Order."""
        cart_field_names = [f.name for f in Cart._meta.get_fields()]
        item_field_names = [f.name for f in CartItem._meta.get_fields()]

        self.assertNotIn("order", cart_field_names)
        self.assertNotIn("orders", cart_field_names)
        self.assertNotIn("order", item_field_names)
        self.assertNotIn("orders", item_field_names)
