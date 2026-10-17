from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

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

    # 8. CART-002 Advanced constraint & anti-leakage tests
    def test_cannot_change_cart_shop_when_items_exist(self):
        """A Cart cannot change its Shop if it already contains items."""
        cart = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("1.000"))

        cart.shop = self.shop2
        with self.assertRaises(ValidationError) as ctx:
            cart.full_clean()
        self.assertIn("shop", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            cart.save()

    def test_can_change_cart_shop_when_empty(self):
        """An empty Cart can update its Shop before items are added."""
        cart = Cart.objects.create(shop=self.shop1)
        cart.shop = self.shop2
        cart.save()
        cart.refresh_from_db()
        self.assertEqual(cart.shop, self.shop2)

    def test_cannot_reassign_cart_item_to_different_shop_cart(self):
        """A CartItem cannot be moved to a Cart belonging to a different Shop."""
        cart1 = Cart.objects.create(shop=self.shop1)
        cart2 = Cart.objects.create(shop=self.shop2)
        item = CartItem.objects.create(cart=cart1, product=self.product1_s1, quantity=Decimal("1.000"))

        item.cart = cart2  # product belongs to shop1, cart2 belongs to shop2
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("product", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            item.save()

    def test_cannot_update_cart_item_product_to_different_shop(self):
        """A CartItem cannot be updated to reference a product from a different Shop."""
        cart = Cart.objects.create(shop=self.shop1)
        item = CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("1.000"))

        item.product = self.product1_s2  # product from shop2
        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()
        self.assertIn("product", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            item.save()

    def test_variant_must_match_both_product_and_cart_shop(self):
        """Variant must strictly belong to the specified product and the cart's shop."""
        cart = Cart.objects.create(shop=self.shop1)

        # Variant from shop2 attached to product from shop1
        item_bad_variant = CartItem(
            cart=cart,
            product=self.product1_s1,
            variant=self.variant1_s2,
            quantity=Decimal("1.000"),
        )
        with self.assertRaises(ValidationError) as ctx:
            item_bad_variant.full_clean()
        self.assertIn("variant", ctx.exception.message_dict)

    def test_database_check_constraint_blocks_negative_quantity_on_bulk_create(self):
        """Database check constraint strictly prohibits negative quantities on bulk_create."""
        cart = Cart.objects.create(shop=self.shop1)
        with self.assertRaises(IntegrityError):
            CartItem.objects.bulk_create([
                CartItem(cart=cart, product=self.product1_s1, quantity=Decimal("-2.000"))
            ])

    def test_no_cross_shop_cart_composition_in_totals(self):
        """Cart totals, item counts, and subtotals never mix or leak across shops."""
        cart_s1 = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(cart=cart_s1, product=self.product1_s1, quantity=Decimal("2.000"))

        cart_s2 = Cart.objects.create(shop=self.shop2)
        CartItem.objects.create(cart=cart_s2, product=self.product1_s2, quantity=Decimal("5.000"))

        self.assertEqual(cart_s1.item_count, 1)
        self.assertEqual(cart_s1.total_quantity, Decimal("2.000"))
        self.assertEqual(cart_s1.subtotal, Decimal("120.00"))  # 2 * 60.00

        self.assertEqual(cart_s2.item_count, 1)
        self.assertEqual(cart_s2.total_quantity, Decimal("5.000"))
        self.assertEqual(cart_s2.subtotal, Decimal("375.00"))  # 5 * 75.00


class PublicCartAPITests(TestCase):
    """API tests for CART-003 Public Create/Retrieve Cart APIs for a Shop."""

    def setUp(self):
        self.client = APIClient()

        # Merchant 1 and Shop 1
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
            delivery_charge=Decimal("40.00"),
        )

        # Merchant 2 and Shop 2 (for multi-tenant isolation testing)
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
            delivery_charge=Decimal("50.00"),
        )

        # Products in Shop 1
        self.product1_s1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Fresh Milk 1L",
            price=Decimal("60.00"),
            sku="MILK-001",
        )
        self.product2_s1 = ShopProduct.objects.create(
            shop=self.shop1,
            name="Basmati Rice",
            price=Decimal("120.00"),
            sku="RICE-001",
        )
        self.variant1_s1 = ProductVariant.objects.create(
            product=self.product2_s1,
            name="1kg Pack",
            price=Decimal("130.00"),
            sku="RICE-1KG",
        )

        # Product in Shop 2
        self.product1_s2 = ShopProduct.objects.create(
            shop=self.shop2,
            name="Organic Milk 1L",
            price=Decimal("75.00"),
            sku="OMILK-001",
        )

        # Customer in Shop 1
        self.customer_s1 = Customer.objects.create(
            shop=self.shop1,
            name="Anand Sharma",
            whatsapp_number="+919876500001",
        )

        # Customer in Shop 2
        self.customer_s2 = Customer.objects.create(
            shop=self.shop2,
            name="Pooja Verma",
            whatsapp_number="+919876500002",
        )

    # 1. Public Create Cart
    def test_public_create_anonymous_empty_cart(self):
        """Unauthenticated customer can create an empty anonymous cart for an active shop."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["shop"]["id"], self.shop1.id)
        self.assertEqual(data["shop"]["public_slug"], self.shop1.public_slug)
        self.assertIsNone(data["customer"])
        self.assertEqual(data["items"], [])
        self.assertEqual(data["item_count"], 0)
        self.assertEqual(Decimal(str(data["total_quantity"])), Decimal("0.000"))
        self.assertEqual(Decimal(str(data["subtotal"])), Decimal("0.00"))

    def test_public_create_cart_with_initial_items(self):
        """Customer can create a cart pre-populated with valid products and variants."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        payload = {
            "items": [
                {"product_id": self.product1_s1.id, "quantity": "2.000"},
                {"product_id": self.product2_s1.id, "variant_id": self.variant1_s1.id, "quantity": "1.500"},
            ]
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["item_count"], 2)
        self.assertEqual(Decimal(str(data["total_quantity"])), Decimal("3.500"))
        # (2 * 60.00) + (1.5 * 130.00) = 120 + 195 = 315.00
        self.assertEqual(Decimal(str(data["subtotal"])), Decimal("315.00"))

        item1 = data["items"][0]
        self.assertEqual(item1["product"]["id"], self.product1_s1.id)
        self.assertIsNone(item1["variant"])
        self.assertEqual(Decimal(str(item1["unit_price"])), Decimal("60.00"))
        self.assertEqual(Decimal(str(item1["line_total"])), Decimal("120.00"))

        item2 = data["items"][1]
        self.assertEqual(item2["variant"]["id"], self.variant1_s1.id)
        self.assertEqual(Decimal(str(item2["unit_price"])), Decimal("130.00"))
        self.assertEqual(Decimal(str(item2["line_total"])), Decimal("195.00"))

    def test_public_create_cart_with_customer_id(self):
        """Customer can create a cart linked to an existing Customer in the same Shop."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        payload = {"customer_id": self.customer_s1.id}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIsNotNone(data["customer"])
        self.assertEqual(data["customer"]["id"], self.customer_s1.id)
        self.assertEqual(data["customer"]["whatsapp_number"], self.customer_s1.whatsapp_number)

    def test_public_create_cart_with_whatsapp_number(self):
        """Customer providing whatsapp_number links or creates the shop-specific Customer profile."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        payload = {"whatsapp_number": "9876543299"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIsNotNone(data["customer"])
        self.assertEqual(data["customer"]["whatsapp_number"], "+919876543299")

        # Verify Customer profile exists in shop1
        self.assertTrue(Customer.objects.filter(shop=self.shop1, whatsapp_number="+919876543299").exists())

    def test_public_create_cart_rejects_customer_from_different_shop(self):
        """Cannot link a customer from another Shop to a new Cart."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        payload = {"customer_id": self.customer_s2.id}  # customer belonging to shop2
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("customer_id", response.json())

    def test_public_create_cart_rejects_product_from_different_shop(self):
        """Cannot add products from another Shop to a Cart."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        payload = {
            "items": [{"product_id": self.product1_s2.id, "quantity": "1.000"}]
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not belong to this Shop", str(response.json()))

    def test_public_create_cart_rejects_invalid_quantity(self):
        """Cannot add item with zero, negative, or invalid decimal places."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"

        # Zero quantity
        res_zero = self.client.post(url, {"items": [{"product_id": self.product1_s1.id, "quantity": "0.000"}]}, format="json")
        self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)

        # Negative quantity
        res_neg = self.client.post(url, {"items": [{"product_id": self.product1_s1.id, "quantity": "-1.500"}]}, format="json")
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)

        # Excessive decimal places
        res_excess = self.client.post(url, {"items": [{"product_id": self.product1_s1.id, "quantity": "1.1234"}]}, format="json")
        self.assertEqual(res_excess.status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_create_cart_inactive_shop_returns_404(self):
        """Cannot create a cart for an inactive, deactivated, or suspended shop."""
        self.shop1.status = Shop.Status.DEACTIVATED
        self.shop1.save()

        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 2. Public Retrieve Cart
    def test_public_retrieve_cart_by_shop_slug_and_id(self):
        """Retrieve cart by shop public slug and cart PK."""
        cart = Cart.objects.create(shop=self.shop1, customer=self.customer_s1)
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("3.000"))

        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/{cart.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], cart.id)
        self.assertEqual(data["shop"]["public_slug"], self.shop1.public_slug)
        self.assertEqual(data["customer"]["id"], self.customer_s1.id)
        self.assertEqual(data["item_count"], 1)
        self.assertEqual(Decimal(str(data["subtotal"])), Decimal("180.00"))

    def test_public_retrieve_cart_via_query_param(self):
        """Retrieve cart using ?cart_id=<id> query parameter."""
        cart = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("1.000"))

        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/?cart_id={cart.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], cart.id)

    def test_public_retrieve_cart_via_header(self):
        """Retrieve cart using X-Cart-ID header."""
        cart = Cart.objects.create(shop=self.shop1)
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        response = self.client.get(url, HTTP_X_CART_ID=str(cart.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], cart.id)

    def test_public_retrieve_cart_missing_param_returns_400(self):
        """GET /public/<slug>/cart/ without cart_id query param or header returns 400."""
        url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "CART_ID_REQUIRED")

    def test_public_retrieve_cart_cross_shop_returns_404(self):
        """Shop 2's public URL cannot retrieve Shop 1's cart (cross-shop leak prevention)."""
        cart_s1 = Cart.objects.create(shop=self.shop1)

        url = f"/api/v1/shops/public/{self.shop2.public_slug}/cart/{cart_s1.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        url_query = f"/api/v1/shops/public/{self.shop2.public_slug}/cart/?cart_id={cart_s1.id}"
        response_query = self.client.get(url_query)
        self.assertEqual(response_query.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_direct_cart_retrieve(self):
        """Direct retrieval via /api/v1/cart/<pk>/ returns cart details for active shop."""
        cart = Cart.objects.create(shop=self.shop1)
        CartItem.objects.create(cart=cart, product=self.product1_s1, quantity=Decimal("1.000"))

        url = f"/api/v1/cart/{cart.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], cart.id)
        self.assertEqual(data["shop"]["id"], self.shop1.id)

    def test_public_direct_cart_retrieve_inactive_shop_returns_404(self):
        """Direct cart retrieval returns 404 if the cart's shop is deactivated."""
        cart = Cart.objects.create(shop=self.shop1)
        self.shop1.status = Shop.Status.DEACTIVATED
        self.shop1.save()

        url = f"/api/v1/cart/{cart.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_client_can_perform_all_cart_operations(self):
        """Clients require zero authentication headers or cookies to create or retrieve carts."""
        self.client.credentials()  # clear all auth credentials

        # 1. Create anonymous cart
        create_url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/"
        res_create = self.client.post(create_url, {"items": [{"product_id": self.product1_s1.id}]}, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        cart_id = res_create.json()["id"]

        # 2. Retrieve by slug and ID
        get_slug_url = f"/api/v1/shops/public/{self.shop1.public_slug}/cart/{cart_id}/"
        res_get_slug = self.client.get(get_slug_url)
        self.assertEqual(res_get_slug.status_code, status.HTTP_200_OK)

        # 3. Direct retrieval by ID
        get_direct_url = f"/api/v1/cart/{cart_id}/"
        res_get_direct = self.client.get(get_direct_url)
        self.assertEqual(res_get_direct.status_code, status.HTTP_200_OK)


