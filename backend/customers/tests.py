from django.contrib.auth.models import AbstractBaseUser, AbstractUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from cart.models import Cart
from shops.models import Shop
from users.models import Merchant, User

from .models import Customer, normalize_whatsapp_number
from .services import create_or_recognize_customer, recognize_customer


class CustomerModelTests(TestCase):
    """Unit and domain tests for CUS-001 Shop-specific Customer profile."""

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
            name="Alpha Groceries",
            address_line="100 First Street",
            area="North",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
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
            address_line="200 Second Street",
            area="South",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            contact_number=self.user2.mobile_number,
        )

    # 1. Customer creation with a Shop
    def test_customer_creation_with_shop_success(self):
        """A customer profile is created associated with a Shop and normalized number."""
        customer = Customer.objects.create(
            shop=self.shop1,
            name="Rahul Sharma",
            whatsapp_number="7896547658",
        )
        self.assertIsNotNone(customer.pk)
        self.assertEqual(customer.shop, self.shop1)
        self.assertEqual(customer.name, "Rahul Sharma")
        self.assertEqual(customer.whatsapp_number, "+917896547658")
        self.assertIsNotNone(customer.created_at)
        self.assertIsNotNone(customer.updated_at)
        self.assertIn("Customer +917896547658 - Rahul Sharma", str(customer))
        self.assertIn(f"Shop: {self.shop1.pk}", str(customer))

    def test_customer_creation_with_optional_name(self):
        """A customer profile can be created without a name (defaults to empty string)."""
        customer = Customer.objects.create(
            shop=self.shop1,
            whatsapp_number="+917896547658",
        )
        self.assertEqual(customer.name, "")
        self.assertEqual(customer.whatsapp_number, "+917896547658")
        self.assertEqual(str(customer), f"Customer +917896547658 (Shop: {self.shop1.pk})")

    def test_customer_missing_whatsapp_number_fails(self):
        """Attempting to create or validate a customer without a WhatsApp number fails."""
        customer = Customer(shop=self.shop1, name="No Number", whatsapp_number="")
        with self.assertRaises(ValidationError) as ctx:
            customer.full_clean()
        self.assertIn("whatsapp_number", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            customer.save()

    # 2. WhatsApp number validation and normalization
    def test_whatsapp_normalization_10_digit_indian_number(self):
        """10-digit Indian numbers starting with 6-9 are accepted and normalized to +91."""
        test_cases = [
            ("7896547658", "+917896547658"),
            ("9876543210", "+919876543210"),
            ("8123456789", "+918123456789"),
            ("6987654321", "+916987654321"),
        ]
        for raw, expected in test_cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_whatsapp_number(raw), expected)

    def test_whatsapp_normalization_plus_91_prefix(self):
        """Numbers already having the +91 country prefix are accepted and normalized."""
        test_cases = [
            ("+917685432278", "+917685432278"),
            ("+919876543210", "+919876543210"),
            ("+91 7685432278", "+917685432278"),
            ("+91-7685432278", "+917685432278"),
            (" 7896547658 ", "+917896547658"),
        ]
        for raw, expected in test_cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_whatsapp_number(raw), expected)

    def test_whatsapp_invalid_lengths_rejected(self):
        """Invalid number lengths (fewer or more than 10 digits) are rejected."""
        invalid_lengths = [
            "789654765",       # 9 digits
            "78965476589",     # 11 digits without prefix
            "+91789654765",    # 9 digits with prefix
            "+9178965476589",  # 11 digits with prefix
            "7",               # single digit
            "",                # empty
        ]
        for val in invalid_lengths:
            with self.subTest(val=val):
                with self.assertRaises(ValidationError):
                    normalize_whatsapp_number(val)

    def test_whatsapp_invalid_characters_rejected(self):
        """Numbers containing non-numeric characters are rejected."""
        invalid_chars = [
            "78965abcde",
            "789654765@",
            "+9178965abcde",
            "abcdefghij",
            "78965#47658",
        ]
        for val in invalid_chars:
            with self.subTest(val=val):
                with self.assertRaises(ValidationError):
                    normalize_whatsapp_number(val)

    def test_whatsapp_invalid_starting_digits_rejected(self):
        """Indian numbers starting with digits outside 6-9 are rejected."""
        invalid_starters = [
            "1234567890",
            "2345678901",
            "3456789012",
            "4567890123",
            "5678901234",
            "0987654321",
            "+911234567890",
            "+915555555555",
        ]
        for val in invalid_starters:
            with self.subTest(val=val):
                with self.assertRaises(ValidationError):
                    normalize_whatsapp_number(val)

    def test_arbitrary_international_numbers_rejected(self):
        """International numbers outside the Indian +91 dial plan are rejected."""
        international_numbers = [
            "+12025550123",    # US
            "+447911123456",   # UK
            "+971501234567",   # UAE
            "+61412345678",    # Australia
            "+819012345678",   # Japan
        ]
        for val in international_numbers:
            with self.subTest(val=val):
                with self.assertRaises(ValidationError):
                    normalize_whatsapp_number(val)

    # 3. Shop-scoped uniqueness
    def test_same_normalized_whatsapp_rejected_twice_in_same_shop_clean(self):
        """A customer with the same normalized WhatsApp number in the same Shop is rejected in clean()."""
        Customer.objects.create(
            shop=self.shop1,
            name="First Customer",
            whatsapp_number="7896547658",
        )

        duplicate = Customer(
            shop=self.shop1,
            name="Duplicate Customer",
            whatsapp_number="+917896547658",
        )
        with self.assertRaises(ValidationError) as ctx:
            duplicate.full_clean()
        self.assertIn("whatsapp_number", ctx.exception.message_dict)

    def test_same_normalized_whatsapp_rejected_twice_in_same_shop_db_constraint(self):
        """Database UniqueConstraint prevents duplicate normalized WhatsApp numbers in the same Shop."""
        Customer.objects.create(
            shop=self.shop1,
            name="First Customer",
            whatsapp_number="7896547658",
        )

        with self.assertRaises(IntegrityError):
            # Bypass clean() by using save() with pre-normalized number
            Customer(
                shop=self.shop1,
                name="Duplicate Direct Save",
                whatsapp_number="+917896547658",
            ).save()

    def test_updating_customer_does_not_trigger_self_uniqueness_error(self):
        """Saving updates to an existing customer does not trigger uniqueness conflict with itself."""
        customer = Customer.objects.create(
            shop=self.shop1,
            name="Original Name",
            whatsapp_number="7896547658",
        )
        customer.name = "Updated Name"
        customer.full_clean()
        customer.save()
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Updated Name")

    def test_same_whatsapp_number_allowed_in_two_different_shops(self):
        """The same WhatsApp number can be registered across multiple distinct Shops."""
        c1 = Customer.objects.create(
            shop=self.shop1,
            name="Customer in Shop 1",
            whatsapp_number="7896547658",
        )
        c2 = Customer.objects.create(
            shop=self.shop2,
            name="Customer in Shop 2",
            whatsapp_number="+917896547658",
        )

        self.assertNotEqual(c1.pk, c2.pk)
        self.assertEqual(c1.whatsapp_number, "+917896547658")
        self.assertEqual(c2.whatsapp_number, "+917896547658")
        self.assertEqual(c1.shop, self.shop1)
        self.assertEqual(c2.shop, self.shop2)

    # 4. Separation from authenticated User
    def test_customer_separate_from_authenticated_user(self):
        """Customer profile is independent of User accounts and has no credentials."""
        customer = Customer.objects.create(
            shop=self.shop1,
            name="Guest Shopper",
            whatsapp_number="7896547658",
        )

        # Assert no user relationship, password, or auth fields
        self.assertFalse(hasattr(customer, "password"))
        self.assertFalse(hasattr(customer, "username"))
        self.assertFalse(hasattr(customer, "user"))
        self.assertFalse(hasattr(customer, "user_id"))
        self.assertFalse(hasattr(customer, "is_authenticated"))
        self.assertFalse(hasattr(customer, "is_staff"))
        self.assertFalse(hasattr(customer, "is_superuser"))

        # Assert not an instance of User classes
        self.assertNotIsInstance(customer, AbstractUser)
        self.assertNotIsInstance(customer, AbstractBaseUser)

    # 5. Profile creation before Order
    def test_customer_exists_without_order(self):
        """A Customer profile exists and is persisted without any Order existing."""
        customer = Customer.objects.create(
            shop=self.shop1,
            name="Cart Visitor",
            whatsapp_number="7896547658",
        )
        self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())
        # Confirms existence without any orders app dependency

    # 6. Lifecycle & cascade behavior
    def test_shop_deletion_cascades_customers(self):
        """Deleting a Shop cascades to delete all associated Customer records."""
        c1 = Customer.objects.create(
            shop=self.shop1,
            name="Cust 1",
            whatsapp_number="7896547658",
        )
        c2 = Customer.objects.create(
            shop=self.shop1,
            name="Cust 2",
            whatsapp_number="9876543210",
        )

        self.assertEqual(Customer.objects.filter(shop=self.shop1).count(), 2)
        self.shop1.delete()
        self.assertFalse(Customer.objects.filter(pk=c1.pk).exists())
        self.assertFalse(Customer.objects.filter(pk=c2.pk).exists())

    # 7. CUS-002 One-Shop Profile Scope & Migration Constraints
    def test_cannot_reassign_customer_to_different_shop(self):
        """A Customer profile is strictly scoped to one Shop and cannot be reassigned to another Shop."""
        customer = Customer.objects.create(
            shop=self.shop1,
            name="Alice",
            whatsapp_number="9876543210",
        )

        customer.shop = self.shop2
        with self.assertRaises(ValidationError) as ctx:
            customer.full_clean()
        self.assertIn("shop", ctx.exception.message_dict)
        self.assertIn("Cannot reassign a Customer profile to a different Shop.", ctx.exception.message_dict["shop"])

        with self.assertRaises(ValidationError):
            customer.save()

    def test_database_check_constraint_rejects_empty_whatsapp_number(self):
        """Database CheckConstraint prevents saving an empty WhatsApp number via bulk_create."""
        with self.assertRaises(IntegrityError):
            Customer.objects.bulk_create([
                Customer(shop=self.shop1, name="Invalid Cust", whatsapp_number="")
            ])

    def test_customer_model_and_migrations_exclude_global_contact_identity(self):
        """Customer profile schema excludes global identity FKs, global claims, or cross-Shop links."""
        customer_fields = [f.name for f in Customer._meta.get_fields()]

        # Assert only Shop-scoped fields exist
        expected_fields = {"id", "shop", "name", "whatsapp_number", "created_at", "updated_at"}
        # Filter for concrete model fields or direct relations
        concrete_field_names = {f.name for f in Customer._meta.fields}
        self.assertEqual(concrete_field_names, expected_fields)

        # Assert no global identity or claim fields
        for forbidden in ["identity", "global_identity", "contact_claim", "user", "account", "login"]:
            self.assertNotIn(forbidden, customer_fields)

    def test_cross_shop_identity_link_models_are_gated_and_absent(self):
        """Any cross-Shop identity link or global claim migration is gated on approval and currently absent."""
        from django.apps import apps
        customer_models = list(apps.get_app_config("customers").get_models())
        model_names = [m.__name__ for m in customer_models]

        self.assertEqual(model_names, ["Customer"])
        self.assertNotIn("CustomerIdentity", model_names)
        self.assertNotIn("ContactIdentityClaim", model_names)
        self.assertNotIn("ShopCustomerProfile", model_names)

    def test_one_shop_profile_scope_isolation_under_queries(self):
        """Profiles with the same phone in different shops remain strictly isolated in queries."""
        c1 = Customer.objects.create(shop=self.shop1, name="Shop 1 Cust", whatsapp_number="9876543210")
        c2 = Customer.objects.create(shop=self.shop2, name="Shop 2 Cust", whatsapp_number="9876543210")

        # Shop 1 query cannot see Shop 2 customer
        s1_customers = list(Customer.objects.filter(shop=self.shop1))
        self.assertEqual(len(s1_customers), 1)
        self.assertEqual(s1_customers[0].pk, c1.pk)
        self.assertEqual(s1_customers[0].name, "Shop 1 Cust")

        # Shop 2 query cannot see Shop 1 customer
        s2_customers = list(Customer.objects.filter(shop=self.shop2))
        self.assertEqual(len(s2_customers), 1)
        self.assertEqual(s2_customers[0].pk, c2.pk)
        self.assertEqual(s2_customers[0].name, "Shop 2 Cust")

    # 8. CUS-003 Customer Profile Creation & Recognition
    def test_create_customer_when_whatsapp_first_provided(self):
        """A Shop-specific Customer profile is created when WhatsApp is first provided for that Shop."""
        customer, created = create_or_recognize_customer(
            shop=self.shop1,
            whatsapp_number="9876543210",
            name="Rohan Sharma",
        )
        self.assertTrue(created)
        self.assertEqual(customer.shop, self.shop1)
        self.assertEqual(customer.whatsapp_number, "+919876543210")
        self.assertEqual(customer.name, "Rohan Sharma")

    def test_recognize_existing_customer_in_same_shop(self):
        """A customer is recognized within the same Shop when WhatsApp is provided again."""
        c1, created1 = create_or_recognize_customer(
            shop=self.shop1,
            whatsapp_number="9876543210",
            name="Original Name",
        )
        self.assertTrue(created1)

        c2, created2 = create_or_recognize_customer(
            shop=self.shop1,
            whatsapp_number="+919876543210",
        )
        self.assertFalse(created2)
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(c2.name, "Original Name")

        # Test recognize_customer standalone function
        recognized = recognize_customer(self.shop1, "9876543210")
        self.assertIsNotNone(recognized)
        self.assertEqual(recognized.pk, c1.pk)

        # Test Customer.objects.recognize model manager method
        manager_recognized = Customer.objects.recognize(self.shop1, "9876543210")
        self.assertIsNotNone(manager_recognized)
        self.assertEqual(manager_recognized.pk, c1.pk)

    def test_recognize_customer_updates_name_if_previously_empty(self):
        """If a customer profile was created without a name, providing a name on recognition updates it."""
        c1, _ = create_or_recognize_customer(
            shop=self.shop1,
            whatsapp_number="9876543210",
            name="",
        )
        self.assertEqual(c1.name, "")

        c2, created = create_or_recognize_customer(
            shop=self.shop1,
            whatsapp_number="9876543210",
            name="New Captured Name",
        )
        self.assertFalse(created)
        self.assertEqual(c2.pk, c1.pk)
        self.assertEqual(c2.name, "New Captured Name")

    def test_customer_creation_before_successful_order_with_cart(self):
        """Customer profile can be created/recognized and associated with an active Cart before an Order."""
        cart = Cart.objects.create(shop=self.shop1)
        self.assertIsNone(cart.customer)

        customer, created = create_or_recognize_customer(
            shop=self.shop1,
            whatsapp_number="9876543210",
            name="Cart Shopper",
            cart=cart,
        )
        self.assertTrue(created)
        cart.refresh_from_db()
        self.assertEqual(cart.customer, customer)
        self.assertEqual(cart.customer.shop, self.shop1)

    def test_cart_cross_shop_mismatch_rejected(self):
        """Associating a customer with a Cart belonging to a different Shop is rejected."""
        cart_shop2 = Cart.objects.create(shop=self.shop2)

        with self.assertRaises(ValidationError) as ctx:
            create_or_recognize_customer(
                shop=self.shop1,
                whatsapp_number="9876543210",
                cart=cart_shop2,
            )
        self.assertIn("cart", ctx.exception.message_dict)

    def test_matching_contact_at_another_shop_does_not_share_profile_data(self):
        """
        A matching contact at another Shop creates an independent profile and does NOT share
        profile data or history.
        """
        # Register in Shop 1 with Shop 1 specific name
        c_shop1, created1 = create_or_recognize_customer(
            shop=self.shop1,
            whatsapp_number="9876543210",
            name="Alice at Alpha Groceries",
        )
        self.assertTrue(created1)

        # Register in Shop 2 with the same phone but Shop 2 specific name
        c_shop2, created2 = create_or_recognize_customer(
            shop=self.shop2,
            whatsapp_number="9876543210",
            name="Bob at Beta Mart",
        )
        self.assertTrue(created2)

        # Must be distinct customer profiles
        self.assertNotEqual(c_shop1.pk, c_shop2.pk)
        self.assertEqual(c_shop1.shop, self.shop1)
        self.assertEqual(c_shop2.shop, self.shop2)

        # Profile data is NOT shared
        self.assertEqual(c_shop1.name, "Alice at Alpha Groceries")
        self.assertEqual(c_shop2.name, "Bob at Beta Mart")

        # Recognition in Shop 1 returns ONLY Shop 1 profile
        self.assertEqual(recognize_customer(self.shop1, "9876543210").pk, c_shop1.pk)
        # Recognition in Shop 2 returns ONLY Shop 2 profile
        self.assertEqual(recognize_customer(self.shop2, "9876543210").pk, c_shop2.pk)

    def test_global_identity_boundary_rejects_authenticated_user_number(self):
        """Customer profile creation rejects WhatsApp numbers claimed by authenticated Users."""
        # self.user1 is a Merchant with mobile_number="+919876543211"
        with self.assertRaises(ValidationError) as ctx:
            create_or_recognize_customer(
                shop=self.shop1,
                whatsapp_number=self.user1.mobile_number,
                name="Imposter",
            )
        self.assertIn("whatsapp_number", ctx.exception.message_dict)
        self.assertTrue(any("already registered as an authenticated user" in msg for msg in ctx.exception.message_dict["whatsapp_number"]))

        # Also rejected on direct Customer.save() and clean()
        direct_cust = Customer(
            shop=self.shop1,
            whatsapp_number=self.user1.mobile_number,
            name="Direct Imposter",
        )
        with self.assertRaises(ValidationError):
            direct_cust.full_clean()
        with self.assertRaises(ValidationError):
            direct_cust.save()


