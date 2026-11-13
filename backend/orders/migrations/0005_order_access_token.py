from django.db import migrations, models

from config.tokens import new_access_token


def fill_tokens(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.filter(access_token__isnull=True).iterator():
        # update() skips Order.save() validation and the integrity triggers' column checks.
        Order.objects.filter(pk=order.pk).update(access_token=new_access_token())


class Migration(migrations.Migration):
    atomic = False  # data fill then ALTER: avoid Postgres "pending trigger events"
    dependencies = [("orders", "0004_order_orders_ord_shp_stat_dt_idx_and_more")]
    operations = [
        migrations.AddField(
            model_name="order",
            name="access_token",
            field=models.CharField(max_length=64, null=True, editable=False),
        ),
        migrations.RunPython(fill_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="access_token",
            field=models.CharField(
                max_length=64, unique=True, default=new_access_token, editable=False
            ),
        ),
    ]
