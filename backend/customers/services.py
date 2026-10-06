"""
Domain services for the Customers application.

Owns Shop-specific Customer profile creation, recognition, and optional Cart association.
Enforces the approved global identity boundary and strict tenant isolation.
"""
from typing import Any, Optional, Tuple

from django.core.exceptions import ValidationError

from .models import Customer, normalize_whatsapp_number


def create_or_recognize_customer(
    shop: Any,
    whatsapp_number: str,
    name: Optional[str] = None,
    cart: Optional[Any] = None,
) -> Tuple[Customer, bool]:
    """
    Create or recognize a Shop-specific Customer profile when WhatsApp is first provided.

    Business Invariants:
    1. Scope: Strictly scoped to the specified Shop. Does not link profiles or share data
       across Shops.
    2. Recognition: Within the same Shop, recognized by normalized WhatsApp number.
       Prefills or updates name if provided and previously empty.
    3. Creation: If not previously known in this Shop, creates a permanent Shop-specific Customer.
       Can be created before an Order exists (e.g. at Cart / checkout stage).
    4. Identity Boundary: Rejects numbers claimed by authenticated User identities (Merchants/Super Admins).
       Never exposes other Shops' profile data or history.
    5. Cart Binding: If a Cart is provided, validates that the Cart belongs to the same Shop
       and associates the Customer with the Cart.
    """
    if not shop:
        raise ValidationError({"shop": "A Shop instance is required to create or recognize a customer profile."})

    if not whatsapp_number:
        raise ValidationError({"whatsapp_number": "WhatsApp number is required."})

    normalized = normalize_whatsapp_number(whatsapp_number)

    # Check approved global identity/claim boundary against authenticated Users
    from users.models import User
    if User.objects.filter(mobile_number=normalized).exists():
        raise ValidationError(
            {"whatsapp_number": "This WhatsApp number is already registered as an authenticated user identity."}
        )

    # Recognize within the specified Shop
    customer = Customer.objects.filter(shop=shop, whatsapp_number=normalized).first()
    created = False

    if customer:
        # Recognized returning customer within this Shop
        if name and name.strip() and not customer.name:
            customer.name = name.strip()
            customer.save(update_fields=["name", "updated_at"])
    else:
        # Create a new Shop-specific Customer profile
        customer = Customer(
            shop=shop,
            whatsapp_number=normalized,
            name=name.strip() if name else "",
        )
        customer.full_clean()
        customer.save()
        created = True

    # Associate with Cart if provided
    if cart is not None:
        if cart.shop_id != (shop.id if hasattr(shop, "id") else shop.pk):
            raise ValidationError({"cart": "Cart must belong to the same Shop as the Customer."})
        if cart.customer_id != customer.id:
            cart.customer = customer
            cart.save(update_fields=["customer", "updated_at"])

    return customer, created


def recognize_customer(
    shop: Any,
    whatsapp_number: str,
) -> Optional[Customer]:
    """
    Recognize an existing customer within a specific Shop by WhatsApp number.

    Returns the Shop-scoped Customer profile if found, or None.
    A matching contact in another Shop is NEVER returned.
    """
    if not shop or not whatsapp_number:
        return None

    try:
        normalized = normalize_whatsapp_number(whatsapp_number)
    except ValidationError:
        return None

    return Customer.objects.filter(shop=shop, whatsapp_number=normalized).first()
