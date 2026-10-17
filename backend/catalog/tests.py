import shutil
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from shops.models import Shop
from users.models import Merchant, User, UserAuthSession
from users.views import refresh_for_user

from .models import (
    Attribute,
    Brand,
    Category,
    CustomAttribute,
    MasterCategory,
    MasterProduct,
    Product,
    ProductVariant,
    ShopAttribute,
    ShopBrand,
    ShopCategory,
    ShopCustomAttribute,
    ShopProduct,
    ShopProductBrand,
    ShopProductVariant,
    Variant,
)




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


class ProductVariantModelTests(TestCase):
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
        self.user = User.objects.create_user(
            username="merchant_var",
            email="merchant_var@example.com",
            mobile_number="+919876543219",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Grocery Corner",
            address_line="50 Market Lane",
            area="Downtown",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )

        dummy_prod_img = SimpleUploadedFile("product.png", b"prod_img_bytes", content_type="image/png")
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Cold Brew Coffee",
            description="Organic slow-steeped cold brew",
            brand="BrewCraft",
            price=Decimal("4.00"),
            sku="CB-MAIN",
            image=dummy_prod_img,
            attributes={"origin": "Ethiopia", "roast": "Medium"},
        )

    def test_non_variant_product_representation(self):
        """
        Non-variant sellable product has direct price and attributes without variants.
        """
        self.assertFalse(self.product.has_variants)
        self.assertEqual(self.product.price, Decimal("4.00"))
        self.assertEqual(self.product.attributes["origin"], "Ethiopia")
        self.assertEqual(self.product.variants.count(), 0)

    def test_variant_creation_with_attributes_and_pricing(self):
        """
        Merchants can create variants with specific name, price, SKU, image, and custom attributes.
        """
        dummy_var_img = SimpleUploadedFile("variant.png", b"var_img_bytes", content_type="image/png")
        variant = ProductVariant.objects.create(
            product=self.product,
            name="Large (1L Bottle)",
            price=Decimal("7.50"),
            sku="CB-1L",
            image=dummy_var_img,
            attributes={"volume": "1L", "packaging": "Glass Bottle"},
            is_visible=True,
            is_available=True,
        )

        self.assertEqual(variant.product, self.product)
        self.assertEqual(variant.name, "Large (1L Bottle)")
        self.assertEqual(variant.price, Decimal("7.50"))
        self.assertEqual(variant.sku, "CB-1L")
        self.assertEqual(variant.attributes, {"volume": "1L", "packaging": "Glass Bottle"})
        self.assertTrue(self.product.has_variants)
        self.assertEqual(str(variant), "Cold Brew Coffee - Large (1L Bottle)")

    def test_duplicate_skus_allowed_across_variants_and_products(self):
        """
        The catalog specification explicitly specifies that SKUs do not need
        to be unique, and duplicate SKUs across variants are permitted.
        """
        v1 = ProductVariant.objects.create(
            product=self.product,
            name="Small 250ml",
            price=Decimal("3.00"),
            sku="SHARED-SKU-99",
        )
        v2 = ProductVariant.objects.create(
            product=self.product,
            name="Medium 500ml",
            price=Decimal("5.00"),
            sku="SHARED-SKU-99",
        )

        self.assertNotEqual(v1.id, v2.id)
        self.assertEqual(v1.sku, v2.sku)
        self.assertEqual(ProductVariant.objects.filter(sku="SHARED-SKU-99").count(), 2)

    def test_variant_image_fallback_to_parent_product(self):
        """
        When a variant has no image, it falls back to the parent product's image.
        When it has its own image, that image is used.
        """
        dummy_var_img = SimpleUploadedFile("specific.png", b"specific_bytes", content_type="image/png")
        variant_with_img = ProductVariant.objects.create(
            product=self.product,
            name="Special Edition",
            image=dummy_var_img,
        )
        variant_no_img = ProductVariant.objects.create(
            product=self.product,
            name="Standard Edition",
            image=None,
        )

        self.assertTrue(variant_with_img.effective_image.name.startswith("catalog/variants/specific"))
        self.assertTrue(variant_no_img.effective_image.name.startswith("catalog/shop_products/product"))

    def test_variant_price_fallback_to_parent_product(self):
        """
        When variant price is null, effective_price falls back to the parent product's price.
        When set, the variant price is used.
        """
        v_custom_price = ProductVariant.objects.create(
            product=self.product,
            name="Single Shot",
            price=Decimal("2.50"),
        )
        v_inherited_price = ProductVariant.objects.create(
            product=self.product,
            name="Standard Serving",
            price=None,
        )

        self.assertEqual(v_custom_price.effective_price, Decimal("2.50"))
        self.assertEqual(v_inherited_price.effective_price, Decimal("4.00"))

    def test_negative_variant_price_validation(self):
        """Variant price cannot be negative."""
        variant = ProductVariant(
            product=self.product,
            name="Invalid Variant",
            price=Decimal("-2.00"),
        )
        with self.assertRaises(ValidationError):
            variant.clean()

    def test_get_available_variants_filter(self):
        """
        Customers and catalog queries see only visible and manually available variants.
        """
        v_avail = ProductVariant.objects.create(
            product=self.product,
            name="Avail",
            is_visible=True,
            is_available=True,
        )
        v_hidden = ProductVariant.objects.create(
            product=self.product,
            name="Hidden",
            is_visible=False,
            is_available=True,
        )
        v_unavail = ProductVariant.objects.create(
            product=self.product,
            name="Unavail",
            is_visible=True,
            is_available=False,
        )

        available_variants = self.product.get_available_variants()
        self.assertIn(v_avail, available_variants)
        self.assertNotIn(v_hidden, available_variants)
        self.assertNotIn(v_unavail, available_variants)

    def test_product_deletion_cascades_to_variants(self):
        """
        Deleting a ShopProduct deletes its variants.
        """
        v = ProductVariant.objects.create(product=self.product, name="Sample Variant")
        v_id = v.id

        self.product.delete()
        self.assertFalse(ProductVariant.objects.filter(id=v_id).exists())

    def test_variant_deletion_does_not_delete_product(self):
        """
        Deleting a variant removes only the variant; the parent product remains.
        """
        v = ProductVariant.objects.create(product=self.product, name="Disposable Variant")
        v.delete()

        self.assertTrue(ShopProduct.objects.filter(id=self.product.id).exists())

    def test_variant_domain_aliases(self):
        """Variant aliases point to ProductVariant."""
        self.assertIs(Variant, ProductVariant)
        self.assertIs(ShopProductVariant, ProductVariant)


class ShopCategoryModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="merchant_cat1",
            email="merchant_cat1@example.com",
            mobile_number="+919876543231",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            status=Merchant.Status.ACTIVE,
        )
        self.shop1 = Shop.objects.create(
            merchant=self.merchant1,
            name="Category Mart Alpha",
            address_line="1 Market St",
            area="North",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user1.mobile_number,
        )

        self.user2 = User.objects.create_user(
            username="merchant_cat2",
            email="merchant_cat2@example.com",
            mobile_number="+919876543232",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            status=Merchant.Status.ACTIVE,
        )
        self.shop2 = Shop.objects.create(
            merchant=self.merchant2,
            name="Category Mart Beta",
            address_line="2 Market St",
            area="South",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user2.mobile_number,
        )

        self.product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Orange Juice 1L",
            price=Decimal("3.50"),
        )

    def test_merchant_category_crud_control(self):
        """Merchants have full CRUD control over Shop-owned categories."""
        # Create
        cat = ShopCategory.objects.create(
            shop=self.shop1,
            name="Beverages",
            slug="beverages",
            description="Drink items",
            is_active=True,
        )
        self.assertEqual(cat.shop, self.shop1)
        self.assertEqual(cat.name, "Beverages")
        self.assertEqual(str(cat), "Beverages (Shop: %s)" % self.shop1.id)

        # Update
        cat.name = "Refreshing Beverages"
        cat.save()
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Refreshing Beverages")

        # Delete
        cat_id = cat.id
        cat.delete()
        self.assertFalse(ShopCategory.objects.filter(id=cat_id).exists())

    def test_subcategory_creation_and_hierarchy(self):
        """Merchants can create subcategories and nested hierarchies."""
        parent_cat = ShopCategory.objects.create(
            shop=self.shop1,
            name="Beverages",
        )
        sub_cat = ShopCategory.objects.create(
            shop=self.shop1,
            parent=parent_cat,
            name="Juices",
        )
        nested_sub_cat = ShopCategory.objects.create(
            shop=self.shop1,
            parent=sub_cat,
            name="Cold-Pressed",
        )

        self.assertFalse(parent_cat.is_subcategory)
        self.assertTrue(sub_cat.is_subcategory)
        self.assertEqual(sub_cat.parent, parent_cat)
        self.assertIn(sub_cat, parent_cat.subcategories.all())
        self.assertEqual(str(sub_cat), "Beverages > Juices (Shop: %s)" % self.shop1.id)
        self.assertEqual(str(nested_sub_cat), "Juices > Cold-Pressed (Shop: %s)" % self.shop1.id)

    def test_parent_category_must_belong_to_same_shop(self):
        """A subcategory parent must belong to the same Shop; cross-shop parent is rejected."""
        shop2_cat = ShopCategory.objects.create(
            shop=self.shop2,
            name="Shop 2 Electronics",
        )
        invalid_subcat = ShopCategory(
            shop=self.shop1,
            parent=shop2_cat,
            name="Shop 1 Illegal Subcat",
        )
        with self.assertRaises(ValidationError):
            invalid_subcat.clean()

    def test_self_parenting_rejected(self):
        """A category cannot be its own parent."""
        cat = ShopCategory.objects.create(
            shop=self.shop1,
            name="Root",
        )
        cat.parent = cat
        with self.assertRaises(ValidationError):
            cat.clean()

    def test_product_belongs_to_multiple_categories(self):
        """Products can belong to multiple categories."""
        cat_drinks = ShopCategory.objects.create(shop=self.shop1, name="Drinks")
        cat_organic = ShopCategory.objects.create(shop=self.shop1, name="Organic")

        self.product.categories.add(cat_drinks, cat_organic)

        self.assertEqual(self.product.categories.count(), 2)
        self.assertIn(cat_drinks, self.product.categories.all())
        self.assertIn(cat_organic, self.product.categories.all())
        self.assertFalse(self.product.is_uncategorized)
        self.assertEqual(cat_drinks.products.count(), 1)

    def test_category_deletion_leaves_products_intact_and_uncategorized(self):
        """
        When a category is deleted, assigned products must remain intact and
        become uncategorized per the finalized Catalog specification.
        """
        cat_dairy = ShopCategory.objects.create(shop=self.shop1, name="Dairy")
        self.product.categories.add(cat_dairy)

        self.assertFalse(self.product.is_uncategorized)
        self.assertEqual(self.product.categories.count(), 1)

        # Delete category
        cat_dairy.delete()

        # Product must remain intact in DB and now be uncategorized
        self.product.refresh_from_db()
        self.assertTrue(ShopProduct.objects.filter(id=self.product.id).exists())
        self.assertEqual(self.product.categories.count(), 0)
        self.assertTrue(self.product.is_uncategorized)

    def test_multi_category_partial_deletion_preserves_remaining_categories(self):
        """
        When a product belongs to multiple categories and one is deleted,
        the product remains associated with the surviving categories.
        """
        cat_a = ShopCategory.objects.create(shop=self.shop1, name="Category A")
        cat_b = ShopCategory.objects.create(shop=self.shop1, name="Category B")
        self.product.categories.add(cat_a, cat_b)

        cat_a.delete()

        self.product.refresh_from_db()
        self.assertEqual(self.product.categories.count(), 1)
        self.assertIn(cat_b, self.product.categories.all())
        self.assertFalse(self.product.is_uncategorized)

    def test_shop_deletion_cascades_categories(self):
        """Deleting a Shop cascades and deletes all of its Shop categories."""
        cat = ShopCategory.objects.create(shop=self.shop1, name="Perishable")
        cat_id = cat.id

        self.shop1.delete()

        self.assertFalse(ShopCategory.objects.filter(id=cat_id).exists())

    def test_category_domain_alias(self):
        """Category alias points to ShopCategory."""
        self.assertIs(Category, ShopCategory)


class ShopBrandModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="merchant_brand1",
            email="merchant_brand1@example.com",
            mobile_number="+919876543241",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            status=Merchant.Status.ACTIVE,
        )
        self.shop1 = Shop.objects.create(
            merchant=self.merchant1,
            name="Brand Mart Alpha",
            address_line="10 Brand Blvd",
            area="North",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user1.mobile_number,
        )

        self.user2 = User.objects.create_user(
            username="merchant_brand2",
            email="merchant_brand2@example.com",
            mobile_number="+919876543242",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            status=Merchant.Status.ACTIVE,
        )
        self.shop2 = Shop.objects.create(
            merchant=self.merchant2,
            name="Brand Mart Beta",
            address_line="20 Brand Blvd",
            area="South",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user2.mobile_number,
        )

        self.product = ShopProduct.objects.create(
            shop=self.shop1,
            name="Almond Milk 1L",
            price=Decimal("4.50"),
        )

    def test_merchant_brand_crud_control(self):
        """Merchants have full CRUD control over Shop-owned brands."""
        brand = ShopBrand.objects.create(
            shop=self.shop1,
            name="NutriLife",
            slug="nutrilife",
            description="Organic nut-based milks and foods",
            is_active=True,
        )
        self.assertEqual(brand.shop, self.shop1)
        self.assertEqual(brand.name, "NutriLife")
        self.assertEqual(brand.slug, "nutrilife")
        self.assertTrue(brand.is_active)
        self.assertEqual(str(brand), "NutriLife (Shop: %s)" % self.shop1.id)

        # Update
        brand.name = "NutriLife Organics"
        brand.is_active = False
        brand.save()
        brand.refresh_from_db()
        self.assertEqual(brand.name, "NutriLife Organics")
        self.assertFalse(brand.is_active)

        # Delete
        brand_id = brand.id
        brand.delete()
        self.assertFalse(ShopBrand.objects.filter(id=brand_id).exists())

    def test_assign_shop_brand_to_product(self):
        """Merchants can assign a ShopBrand to a ShopProduct."""
        brand = ShopBrand.objects.create(shop=self.shop1, name="FarmFresh")
        self.product.brand_ref = brand
        self.product.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.brand_ref, brand)
        self.assertEqual(self.product.shop_brand, brand)
        self.assertEqual(self.product.effective_brand, "FarmFresh")
        self.assertIn(self.product, brand.products.all())

    def test_assign_via_shop_brand_property_setter(self):
        """Merchants can assign brand via shop_brand property setter."""
        brand = ShopBrand.objects.create(shop=self.shop1, name="SetterBrand")
        self.product.shop_brand = brand
        self.assertEqual(self.product.brand_ref, brand)
        self.assertEqual(self.product.effective_brand, "SetterBrand")

    def test_effective_brand_fallback_to_string_brand(self):
        """
        When brand_ref is not assigned, effective_brand returns product.brand string.
        """
        prod_with_str = ShopProduct.objects.create(
            shop=self.shop1,
            name="Green Tea",
            brand="ZenBrew",
        )
        self.assertIsNone(prod_with_str.brand_ref)
        self.assertEqual(prod_with_str.effective_brand, "ZenBrew")

    def test_cross_shop_brand_assignment_rejected(self):
        """
        Assigning a brand from a different Shop is rejected by multi-tenant validation.
        """
        shop2_brand = ShopBrand.objects.create(shop=self.shop2, name="ForeignBrand")
        self.product.brand_ref = shop2_brand
        with self.assertRaises(ValidationError) as ctx:
            self.product.clean()
        self.assertIn("brand_ref", ctx.exception.message_dict)

    def test_brand_deletion_preserves_assigned_product(self):
        """
        When a ShopBrand is deleted, assigned products must remain intact with
        their brand reference set to None (SET_NULL), preserving historical products.
        """
        brand = ShopBrand.objects.create(shop=self.shop1, name="PerishableBrand")
        self.product.brand_ref = brand
        self.product.brand = "PerishableBrand"
        self.product.save()

        brand_id = brand.id
        brand.delete()

        self.assertFalse(ShopBrand.objects.filter(id=brand_id).exists())
        self.product.refresh_from_db()
        self.assertTrue(ShopProduct.objects.filter(id=self.product.id).exists())
        self.assertIsNone(self.product.brand_ref)
        self.assertEqual(self.product.effective_brand, "PerishableBrand")

    def test_shop_deletion_cascades_brands(self):
        """Deleting a Shop cascades and deletes all of its Shop brands."""
        brand = ShopBrand.objects.create(shop=self.shop1, name="LocalBrand")
        brand_id = brand.id

        self.shop1.delete()
        self.assertFalse(ShopBrand.objects.filter(id=brand_id).exists())

    def test_independent_brand_customization_from_master_product(self):
        """
        Merchants can customize a selected Master Product's brand independently.
        Master Product brand updates/deletion do not affect Shop Product brand.
        """
        master_product = MasterProduct.objects.create(
            name="Cereal Box",
            brand="MasterBrand",
        )
        shop_product = ShopProduct.from_master_product(self.shop1, master_product)
        self.assertEqual(shop_product.brand, "MasterBrand")
        self.assertEqual(shop_product.effective_brand, "MasterBrand")

        # Merchant assigns a ShopBrand independently
        local_brand = ShopBrand.objects.create(shop=self.shop1, name="ShopCustomBrand")
        shop_product.brand_ref = local_brand
        shop_product.save()
        self.assertEqual(shop_product.effective_brand, "ShopCustomBrand")

        # Modifying master product brand does not affect shop product
        master_product.brand = "AlteredMasterBrand"
        master_product.save()
        shop_product.refresh_from_db()
        self.assertEqual(shop_product.effective_brand, "ShopCustomBrand")

        # Deleting master product does not affect shop product or shop brand
        master_product.delete()
        shop_product.refresh_from_db()
        self.assertTrue(ShopProduct.objects.filter(id=shop_product.id).exists())
        self.assertTrue(ShopBrand.objects.filter(id=local_brand.id).exists())
        self.assertEqual(shop_product.effective_brand, "ShopCustomBrand")

    def test_brand_domain_aliases(self):
        """Brand aliases point to ShopBrand."""
        self.assertIs(Brand, ShopBrand)
        self.assertIs(ShopProductBrand, ShopBrand)


class ShopCustomAttributeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="merchant_attr",
            email="merchant_attr@example.com",
            mobile_number="+919876543251",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Attr Mart",
            address_line="55 Config Way",
            area="Central",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )

    def test_merchant_custom_attribute_crud_control(self):
        """Merchants have full CRUD control over Shop-owned custom attributes and basic values."""
        attr = ShopCustomAttribute.objects.create(
            shop=self.shop,
            name="Dietary Preference",
            description="Customer dietary tags",
            values=["Vegan", "Vegetarian", "Gluten-Free"],
            is_active=True,
        )
        self.assertEqual(attr.shop, self.shop)
        self.assertEqual(attr.name, "Dietary Preference")
        self.assertEqual(attr.values, ["Vegan", "Vegetarian", "Gluten-Free"])
        self.assertEqual(str(attr), "Dietary Preference (Shop: %s)" % self.shop.id)

        # Update
        attr.name = "Dietary Lifestyle"
        attr.values = ["Vegan", "Keto", "Paleo"]
        attr.is_active = False
        attr.save()
        attr.refresh_from_db()
        self.assertEqual(attr.name, "Dietary Lifestyle")
        self.assertEqual(attr.values, ["Vegan", "Keto", "Paleo"])
        self.assertFalse(attr.is_active)

        # Delete
        attr_id = attr.id
        attr.delete()
        self.assertFalse(ShopCustomAttribute.objects.filter(id=attr_id).exists())

    def test_attribute_add_and_remove_value_helpers(self):
        """Helpers allow adding and removing basic attribute values cleanly."""
        attr = ShopCustomAttribute.objects.create(
            shop=self.shop,
            name="Size Options",
            values=["Small", "Medium"],
        )
        attr.add_value("Large")
        self.assertEqual(attr.values, ["Small", "Medium", "Large"])

        # Idempotent add
        attr.add_value("Large")
        self.assertEqual(attr.values, ["Small", "Medium", "Large"])

        attr.remove_value("Medium")
        self.assertEqual(attr.values, ["Small", "Large"])

    def test_attribute_values_validation(self):
        """Values field must be a list containing primitive items."""
        invalid_attr_not_list = ShopCustomAttribute(
            shop=self.shop,
            name="Bad Attr",
            values="not a list",
        )
        with self.assertRaises(ValidationError) as ctx:
            invalid_attr_not_list.clean()
        self.assertIn("values", ctx.exception.message_dict)

        invalid_attr_nested = ShopCustomAttribute(
            shop=self.shop,
            name="Bad Nested",
            values=[{"nested": "dictionary"}],
        )
        with self.assertRaises(ValidationError) as ctx:
            invalid_attr_nested.clean()
        self.assertIn("values", ctx.exception.message_dict)

    def test_shop_deletion_cascades_custom_attributes(self):
        """Deleting a Shop cascades and deletes its custom attributes."""
        attr = ShopCustomAttribute.objects.create(shop=self.shop, name="Packaging")
        attr_id = attr.id

        self.shop.delete()
        self.assertFalse(ShopCustomAttribute.objects.filter(id=attr_id).exists())

    def test_attribute_domain_aliases(self):
        """Attribute domain aliases point to ShopCustomAttribute."""
        self.assertIs(ShopAttribute, ShopCustomAttribute)
        self.assertIs(CustomAttribute, ShopCustomAttribute)
        self.assertIs(Attribute, ShopCustomAttribute)


class ProductAndVariantCustomAttributesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="merchant_prod_attr",
            email="merchant_prod_attr@example.com",
            mobile_number="+919876543261",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Product Attr Mart",
            address_line="77 Feature Rd",
            area="West",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Artisan Sourdough",
            price=Decimal("5.00"),
            attributes={
                "Flavors": ["Original", "Rosemary", "Garlic"],
                "Dietary": ["Vegan", "Organic"],
                "Shelf Life Days": 5,
                "Contains Gluten": True,
            },
        )

    def test_product_multiple_attributes_with_multiple_values(self):
        """
        Shop products support multiple custom attributes with multiple values
        per the finalized specification.
        """
        self.assertEqual(len(self.product.attributes["Flavors"]), 3)
        self.assertIn("Rosemary", self.product.attributes["Flavors"])
        self.assertEqual(self.product.attributes["Dietary"], ["Vegan", "Organic"])
        self.assertEqual(self.product.attributes["Shelf Life Days"], 5)
        self.assertTrue(self.product.attributes["Contains Gluten"])

    def test_product_attribute_helper_methods(self):
        """Product helper methods for managing attributes and multiple values."""
        # get_attribute
        self.assertEqual(self.product.get_attribute("Shelf Life Days"), 5)
        self.assertIsNone(self.product.get_attribute("NonExistent"))
        self.assertEqual(self.product.get_attribute("NonExistent", default="DefaultVal"), "DefaultVal")

        # set_attribute
        self.product.set_attribute("Origin", "France")
        self.assertEqual(self.product.get_attribute("Origin"), "France")

        # add_attribute_value to existing list
        self.product.add_attribute_value("Flavors", "Olive")
        self.assertIn("Olive", self.product.get_attribute("Flavors"))
        # idempotent add
        self.product.add_attribute_value("Flavors", "Olive")
        self.assertEqual(self.product.get_attribute("Flavors").count("Olive"), 1)

        # add_attribute_value to scalar converts to list
        self.product.add_attribute_value("Origin", "Italy")
        self.assertEqual(self.product.get_attribute("Origin"), ["France", "Italy"])

        # add_attribute_value to new attribute
        self.product.add_attribute_value("Packaging", "Paper Bag")
        self.assertEqual(self.product.get_attribute("Packaging"), ["Paper Bag"])

        # remove_attribute
        self.product.remove_attribute("Contains Gluten")
        self.assertIsNone(self.product.get_attribute("Contains Gluten"))

    def test_variant_custom_attributes_independent_from_product(self):
        """
        Variants have their own custom attributes independent of the parent product.
        """
        v1 = ProductVariant.objects.create(
            product=self.product,
            name="Half Loaf",
            price=Decimal("3.00"),
            attributes={
                "Weight": "400g",
                "Slice Options": ["Thick", "Thin"],
            },
        )
        v2 = ProductVariant.objects.create(
            product=self.product,
            name="Whole Loaf",
            price=Decimal("5.00"),
            attributes={
                "Weight": "800g",
                "Slice Options": ["Thick", "Thin", "Unsliced"],
            },
        )

        self.assertEqual(v1.attributes["Weight"], "400g")
        self.assertEqual(v1.attributes["Slice Options"], ["Thick", "Thin"])
        self.assertEqual(v2.attributes["Weight"], "800g")
        self.assertEqual(len(v2.attributes["Slice Options"]), 3)
        # Parent product attributes unchanged
        self.assertNotIn("Weight", self.product.attributes)

    def test_variant_attribute_helper_methods(self):
        """Variant helper methods for managing attributes and multiple values."""
        variant = ProductVariant.objects.create(
            product=self.product,
            name="Mini Bun",
            price=Decimal("1.50"),
            attributes={"Pack": "Single"},
        )
        self.assertEqual(variant.get_attribute("Pack"), "Single")
        variant.set_attribute("Temperature", "Room")
        self.assertEqual(variant.get_attribute("Temperature"), "Room")

        variant.add_attribute_value("Pack", "4-Pack")
        self.assertEqual(variant.get_attribute("Pack"), ["Single", "4-Pack"])

        variant.remove_attribute("Temperature")
        self.assertIsNone(variant.get_attribute("Temperature"))

    def test_attribute_validation_rejects_malformed_structures(self):
        """clean() validation catches invalid attribute structures on product and variant."""
        # Non-dict product attributes
        p_invalid_type = ShopProduct(
            shop=self.shop,
            name="Bad Attr Product",
            attributes="not a dictionary",
        )
        with self.assertRaises(ValidationError) as ctx:
            p_invalid_type.clean()
        self.assertIn("attributes", ctx.exception.message_dict)

        # Empty key
        p_invalid_key = ShopProduct(
            shop=self.shop,
            name="Bad Key Product",
            attributes={"": "value"},
        )
        with self.assertRaises(ValidationError) as ctx:
            p_invalid_key.clean()
        self.assertIn("attributes", ctx.exception.message_dict)

        # Nested complex object in value
        p_invalid_val = ShopProduct(
            shop=self.shop,
            name="Bad Value Product",
            attributes={"Complex": {"deep": "nested"}},
        )
        with self.assertRaises(ValidationError) as ctx:
            p_invalid_val.clean()
        self.assertIn("attributes", ctx.exception.message_dict)

        # Non-primitive item in list
        p_invalid_list = ShopProduct(
            shop=self.shop,
            name="Bad List Product",
            attributes={"Items": [{"dict": "item"}]},
        )
        with self.assertRaises(ValidationError) as ctx:
            p_invalid_list.clean()
        self.assertIn("attributes", ctx.exception.message_dict)

        # Variant validation
        v_invalid = ProductVariant(
            product=self.product,
            name="Bad Variant",
            attributes="invalid",
        )
        with self.assertRaises(ValidationError) as ctx:
            v_invalid.clean()
        self.assertIn("attributes", ctx.exception.message_dict)

    def test_master_product_independence_with_attributes(self):
        """
        Master Catalog product has no custom attributes.
        Shop product created from Master Product can define custom attributes freely.
        """
        mp = MasterProduct.objects.create(name="Global Pasta")
        sp = ShopProduct.from_master_product(self.shop, mp)

        self.assertEqual(sp.attributes, {})
        sp.set_attribute("Grain", ["Durum Wheat", "Semolina"])
        sp.save()
        sp.refresh_from_db()
        self.assertEqual(sp.attributes["Grain"], ["Durum Wheat", "Semolina"])


