from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MerchantIdentifiersMigrationTests(TransactionTestCase):
    migrate_from = [("users", "0002_merchant")]
    migrate_to = [("users", "0003_remove_merchant_email_remove_merchant_mobile_number_and_more")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        User = old_apps.get_model("users", "User")
        Merchant = old_apps.get_model("users", "Merchant")
        merchant_user = User.objects.create(
            username="merchant-one",
            password="encoded-password",
            role="MERCHANT",
        )
        Merchant.objects.create(
            user=merchant_user,
            mobile_number="+911234567890",
            email="merchant@example.com",
        )
        User.objects.create(
            username="admin-one",
            password="encoded-password",
            role="SUPER_ADMIN",
            email="admin@example.com",
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_merchant_identifiers_move_to_the_user(self):
        User = self.apps.get_model("users", "User")
        user = User.objects.get(username="merchant-one")

        self.assertEqual(user.mobile_number, "+911234567890")
        self.assertEqual(user.email, "merchant@example.com")
