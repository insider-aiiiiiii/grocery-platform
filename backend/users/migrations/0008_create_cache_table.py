from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    # Backs CACHES['default'] (DatabaseCache): login throttling must be shared by every
    # serverless instance, which an in-memory cache cannot do. Idempotent.
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = [("users", "0007_superadminrecoverythrottle_and_more")]
    operations = [migrations.RunPython(create_cache_table, migrations.RunPython.noop)]
