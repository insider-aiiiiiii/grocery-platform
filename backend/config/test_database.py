import unittest
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.database import database_settings


class DatabaseSettingsTests(unittest.TestCase):
    def test_database_url_selects_postgresql_and_preserves_ssl(self):
        settings = database_settings({
            "DATABASE_URL": "postgresql://dbuser:secret@db.example.test:5432/app?sslmode=require",
        }, base_dir=Path("/tmp/project"))["default"]

        self.assertEqual(settings["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(settings["NAME"], "app")
        self.assertEqual(settings["OPTIONS"], {"sslmode": "require"})
        self.assertEqual(settings["CONN_MAX_AGE"], 60)
        self.assertTrue(settings["CONN_HEALTH_CHECKS"])
        self.assertNotIn("DISABLE_SERVER_SIDE_CURSORS", settings)

    def test_pooler_host_disables_server_side_cursors(self):
        settings = database_settings({
            "DATABASE_URL": "postgresql://u:p@ep-x-pooler.example.test/app?sslmode=require",
        })["default"]

        self.assertTrue(settings["DISABLE_SERVER_SIDE_CURSORS"])

    def test_serverless_and_override_connection_age(self):
        url = "postgresql://u:p@db.example.test/app"
        self.assertEqual(
            database_settings({"DATABASE_URL": url, "VERCEL": "1"})["default"]["CONN_MAX_AGE"], 0
        )
        self.assertEqual(
            database_settings({"DATABASE_URL": url, "DB_CONN_MAX_AGE": "0"})["default"]["CONN_MAX_AGE"], 0
        )

    def test_postgres_fields_remain_supported(self):
        settings = database_settings({
            "POSTGRES_DB": "app",
            "POSTGRES_USER": "dbuser",
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_HOST": "db.example.test",
            "POSTGRES_PORT": "6543",
        })["default"]

        self.assertEqual(settings["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(settings["PORT"], "6543")

    def test_local_development_defaults_to_sqlite(self):
        settings = database_settings({}, base_dir=Path("/tmp/project"))["default"]

        self.assertEqual(settings["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(settings["NAME"], Path("/tmp/project/db.sqlite3"))

    def test_vercel_without_postgres_configuration_fails_closed(self):
        with self.assertRaisesRegex(ImproperlyConfigured, "required in production"):
            database_settings({"VERCEL": "1"})

    def test_invalid_database_url_fails_without_echoing_credentials(self):
        secret_url = "mysql://private-user:private-password@db.example.test/app"

        with self.assertRaises(ImproperlyConfigured) as raised:
            database_settings({"DATABASE_URL": secret_url})

        self.assertNotIn("private-user", str(raised.exception))
        self.assertNotIn("private-password", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
