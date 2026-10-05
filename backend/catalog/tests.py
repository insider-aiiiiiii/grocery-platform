import shutil
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings

from shops.models import Shop
from users.models import Merchant, User

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

