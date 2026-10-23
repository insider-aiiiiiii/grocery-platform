from django.db import transaction

from .models import Shop


def cleanup_shop_dependencies(shop_id: int) -> None:
    """
    Clean up all Shop-owned domain data in dependency-safe order.
    Ensures that foreign key constraints (such as Order.customer on_delete=PROTECT)
    do not block deletion.
    """
    # 1. Campaign targeting: remove association from selected_shops
    from campaigns.models import Campaign

    Campaign.selected_shops.through.objects.filter(shop_id=shop_id).delete()

    # 2. Notifications outbox items
    from notifications.models import NotificationOutbox

    NotificationOutbox.objects.filter(shop_id=shop_id).delete()

    # 3. Customer credentials, grants and sessions
    from customers.models import CustomerSession, HistoryLinkGrant

    HistoryLinkGrant.objects.filter(shop_id=shop_id).delete()
    CustomerSession.objects.filter(customer__shop_id=shop_id).delete()

    # 4. Cart and CartItems
    from cart.models import Cart

    Cart.objects.filter(shop_id=shop_id).delete()

    # 5. Orders, OrderItems, OrderDeliveryAddresses
    # Deleting Orders first removes the ProtectedError on Customer
    from orders.models import Order

    Order.objects.filter(shop_id=shop_id).delete()

    # 6. Customer profiles scoped to the shop
    from customers.models import Customer

    Customer.objects.filter(shop_id=shop_id).delete()

    # 7. Inventory Items
    from inventory.models import InventoryItem

    InventoryItem.objects.filter(shop_id=shop_id).delete()

    # 8. Catalog entities: Products (and Variants), Attributes, Brands, Categories
    from catalog.models import ShopBrand, ShopCategory, ShopCustomAttribute, ShopProduct

    ShopProduct.objects.filter(shop_id=shop_id).delete()
    ShopCustomAttribute.objects.filter(shop_id=shop_id).delete()
    ShopBrand.objects.filter(shop_id=shop_id).delete()
    ShopCategory.objects.filter(shop_id=shop_id).delete()


def permanently_delete_shop(shop: Shop | int, requested_by=None) -> None:
    """
    Permanently delete a Shop and all its owned domain data in dependency-safe order.

    Preserves Merchant account credentials (Merchant and User records).
    Never transfers old data to a replacement shop.
    """
    if isinstance(shop, (int, str)):
        shop_instance = Shop.objects.filter(pk=shop).first()
        if not shop_instance:
            return
    else:
        shop_instance = shop

    with transaction.atomic():
        # Lock shop row to avoid concurrent operations
        locked_shop = Shop.objects.select_for_update().filter(pk=shop_instance.pk).first()
        if not locked_shop:
            return

        locked_shop.delete()