class ShopProductAndVariantFieldsAndAvailabilityTests(TestCase):
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
        self.user = User.objects.create_user(
            username="merchant_cat006",
            email="merchant_cat006@example.com",
            mobile_number="+919876543271",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Field Mart",
            address_line="100 Field St",
            area="North",
            city="Metropolis",
            state="State",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )
        self.category = ShopCategory.objects.create(shop=self.shop, name="Dairy & Eggs")
        self.brand = ShopBrand.objects.create(shop=self.shop, name="PureFarm")

        dummy_img = SimpleUploadedFile("product.png", b"dummy_img_bytes", content_type="image/png")
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Farm Fresh Whole Milk",
            description="Pure pasteurized cow milk",
            brand="PureFarm",
            brand_ref=self.brand,
            price=Decimal("3.75"),
            sku="MILK-FF-01",
            image=dummy_img,
            is_visible=True,
            is_available=True,
            attributes={"Origin": "Local Dairy", "Fat Content": "3.5%"},
        )
        self.product.categories.add(self.category)

    def test_catalog_visibility_hidden_product_and_variant(self):
        """
        Hidden products/variants are not visible in customer catalog and cannot be ordered.
        Hiding a parent product also hides its variants from customer visibility.
        """
        # Visible product
        self.assertTrue(self.product.is_customer_visible)
        self.assertEqual(self.product.get_display_status(), "AVAILABLE")

        # Hide product
        self.product.is_visible = False
        self.assertFalse(self.product.is_customer_visible)
        self.assertEqual(self.product.get_display_status(), "HIDDEN")
        self.assertFalse(self.product.is_orderable())

        # Variant visibility under hidden product
        variant = ProductVariant.objects.create(
            product=self.product,
            name="1L Bottle",
            is_visible=True,
            is_available=True,
        )
        self.assertFalse(variant.is_customer_visible)
        self.assertEqual(variant.get_display_status(), "HIDDEN")
        self.assertFalse(variant.is_orderable())

        # Unhide product, but hide variant
        self.product.is_visible = True
        self.product.save()
        variant.is_visible = False
        variant.save()
        self.assertTrue(self.product.is_customer_visible)
        self.assertFalse(variant.is_customer_visible)
        self.assertEqual(variant.get_display_status(), "HIDDEN")
        self.assertNotIn(variant, self.product.get_visible_variants())

    def test_distinction_manual_availability_vs_inventory_stock(self):
        """
        Preserve strict distinction between manual availability and inventory availability:
        - Manual availability=False: remains visible in catalog, shows UNAVAILABLE, not orderable.
        - Out-of-stock (stock=0): remains visible in catalog, shows OUT_OF_STOCK, not orderable. Zero stock does not hide.
        - In-stock + manually available: AVAILABLE and orderable.
        """
        # 1. Manually unavailable: remains visible to customers, cannot be ordered
        self.product.is_available = False
        self.assertTrue(self.product.is_customer_visible)
        self.assertEqual(self.product.get_display_status(), "UNAVAILABLE")
        self.assertFalse(self.product.is_orderable())

        # 2. Manually available, but out of stock (stock_quantity=0)
        self.product.is_available = True
        self.assertTrue(self.product.is_customer_visible)
        self.assertEqual(self.product.get_display_status(stock_quantity=0), "OUT_OF_STOCK")
        self.assertFalse(self.product.is_orderable(stock_quantity=0))

        # 3. Manually available and in stock (stock_quantity=10)
        self.assertTrue(self.product.is_customer_visible)
        self.assertEqual(self.product.get_display_status(stock_quantity=10), "AVAILABLE")
        self.assertTrue(self.product.is_orderable(stock_quantity=10))

    def test_variant_availability_permutations_and_all_unavailable_oos_behavior(self):
        """
        For variant products:
        - Customers see only available variants.
        - If all variants are unavailable or out-of-stock, the main product displays OUT_OF_STOCK.
        """
        v1 = ProductVariant.objects.create(
            product=self.product,
            name="500ml",
            price=Decimal("2.00"),
            is_visible=True,
            is_available=True,
        )
        v2 = ProductVariant.objects.create(
            product=self.product,
            name="1L",
            price=Decimal("3.50"),
            is_visible=True,
            is_available=True,
        )

        stock_map = {v1.id: 5, v2.id: 0}  # v1 in stock, v2 out of stock
        available_variants = self.product.get_available_variants(stock_map=stock_map)
        self.assertIn(v1, available_variants)
        self.assertNotIn(v2, available_variants)
        self.assertEqual(self.product.get_display_status(variant_stock_map=stock_map), "AVAILABLE")

        # When all variants are out of stock
        all_oos_stock_map = {v1.id: 0, v2.id: 0}
        self.assertEqual(self.product.get_display_status(variant_stock_map=all_oos_stock_map), "OUT_OF_STOCK")

        # When all variants are manually unavailable
        v1.is_available = False
        v1.save()
        v2.is_available = False
        v2.save()
        self.assertEqual(self.product.get_display_status(), "OUT_OF_STOCK")

    def test_image_behavior_and_variant_fallback(self):
        """
        MVP supports one image per product and optional image per variant.
        Variant without image falls back to parent product image; variant with image uses its own.
        Product can exist without image.
        """
        # Product with image
        self.assertTrue(self.product.has_image)

        # Variant with no image falls back to product image
        v_no_img = ProductVariant.objects.create(
            product=self.product,
            name="2L Jug",
            image=None,
        )
        self.assertTrue(v_no_img.has_image)
        self.assertEqual(v_no_img.effective_image, self.product.image)

        # Variant with its own image
        dummy_var_img = SimpleUploadedFile("var.png", b"var_bytes", content_type="image/png")
        v_with_img = ProductVariant.objects.create(
            product=self.product,
            name="5L Can",
            image=dummy_var_img,
        )
        self.assertTrue(v_with_img.has_image)
        self.assertEqual(v_with_img.effective_image, v_with_img.image)

        # Product without image
        prod_no_img = ShopProduct.objects.create(shop=self.shop, name="Bulk Grain")
        self.assertFalse(prod_no_img.has_image)
        self.assertFalse(bool(prod_no_img.image))

    def test_decimal_pricing_and_sku_behavior(self):
        """
        Pricing is shop-specific decimal values; variants support optional price falling back to product.
        SKUs are merchant-managed and duplicate SKUs are allowed across variants.
        """
        v_custom_price = ProductVariant.objects.create(
            product=self.product,
            name="Single Serve",
            price=Decimal("1.25"),
            sku="SHARED-SKU-100",
        )
        v_inherited_price = ProductVariant.objects.create(
            product=self.product,
            name="Family Pack",
            price=None,
            sku="SHARED-SKU-100",
        )

        self.assertEqual(v_custom_price.effective_price, Decimal("1.25"))
        self.assertEqual(v_inherited_price.effective_price, Decimal("3.75"))
        self.assertEqual(v_custom_price.sku, v_inherited_price.sku)

    def test_brand_description_and_category_relationships(self):
        """
        Verify brand, description, and category relationships:
        - Product categories and is_uncategorized.
        - Variant description and brand fallbacks to parent product.
        """
        self.assertEqual(self.product.categories.count(), 1)
        self.assertFalse(self.product.is_uncategorized)
        self.assertEqual(self.product.effective_brand, "PureFarm")

        v_inherited = ProductVariant.objects.create(
            product=self.product,
            name="Standard Variant",
        )
        self.assertEqual(v_inherited.effective_description, self.product.description)
        self.assertEqual(v_inherited.effective_brand, "PureFarm")

        v_custom_desc = ProductVariant.objects.create(
            product=self.product,
            name="Custom Variant",
            description="Special variant notes",
        )
        self.assertEqual(v_custom_desc.effective_description, "Special variant notes")


