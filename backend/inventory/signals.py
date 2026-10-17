from django.db.models.signals import post_save
from django.dispatch import receiver

from catalog.models import ProductVariant, ShopProduct
from .services import initialize_product_stock, initialize_variant_stock


@receiver(post_save, sender=ShopProduct)
def initialize_product_inventory(sender, instance, created, **kwargs):
    """
    Ensure newly created Shop Products start with stock 0.000.
    If the product does not have variants, create a product-level stock item.
    """
    if created and not instance.variants.exists():
        initialize_product_stock(instance)


@receiver(post_save, sender=ProductVariant)
def initialize_variant_inventory(sender, instance, created, **kwargs):
    """
    Ensure newly created Variants start with stock 0.000.
    For variant-based products, variant stock is authoritative.
    Any obsolete independent product-level stock record is removed.
    """
    if created:
        initialize_variant_stock(instance)
