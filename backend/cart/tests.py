from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import ProductVariant, ShopProduct
from customers.models import Customer
from inventory.models import InventoryItem
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


class CartItemAPITests(TestCase):
    """API tests for CART-004 Add/Update/Remove Cart Item APIs."""

    def setUp(self):
        self.client = APIClient()

        # Merchant 1 and Shop 1 (Active)
        self.user1 = User.objects.create_user(
            username="merchant_cart_1",
            email="merchantcart1@example.com",
            mobile_number="+919876543301",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            status=Merchant.Status.ACTIVE,
        )
        self.shop1 = Shop.objects.create(
            merchant=self.merchant1,
            name="Green Valley Grocers",
            address_line="50 Market Road",
            area="Kothrud",
            city="Pune",
            state="Maharashtra",
            pincode="411038",
            contact_number=self.user1.mobile_number,
            status=Shop.Status.ACTIVE,
        )

        # Merchant 2 and Shop 2 (Active, for cross-shop tenancy checks)
        self.user2 = User.objects.create_user(
            username="merchant_cart_2",
            email="merchantcart2@example.com",
            mobile_number="+919876543302",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            status=Merchant.Status.ACTIVE,
        )
        self.shop2 = Shop.objects.create(
            merchant=self.merchant2,
            name="Coastal Fresh",
            address_line="100 Sea Beach Road",
            area="Bandra",
            city="Mumbai",
            state="Maharashtra",
            pincode="400050",
            contact_number=self.user2.mobile_number,
            status=Shop.Status.ACTIVE,
        )

        # Shop 1 Catalog Products & Inventory
        # 1. Simple product (in stock: 10 on-hand, 2 reserved -> 8 available)
        self.product_simple = ShopProduct.objects.create(
            shop=self.shop1,
            name="Fresh Apples 1kg",
            price=Decimal("120.00"),
            sku="APPLE-1KG",
            is_visible=True,
            is_available=True,
        )
        self.inv_simple = InventoryItem.objects.get(
            shop=self.shop1,
            product=self.product_simple,
            variant__isnull=True,
        )
        self.inv_simple.quantity = Decimal("10.000")
        self.inv_simple.reserved_quantity = Decimal("2.000")
        self.inv_simple.save()

        # 2. Variant-based product
        self.product_var = ShopProduct.objects.create(
            shop=self.shop1,
            name="Basmati Premium Rice",
            price=None,
            sku="RICE-MAIN",
            is_visible=True,
            is_available=True,
        )
        # Variant 1 (in stock: 5 on-hand, 0 reserved -> 5 available)
        self.var1 = ProductVariant.objects.create(
            product=self.product_var,
            name="1kg Bag",
            price=Decimal("150.00"),
            sku="RICE-1KG",
            is_visible=True,
            is_available=True,
        )
        self.inv_var1 = InventoryItem.objects.get(
            shop=self.shop1,
            variant=self.var1,
        )
        self.inv_var1.quantity = Decimal("5.000")
        self.inv_var1.save()

        # Variant 2 (out of stock: 0 on-hand -> 0 available)
        self.var2_oos = ProductVariant.objects.create(
            product=self.product_var,
            name="5kg Bag",
            price=Decimal("700.00"),
            sku="RICE-5KG",
            is_visible=True,
            is_available=True,
        )
        self.inv_var2 = InventoryItem.objects.get(
            shop=self.shop1,
            variant=self.var2_oos,
        )

        # 3. Hidden product (not visible)
        self.product_hidden = ShopProduct.objects.create(
            shop=self.shop1,
            name="Seasonal Strawberries",
            price=Decimal("80.00"),
            is_visible=False,
            is_available=True,
        )
        inv_hidden = InventoryItem.objects.get(
            shop=self.shop1,
            product=self.product_hidden,
            variant__isnull=True,
        )
        inv_hidden.quantity = Decimal("10.000")
        inv_hidden.save()

        # 4. Manually unavailable product
        self.product_unavail = ShopProduct.objects.create(
            shop=self.shop1,
            name="Imported Cheese",
            price=Decimal("250.00"),
            is_visible=True,
            is_available=False,
        )
        inv_unavail = InventoryItem.objects.get(
            shop=self.shop1,
            product=self.product_unavail,
            variant__isnull=True,
        )
        inv_unavail.quantity = Decimal("10.000")
        inv_unavail.save()

        # 5. Product with no inventory record created
        self.product_no_inv = ShopProduct.objects.create(
            shop=self.shop1,
            name="Exotic Kiwi",
            price=Decimal("200.00"),
            is_visible=True,
            is_available=True,
        )
        InventoryItem.objects.filter(
            shop=self.shop1,
            product=self.product_no_inv,
        ).delete()

        # 6. Hidden variant & unavailable variant
        self.product_multi_var = ShopProduct.objects.create(
            shop=self.shop1,
            name="Organic Honey",
            is_visible=True,
            is_available=True,
        )
        self.var_hidden = ProductVariant.objects.create(
            product=self.product_multi_var,
            name="Small Jar",
            price=Decimal("90.00"),
            is_visible=False,
            is_available=True,
        )
        inv_var_hidden = InventoryItem.objects.get(
            shop=self.shop1,
            variant=self.var_hidden,
        )
        inv_var_hidden.quantity = Decimal("10.000")
        inv_var_hidden.save()

        self.var_unavail = ProductVariant.objects.create(
            product=self.product_multi_var,
            name="Large Jar",
            price=Decimal("220.00"),
            is_visible=True,
            is_available=False,
        )
        inv_var_unavail = InventoryItem.objects.get(
            shop=self.shop1,
            variant=self.var_unavail,
        )
        inv_var_unavail.quantity = Decimal("10.000")
        inv_var_unavail.save()

        # Shop 2 Catalog Product & Inventory
        self.product_s2 = ShopProduct.objects.create(
            shop=self.shop2,
            name="Alphonso Mangoes 1kg",
            price=Decimal("500.00"),
            is_visible=True,
            is_available=True,
        )
        inv_s2 = InventoryItem.objects.get(
            shop=self.shop2,
            product=self.product_s2,
            variant__isnull=True,
        )
        inv_s2.quantity = Decimal("20.000")
        inv_s2.save()

        # Carts
        self.cart1 = Cart.objects.create(shop=self.shop1)
        self.cart2 = Cart.objects.create(shop=self.shop2)


    # --- ADD ITEM TESTS ---

    def test_add_simple_product_success(self):
        """Customer can add an in-stock simple product with default quantity 1.000."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_simple.id}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["product"]["id"], self.product_simple.id)
        self.assertIsNone(data["variant"])
        self.assertEqual(Decimal(str(data["quantity"])), Decimal("1.000"))
        self.assertEqual(Decimal(str(data["unit_price"])), Decimal("120.00"))
        self.assertEqual(Decimal(str(data["line_total"])), Decimal("120.00"))

        # Verify cart totals
        self.cart1.refresh_from_db()
        self.assertEqual(self.cart1.item_count, 1)
        self.assertEqual(self.cart1.total_quantity, Decimal("1.000"))
        self.assertEqual(self.cart1.subtotal, Decimal("120.00"))

    def test_add_variant_product_success(self):
        """Customer can add a variant of a product with specified decimal quantity."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {
            "product_id": self.product_var.id,
            "variant_id": self.var1.id,
            "quantity": "2.500",
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["product"]["id"], self.product_var.id)
        self.assertEqual(data["variant"]["id"], self.var1.id)
        self.assertEqual(Decimal(str(data["quantity"])), Decimal("2.500"))
        self.assertEqual(Decimal(str(data["unit_price"])), Decimal("150.00"))
        # 2.5 * 150.00 = 375.00
        self.assertEqual(Decimal(str(data["line_total"])), Decimal("375.00"))

    def test_add_existing_item_increments_quantity(self):
        """Adding a product already in the cart increments its quantity within available stock."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        # First add 2.000
        res1 = self.client.post(url, {"product_id": self.product_simple.id, "quantity": "2.000"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(res1.json()["quantity"])), Decimal("2.000"))

        # Add 3.000 more
        res2 = self.client.post(url, {"product_id": self.product_simple.id, "quantity": "3.000"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(res2.json()["quantity"])), Decimal("5.000"))

        # Verify database has exactly 1 CartItem with quantity 5.000
        self.assertEqual(CartItem.objects.filter(cart=self.cart1).count(), 1)
        item = CartItem.objects.get(cart=self.cart1)
        self.assertEqual(item.quantity, Decimal("5.000"))

    def test_add_existing_item_exceeding_stock_rejected(self):
        """Adding more quantity to an existing item that causes combined total to exceed available stock is rejected."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        # Available stock is 8.000 (10 on hand - 2 reserved)
        res1 = self.client.post(url, {"product_id": self.product_simple.id, "quantity": "5.000"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Adding 4.000 more makes 9.000, exceeding 8.000
        res2 = self.client.post(url, {"product_id": self.product_simple.id, "quantity": "4.000"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceeds available stock", str(res2.json()))

        # CartItem remains at 5.000
        item = CartItem.objects.get(cart=self.cart1)
        self.assertEqual(item.quantity, Decimal("5.000"))

    def test_add_out_of_stock_item_rejected(self):
        """Adding an out-of-stock variant is rejected under finalized Catalog/Inventory rules."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_var.id, "variant_id": self.var2_oos.id, "quantity": "1.000"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("out of stock", str(response.json()).lower())

    def test_add_item_with_no_inventory_record_rejected(self):
        """A product with no inventory record initialized has 0 available stock and cannot be ordered."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_no_inv.id, "quantity": "1.000"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("out of stock", str(response.json()).lower())

    def test_add_item_quantity_exceeding_available_stock_rejected(self):
        """Adding a quantity greater than available stock (available: 8) is rejected."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_simple.id, "quantity": "8.001"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceeds available stock", str(response.json()))

    def test_add_hidden_product_rejected(self):
        """Hidden product (is_visible=False) cannot be ordered."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_hidden.id, "quantity": "1.000"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not visible", str(response.json()).lower())

    def test_add_hidden_variant_rejected(self):
        """Hidden variant (is_visible=False) cannot be ordered."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {
            "product_id": self.product_multi_var.id,
            "variant_id": self.var_hidden.id,
            "quantity": "1.000",
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not visible", str(response.json()).lower())

    def test_add_unavailable_product_rejected(self):
        """Manually unavailable product (is_available=False) cannot be ordered."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_unavail.id, "quantity": "1.000"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unavailable", str(response.json()).lower())

    def test_add_unavailable_variant_rejected(self):
        """Manually unavailable variant (is_available=False) cannot be ordered."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {
            "product_id": self.product_multi_var.id,
            "variant_id": self.var_unavail.id,
            "quantity": "1.000",
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unavailable", str(response.json()).lower())

    def test_add_variant_product_without_variant_id_rejected(self):
        """Adding a product that has variants without specifying variant_id is rejected."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_var.id, "quantity": "1.000"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("variant", str(response.json()).lower())

    def test_add_non_variant_product_with_variant_id_rejected(self):
        """Adding a product that has no variants with a variant_id is rejected."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {
            "product_id": self.product_simple.id,
            "variant_id": self.var1.id,
            "quantity": "1.000",
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be specified", str(response.json()).lower())

    def test_add_cross_shop_product_rejected(self):
        """Adding a product from Shop 2 into Shop 1's Cart is strictly prohibited."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"
        payload = {"product_id": self.product_s2.id, "quantity": "1.000"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not belong to this shop", str(response.json()).lower())

    def test_add_item_invalid_quantities_rejected(self):
        """Zero, negative, or excessive precision decimal quantities are rejected."""
        url = f"/api/v1/cart/{self.cart1.id}/items/"

        # Zero quantity
        res_zero = self.client.post(url, {"product_id": self.product_simple.id, "quantity": "0.000"}, format="json")
        self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)

        # Negative quantity
        res_neg = self.client.post(url, {"product_id": self.product_simple.id, "quantity": "-2.000"}, format="json")
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)

        # Excessive precision (> 3 decimal places)
        res_prec = self.client.post(url, {"product_id": self.product_simple.id, "quantity": "1.0005"}, format="json")
        self.assertEqual(res_prec.status_code, status.HTTP_400_BAD_REQUEST)

    # --- LIST & DETAIL ITEMS TESTS ---

    def test_list_cart_items(self):
        """GET /api/v1/cart/<cart_id>/items/ lists all items currently in the cart."""
        CartItem.objects.create(cart=self.cart1, product=self.product_simple, quantity=Decimal("2.000"))
        CartItem.objects.create(cart=self.cart1, product=self.product_var, variant=self.var1, quantity=Decimal("1.000"))

        url = f"/api/v1/cart/{self.cart1.id}/items/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 2)
        product_ids = [item["product"]["id"] for item in data]
        self.assertIn(self.product_simple.id, product_ids)
        self.assertIn(self.product_var.id, product_ids)

    def test_get_single_cart_item(self):
        """GET /api/v1/cart/<cart_id>/items/<item_id>/ retrieves a single cart item."""
        item = CartItem.objects.create(cart=self.cart1, product=self.product_simple, quantity=Decimal("2.000"))

        url = f"/api/v1/cart/{self.cart1.id}/items/{item.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], item.id)
        self.assertEqual(Decimal(str(data["quantity"])), Decimal("2.000"))

    def test_get_cart_item_not_found(self):
        """GET non-existent cart item returns 404."""
        url = f"/api/v1/cart/{self.cart1.id}/items/99999/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- UPDATE ITEM TESTS ---

    def test_update_cart_item_quantity_success(self):
        """PATCH /api/v1/cart/<cart_id>/items/<item_id>/ updates quantity within available stock."""
        item = CartItem.objects.create(cart=self.cart1, product=self.product_simple, quantity=Decimal("2.000"))

        url = f"/api/v1/cart/{self.cart1.id}/items/{item.id}/"
        payload = {"quantity": "4.500"}
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(Decimal(str(data["quantity"])), Decimal("4.500"))
        # 4.5 * 120.00 = 540.00
        self.assertEqual(Decimal(str(data["line_total"])), Decimal("540.00"))

        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("4.500"))

    def test_update_cart_item_quantity_exceeding_stock_rejected(self):
        """Updating quantity beyond available stock is rejected."""
        item = CartItem.objects.create(cart=self.cart1, product=self.product_simple, quantity=Decimal("2.000"))

        # Available stock is 8.000
        url = f"/api/v1/cart/{self.cart1.id}/items/{item.id}/"
        payload = {"quantity": "8.500"}
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceeds available stock", str(response.json()))

        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("2.000"))

    def test_update_cart_item_invalid_quantities_rejected(self):
        """Zero or negative quantities on update are rejected."""
        item = CartItem.objects.create(cart=self.cart1, product=self.product_simple, quantity=Decimal("2.000"))

        url = f"/api/v1/cart/{self.cart1.id}/items/{item.id}/"
        res_zero = self.client.patch(url, {"quantity": "0.000"}, format="json")
        self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)

        res_neg = self.client.patch(url, {"quantity": "-1.000"}, format="json")
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)

    # --- REMOVE & CLEAR ITEM TESTS ---

    def test_remove_cart_item_success(self):
        """DELETE /api/v1/cart/<cart_id>/items/<item_id>/ deletes the item from the cart."""
        item1 = CartItem.objects.create(cart=self.cart1, product=self.product_simple, quantity=Decimal("2.000"))
        item2 = CartItem.objects.create(cart=self.cart1, product=self.product_var, variant=self.var1, quantity=Decimal("1.000"))

        url = f"/api/v1/cart/{self.cart1.id}/items/{item1.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(id=item1.id).exists())
        self.assertTrue(CartItem.objects.filter(id=item2.id).exists())

        self.cart1.refresh_from_db()
        self.assertEqual(self.cart1.item_count, 1)

    def test_remove_item_from_another_cart_rejected(self):
        """Attempting to delete an item belonging to Cart 2 using Cart 1's URL returns 404."""
        item2 = CartItem.objects.create(cart=self.cart2, product=self.product_s2, quantity=Decimal("1.000"))

        url = f"/api/v1/cart/{self.cart1.id}/items/{item2.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(CartItem.objects.filter(id=item2.id).exists())

    def test_clear_all_cart_items_success(self):
        """DELETE /api/v1/cart/<cart_id>/items/ removes all items from the cart."""
        CartItem.objects.create(cart=self.cart1, product=self.product_simple, quantity=Decimal("2.000"))
        CartItem.objects.create(cart=self.cart1, product=self.product_var, variant=self.var1, quantity=Decimal("1.000"))

        url = f"/api/v1/cart/{self.cart1.id}/items/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.filter(cart=self.cart1).count(), 0)

        self.cart1.refresh_from_db()
        self.assertEqual(self.cart1.item_count, 0)
        self.assertEqual(self.cart1.total_quantity, Decimal("0.000"))
        self.assertEqual(self.cart1.subtotal, Decimal("0.00"))

    # --- SHOP-SCOPED PUBLIC URL TESTS ---

    def test_shop_scoped_public_cart_items_flow(self):
        """Full item lifecycle works via shop public slug URLs."""
        slug = self.shop1.public_slug

        # 1. Add item
        add_url = f"/api/v1/shops/public/{slug}/cart/{self.cart1.id}/items/"
        res_add = self.client.post(add_url, {"product_id": self.product_simple.id, "quantity": "1.000"}, format="json")
        self.assertEqual(res_add.status_code, status.HTTP_201_CREATED)
        item_id = res_add.json()["id"]

        # 2. List items
        list_url = f"/api/v1/shops/public/{slug}/cart/{self.cart1.id}/items/"
        res_list = self.client.get(list_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.json()), 1)

        # 3. Update item
        detail_url = f"/api/v1/shops/public/{slug}/cart/{self.cart1.id}/items/{item_id}/"
        res_patch = self.client.patch(detail_url, {"quantity": "3.000"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res_patch.json()["quantity"])), Decimal("3.000"))

        # 4. Delete item
        res_del = self.client.delete(detail_url)
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.filter(cart=self.cart1).count(), 0)

    def test_shop_scoped_cart_cross_shop_rejected(self):
        """Accessing Cart 1 items using Shop 2's public slug is rejected with 404."""
        slug_s2 = self.shop2.public_slug
        url = f"/api/v1/shops/public/{slug_s2}/cart/{self.cart1.id}/items/"

        # GET
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # POST
        res_post = self.client.post(url, {"product_id": self.product_simple.id}, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_404_NOT_FOUND)


