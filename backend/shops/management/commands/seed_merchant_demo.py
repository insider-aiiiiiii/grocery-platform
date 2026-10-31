from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import ProductVariant, ShopCategory, ShopProduct
from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderDeliveryAddress, OrderItem
from shops.models import Shop
from users.models import Merchant


DEMO_PREFIX = "DEMO-SEED"


class Command(BaseCommand):
    help = "Create repeatable demo data for an active merchant's existing shop."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            required=True,
            help="Username of the active merchant whose existing shop will receive demo data.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        merchant = (
            Merchant.objects.select_related("user")
            .filter(user__username=username, user__role="MERCHANT")
            .first()
        )
        if merchant is None:
            raise CommandError(f"No merchant account found for username '{username}'.")
        if merchant.status != Merchant.Status.ACTIVE:
            raise CommandError(f"Merchant '{username}' is not active.")
        if not Shop.objects.filter(merchant=merchant).exists():
            raise CommandError(f"Merchant '{username}' does not have a shop yet.")

        shop = Shop.objects.get(merchant=merchant)
        with transaction.atomic():
            data = self._seed_shop(shop)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo data for '{shop.name}' (merchant '{username}'): "
                f"{data['categories']} categories, {data['products']} products, "
                f"{data['customers']} customers, and {data['orders']} orders."
            )
        )

    def _seed_shop(self, shop):
        category_specs = [
            ("fresh-produce", "DEMO-SEED Fresh Produce", "Sample fruits and vegetables."),
            ("daily-essentials", "DEMO-SEED Daily Essentials", "Sample pantry and household items."),
        ]
        categories = {}
        for slug, name, description in category_specs:
            category, _ = ShopCategory.objects.update_or_create(
                shop=shop,
                slug=f"{DEMO_PREFIX.lower()}-{slug}",
                defaults={"name": name, "description": description, "is_active": True},
            )
            categories[slug] = category

        product_specs = [
            {
                "sku": f"{DEMO_PREFIX}-APPLE-001",
                "name": "DEMO-SEED Kashmiri Apples",
                "description": "Crisp apples for storefront and catalog previews.",
                "brand": "Demo Orchard",
                "price": Decimal("180.00"),
                "category": "fresh-produce",
                "visible": True,
                "available": True,
                "stock": Decimal("24.000"),
                "reserved": Decimal("1.000"),
            },
            {
                "sku": f"{DEMO_PREFIX}-BANANA-001",
                "name": "DEMO-SEED Robusta Bananas",
                "description": "Visible sample item with no stock.",
                "brand": "Demo Orchard",
                "price": Decimal("60.00"),
                "category": "fresh-produce",
                "visible": True,
                "available": True,
                "stock": Decimal("0.000"),
                "reserved": Decimal("0.000"),
            },
            {
                "sku": f"{DEMO_PREFIX}-MILK-001",
                "name": "DEMO-SEED Toned Milk 1L",
                "description": "Sample dairy item with regular availability.",
                "brand": "Demo Dairy",
                "price": Decimal("68.00"),
                "category": "daily-essentials",
                "visible": True,
                "available": True,
                "stock": Decimal("18.000"),
                "reserved": Decimal("0.000"),
            },
            {
                "sku": f"{DEMO_PREFIX}-RICE-001",
                "name": "DEMO-SEED Basmati Rice",
                "description": "Sample staple product with selectable pack sizes.",
                "brand": "Demo Pantry",
                "price": None,
                "category": "daily-essentials",
                "visible": True,
                "available": True,
                "stock": None,
                "reserved": None,
            },
            {
                "sku": f"{DEMO_PREFIX}-BREAD-001",
                "name": "DEMO-SEED Whole Wheat Bread",
                "description": "Sample item currently marked unavailable.",
                "brand": "Demo Bakery",
                "price": Decimal("55.00"),
                "category": "daily-essentials",
                "visible": True,
                "available": False,
                "stock": Decimal("7.000"),
                "reserved": Decimal("0.000"),
            },
            {
                "sku": f"{DEMO_PREFIX}-SOAP-001",
                "name": "DEMO-SEED Dish Soap",
                "description": "Hidden sample item for merchant catalog previews.",
                "brand": "Demo Home",
                "price": Decimal("95.00"),
                "category": "daily-essentials",
                "visible": False,
                "available": True,
                "stock": Decimal("9.000"),
                "reserved": Decimal("0.000"),
            },
        ]

        products = {}
        for spec in product_specs:
            product, _ = ShopProduct.objects.update_or_create(
                shop=shop,
                sku=spec["sku"],
                defaults={
                    "name": spec["name"],
                    "description": spec["description"],
                    "brand": spec["brand"],
                    "price": spec["price"],
                    "is_visible": spec["visible"],
                    "is_available": spec["available"],
                },
            )
            product.categories.set([categories[spec["category"]]])
            products[spec["sku"]] = product
            if spec["stock"] is not None:
                self._set_inventory(
                    shop,
                    product,
                    spec["stock"],
                    spec["reserved"],
                )

        rice = products[f"{DEMO_PREFIX}-RICE-001"]
        rice_variants = []
        for sku, name, price, quantity in [
            (f"{DEMO_PREFIX}-RICE-1KG", "1 kg pack", Decimal("145.00"), Decimal("16.000")),
            (f"{DEMO_PREFIX}-RICE-5KG", "5 kg pack", Decimal("690.00"), Decimal("4.000")),
        ]:
            variant, _ = ProductVariant.objects.update_or_create(
                product=rice,
                sku=sku,
                defaults={
                    "name": name,
                    "description": "Sample demo pack size.",
                    "price": price,
                    "is_visible": True,
                    "is_available": True,
                },
            )
            self._set_inventory(shop, rice, quantity, Decimal("0.000"), variant=variant)
            rice_variants.append(variant)

        customer_specs = [
            ("+919900002101", "DEMO-SEED Asha Rao"),
            ("+919900002102", "DEMO-SEED Kabir Mehta"),
            ("+919900002103", "DEMO-SEED Nisha Iyer"),
            ("+919900002104", "DEMO-SEED Rohan Das"),
            ("+919900002105", "DEMO-SEED Tara Shah"),
            ("+919900002106", "DEMO-SEED Vihaan Sen"),
        ]
        customers = []
        for whatsapp_number, name in customer_specs:
            customer, _ = Customer.objects.update_or_create(
                shop=shop,
                whatsapp_number=whatsapp_number,
                defaults={"name": name},
            )
            customers.append(customer)

        order_specs = [
            ("pending", Order.Status.PENDING, 0, products[f"{DEMO_PREFIX}-APPLE-001"], None, Order.FulfillmentType.HOME_DELIVERY),
            ("accepted", Order.Status.ACCEPTED, 1, products[f"{DEMO_PREFIX}-MILK-001"], None, Order.FulfillmentType.PICKUP),
            ("preparing", Order.Status.PREPARING, 2, products[f"{DEMO_PREFIX}-APPLE-001"], None, Order.FulfillmentType.HOME_DELIVERY),
            ("ready", Order.Status.READY, 3, rice, rice_variants[0], Order.FulfillmentType.PICKUP),
            ("completed", Order.Status.COMPLETED, 4, products[f"{DEMO_PREFIX}-MILK-001"], None, Order.FulfillmentType.HOME_DELIVERY),
            ("rejected", Order.Status.REJECTED, 5, products[f"{DEMO_PREFIX}-APPLE-001"], None, Order.FulfillmentType.PICKUP),
        ]
        now = timezone.now()
        for _, (key, status, customer_index, product, variant, fulfillment) in enumerate(order_specs):
            customer = customers[customer_index]
            quantity = Decimal("2.000") if key != "pending" else Decimal("1.000")
            unit_price = variant.price if variant else product.price
            subtotal = (unit_price * quantity).quantize(Decimal("0.01"))
            delivery_charge = Decimal("25.00") if fulfillment == Order.FulfillmentType.HOME_DELIVERY else Decimal("0.00")
            idempotency_key = f"{DEMO_PREFIX.lower()}:{key}"
            order_defaults = {
                "customer": customer,
                "status": status,
                "payment_status": Order.PaymentStatus.PAID if status == Order.Status.COMPLETED else Order.PaymentStatus.UNPAID,
                "fulfillment_type": fulfillment,
                "customer_name_snapshot": customer.name,
                "customer_phone_snapshot": customer.whatsapp_number,
                "delivery_fee_type_snapshot": Order.DeliveryFeeType.FIXED,
                "delivery_charge_snapshot": delivery_charge,
                "items_subtotal": subtotal,
                "total_amount": subtotal + delivery_charge,
                "expires_at": now + timedelta(minutes=30) if status == Order.Status.PENDING else None,
                "accepted_at": now - timedelta(minutes=25) if status in {Order.Status.ACCEPTED, Order.Status.PREPARING, Order.Status.READY, Order.Status.COMPLETED} else None,
                "completed_at": now - timedelta(minutes=5) if status == Order.Status.COMPLETED else None,
                "rejected_at": now - timedelta(minutes=5) if status == Order.Status.REJECTED else None,
                "rejection_actor": Order.RejectionActor.MERCHANT if status == Order.Status.REJECTED else "",
                "rejection_reason_code": "MERCHANT_REJECTED" if status == Order.Status.REJECTED else "",
                "rejection_note": "DEMO-SEED sample rejection" if status == Order.Status.REJECTED else "",
            }
            order, _ = Order.objects.update_or_create(
                shop=shop,
                idempotency_key=idempotency_key,
                defaults=order_defaults,
            )
            Order.objects.filter(pk=order.pk).update(created_at=now - timedelta(minutes=30))
            OrderItem.objects.update_or_create(
                order=order,
                sku_snapshot=variant.sku if variant else product.sku,
                defaults={
                    "product": product,
                    "variant": variant,
                    "product_name_snapshot": product.name,
                    "variant_name_snapshot": variant.name if variant else "",
                    "unit_snapshot": "pack" if variant else "item",
                    "ordered_quantity": quantity,
                    "quantity": quantity,
                    "unit_price_snapshot": unit_price,
                    "line_total": subtotal,
                },
            )
            order.recalculate_totals(save=True)
            if fulfillment == Order.FulfillmentType.HOME_DELIVERY:
                OrderDeliveryAddress.objects.update_or_create(
                    order=order,
                    defaults={
                        "recipient_name": customer.name,
                        "recipient_phone": customer.whatsapp_number,
                        "address_line": f"{100 + customer_index} Demo Lane",
                        "area": "Demo Nagar",
                        "city": shop.city,
                        "state": shop.state,
                        "pincode": shop.pincode,
                        "landmark": "Near Demo Market",
                        "delivery_notes": "DEMO-SEED sample delivery details",
                    },
                )
            else:
                OrderDeliveryAddress.objects.filter(order=order).delete()

        return {
            "categories": len(categories),
            "products": len(products),
            "customers": len(customers),
            "orders": len(order_specs),
        }

    @staticmethod
    def _set_inventory(shop, product, quantity, reserved_quantity, variant=None):
        InventoryItem.objects.update_or_create(
            shop=shop,
            product=product,
            variant=variant,
            defaults={
                "quantity": quantity,
                "reserved_quantity": reserved_quantity,
            },
        )
