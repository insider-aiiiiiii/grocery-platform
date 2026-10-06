from django.contrib.auth.models import AbstractBaseUser, AbstractUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from shops.models import Shop
from users.models import Merchant, User

from .models import Customer, normalize_whatsapp_number


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

