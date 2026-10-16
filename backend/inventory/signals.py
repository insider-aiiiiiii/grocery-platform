from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from catalog.models import ProductVariant, ShopProduct
from .models import InventoryItem


@receiver(post_save, sender=ShopProduct)
def initialize_product_inventory(sender, instance, created, **kwargs):
    """
    Ensure newly created Shop Products start with stock 0.000.
    If the product does not have variants, create a product-level stock item.
    """
    if created and not instance.variants.exists():
        InventoryItem.objects.get_or_create(
            shop=instance.shop,
            product=instance,
            variant=None,
            defaults={
                "quantity": Decimal("0.000"),
                "reserved_quantity": Decimal("0.000"),
            },
        )


@receiver(post_save, sender=ProductVariant)
def initialize_variant_inventory(sender, instance, created, **kwargs):
    """
    Ensure newly created Variants start with stock 0.000.
    For variant-based products, variant stock is authoritative.
    Any obsolete independent product-level stock record is removed.
    """
    if created:
        # Create authoritative variant inventory record
        InventoryItem.objects.get_or_create(
            shop=instance.product.shop,
            product=instance.product,
            variant=instance,
            defaults={
                "quantity": Decimal("0.000"),
                "reserved_quantity": Decimal("0.000"),
            },
        )
        # Remove any obsolete non-variant stock record for this parent product
        InventoryItem.objects.filter(
            product=instance.product,
            variant__isnull=True,
        ).delete()
