from django.db import migrations, models

from config.tokens import new_access_token


def fill_tokens(apps, schema_editor):
    Cart = apps.get_model("cart", "Cart")
    for cart in Cart.objects.filter(access_token__isnull=True).iterator():
        cart.access_token = new_access_token()
        cart.save(update_fields=["access_token"])


class Migration(migrations.Migration):
    atomic = False  # data fill then ALTER: avoid Postgres "pending trigger events"
    dependencies = [("cart", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="cart",
            name="access_token",
            field=models.CharField(max_length=64, null=True, editable=False),
        ),
        migrations.RunPython(fill_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="cart",
            name="access_token",
            field=models.CharField(
                max_length=64, unique=True, default=new_access_token, editable=False
            ),
        ),
    ]