class PublicCustomerAPITests(TestCase):
    """API tests for CUS-004 documented public Customer/profile operations."""

    def setUp(self):
        self.client = APIClient()
        self.merchant_user = User.objects.create_user(
            username="merchant_pub",
            email="merchant_pub@example.com",
            mobile_number="+919876543200",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Green Valley Organics",
            address_line="500 High St",
            area="Kothrud",
            city="Pune",
            state="Maharashtra",
            pincode="411038",
            contact_number=self.merchant_user.mobile_number,
        )

        self.merchant_user2 = User.objects.create_user(
            username="merchant_pub2",
            email="merchant_pub2@example.com",
            mobile_number="+919876543201",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant2 = Merchant.objects.create(
            user=self.merchant_user2,
            status=Merchant.Status.ACTIVE,
        )
        self.shop2 = Shop.objects.create(
            merchant=self.merchant2,
            name="City Fresh Mart",
            address_line="600 Low St",
            area="Bandra",
            city="Mumbai",
            state="Maharashtra",
            pincode="400050",
            contact_number=self.merchant_user2.mobile_number,
        )

    def test_create_customer_via_public_api_success(self):
        """Unauthenticated customer can provide WhatsApp and name to create a Shop profile."""
        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/"
        payload = {
            "whatsapp_number": "9123456789",
            "name": "Pooja Hegde",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["created"])
        self.assertEqual(res.data["customer"]["name"], "Pooja Hegde")
        self.assertEqual(res.data["customer"]["whatsapp_number"], "+919123456789")
        self.assertIn("id", res.data["customer"])
        self.assertIn("created_at", res.data["customer"])

        # Confirm no login, credentials, or private merchant fields leaked
        for secret in ["password", "token", "access", "refresh", "jwt", "merchant", "user", "is_staff"]:
            self.assertNotIn(secret, res.data)
            self.assertNotIn(secret, res.data["customer"])

    def test_recognize_existing_customer_via_create_or_recognize_api(self):
        """Submitting an existing customer's number recognizes them without duplicate creation."""
        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/"
        Customer.objects.create(
            shop=self.shop,
            name="Existing Shopper",
            whatsapp_number="9123456789",
        )

        res = self.client.post(url, {"whatsapp_number": "9123456789"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["created"])
        self.assertEqual(res.data["customer"]["name"], "Existing Shopper")
        self.assertEqual(res.data["customer"]["whatsapp_number"], "+919123456789")

    def test_create_customer_with_cart_association_before_order(self):
        """Public customer endpoint associates newly created customer with active Cart before an Order."""
        cart = Cart.objects.create(shop=self.shop)
        self.assertIsNone(cart.customer)

        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/"
        payload = {
            "whatsapp_number": "9123456789",
            "name": "Cart Visitor",
            "cart_id": cart.id,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        cart.refresh_from_db()
        self.assertIsNotNone(cart.customer)
        self.assertEqual(cart.customer.id, res.data["customer"]["id"])
        self.assertEqual(cart.customer.shop, self.shop)

    def test_reject_cart_from_different_shop(self):
        """Passing a Cart belonging to a different shop is rejected with 400 CART_NOT_FOUND."""
        cart_shop2 = Cart.objects.create(shop=self.shop2)

        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/"
        payload = {
            "whatsapp_number": "9123456789",
            "cart_id": cart_shop2.id,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["code"], "CART_NOT_FOUND")

    def test_unknown_public_slug_returns_404(self):
        """Requests to an unknown public slug return 404 SHOP_NOT_FOUND."""
        url = "/api/v1/shops/public/non-existent-shop-slug/customer/"
        res = self.client.post(url, {"whatsapp_number": "9123456789"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["code"], "SHOP_NOT_FOUND")

    def test_inactive_shop_returns_404(self):
        """Requests to a deactivated or suspended shop return 404 SHOP_UNAVAILABLE."""
        self.shop.deactivate()
        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/"
        res = self.client.post(url, {"whatsapp_number": "9123456789"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["code"], "SHOP_UNAVAILABLE")

    def test_authenticated_user_number_rejected_by_api(self):
        """Supplying an authenticated merchant/admin mobile number is rejected with 400."""
        url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/"
        payload = {
            "whatsapp_number": self.merchant_user.mobile_number,
            "name": "Imposter",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["code"], "INVALID_CUSTOMER_DATA")

    def test_recognize_endpoint_get_and_post(self):
        """Public recognize endpoint recognizes returning customer via GET and POST."""
        cust = Customer.objects.create(
            shop=self.shop,
            name="Returning Buyer",
            whatsapp_number="9123456789",
        )

        rec_url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/recognize/"

        # GET request with query param
        res_get = self.client.get(rec_url, {"whatsapp_number": "9123456789"})
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertTrue(res_get.data["recognized"])
        self.assertEqual(res_get.data["customer"]["name"], "Returning Buyer")
        self.assertEqual(res_get.data["customer"]["id"], cust.id)

        # POST request with body
        res_post = self.client.post(rec_url, {"whatsapp_number": "+919123456789"}, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_200_OK)
        self.assertTrue(res_post.data["recognized"])
        self.assertEqual(res_post.data["customer"]["id"], cust.id)

    def test_recognize_endpoint_unknown_customer_returns_404(self):
        """Recognize endpoint for an unknown customer returns 404 with CUSTOMER_NOT_FOUND."""
        rec_url = f"/api/v1/shops/public/{self.shop.public_slug}/customer/recognize/"
        res = self.client.get(rec_url, {"whatsapp_number": "9999999999"})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(res.data["recognized"])
        self.assertEqual(res.data["code"], "CUSTOMER_NOT_FOUND")

    def test_cross_shop_isolation_in_public_api(self):
        """Customer registered in Shop 1 is NOT recognized in Shop 2."""
        c1 = Customer.objects.create(
            shop=self.shop,
            name="Shop 1 Shopper",
            whatsapp_number="9123456789",
        )

        # Recognize in Shop 2 returns 404
        rec_shop2_url = f"/api/v1/shops/public/{self.shop2.public_slug}/customer/recognize/"
        res_s2 = self.client.get(rec_shop2_url, {"whatsapp_number": "9123456789"})
        self.assertEqual(res_s2.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(res_s2.data["recognized"])

        # Creating in Shop 2 creates a completely separate Customer
        create_shop2_url = f"/api/v1/shops/public/{self.shop2.public_slug}/customer/"
        res_create_s2 = self.client.post(create_shop2_url, {"whatsapp_number": "9123456789", "name": "Shop 2 Shopper"}, format="json")
        self.assertEqual(res_create_s2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(res_create_s2.data["customer"]["id"], c1.id)
        self.assertEqual(res_create_s2.data["customer"]["name"], "Shop 2 Shopper")

    def test_customers_app_url_alias(self):
        """Endpoint is accessible via /api/v1/customers/public/<slug>/customer/ as well."""
        url = f"/api/v1/customers/public/{self.shop.public_slug}/customer/"
        res = self.client.post(url, {"whatsapp_number": "9123456789", "name": "Alias Shopper"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["customer"]["name"], "Alias Shopper")


class MerchantCustomerAPITests(TestCase):
    """
    Tests for CUS-005: Merchant retrieval of Shop-specific Customer profiles for ERP use.
    Enforces shared API conventions, server-derived Shop authorization, and strict tenant isolation.
    """

    def setUp(self):
        self.client = APIClient()

        # Merchant 1 & Shop 1
        self.user1 = User.objects.create_user(
            username="merchant_1",
            email="merchant1@example.com",
            mobile_number="+919876543210",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop1 = Shop.objects.create(
            merchant=self.merchant1,
            name="Alpha Fresh",
            address_line="100 First St",
            area="Kothrud",
            city="Pune",
            state="Maharashtra",
            pincode="411038",
            contact_number=self.user1.mobile_number,
        )

        # Merchant 2 & Shop 2
        self.user2 = User.objects.create_user(
            username="merchant_2",
            email="merchant2@example.com",
            mobile_number="+919876543211",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop2 = Shop.objects.create(
            merchant=self.merchant2,
            name="Beta Mart",
            address_line="200 Second St",
            area="Bandra",
            city="Mumbai",
            state="Maharashtra",
            pincode="400050",
            contact_number=self.user2.mobile_number,
        )

        # Super Admin
        self.admin_user = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            mobile_number="+919876543299",
            role=User.Role.SUPER_ADMIN,
            password="testpassword123",
        )

    def authenticate(self, user):
        if user.role == User.Role.SUPER_ADMIN:
            res = self.client.post(
                "/api/v1/auth/super-admin/login/",
                {"identifier": user.email, "password": "testpassword123"},
                format="json",
            )

        else:
            res = self.client.post(
                "/api/v1/auth/login/",
                {"mobile_number": user.mobile_number, "password": "testpassword123"},
                format="json",
            )
        self.assertEqual(res.status_code, 200, f"Login failed: {res.data}")
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


    def test_merchant_can_list_shop_customers(self):
        """Merchant can list Customer profiles scoped strictly to their own Shop."""
        c1 = Customer.objects.create(shop=self.shop1, name="Alice Brown", whatsapp_number="9111111111")
        c2 = Customer.objects.create(shop=self.shop1, name="Bob Green", whatsapp_number="9222222222")

        self.authenticate(self.user1)

        # Test both endpoint conventions: /api/v1/customers/ and /api/v1/shops/me/customers/
        for url in ["/api/v1/customers/", "/api/v1/shops/me/customers/"]:
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 2)
            ids = [item["id"] for item in res.data]
            self.assertIn(c1.id, ids)
            self.assertIn(c2.id, ids)

            # Check ERP field schema
            sample = res.data[0]
            self.assertIn("id", sample)
            self.assertEqual(sample["shop"], self.shop1.id)
            self.assertIn("name", sample)
            self.assertIn("whatsapp_number", sample)
            self.assertIn("created_at", sample)
            self.assertIn("updated_at", sample)

    def test_merchant_can_retrieve_single_customer_detail(self):
        """Merchant can retrieve a single Customer profile detail by ID within their Shop."""
        c = Customer.objects.create(shop=self.shop1, name="Alice Brown", whatsapp_number="9111111111")

        self.authenticate(self.user1)

        for url in [f"/api/v1/customers/{c.id}/", f"/api/v1/shops/me/customers/{c.id}/"]:
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["id"], c.id)
            self.assertEqual(res.data["shop"], self.shop1.id)
            self.assertEqual(res.data["name"], "Alice Brown")
            self.assertEqual(res.data["whatsapp_number"], "+919111111111")

    def test_tenant_isolation_global_contact_cannot_access_other_shop_profile(self):
        """
        Global contact identity boundary: Even when a customer uses the same WhatsApp number
        across different shops, Merchant 1 cannot access Merchant 2's Customer profile.
        """
        shared_number = "9111111111"
        cust_shop1 = Customer.objects.create(shop=self.shop1, name="Alice at Shop 1", whatsapp_number=shared_number)
        cust_shop2 = Customer.objects.create(shop=self.shop2, name="Alice at Shop 2", whatsapp_number=shared_number)

        self.authenticate(self.user1)

        # Merchant 1 listing only returns cust_shop1
        res = self.client.get("/api/v1/customers/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], cust_shop1.id)
        self.assertEqual(res.data[0]["name"], "Alice at Shop 1")
        self.assertEqual(res.data[0]["shop"], self.shop1.id)

        # Merchant 1 cannot retrieve cust_shop2 by ID (must return 404)
        res_other = self.client.get(f"/api/v1/customers/{cust_shop2.id}/")
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

        res_other_me = self.client.get(f"/api/v1/shops/me/customers/{cust_shop2.id}/")
        self.assertEqual(res_other_me.status_code, status.HTTP_404_NOT_FOUND)

        # Merchant 2 authenticating sees only cust_shop2
        self.authenticate(self.user2)
        res2 = self.client.get("/api/v1/customers/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res2.data), 1)
        self.assertEqual(res2.data[0]["id"], cust_shop2.id)
        self.assertEqual(res2.data[0]["name"], "Alice at Shop 2")
        self.assertEqual(res2.data[0]["shop"], self.shop2.id)

        # Merchant 2 cannot retrieve cust_shop1 by ID
        res_other_m2 = self.client.get(f"/api/v1/customers/{cust_shop1.id}/")
        self.assertEqual(res_other_m2.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_provided_shop_id_never_trusted_or_leaks(self):
        """
        Never trust client-provided shop_id as proof of authorization.
        If client specifies another shop_id in query params, it does not reveal that shop's data.
        """
        Customer.objects.create(shop=self.shop1, name="Cust 1", whatsapp_number="9111111111")
        Customer.objects.create(shop=self.shop2, name="Cust 2", whatsapp_number="9222222222")

        self.authenticate(self.user1)

        # Attempt to request shop 2's customers via query parameter
        res = self.client.get(f"/api/v1/customers/?shop_id={self.shop2.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should be empty or only shop1; never returns shop2's customers
        self.assertEqual(len(res.data), 0)

    def test_erp_search_and_filtering(self):
        """Supports filtering by search keyword, customer name, and WhatsApp number."""
        c1 = Customer.objects.create(shop=self.shop1, name="Ramesh Kumar", whatsapp_number="9811111111")
        c2 = Customer.objects.create(shop=self.shop1, name="Suresh Gupta", whatsapp_number="9822222222")
        c3 = Customer.objects.create(shop=self.shop1, name="Pooja Sharma", whatsapp_number="9833333333")

        self.authenticate(self.user1)

        # Search by name keyword
        res_search_name = self.client.get("/api/v1/customers/?search=Ramesh")
        self.assertEqual(res_search_name.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_search_name.data), 1)
        self.assertEqual(res_search_name.data[0]["id"], c1.id)

        # Search by number keyword
        res_search_num = self.client.get("/api/v1/customers/?search=9822222222")
        self.assertEqual(res_search_num.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_search_num.data), 1)
        self.assertEqual(res_search_num.data[0]["id"], c2.id)

        # Filter by name parameter
        res_name = self.client.get("/api/v1/customers/?name=Pooja")
        self.assertEqual(res_name.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_name.data), 1)
        self.assertEqual(res_name.data[0]["id"], c3.id)

        # Filter by whatsapp_number parameter
        res_wa = self.client.get("/api/v1/customers/?whatsapp_number=9811111111")
        self.assertEqual(res_wa.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_wa.data), 1)
        self.assertEqual(res_wa.data[0]["id"], c1.id)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests are rejected with 401."""
        res = self.client.get("/api/v1/customers/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res_detail = self.client.get("/api/v1/customers/1/")
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_cannot_access_merchant_erp_endpoint(self):
        """Super Admin is rejected from merchant-scoped ERP endpoints."""
        self.authenticate(self.admin_user)
        res = self.client.get("/api/v1/customers/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_merchant_without_shop_returns_404(self):
        """Merchant without an associated Shop receives 404 SHOP_NOT_FOUND."""
        user_no_shop = User.objects.create_user(
            username="merchant_no_shop",
            email="noshop@example.com",
            mobile_number="+919876543277",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        Merchant.objects.create(
            user=user_no_shop,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.authenticate(user_no_shop)

        res = self.client.get("/api/v1/customers/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["code"], "SHOP_NOT_FOUND")

    def test_deactivated_shop_returns_403_shop_inactive(self):
        """Deactivated or suspended shop receives 403 SHOP_INACTIVE."""
        self.shop1.status = Shop.Status.DEACTIVATED
        self.shop1.save()

        self.authenticate(self.user1)
        res = self.client.get("/api/v1/customers/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["code"], "SHOP_INACTIVE")

    def test_suspended_shop_returns_403_shop_inactive(self):
        """Suspended shop receives 403 SHOP_INACTIVE."""
        self.shop1.status = Shop.Status.SUSPENDED
        self.shop1.save()

        self.authenticate(self.user1)
        res = self.client.get("/api/v1/customers/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["code"], "SHOP_INACTIVE")

    def test_modification_methods_disallowed(self):
        """ReadOnly ViewSet disallows POST, PUT, PATCH, DELETE operations."""
        c = Customer.objects.create(shop=self.shop1, name="Read Only Cust", whatsapp_number="9111111111")
        self.authenticate(self.user1)

        # POST /api/v1/customers/ -> 405
        res_post = self.client.post("/api/v1/customers/", {"name": "New Cust", "whatsapp_number": "9222222222"}, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PUT /api/v1/customers/<id>/ -> 405
        res_put = self.client.put(f"/api/v1/customers/{c.id}/", {"name": "Updated Cust"}, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PATCH /api/v1/customers/<id>/ -> 405
        res_patch = self.client.patch(f"/api/v1/customers/{c.id}/", {"name": "Patched Cust"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # DELETE /api/v1/customers/<id>/ -> 405
        res_delete = self.client.delete(f"/api/v1/customers/{c.id}/")
        self.assertEqual(res_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


