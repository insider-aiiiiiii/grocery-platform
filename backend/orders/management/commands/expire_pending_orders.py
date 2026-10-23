from django.core.management.base import BaseCommand

from orders.services import expire_overdue_pending_orders


class Command(BaseCommand):
    help = "Expire overdue PENDING orders and release reserved inventory exactly once."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Maximum number of overdue orders to process in this run (default: 100).",
        )
        parser.add_argument(
            "--shop-id",
            type=int,
            default=None,
            help="Optional Shop ID to restrict expiration processing to a specific shop.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        shop_id = options.get("shop_id")

        if batch_size <= 0:
            self.stderr.write(self.style.ERROR("batch-size must be greater than 0."))
            return

        expired_count = expire_overdue_pending_orders(batch_size=batch_size, shop_id=shop_id)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully expired {expired_count} overdue pending order(s) and released reservations."
            )
        )