class MasterProductSuperAdminAPITests(TestCase):
    """
    Unit and integration tests for Super Admin CRUD APIs on Master Catalog products.

    Validates:
    - Super Admin full CRUD operations (Create, List, Retrieve, Update, Delete).
    - Unauthenticated requests are rejected with 401.
    - Non-Super Admin (Merchant) requests are rejected with 403.
    - Input validation (blank/whitespace name, non-existent category).
    - Queryset filtering (is_active, category, search).
    - Master Catalog independence: updates and deletions do not alter or delete Shop Products.
    """

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
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            username="test_super_admin",
            mobile_number="+919876543210",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )
        self.merchant_user = User.objects.create_user(
            username="test_merchant",
            mobile_number="+919876543211",
            password="merchantpassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Organic Corner",
        )
        self.category = MasterCategory.objects.create(
            name="Fresh Dairy",
            slug="fresh-dairy",
            description="Dairy and refrigerated items",
        )
        self.base_url = "/api/v1/catalog/master-products/"

    def _auth_super_admin(self):
        login_res = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": self.super_admin.mobile_number, "password": "adminpassword123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _auth_merchant(self):
        login_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.merchant_user.mobile_number, "password": "merchantpassword123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_super_admin_create_master_product(self):
        self._auth_super_admin()
        payload = {
            "name": "Whole Milk 1L",
            "description": "Farm-fresh pasteurized whole milk",
            "category": self.category.id,
            "brand": "Amul",
            "is_active": True,
        }
        response = self.client.post(self.base_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Whole Milk 1L")
        self.assertEqual(response.data["category"], self.category.id)
        self.assertEqual(response.data["category_name"], "Fresh Dairy")
        self.assertEqual(response.data["brand"], "Amul")
        self.assertTrue(response.data["is_active"])
        self.assertTrue(MasterProduct.objects.filter(id=response.data["id"]).exists())

    def test_super_admin_create_master_product_validation(self):
        self._auth_super_admin()

        # Missing or blank name
        response = self.client.post(self.base_url, {"name": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

        # Whitespace-only name
        response = self.client.post(self.base_url, {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

        # Invalid category ID
        response = self.client.post(self.base_url, {"name": "Valid Name", "category": 99999}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_super_admin_list_master_products_and_filtering(self):
        self._auth_super_admin()
        cat2 = MasterCategory.objects.create(name="Beverages", slug="beverages")

        mp1 = MasterProduct.objects.create(name="Apple Juice", category=cat2, brand="Tropicana", is_active=True)
        mp2 = MasterProduct.objects.create(name="Orange Juice", category=cat2, brand="Tropicana", is_active=False)
        mp3 = MasterProduct.objects.create(name="Greek Yogurt", category=self.category, brand="Nestle", is_active=True)

        # List all
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        # Filter by is_active=true
        response_active = self.client.get(f"{self.base_url}?is_active=true")
        self.assertEqual(response_active.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_active.data), 2)
        names = [item["name"] for item in response_active.data]
        self.assertIn("Apple Juice", names)
        self.assertIn("Greek Yogurt", names)

        # Filter by is_active=false
        response_inactive = self.client.get(f"{self.base_url}?is_active=false")
        self.assertEqual(response_inactive.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_inactive.data), 1)
        self.assertEqual(response_inactive.data[0]["name"], "Orange Juice")

        # Filter by category
        response_cat = self.client.get(f"{self.base_url}?category={cat2.id}")
        self.assertEqual(response_cat.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_cat.data), 2)

        # Search by name
        response_search = self.client.get(f"{self.base_url}?search=Yogurt")
        self.assertEqual(response_search.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_search.data), 1)
        self.assertEqual(response_search.data[0]["name"], "Greek Yogurt")

    def test_super_admin_retrieve_master_product(self):
        self._auth_super_admin()
        mp = MasterProduct.objects.create(
            name="Almond Milk",
            description="Unsweetened almond milk",
            category=self.category,
            brand="Silk",
            is_active=True,
        )
        response = self.client.get(f"{self.base_url}{mp.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Almond Milk")
        self.assertEqual(response.data["brand"], "Silk")
        self.assertEqual(response.data["category_name"], "Fresh Dairy")

    def test_super_admin_update_master_product_put_and_patch(self):
        self._auth_super_admin()
        mp = MasterProduct.objects.create(
            name="Organic Butter",
            description="Salted butter",
            category=self.category,
            brand="Amul",
            is_active=True,
        )

        # PATCH partial update
        patch_res = self.client.patch(
            f"{self.base_url}{mp.id}/",
            {"brand": "Amul Gold", "description": "Unsalted pure butter"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        mp.refresh_from_db()
        self.assertEqual(mp.brand, "Amul Gold")
        self.assertEqual(mp.description, "Unsalted pure butter")
        self.assertEqual(mp.name, "Organic Butter")

        # PUT full update
        put_res = self.client.put(
            f"{self.base_url}{mp.id}/",
            {
                "name": "Organic Table Butter",
                "description": "500g block",
                "category": self.category.id,
                "brand": "Amul Gold",
                "is_active": False,
            },
            format="json",
        )
        self.assertEqual(put_res.status_code, status.HTTP_200_OK)
        mp.refresh_from_db()
        self.assertEqual(mp.name, "Organic Table Butter")
        self.assertFalse(mp.is_active)

    def test_super_admin_delete_master_product(self):
        self._auth_super_admin()
        mp = MasterProduct.objects.create(name="Temporary Product")
        response = self.client.delete(f"{self.base_url}{mp.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MasterProduct.objects.filter(id=mp.id).exists())

    def test_unauthenticated_requests_denied(self):
        # Without credentials
        mp = MasterProduct.objects.create(name="Secured Product")

        self.assertEqual(self.client.get(self.base_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.base_url, {"name": "Test"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(f"{self.base_url}{mp.id}/").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(f"{self.base_url}{mp.id}/", {"name": "New"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(f"{self.base_url}{mp.id}/").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_merchant_requests_denied_with_403(self):
        self._auth_merchant()
        mp = MasterProduct.objects.create(name="Secured Product")

        self.assertEqual(self.client.get(self.base_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(self.base_url, {"name": "Test"}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(f"{self.base_url}{mp.id}/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(f"{self.base_url}{mp.id}/", {"name": "New"}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(f"{self.base_url}{mp.id}/").status_code, status.HTTP_403_FORBIDDEN)

    def test_master_product_independence_on_update(self):
        """
        Updating a Master Product does NOT alter any existing Shop Product.
        """
        self._auth_super_admin()
        mp = MasterProduct.objects.create(
            name="Original Master Name",
            brand="Original Master Brand",
            description="Original Master Desc",
        )
        shop_product = ShopProduct.objects.create(
            shop=self.shop,
            master_product=mp,
            name="Shop Customized Product",
            brand="Shop Independent Brand",
            description="Shop specific description",
            price=Decimal("15.50"),
        )

        # Super Admin updates MasterProduct
        response = self.client.patch(
            f"{self.base_url}{mp.id}/",
            {
                "name": "Modified Master Name",
                "brand": "Modified Master Brand",
                "description": "Modified Master Desc",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # ShopProduct must remain completely unchanged
        shop_product.refresh_from_db()
        self.assertEqual(shop_product.name, "Shop Customized Product")
        self.assertEqual(shop_product.brand, "Shop Independent Brand")
        self.assertEqual(shop_product.description, "Shop specific description")
        self.assertEqual(shop_product.price, Decimal("15.50"))
        self.assertEqual(shop_product.master_product_id, mp.id)

    def test_master_product_independence_on_deletion(self):
        """
        Deleting a Master Product preserves existing Shop Products.
        The reference becomes NULL (SET_NULL) without deleting the Shop Product.
        """
        self._auth_super_admin()
        mp = MasterProduct.objects.create(
            name="To Be Deleted Master",
            brand="Master Brand",
        )
        shop_product = ShopProduct.objects.create(
            shop=self.shop,
            master_product=mp,
            name="Merchant Sellable Product",
            brand="Merchant Brand",
            price=Decimal("25.00"),
        )

        # Super Admin deletes MasterProduct
        response = self.client.delete(f"{self.base_url}{mp.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # MasterProduct is deleted
        self.assertFalse(MasterProduct.objects.filter(id=mp.id).exists())

        # ShopProduct remains intact in the shop's catalog
        shop_product.refresh_from_db()
        self.assertIsNone(shop_product.master_product)
        self.assertEqual(shop_product.name, "Merchant Sellable Product")
        self.assertEqual(shop_product.price, Decimal("25.00"))

    def test_direct_url_alias(self):
        """
        Test direct /api/v1/master-products/ alias also routes to the same CRUD operations.
        """
        self._auth_super_admin()
        direct_url = "/api/v1/master-products/"
        response = self.client.post(
            direct_url,
            {"name": "Direct Alias Product", "brand": "Direct Brand"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Direct Alias Product")


class SuperAdminPromoteShopProductAPITests(TestCase):
    """
    Tests for Super Admin promotion of a Merchant-created Shop Product into the Master Catalog (CAT-009).

    Validates:
    - Super Admin can promote a Merchant-created Shop Product into Master Catalog via
      /api/v1/catalog/shop-products/<id>/promote/ and /api/v1/catalog/master-products/promote/.
    - Promotion creates reusable Master Catalog content available to other Merchants.
    - Promotion strictly does NOT link, replace, update, or merge the originating Shop Product.
    - Originating Shop Product's fields, pricing, SKU, and master_product FK remain unmodified.
    - Subsequent updates/deletions on the Master Product do not alter the originating Shop Product,
      and vice versa.
    - Optional overrides (name, description, brand, category, is_active) work as expected.
    - Image fallback/assignment is preserved.
    - Authorization: unauthenticated requests return 401; non-Super Admin (Merchant) requests return 403.
    - Edge cases: non-existent Shop Product returns 404; invalid overrides return 400.
    """

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
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            username="super_admin_promoter",
            mobile_number="+919876543220",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )
        self.merchant_user = User.objects.create_user(
            username="merchant_creator",
            mobile_number="+919876543221",
            password="merchantpassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Baker Street Delights",
        )
        self.master_category = MasterCategory.objects.create(
            name="Bakery & Bread",
            slug="bakery-bread",
            description="Freshly baked goods",
        )
        self.shop_product = ShopProduct.objects.create(
            shop=self.shop,
            master_product=None,
            name="Sourdough Loaf",
            description="Slow-fermented artisan sourdough",
            brand="Artisan Bake",
            price=Decimal("4.50"),
            sku="SOUR-001",
            is_visible=True,
            is_available=True,
        )

    def _auth_super_admin(self):
        login_res = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": self.super_admin.mobile_number, "password": "adminpassword123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _auth_merchant(self):
        login_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.merchant_user.mobile_number, "password": "merchantpassword123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_super_admin_promote_shop_product_via_shop_product_endpoint(self):
        """
        Super Admin promotes a Shop Product via /api/v1/catalog/shop-products/<id>/promote/.
        """
        self._auth_super_admin()
        url = f"/api/v1/catalog/shop-products/{self.shop_product.id}/promote/"
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Sourdough Loaf")
        self.assertEqual(response.data["description"], "Slow-fermented artisan sourdough")
        self.assertEqual(response.data["brand"], "Artisan Bake")
        self.assertIsNone(response.data["category"])
        self.assertTrue(response.data["is_active"])

        # Master Product was created
        master_product = MasterProduct.objects.get(id=response.data["id"])
        self.assertEqual(master_product.name, "Sourdough Loaf")

        # Originating Shop Product was NOT linked, replaced, updated, or merged
        self.shop_product.refresh_from_db()
        self.assertIsNone(self.shop_product.master_product)
        self.assertEqual(self.shop_product.name, "Sourdough Loaf")
        self.assertEqual(self.shop_product.price, Decimal("4.50"))
        self.assertEqual(self.shop_product.sku, "SOUR-001")

    def test_super_admin_promote_shop_product_via_master_product_promote_action(self):
        """
        Super Admin promotes a Shop Product via /api/v1/catalog/master-products/promote/.
        """
        self._auth_super_admin()
        url = "/api/v1/catalog/master-products/promote/"
        response = self.client.post(url, {"shop_product_id": self.shop_product.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Sourdough Loaf")

        # Originating Shop Product was NOT linked
        self.shop_product.refresh_from_db()
        self.assertIsNone(self.shop_product.master_product)

    def test_promotion_with_optional_overrides_and_category(self):
        """
        Super Admin can override name, description, brand, category, and is_active during promotion.
        """
        self._auth_super_admin()
        url = f"/api/v1/catalog/shop-products/{self.shop_product.id}/promote/"
        payload = {
            "name": "Platform Universal Sourdough",
            "description": "Standardized description for catalog",
            "brand": "Universal Bakery",
            "category": self.master_category.id,
            "is_active": True,
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Platform Universal Sourdough")
        self.assertEqual(response.data["description"], "Standardized description for catalog")
        self.assertEqual(response.data["brand"], "Universal Bakery")
        self.assertEqual(response.data["category"], self.master_category.id)
        self.assertEqual(response.data["category_name"], "Bakery & Bread")

        # Originating Shop Product retains all its original data
        self.shop_product.refresh_from_db()
        self.assertEqual(self.shop_product.name, "Sourdough Loaf")
        self.assertEqual(self.shop_product.brand, "Artisan Bake")
        self.assertEqual(self.shop_product.description, "Slow-fermented artisan sourdough")
        self.assertIsNone(self.shop_product.master_product)

    def test_promotion_strict_independence_after_promotion(self):
        """
        Verify that after promotion:
        - Modifying the new MasterProduct does NOT modify the originating ShopProduct.
        - Modifying the originating ShopProduct does NOT modify the new MasterProduct.
        - Deleting the new MasterProduct does NOT delete or alter the ShopProduct.
        - Deleting the originating ShopProduct does NOT delete or alter the MasterProduct.
        """
        self._auth_super_admin()
        url = f"/api/v1/catalog/shop-products/{self.shop_product.id}/promote/"
        response = self.client.post(url, {}, format="json")
        master_id = response.data["id"]
        master_product = MasterProduct.objects.get(id=master_id)

        # 1. Update Master Product -> Shop Product untouched
        master_product.name = "Globally Renamed Sourdough"
        master_product.brand = "Global Brand"
        master_product.save()

        self.shop_product.refresh_from_db()
        self.assertEqual(self.shop_product.name, "Sourdough Loaf")
        self.assertEqual(self.shop_product.brand, "Artisan Bake")

        # 2. Update Shop Product -> Master Product untouched
        self.shop_product.name = "Locally Modified Loaf"
        self.shop_product.save()

        master_product.refresh_from_db()
        self.assertEqual(master_product.name, "Globally Renamed Sourdough")

        # 3. Delete Master Product -> Shop Product untouched
        master_product.delete()
        self.assertFalse(MasterProduct.objects.filter(id=master_id).exists())

        self.shop_product.refresh_from_db()
        self.assertEqual(self.shop_product.name, "Locally Modified Loaf")
        self.assertIsNone(self.shop_product.master_product)

    def test_promote_shop_product_with_image(self):
        """
        Promotion preserves the shop product image reference for reusable content.
        """
        self._auth_super_admin()
        image = SimpleUploadedFile("sourdough.jpg", b"image_binary_data", content_type="image/jpeg")
        self.shop_product.image = image
        self.shop_product.save()

        url = f"/api/v1/catalog/shop-products/{self.shop_product.id}/promote/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        master_product = MasterProduct.objects.get(id=response.data["id"])
        self.assertTrue(bool(master_product.image))

    def test_promotion_non_existent_shop_product_returns_404(self):
        self._auth_super_admin()
        # Via shop-products endpoint
        url_shop = "/api/v1/catalog/shop-products/99999/promote/"
        response = self.client.post(url_shop, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Via master-products endpoint
        url_master = "/api/v1/catalog/master-products/promote/"
        response = self.client.post(url_master, {"shop_product_id": 99999}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_promotion_validation_errors(self):
        self._auth_super_admin()
        url = f"/api/v1/catalog/shop-products/{self.shop_product.id}/promote/"

        # Whitespace-only name override
        response = self.client.post(url, {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

        # Invalid category ID
        response = self.client.post(url, {"category": 99999}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_promotion_unauthenticated_request_denied_with_401(self):
        url = f"/api/v1/catalog/shop-products/{self.shop_product.id}/promote/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_promotion_merchant_request_denied_with_403(self):
        self._auth_merchant()
        url = f"/api/v1/catalog/shop-products/{self.shop_product.id}/promote/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MerchantShopProductAPITests(TestCase):
    """
    Unit and integration tests for Merchant CRUD APIs on their own Shop Products (CAT-010, CAT-011).

    Validates:
    - Direct creation by Merchant (no Super Admin approval needed; immediately active and usable).
    - Creation by selecting from Master Catalog (reusing master metadata with optional overrides).
    - Server-side shop authorization on every operation (unauthenticated 401, non-merchant 403,
      no-shop 404, inactive-shop 403).
    - Strict multi-tenant isolation: Merchant A cannot list, retrieve, update, or delete Merchant B's products.
    - Cross-tenant validation: Cannot assign brand_ref or categories belonging to another shop.
    - Full CRUD support (list, retrieve, create, update, delete).
    - Client-provided shop_id is ignored and cannot override authenticated tenancy.
    - Both /api/v1/catalog/products/ and /api/v1/shops/me/products/ routes work as expected.
    """

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
        self.client = APIClient()

        # Merchant A and Shop A
        self.user_a = User.objects.create_user(
            username="merchant_a",
            mobile_number="+919876543310",
            password="password123",
            role=User.Role.MERCHANT,
        )
        self.merchant_a = Merchant.objects.create(
            user=self.user_a,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop_a = Shop.objects.create(
            merchant=self.merchant_a,
            name="Shop A Green Grocer",
        )
        self.brand_a = ShopBrand.objects.create(
            shop=self.shop_a,
            name="Organic A",
            slug="organic-a",
        )
        self.category_a = ShopCategory.objects.create(
            shop=self.shop_a,
            name="Fresh Veggies A",
            slug="veggies-a",
        )

        # Merchant B and Shop B (Tenant isolation adversary)
        self.user_b = User.objects.create_user(
            username="merchant_b",
            mobile_number="+919876543320",
            password="password123",
            role=User.Role.MERCHANT,
        )
        self.merchant_b = Merchant.objects.create(
            user=self.user_b,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop_b = Shop.objects.create(
            merchant=self.merchant_b,
            name="Shop B Supermart",
        )
        self.brand_b = ShopBrand.objects.create(
            shop=self.shop_b,
            name="Organic B",
            slug="organic-b",
        )
        self.category_b = ShopCategory.objects.create(
            shop=self.shop_b,
            name="Fresh Veggies B",
            slug="veggies-b",
        )

        # Super Admin
        self.super_admin = User.objects.create_user(
            username="super_admin_cat10",
            mobile_number="+919876543330",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )

        # Platform Master Product
        self.master_cat = MasterCategory.objects.create(name="Dairy", slug="dairy")
        self.master_product = MasterProduct.objects.create(
            name="Pure Cow Ghee 500g",
            description="Traditional aromatic cow ghee",
            brand="Heritage Cow",
            category=self.master_cat,
            is_active=True,
        )

        self.base_url = "/api/v1/catalog/products/"

    def _auth_merchant(self, user):
        login_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": user.mobile_number, "password": "password123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _auth_super_admin(self):
        login_res = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": self.super_admin.mobile_number, "password": "adminpassword123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_direct_product_creation_by_merchant(self):
        """
        Merchant can directly create a product in their Shop Catalog.
        No Super Admin approval is required.
        """
        self._auth_merchant(self.user_a)
        payload = {
            "name": "Fresh Spinach Bunch",
            "description": "Crisp local green spinach",
            "brand": "Local Farm",
            "brand_ref": self.brand_a.id,
            "categories": [self.category_a.id],
            "price": "1.50",
            "sku": "SPIN-001",
            "is_visible": True,
            "is_available": True,
            "attributes": {"weight": "250g", "organic": True},
        }
        response = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Fresh Spinach Bunch")
        self.assertEqual(response.data["price"], "1.50")
        self.assertEqual(response.data["sku"], "SPIN-001")
        self.assertEqual(response.data["shop"], self.shop_a.id)
        self.assertIsNone(response.data["master_product"])
        self.assertTrue(response.data["is_visible"])
        self.assertTrue(response.data["is_available"])

        # Directly created product exists in DB and is active
        prod = ShopProduct.objects.get(id=response.data["id"])
        self.assertEqual(prod.shop, self.shop_a)
        self.assertIsNone(prod.master_product)

    def test_product_creation_selected_from_master_catalog(self):
        """
        Merchant selects a Master Product. Metadata is copied without automatic
        synchronization or binding. Merchant can customize price, SKU, etc.
        """
        self._auth_merchant(self.user_a)
        payload = {
            "master_product": self.master_product.id,
            "price": "8.50",
            "sku": "GHEE-A-01",
        }
        response = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], self.master_product.name)
        self.assertEqual(response.data["description"], self.master_product.description)
        self.assertEqual(response.data["brand"], self.master_product.brand)
        self.assertEqual(response.data["master_product"], self.master_product.id)
        self.assertEqual(response.data["price"], "8.50")
        self.assertEqual(response.data["sku"], "GHEE-A-01")
        self.assertEqual(response.data["shop"], self.shop_a.id)

    def test_product_creation_selected_from_master_catalog_with_custom_overrides(self):
        """
        Merchant can override name, description, and brand when selecting from Master Catalog.
        """
        self._auth_merchant(self.user_a)
        payload = {
            "master_product": self.master_product.id,
            "name": "Shop A Premium Desi Ghee",
            "description": "Store-curated ghee description",
            "brand": "Custom Cow Brand",
            "price": "9.99",
        }
        response = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Shop A Premium Desi Ghee")
        self.assertEqual(response.data["description"], "Store-curated ghee description")
        self.assertEqual(response.data["brand"], "Custom Cow Brand")
        self.assertEqual(response.data["master_product"], self.master_product.id)

    def test_multi_tenant_isolation_list_and_retrieve(self):
        """
        Merchant A cannot view, retrieve, or infer products belonging to Merchant B.
        """
        prod_a = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Product A",
            price=Decimal("10.00"),
        )
        prod_b = ShopProduct.objects.create(
            shop=self.shop_b,
            name="Product B",
            price=Decimal("20.00"),
        )

        # Merchant A list
        self._auth_merchant(self.user_a)
        list_res = self.client.get(self.base_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in list_res.data]
        self.assertIn(prod_a.id, ids)
        self.assertNotIn(prod_b.id, ids)

        # Merchant A retrieves own product
        get_a = self.client.get(f"{self.base_url}{prod_a.id}/")
        self.assertEqual(get_a.status_code, status.HTTP_200_OK)

        # Merchant A attempts to retrieve Merchant B's product -> 404
        get_b = self.client.get(f"{self.base_url}{prod_b.id}/")
        self.assertEqual(get_b.status_code, status.HTTP_404_NOT_FOUND)

    def test_multi_tenant_isolation_update_and_delete(self):
        """
        Merchant A cannot update or delete Merchant B's product.
        """
        prod_b = ShopProduct.objects.create(
            shop=self.shop_b,
            name="Secret Product B",
            price=Decimal("50.00"),
        )

        self._auth_merchant(self.user_a)

        # Merchant A attempts to PATCH Product B -> 404
        patch_res = self.client.patch(
            f"{self.base_url}{prod_b.id}/",
            {"name": "Hacked Name"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_404_NOT_FOUND)
        prod_b.refresh_from_db()
        self.assertEqual(prod_b.name, "Secret Product B")

        # Merchant A attempts to DELETE Product B -> 404
        delete_res = self.client.delete(f"{self.base_url}{prod_b.id}/")
        self.assertEqual(delete_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(ShopProduct.objects.filter(id=prod_b.id).exists())

    def test_client_provided_shop_id_is_ignored(self):
        """
        Server ignores submitted shop_id and binds strictly to authenticated Merchant's Shop.
        """
        self._auth_merchant(self.user_a)
        payload = {
            "name": "Tampered Shop Product",
            "price": "5.00",
            "shop": self.shop_b.id,
            "shop_id": self.shop_b.id,
        }
        response = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["shop"], self.shop_a.id)

        prod = ShopProduct.objects.get(id=response.data["id"])
        self.assertEqual(prod.shop, self.shop_a)

    def test_cross_tenant_brand_and_category_injection_rejected(self):
        """
        Merchant cannot associate brands or categories belonging to another Shop.
        """
        self._auth_merchant(self.user_a)

        # Attempt to inject brand belonging to Shop B
        res_brand = self.client.post(
            self.base_url,
            {"name": "Apples", "brand_ref": self.brand_b.id},
            format="json",
        )
        self.assertEqual(res_brand.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("brand_ref", res_brand.data)

        # Attempt to inject category belonging to Shop B
        res_cat = self.client.post(
            self.base_url,
            {"name": "Apples", "categories": [self.category_b.id]},
            format="json",
        )
        self.assertEqual(res_cat.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("categories", res_cat.data)

    def test_merchant_update_and_delete_own_product(self):
        """
        Merchant can successfully update and delete their own product.
        """
        self._auth_merchant(self.user_a)
        prod = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Original Tomatoes",
            price=Decimal("2.00"),
            sku="TOM-01",
        )

        # Update
        patch_res = self.client.patch(
            f"{self.base_url}{prod.id}/",
            {"price": "2.50", "sku": "TOM-02", "is_available": False},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        prod.refresh_from_db()
        self.assertEqual(prod.price, Decimal("2.50"))
        self.assertEqual(prod.sku, "TOM-02")
        self.assertFalse(prod.is_available)

        # Delete
        del_res = self.client.delete(f"{self.base_url}{prod.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ShopProduct.objects.filter(id=prod.id).exists())

    def test_authorization_checks(self):
        """
        Validate unauthenticated (401), non-merchant (403), no-shop (404),
        and inactive shop (403).
        """
        # 1. Unauthenticated -> 401
        self.assertEqual(self.client.get(self.base_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.base_url, {"name": "X"}).status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Super Admin -> 403 (IsActiveMerchant requires merchant role)
        self._auth_super_admin()
        self.assertEqual(self.client.get(self.base_url).status_code, status.HTTP_403_FORBIDDEN)

        # 3. Merchant without Shop -> 404 SHOP_NOT_FOUND
        user_no_shop = User.objects.create_user(
            username="merchant_no_shop",
            mobile_number="+919876543340",
            password="password123",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=user_no_shop, status=Merchant.Status.ACTIVE, must_change_password=False)
        self._auth_merchant(user_no_shop)

        no_shop_res = self.client.get(self.base_url)
        self.assertEqual(no_shop_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(no_shop_res.data.get("code"), "SHOP_NOT_FOUND")

        # 4. Merchant with Inactive/Deactivated Shop -> 403 SHOP_INACTIVE
        self.shop_a.status = Shop.Status.DEACTIVATED
        self.shop_a.save()
        self._auth_merchant(self.user_a)

        inactive_res = self.client.get(self.base_url)
        self.assertEqual(inactive_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(inactive_res.data.get("code"), "SHOP_INACTIVE")

    def test_shops_me_products_route_alias(self):
        """
        Verify that /api/v1/shops/me/products/ also resolves and performs CRUD identically.
        """
        self._auth_merchant(self.user_a)
        url = "/api/v1/shops/me/products/"

        response = self.client.post(
            url,
            {"name": "Fresh Cucumbers", "price": "1.20"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Fresh Cucumbers")
        prod_id = response.data["id"]

        get_res = self.client.get(f"{url}{prod_id}/")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data["name"], "Fresh Cucumbers")

    def test_put_full_update_own_product(self):
        """
        Merchant can perform a full update (PUT) on their own product.
        """
        self._auth_merchant(self.user_a)
        prod = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Initial Name",
            price=Decimal("10.00"),
            sku="SKU-INIT",
        )
        put_payload = {
            "name": "Updated Full Name",
            "description": "Full updated description",
            "price": "12.50",
            "sku": "SKU-UPD",
            "is_visible": False,
            "is_available": False,
        }
        res = self.client.put(f"{self.base_url}{prod.id}/", put_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Updated Full Name")
        self.assertEqual(res.data["price"], "12.50")
        self.assertEqual(res.data["sku"], "SKU-UPD")
        self.assertFalse(res.data["is_visible"])
        self.assertFalse(res.data["is_available"])

    def test_filter_products_by_visibility_availability_category_and_search(self):
        """
        Merchant product listing supports filtering by visibility, manual availability,
        category, and search term (name, sku, brand).
        """
        self._auth_merchant(self.user_a)
        p1 = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Alpha Apple",
            sku="FRUIT-01",
            brand="NatureBrand",
            is_visible=True,
            is_available=True,
        )
        p1.categories.add(self.category_a)

        p2 = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Beta Banana",
            sku="FRUIT-02",
            brand="NatureBrand",
            is_visible=False,
            is_available=True,
        )

        p3 = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Gamma Garlic",
            sku="VEG-01",
            brand="SpiceCo",
            is_visible=True,
            is_available=False,
        )

        # Filter by visibility
        res_vis = self.client.get(f"{self.base_url}?is_visible=true")
        self.assertEqual(res_vis.status_code, status.HTTP_200_OK)
        ids_vis = [item["id"] for item in res_vis.data]
        self.assertIn(p1.id, ids_vis)
        self.assertIn(p3.id, ids_vis)
        self.assertNotIn(p2.id, ids_vis)

        # Filter by availability
        res_avail = self.client.get(f"{self.base_url}?is_available=false")
        self.assertEqual(res_avail.status_code, status.HTTP_200_OK)
        ids_avail = [item["id"] for item in res_avail.data]
        self.assertIn(p3.id, ids_avail)
        self.assertNotIn(p1.id, ids_avail)

        # Filter by category
        res_cat = self.client.get(f"{self.base_url}?category={self.category_a.id}")
        self.assertEqual(res_cat.status_code, status.HTTP_200_OK)
        ids_cat = [item["id"] for item in res_cat.data]
        self.assertIn(p1.id, ids_cat)
        self.assertNotIn(p2.id, ids_cat)
        self.assertNotIn(p3.id, ids_cat)

        # Search by term
        res_search = self.client.get(f"{self.base_url}?search=FRUIT-02")
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        ids_search = [item["id"] for item in res_search.data]
        self.assertIn(p2.id, ids_search)
        self.assertNotIn(p1.id, ids_search)

    def test_direct_creation_validation_errors(self):
        """
        Direct creation rejects blank names, negative prices, and invalid attributes.
        """
        self._auth_merchant(self.user_a)

        # 1. Blank name
        res_blank = self.client.post(self.base_url, {"name": "   ", "price": "1.00"}, format="json")
        self.assertEqual(res_blank.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", res_blank.data)

        # 2. Missing name without master_product
        res_noname = self.client.post(self.base_url, {"price": "1.00"}, format="json")
        self.assertEqual(res_noname.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", res_noname.data)

        # 3. Negative price
        res_neg = self.client.post(self.base_url, {"name": "Item", "price": "-5.00"}, format="json")
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", res_neg.data)

        # 4. Non-dict attributes
        res_attr = self.client.post(self.base_url, {"name": "Item", "attributes": "invalid"}, format="json")
        self.assertEqual(res_attr.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("attributes", res_attr.data)

        # 5. Non-existent master product
        res_mp = self.client.post(self.base_url, {"master_product": 999999}, format="json")
        self.assertEqual(res_mp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("master_product", res_mp.data)

    def test_cross_tenant_update_brand_and_category_rejected(self):
        """
        Merchant cannot update existing product with brands or categories belonging to another shop.
        """
        self._auth_merchant(self.user_a)
        prod = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Valid Product",
            price=Decimal("3.00"),
        )

        # Cross-tenant brand on update
        res_b = self.client.patch(
            f"{self.base_url}{prod.id}/",
            {"brand_ref": self.brand_b.id},
            format="json",
        )
        self.assertEqual(res_b.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("brand_ref", res_b.data)

        # Cross-tenant category on update
        res_c = self.client.patch(
            f"{self.base_url}{prod.id}/",
            {"categories": [self.category_b.id]},
            format="json",
        )
        self.assertEqual(res_c.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("categories", res_c.data)

    def test_catalog_shop_products_alias_route(self):
        """
        Verify that /api/v1/catalog/shop-products/ acts as a direct alias for the merchant product API.
        """
        self._auth_merchant(self.user_a)
        alias_url = "/api/v1/catalog/shop-products/"

        res = self.client.post(alias_url, {"name": "Alias Test Item", "price": "4.20"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Alias Test Item")
        prod_id = res.data["id"]

        get_res = self.client.get(f"{alias_url}{prod_id}/")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data["name"], "Alias Test Item")


class MerchantShopCategoryAPITests(TestCase):
    """
    Unit and integration tests for Merchant CRUD APIs on Categories and subcategories (CAT-012).

    Validates:
    - Merchant CRUD control over Shop-owned categories and subcategories.
    - Preserves Shop ownership: server-side binding to authenticated merchant's shop; client shop_id ignored.
    - Category deletion leaves assigned products intact and uncategorized per domain rules.
    - Subcategory parent-child relationships, counts, and tenant-scoped validation.
    - Strict multi-tenant isolation: Merchant A cannot list, retrieve, update, or delete Merchant B's categories.
    - Cross-tenant parent category injection rejected with 400.
    - Self-parenting and cyclic hierarchies rejected with 400.
    - Filtering by parent (root/subcategories), active status, and search query.
    - Authorization enforcement on all operations (unauthenticated 401, non-merchant 403, no-shop 404, inactive-shop 403).
    - URL aliases: /api/v1/catalog/categories/, /api/v1/catalog/shop-categories/, and /api/v1/shops/me/categories/.
    """

    def setUp(self):
        self.client = APIClient()

        # Merchant A and Shop A
        self.user_a = User.objects.create_user(
            username="merchant_cat_a",
            mobile_number="+919876543410",
            password="password123",
            role=User.Role.MERCHANT,
        )
        self.merchant_a = Merchant.objects.create(
            user=self.user_a,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop_a = Shop.objects.create(
            merchant=self.merchant_a,
            name="Shop A Groceries",
        )

        # Merchant B and Shop B
        self.user_b = User.objects.create_user(
            username="merchant_cat_b",
            mobile_number="+919876543420",
            password="password123",
            role=User.Role.MERCHANT,
        )
        self.merchant_b = Merchant.objects.create(
            user=self.user_b,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop_b = Shop.objects.create(
            merchant=self.merchant_b,
            name="Shop B Supermart",
        )

        # Super Admin
        self.super_admin = User.objects.create_user(
            username="super_admin_cat12",
            mobile_number="+919876543430",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )

        self.base_url = "/api/v1/catalog/categories/"

    def _auth_merchant(self, user):
        login_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": user.mobile_number, "password": "password123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _auth_super_admin(self):
        login_res = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": self.super_admin.mobile_number, "password": "adminpassword123"},
            format="json",
        )
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_merchant_create_root_category(self):
        """
        Merchant can create a top-level category. Server preserves Shop ownership
        and ignores client-provided shop IDs.
        """
        self._auth_merchant(self.user_a)
        payload = {
            "name": "Fresh Dairy",
            "description": "Milk, butter, and cheese",
            "slug": "fresh-dairy",
            "shop": self.shop_b.id,
            "shop_id": self.shop_b.id,
        }
        res = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Fresh Dairy")
        self.assertEqual(res.data["slug"], "fresh-dairy")
        self.assertEqual(res.data["description"], "Milk, butter, and cheese")
        self.assertEqual(res.data["shop"], self.shop_a.id)
        self.assertFalse(res.data["is_subcategory"])
        self.assertIsNone(res.data["parent"])

        # DB verification
        cat = ShopCategory.objects.get(id=res.data["id"])
        self.assertEqual(cat.shop, self.shop_a)
        self.assertIsNone(cat.parent)

    def test_merchant_create_subcategory(self):
        """
        Merchant can create subcategories by setting a valid parent category.
        """
        parent = ShopCategory.objects.create(
            shop=self.shop_a,
            name="Beverages",
            slug="beverages",
        )
        self._auth_merchant(self.user_a)
        payload = {
            "name": "Fruit Juices",
            "parent": parent.id,
            "description": "Cold-pressed juices",
        }
        res = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Fruit Juices")
        self.assertEqual(res.data["parent"], parent.id)
        self.assertEqual(res.data["parent_name"], "Beverages")
        self.assertTrue(res.data["is_subcategory"])

        subcat = ShopCategory.objects.get(id=res.data["id"])
        self.assertEqual(subcat.parent, parent)
        self.assertEqual(subcat.shop, self.shop_a)

    def test_merchant_crud_full_lifecycle(self):
        """
        Merchant can list, retrieve, update (PUT/PATCH), and delete categories.
        """
        self._auth_merchant(self.user_a)
        cat = ShopCategory.objects.create(
            shop=self.shop_a,
            name="Bakery",
            slug="bakery",
            description="Breads and buns",
        )

        # Retrieve
        get_res = self.client.get(f"{self.base_url}{cat.id}/")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data["name"], "Bakery")
        self.assertEqual(get_res.data["subcategories_count"], 0)
        self.assertEqual(get_res.data["products_count"], 0)

        # Update via PATCH
        patch_res = self.client.patch(
            f"{self.base_url}{cat.id}/",
            {"description": "Artisan breads and fresh buns", "is_active": False},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertEqual(cat.description, "Artisan breads and fresh buns")
        self.assertFalse(cat.is_active)

        # Update via PUT
        put_res = self.client.put(
            f"{self.base_url}{cat.id}/",
            {"name": "Artisan Bakery", "slug": "artisan-bakery", "is_active": True},
            format="json",
        )
        self.assertEqual(put_res.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Artisan Bakery")
        self.assertTrue(cat.is_active)

        # Delete
        del_res = self.client.delete(f"{self.base_url}{cat.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ShopCategory.objects.filter(id=cat.id).exists())

    def test_category_deletion_preserves_assigned_products(self):
        """
        Deleting a category MUST allow assigned products to remain intact,
        becoming uncategorized per the Catalog domain specification.
        """
        self._auth_merchant(self.user_a)
        cat = ShopCategory.objects.create(
            shop=self.shop_a,
            name="Snacks",
            slug="snacks",
        )
        prod = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Potato Chips 50g",
            price=Decimal("1.50"),
        )
        prod.categories.add(cat)

        self.assertFalse(prod.is_uncategorized)
        self.assertEqual(prod.categories.count(), 1)

        # Delete category via API
        del_res = self.client.delete(f"{self.base_url}{cat.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)

        # Category is gone
        self.assertFalse(ShopCategory.objects.filter(id=cat.id).exists())

        # Product remains intact and is now uncategorized
        prod.refresh_from_db()
        self.assertTrue(ShopProduct.objects.filter(id=prod.id).exists())
        self.assertEqual(prod.categories.count(), 0)
        self.assertTrue(prod.is_uncategorized)

    def test_multi_category_partial_deletion_preserves_remaining_categories(self):
        """
        When a product belongs to multiple categories and one is deleted via API,
        the product remains intact and retains its remaining category relationships.
        """
        self._auth_merchant(self.user_a)
        cat_a = ShopCategory.objects.create(shop=self.shop_a, name="Organic Food", slug="organic-food")
        cat_b = ShopCategory.objects.create(shop=self.shop_a, name="Pantry Staples", slug="pantry-staples")

        prod = ShopProduct.objects.create(
            shop=self.shop_a,
            name="Organic Rolled Oats 1kg",
            price=Decimal("4.00"),
        )
        prod.categories.add(cat_a, cat_b)

        # Delete Category A via API
        del_res = self.client.delete(f"{self.base_url}{cat_a.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)

        # Product remains intact and still linked to Category B
        prod.refresh_from_db()
        self.assertTrue(ShopProduct.objects.filter(id=prod.id).exists())
        self.assertEqual(prod.categories.count(), 1)
        self.assertIn(cat_b, prod.categories.all())
        self.assertFalse(prod.is_uncategorized)

    def test_multi_tenant_isolation_list_and_retrieve(self):
        """
        Merchant A cannot view or retrieve categories belonging to Merchant B.
        """
        cat_a = ShopCategory.objects.create(shop=self.shop_a, name="Shop A Category", slug="shop-a-cat")
        cat_b = ShopCategory.objects.create(shop=self.shop_b, name="Shop B Category", slug="shop-b-cat")

        self._auth_merchant(self.user_a)

        # Listing only includes Shop A categories
        list_res = self.client.get(self.base_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in list_res.data]
        self.assertIn(cat_a.id, ids)
        self.assertNotIn(cat_b.id, ids)

        # Retrieve own category
        get_a = self.client.get(f"{self.base_url}{cat_a.id}/")
        self.assertEqual(get_a.status_code, status.HTTP_200_OK)

        # Retrieve Merchant B's category -> 404
        get_b = self.client.get(f"{self.base_url}{cat_b.id}/")
        self.assertEqual(get_b.status_code, status.HTTP_404_NOT_FOUND)

    def test_multi_tenant_isolation_update_and_delete(self):
        """
        Merchant A cannot update or delete Merchant B's categories.
        """
        cat_b = ShopCategory.objects.create(shop=self.shop_b, name="Secret Category B", slug="secret-b")
        self._auth_merchant(self.user_a)

        # Update attempt -> 404
        patch_res = self.client.patch(f"{self.base_url}{cat_b.id}/", {"name": "Hacked Name"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_404_NOT_FOUND)
        cat_b.refresh_from_db()
        self.assertEqual(cat_b.name, "Secret Category B")

        # Delete attempt -> 404
        del_res = self.client.delete(f"{self.base_url}{cat_b.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(ShopCategory.objects.filter(id=cat_b.id).exists())

    def test_cross_tenant_parent_category_rejected(self):
        """
        Merchant cannot assign a parent category belonging to another Shop.
        """
        cat_b = ShopCategory.objects.create(shop=self.shop_b, name="Parent from Shop B", slug="parent-b")
        self._auth_merchant(self.user_a)

        # Create subcategory pointing to Shop B category
        res = self.client.post(
            self.base_url,
            {"name": "Invalid Subcat", "parent": cat_b.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", res.data)

        # Update subcategory pointing to Shop B category
        cat_a = ShopCategory.objects.create(shop=self.shop_a, name="Own Category", slug="own-cat")
        patch_res = self.client.patch(
            f"{self.base_url}{cat_a.id}/",
            {"parent": cat_b.id},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", patch_res.data)

    def test_self_parenting_and_cyclic_hierarchy_rejected(self):
        """
        A category cannot be its own parent, nor can circular parenting be formed.
        """
        cat_a = ShopCategory.objects.create(shop=self.shop_a, name="Cat A", slug="cat-a")
        cat_b = ShopCategory.objects.create(shop=self.shop_a, parent=cat_a, name="Cat B", slug="cat-b")
        self._auth_merchant(self.user_a)

        # Self-parenting
        res_self = self.client.patch(f"{self.base_url}{cat_a.id}/", {"parent": cat_a.id}, format="json")
        self.assertEqual(res_self.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", res_self.data)

        # Cyclic parenting (setting A's parent to B, when B's parent is A)
        res_cycle = self.client.patch(f"{self.base_url}{cat_a.id}/", {"parent": cat_b.id}, format="json")
        self.assertEqual(res_cycle.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", res_cycle.data)

    def test_filter_categories_by_parent_active_and_search(self):
        """
        Categories list supports filtering by parent (root vs subcategories), active state, and search.
        """
        self._auth_merchant(self.user_a)
        root1 = ShopCategory.objects.create(shop=self.shop_a, name="Fruits", slug="fruits", is_active=True)
        root2 = ShopCategory.objects.create(shop=self.shop_a, name="Vegetables", slug="vegetables", is_active=False)
        sub1 = ShopCategory.objects.create(shop=self.shop_a, parent=root1, name="Apples", slug="apples", is_active=True)

        # Filter root categories only
        res_root = self.client.get(f"{self.base_url}?parent=root")
        self.assertEqual(res_root.status_code, status.HTTP_200_OK)
        ids_root = [c["id"] for c in res_root.data]
        self.assertIn(root1.id, ids_root)
        self.assertIn(root2.id, ids_root)
        self.assertNotIn(sub1.id, ids_root)

        # Filter subcategories by parent ID
        res_sub = self.client.get(f"{self.base_url}?parent={root1.id}")
        self.assertEqual(res_sub.status_code, status.HTTP_200_OK)
        ids_sub = [c["id"] for c in res_sub.data]
        self.assertIn(sub1.id, ids_sub)
        self.assertNotIn(root1.id, ids_sub)

        # Filter by active
        res_active = self.client.get(f"{self.base_url}?is_active=false")
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        ids_active = [c["id"] for c in res_active.data]
        self.assertIn(root2.id, ids_active)
        self.assertNotIn(root1.id, ids_active)

        # Search
        res_search = self.client.get(f"{self.base_url}?search=Apples")
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        ids_search = [c["id"] for c in res_search.data]
        self.assertIn(sub1.id, ids_search)
        self.assertNotIn(root1.id, ids_search)

    def test_authorization_checks(self):
        """
        Validate unauthenticated (401), non-merchant (403), merchant without shop (404),
        and merchant with inactive shop (403).
        """
        # 1. Unauthenticated -> 401
        self.assertEqual(self.client.get(self.base_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.base_url, {"name": "X"}).status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Super Admin -> 403
        self._auth_super_admin()
        self.assertEqual(self.client.get(self.base_url).status_code, status.HTTP_403_FORBIDDEN)

        # 3. Merchant without Shop -> 404
        user_no_shop = User.objects.create_user(
            username="merchant_cat_no_shop",
            mobile_number="+919876543440",
            password="password123",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=user_no_shop, status=Merchant.Status.ACTIVE, must_change_password=False)
        self._auth_merchant(user_no_shop)
        no_shop_res = self.client.get(self.base_url)
        self.assertEqual(no_shop_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(no_shop_res.data.get("code"), "SHOP_NOT_FOUND")

        # 4. Merchant with Inactive Shop -> 403
        self.shop_a.status = Shop.Status.DEACTIVATED
        self.shop_a.save()
        self._auth_merchant(self.user_a)
        inactive_res = self.client.get(self.base_url)
        self.assertEqual(inactive_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(inactive_res.data.get("code"), "SHOP_INACTIVE")

    def test_url_aliases(self):
        """
        Verify /api/v1/catalog/shop-categories/ and /api/v1/shops/me/categories/ route properly.
        """
        self._auth_merchant(self.user_a)

        # /api/v1/catalog/shop-categories/
        url1 = "/api/v1/catalog/shop-categories/"
        res1 = self.client.post(url1, {"name": "Alias Cat 1"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["name"], "Alias Cat 1")

        # /api/v1/shops/me/categories/
        url2 = "/api/v1/shops/me/categories/"
        res2 = self.client.post(url2, {"name": "Alias Cat 2"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["name"], "Alias Cat 2")
        cat2_id = res2.data["id"]

        get2 = self.client.get(f"{url2}{cat2_id}/")
        self.assertEqual(get2.status_code, status.HTTP_200_OK)
        self.assertEqual(get2.data["name"], "Alias Cat 2")