class CartValidationAPITests(TestCase):
    """API tests for CART-005 Cart validation against Catalog and Inventory."""

    def setUp(self):
        self.client = APIClient()

        # Merchant & Active Shop
        self.user = User.objects.create_user(
            username="merchant_val",
            email="merchantval@example.com",
            mobile_number="+919876543401",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Sunrise Market",
            address_line="12 Sunrise Way",
            area="Aundh",
            city="Pune",
            state="Maharashtra",
            pincode="411007",
            contact_number=self.user.mobile_number,
            status=Shop.Status.ACTIVE,
        )

        # Other Merchant & Shop (for cross-shop isolation test)
        self.user_other = User.objects.create_user(
            username="merchant_other",
            email="merchantother@example.com",
            mobile_number="+919876543402",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant_other = Merchant.objects.create(
            user=self.user_other,
            status=Merchant.Status.ACTIVE,
        )
        self.shop_other = Shop.objects.create(
            merchant=self.merchant_other,
            name="Sunset Supermarket",
            address_line="88 Sunset Blvd",
            area="Colaba",
            city="Mumbai",
            state="Maharashtra",
            pincode="400005",
            contact_number=self.user_other.mobile_number,
            status=Shop.Status.ACTIVE,
        )

        # Catalog Products & Inventory in self.shop
        # 1. Simple Product
        self.prod_apple = ShopProduct.objects.create(
            shop=self.shop,
            name="Crisp Apples 1kg",
            price=Decimal("120.00"),
            sku="APL-01",
            is_visible=True,
            is_available=True,
        )
        self.inv_apple = InventoryItem.objects.get(
            shop=self.shop,
            product=self.prod_apple,
            variant__isnull=True,
        )
        self.inv_apple.quantity = Decimal("10.000")
        self.inv_apple.save()

        # 2. Product with Variants
        self.prod_rice = ShopProduct.objects.create(
            shop=self.shop,
            name="Sona Masoori Rice",
            price=None,
            sku="RICE-SONA",
            is_visible=True,
            is_available=True,
        )
        self.var_rice_1kg = ProductVariant.objects.create(
            product=self.prod_rice,
            name="1kg Pouch",
            price=Decimal("80.00"),
            sku="RICE-SONA-1KG",
            is_visible=True,
            is_available=True,
        )
        self.inv_rice_1kg = InventoryItem.objects.get(
            shop=self.shop,
            variant=self.var_rice_1kg,
        )
        self.inv_rice_1kg.quantity = Decimal("6.000")
        self.inv_rice_1kg.save()

        # Carts
        self.cart = Cart.objects.create(shop=self.shop)
        self.empty_cart = Cart.objects.create(shop=self.shop)
        self.cart_other = Cart.objects.create(shop=self.shop_other)

    def test_validate_fully_valid_cart(self):
        """A cart with available in-stock items returns is_valid=True and can_checkout=True."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("2.000"))
        CartItem.objects.create(cart=self.cart, product=self.prod_rice, variant=self.var_rice_1kg, quantity=Decimal("3.000"))

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["is_valid"])
        self.assertTrue(data["can_checkout"])
        self.assertEqual(data["errors"], [])
        self.assertEqual(len(data["items"]), 2)

        # Verify summary
        summary = data["summary"]
        self.assertEqual(summary["item_count"], 2)
        self.assertEqual(summary["valid_item_count"], 2)
        self.assertEqual(summary["invalid_item_count"], 0)
        self.assertEqual(Decimal(str(summary["total_quantity"])), Decimal("5.000"))
        # (2 * 120.00) + (3 * 80.00) = 240.00 + 240.00 = 480.00
        self.assertEqual(Decimal(str(summary["current_subtotal"])), Decimal("480.00"))

        # Verify Orders dependencies notes
        deps = data["orders_dependencies"]
        self.assertIn("price_snapshot_strategy", deps)
        self.assertIn("cart_expiration", deps)
        self.assertIn("quantity_limits", deps)
        self.assertIn("checkout_fulfillment", deps)
        self.assertIn("stock_reservation", deps)
        self.assertIn("cart_clearing", deps)

    def test_validate_empty_cart(self):
        """Validating an empty cart returns is_valid=False, can_checkout=False, and CART_EMPTY error."""
        url = f"/api/v1/cart/{self.empty_cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_valid"])
        self.assertFalse(data["can_checkout"])
        self.assertIn("CART_EMPTY", data["errors"])
        self.assertEqual(data["items"], [])

    def test_validate_out_of_stock_item_remains_visible_with_issue(self):
        """When an item in the cart becomes out of stock, it remains in the output with OUT_OF_STOCK flag."""
        item = CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("2.000"))

        # Stock is reduced to 0
        self.inv_apple.set_quantity(Decimal("0.000"))

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_valid"])
        self.assertFalse(data["can_checkout"])

        item_data = data["items"][0]
        self.assertEqual(item_data["item_id"], item.id)
        self.assertFalse(item_data["is_valid"])
        self.assertIn("OUT_OF_STOCK", item_data["issues"])
        self.assertEqual(Decimal(str(item_data["requested_quantity"])), Decimal("2.000"))
        self.assertEqual(Decimal(str(item_data["available_quantity"])), Decimal("0.000"))

    def test_validate_insufficient_stock_item(self):
        """When cart quantity exceeds available stock, it is flagged with INSUFFICIENT_STOCK."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("5.000"))

        # Available stock dropped to 3
        self.inv_apple.set_quantity(Decimal("3.000"))

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_valid"])
        self.assertFalse(data["can_checkout"])

        item_data = data["items"][0]
        self.assertFalse(item_data["is_valid"])
        self.assertIn("INSUFFICIENT_STOCK", item_data["issues"])
        self.assertEqual(Decimal(str(item_data["available_quantity"])), Decimal("3.000"))

    def test_validate_hidden_product(self):
        """A product hidden in catalog is flagged with PRODUCT_HIDDEN."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("1.000"))

        self.prod_apple.is_visible = False
        self.prod_apple.save()

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_valid"])
        self.assertIn("PRODUCT_HIDDEN", data["items"][0]["issues"])

    def test_validate_unavailable_product(self):
        """A product marked manually unavailable is flagged with PRODUCT_UNAVAILABLE."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("1.000"))

        self.prod_apple.is_available = False
        self.prod_apple.save()

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_valid"])
        self.assertIn("PRODUCT_UNAVAILABLE", data["items"][0]["issues"])

    def test_validate_hidden_and_unavailable_variant(self):
        """Variants hidden or marked unavailable are flagged accordingly."""
        CartItem.objects.create(cart=self.cart, product=self.prod_rice, variant=self.var_rice_1kg, quantity=Decimal("1.000"))

        self.var_rice_1kg.is_visible = False
        self.var_rice_1kg.is_available = False
        self.var_rice_1kg.save()

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_valid"])
        issues = data["items"][0]["issues"]
        self.assertIn("VARIANT_HIDDEN", issues)
        self.assertIn("VARIANT_UNAVAILABLE", issues)

    def test_validate_recalculates_latest_catalog_price(self):
        """Subtotal and line totals use current Shop Catalog price rather than add-time price."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("2.000"))

        # Merchant updates price from 120.00 to 150.00
        self.prod_apple.price = Decimal("150.00")
        self.prod_apple.save()

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["is_valid"])

        item_data = data["items"][0]
        self.assertEqual(Decimal(str(item_data["current_unit_price"])), Decimal("150.00"))
        self.assertEqual(Decimal(str(item_data["line_total"])), Decimal("300.00"))
        self.assertEqual(Decimal(str(data["summary"]["current_subtotal"])), Decimal("300.00"))

    def test_validate_deactivated_shop(self):
        """If shop is deactivated, validation flags SHOP_UNAVAILABLE and can_checkout=False."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("1.000"))

        self.shop.status = Shop.Status.DEACTIVATED
        self.shop.save()

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["is_valid"])
        self.assertFalse(data["can_checkout"])
        self.assertIn("SHOP_UNAVAILABLE", data["errors"])

    def test_validate_post_method_supported(self):
        """POST /api/v1/cart/<cart_id>/validate/ returns the same validation result as GET."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("1.000"))

        url = f"/api/v1/cart/{self.cart.id}/validate/"
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["is_valid"])

    def test_validate_shop_public_slug_endpoints(self):
        """Validation is accessible under the shop's public slug routes."""
        CartItem.objects.create(cart=self.cart, product=self.prod_apple, quantity=Decimal("1.000"))
        slug = self.shop.public_slug

        # 1. /api/v1/shops/public/<slug>/cart/<cart_id>/validate/
        url_detail = f"/api/v1/shops/public/{slug}/cart/{self.cart.id}/validate/"
        res1 = self.client.get(url_detail)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertTrue(res1.json()["is_valid"])

        # 2. /api/v1/shops/public/<slug>/cart/validate/?cart_id=<cart_id>
        url_query = f"/api/v1/shops/public/{slug}/cart/validate/?cart_id={self.cart.id}"
        res2 = self.client.get(url_query)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.json()["is_valid"])

    def test_validate_cross_shop_access_rejected(self):
        """Attempting to validate Cart 1 using Shop 2's slug is rejected with 404."""
        slug_other = self.shop_other.public_slug
        url = f"/api/v1/shops/public/{slug_other}/cart/{self.cart.id}/validate/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


