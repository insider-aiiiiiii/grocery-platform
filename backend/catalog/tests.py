import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import MasterCategory, MasterProduct


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

