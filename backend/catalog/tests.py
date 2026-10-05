import shutil
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings

from shops.models import Shop
from users.models import Merchant, User

from .models import MasterCategory, MasterProduct, Product, ShopProduct



class MasterCategoryModelTests(TestCase):
    def test_master_category_creation(self):
        category = MasterCategory.objects.create(
            name="Groceries",
            slug="groceries",
            description="Platform-wide grocery category",
        )

        self.assertEqual(str(category), "Groceries")
        self.assertTrue(category.is_active)
        self.assertEqual(category.slug, "groceries")


class MasterProductModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.temp_media)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.category = MasterCategory.objects.create(
            name="Dairy & Eggs",
            slug="dairy-eggs",
            description="Platform dairy category",
        )

    def test_master_product_minimal_creation(self):
        """A Master Product can be created with only the required name."""
        product = MasterProduct.objects.create(name="Whole Milk 1L")

        self.assertEqual(product.name, "Whole Milk 1L")
        self.assertEqual(str(product), "Whole Milk 1L")
        self.assertEqual(product.description, "")
        self.assertEqual(product.brand, "")
        self.assertIsNone(product.category)
        self.assertFalse(bool(product.image))
        self.assertTrue(product.is_active)
        self.assertIsNotNone(product.created_at)
        self.assertIsNotNone(product.updated_at)

    def test_master_product_full_creation(self):
        """A Master Product can be created with all attributes."""
        dummy_file = SimpleUploadedFile("milk.png", b"file_content", content_type="image/png")
        product = MasterProduct.objects.create(
            name="Whole Milk 1L",
            description="Pasteurized homogenized whole milk",
            brand="FreshDairy",
            category=self.category,
            image=dummy_file,
            is_active=True,
        )

        self.assertEqual(product.name, "Whole Milk 1L")
        self.assertEqual(product.description, "Pasteurized homogenized whole milk")
        self.assertEqual(product.brand, "FreshDairy")
        self.assertEqual(product.category, self.category)
        self.assertTrue(product.image.name.startswith("catalog/master_products/milk"))
        self.assertTrue(product.is_active)

    def test_duplicate_product_names_allowed(self):
        """
        Duplicate product names are explicitly allowed per the specification.
        Master Products are identified by Master Product ID, not name.
        """
        product1 = MasterProduct.objects.create(name="Organic Apples", brand="Brand A")
        product2 = MasterProduct.objects.create(name="Organic Apples", brand="Brand B")

        self.assertNotEqual(product1.id, product2.id)
        self.assertEqual(product1.name, product2.name)
        self.assertEqual(MasterProduct.objects.filter(name="Organic Apples").count(), 2)

    def test_category_deletion_preserves_product(self):
        """
        Deleting a Master Category must set the product's category to NULL
        without deleting or impairing the Master Product.
        """
        product = MasterProduct.objects.create(
            name="Cheddar Cheese",
            category=self.category,
        )
        self.assertEqual(product.category, self.category)

        self.category.delete()
        product.refresh_from_db()

        self.assertIsNone(product.category)
        self.assertTrue(MasterProduct.objects.filter(id=product.id).exists())

    def test_product_exists_without_image(self):
        """A product may exist without an image."""
        product = MasterProduct.objects.create(name="Brown Bread")
        self.assertFalse(bool(product.image))

    def test_deactivate_and_filter_active_products(self):
        """Super Admin can deactivate a Master Product and query active library products."""
        active_product = MasterProduct.objects.create(name="Butter 500g", is_active=True)
        inactive_product = MasterProduct.objects.create(name="Discontinued Item", is_active=False)

        active_qs = MasterProduct.objects.filter(is_active=True)
        self.assertIn(active_product, active_qs)
        self.assertNotIn(inactive_product, active_qs)

    def test_ordering_by_name_and_id(self):
        """Master Products are ordered by name, then id."""
        p_c = MasterProduct.objects.create(name="Cheese")
        p_b = MasterProduct.objects.create(name="Bread")
        p_a = MasterProduct.objects.create(name="Apples")

        names = list(MasterProduct.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Apples", "Bread", "Cheese"])

    def test_platform_global_isolation(self):
        """
        Master Product is a platform-global library entity.
        It must not have a Shop relationship or be a sellable Shop Product.
        """
        product = MasterProduct.objects.create(name="Generic Rice 5kg")
        # Ensure there is no Shop foreign key or sellable Shop association on MasterProduct
        field_names = [f.name for f in MasterProduct._meta.get_fields()]
        self.assertNotIn("shop", field_names)
        self.assertNotIn("shop_id", field_names)
        self.assertNotIn("price", field_names)
        self.assertNotIn("sku", field_names)


class ShopProductModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.temp_media)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
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
            name="Alpha Mart",
            address_line="100 First St",
            area="North",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user1.mobile_number,
        )

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
            address_line="200 Second St",
            area="South",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user2.mobile_number,
        )

        self.master_product = MasterProduct.objects.create(
            name="Fresh Cow Milk 1L",
            description="Pure pasteurized cow milk",
            brand="DairyBest",
        )

    def test_merchant_direct_creation_requires_no_approval(self):
        """
        Merchants can create products directly in their Shop Catalog without a
        Master Product and without any Super Admin approval workflow.
        """
        product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Artisanal Sourdough Bread",
            description="Locally baked sourdough",
            brand="LocalBakery",
            price=Decimal("4.50"),
            sku="BREAD-001",
        )

        self.assertEqual(product.shop, self.shop1)
        self.assertIsNone(product.master_product)
        self.assertTrue(product.is_visible)
        self.assertTrue(product.is_available)
        self.assertEqual(product.price, Decimal("4.50"))
        # Verify no approval fields exist on ShopProduct
        field_names = [f.name for f in ShopProduct._meta.get_fields()]
        self.assertNotIn("is_approved", field_names)
        self.assertNotIn("approval_status", field_names)

    def test_selection_from_master_product_via_factory(self):
        """
        A Merchant can add a product by selecting a Master Product.
        Template details are copied to the Shop Product.
        """
        product = ShopProduct.from_master_product(
            shop=self.shop1,
            master_product=self.master_product,
            price=Decimal("2.99"),
            sku="MILK-ALPHA-01",
        )

        self.assertEqual(product.shop, self.shop1)
        self.assertEqual(product.master_product, self.master_product)
        self.assertEqual(product.name, "Fresh Cow Milk 1L")
        self.assertEqual(product.description, "Pure pasteurized cow milk")
        self.assertEqual(product.brand, "DairyBest")
        self.assertEqual(product.price, Decimal("2.99"))
        self.assertEqual(product.sku, "MILK-ALPHA-01")

    def test_independence_master_product_update_does_not_affect_shop_product(self):
        """
        Master Product updates do NOT automatically synchronize or modify
        existing Shop Products.
        """
        product = ShopProduct.from_master_product(
            shop=self.shop1,
            master_product=self.master_product,
            price=Decimal("2.99"),
        )

        # Update the Master Product
        self.master_product.name = "Changed Master Product Name"
        self.master_product.description = "Changed Master Description"
        self.master_product.brand = "Brand New Master Brand"
        self.master_product.save()

        # Shop Product must preserve its original values
        product.refresh_from_db()
        self.assertEqual(product.name, "Fresh Cow Milk 1L")
        self.assertEqual(product.description, "Pure pasteurized cow milk")
        self.assertEqual(product.brand, "DairyBest")

    def test_independence_master_product_deletion_preserves_shop_product(self):
        """
        Deleting a Master Product does NOT delete or impair existing Shop Products.
        The reference becomes NULL.
        """
        product = ShopProduct.from_master_product(
            shop=self.shop1,
            master_product=self.master_product,
            price=Decimal("2.99"),
        )
        product_id = product.id

        # Delete the Master Product
        self.master_product.delete()

        # Shop Product must still exist with master_product=None
        product.refresh_from_db()
        self.assertEqual(product.id, product_id)
        self.assertIsNone(product.master_product)
        self.assertEqual(product.name, "Fresh Cow Milk 1L")
        self.assertTrue(ShopProduct.objects.filter(id=product_id).exists())

    def test_independent_customization_across_multiple_shops(self):
        """
        Multiple Shops can select the same Master Product while maintaining
        fully independent pricing, names, and customizations.
        """
        sp1 = ShopProduct.from_master_product(
            shop=self.shop1,
            master_product=self.master_product,
            name="Alpha Cow Milk 1L",
            price=Decimal("3.00"),
            sku="SKU-ALPHA",
        )
        sp2 = ShopProduct.from_master_product(
            shop=self.shop2,
            master_product=self.master_product,
            name="Beta Cow Milk 1L",
            price=Decimal("2.50"),
            sku="SKU-BETA",
        )

        self.assertEqual(sp1.master_product, self.master_product)
        self.assertEqual(sp2.master_product, self.master_product)
        self.assertNotEqual(sp1.price, sp2.price)
        self.assertNotEqual(sp1.name, sp2.name)

        # Modifying sp1 does not alter sp2
        sp1.price = Decimal("3.50")
        sp1.save()
        sp2.refresh_from_db()
        self.assertEqual(sp2.price, Decimal("2.50"))

    def test_duplicate_product_names_allowed(self):
        """
        Duplicate product names are allowed in the same shop and across shops.
        """
        p1 = ShopProduct.objects.create(shop=self.shop1, name="Red Apples 1kg")
        p2 = ShopProduct.objects.create(shop=self.shop1, name="Red Apples 1kg")
        p3 = ShopProduct.objects.create(shop=self.shop2, name="Red Apples 1kg")

        self.assertNotEqual(p1.id, p2.id)
        self.assertNotEqual(p1.id, p3.id)
        self.assertEqual(ShopProduct.objects.filter(shop=self.shop1, name="Red Apples 1kg").count(), 2)

    def test_price_validation_non_negative(self):
        """Prices cannot be negative."""
        product = ShopProduct(shop=self.shop1, name="Negative Item", price=Decimal("-1.00"))
        with self.assertRaises(ValidationError):
            product.clean()

    def test_null_price_allowed(self):
        """Price can be null (e.g., when prices are defined at variant level)."""
        product = ShopProduct.objects.create(shop=self.shop1, name="Unpriced Item", price=None)
        self.assertIsNone(product.price)

    def test_visibility_and_manual_availability_controls(self):
        """Merchant can independently control visibility and availability."""
        p_visible = ShopProduct.objects.create(shop=self.shop1, name="Visible Item", is_visible=True, is_available=True)
        p_hidden = ShopProduct.objects.create(shop=self.shop1, name="Hidden Item", is_visible=False, is_available=True)
        p_unavail = ShopProduct.objects.create(shop=self.shop1, name="Unavailable Item", is_visible=True, is_available=False)

        visible_products = ShopProduct.objects.filter(shop=self.shop1, is_visible=True)
        self.assertIn(p_visible, visible_products)
        self.assertNotIn(p_hidden, visible_products)

        available_products = ShopProduct.objects.filter(shop=self.shop1, is_available=True)
        self.assertIn(p_visible, available_products)
        self.assertNotIn(p_unavail, available_products)

    def test_shop_deletion_cascades_products_without_affecting_master_product(self):
        """
        Deleting a Shop removes its Shop Products, but preserves the Master Product.
        """
        product = ShopProduct.from_master_product(
            shop=self.shop1,
            master_product=self.master_product,
        )
        product_id = product.id

        self.shop1.delete()

        self.assertFalse(ShopProduct.objects.filter(id=product_id).exists())
        self.assertTrue(MasterProduct.objects.filter(id=self.master_product.id).exists())

    def test_product_domain_alias(self):
        """Product alias points to ShopProduct."""
        self.assertIs(Product, ShopProduct)


