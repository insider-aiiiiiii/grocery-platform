from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Order(models.Model):
    """
    Historical purchase transaction post-checkout.

    Belongs to strictly one Shop and one Shop-scoped Customer.
    Preserves immutable checkout-time commercial snapshots (customer details,
    delivery charge, line item titles/prices, address).
    Guarantees strict state transitions without separate CANCELLED or EXPIRED states.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        PREPARING = "PREPARING", "Preparing"
        READY = "READY", "Ready"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"

    class FulfillmentType(models.TextChoices):
        PICKUP = "PICKUP", "Pickup"
        HOME_DELIVERY = "HOME_DELIVERY", "Home Delivery"

    class DeliveryFeeType(models.TextChoices):
        FIXED = "FIXED", "Fixed Fee"
        CONFIRMED_ON_WHATSAPP = "CONFIRMED_ON_WHATSAPP", "Fee Confirmed on WhatsApp"

    class RejectionActor(models.TextChoices):
        MERCHANT = "MERCHANT", "Merchant"
        CUSTOMER = "CUSTOMER", "Customer"
        SYSTEM = "SYSTEM", "System"

    # Multi-tenancy & Customer Relationships
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # Lifecycle & Payment State
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )

    # Fulfillment Choice
    fulfillment_type = models.CharField(
        max_length=16,
        choices=FulfillmentType.choices,
        default=FulfillmentType.HOME_DELIVERY,
    )

    # Customer Contact Snapshot at Checkout Time
    customer_name_snapshot = models.CharField(max_length=255)
    customer_phone_snapshot = models.CharField(max_length=16)

    # Preserved Delivery Fee Settings at Checkout Time
    delivery_fee_type_snapshot = models.CharField(
        max_length=24,
        choices=DeliveryFeeType.choices,
        default=DeliveryFeeType.FIXED,
    )
    delivery_charge_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Financial Totals (Derived from frozen line items & delivery snapshot)
    items_subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Checkout Idempotency Key (Per-shop idempotency guard)
    idempotency_key = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
    )

    # Pending Timeout & Lifecycle Timestamps
    expires_at = models.DateTimeField(db_index=True, null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Rejection / Cancellation / Expiry Metadata (Preserves single REJECTED state)
    rejection_actor = models.CharField(
        max_length=16,
        choices=RejectionActor.choices,
        blank=True,
        default="",
    )
    rejection_reason_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
    )
    rejection_note = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=["PENDING", "ACCEPTED", "PREPARING", "READY", "COMPLETED", "REJECTED"]),
                name="orders_order_valid_status",
            ),
            models.CheckConstraint(
                check=Q(payment_status__in=["UNPAID", "PAID"]),
                name="orders_order_valid_payment_status",
            ),
            models.CheckConstraint(
                check=Q(fulfillment_type__in=["PICKUP", "HOME_DELIVERY"]),
                name="orders_order_valid_fulfillment",
            ),
            models.CheckConstraint(
                check=~Q(status="COMPLETED", payment_status="UNPAID"),
                name="orders_order_completed_requires_paid",
            ),
            models.CheckConstraint(
                check=Q(items_subtotal__gte=0),
                name="orders_order_items_subtotal_non_negative",
            ),
            models.CheckConstraint(
                check=Q(delivery_charge_snapshot__gte=0),
                name="orders_order_delivery_charge_non_negative",
            ),
            models.CheckConstraint(
                check=Q(total_amount__gte=0),
                name="orders_order_total_amount_non_negative",
            ),
            models.CheckConstraint(
                check=~Q(customer_name_snapshot=""),
                name="orders_order_customer_name_required",
            ),
            models.CheckConstraint(
                check=~Q(customer_phone_snapshot=""),
                name="orders_order_customer_phone_required",
            ),
            models.CheckConstraint(
                check=Q(delivery_fee_type_snapshot__in=["FIXED", "CONFIRMED_ON_WHATSAPP"]),
                name="orders_order_valid_delivery_fee_type",
            ),
            models.CheckConstraint(
                check=~Q(delivery_fee_type_snapshot="CONFIRMED_ON_WHATSAPP")
                | Q(delivery_charge_snapshot=Decimal("0.00")),
                name="orders_order_whatsapp_fee_is_zero",
            ),
            models.UniqueConstraint(
                fields=["shop", "idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="orders_order_unique_shop_idempotency",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "status"], name="orders_order_shop_status_idx"),
            models.Index(fields=["shop", "customer"], name="orders_order_shop_cust_idx"),
            models.Index(fields=["shop", "-created_at"], name="orders_order_shop_created_idx"),
            models.Index(fields=["status", "expires_at"], name="orders_order_stat_expires_idx"),
            models.Index(fields=["shop", "status", "-created_at"], name="orders_ord_shp_stat_dt_idx"),
            models.Index(fields=["status", "-created_at"], name="orders_ord_stat_created_idx"),
            models.Index(fields=["-created_at"], name="orders_order_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk} ({self.status}) - Shop: {self.shop_id} - Customer: {self.customer_id}"

    def clean(self) -> None:
        super().clean()
        # Tenant isolation check: customer must belong to the same shop as the order
        if self.customer_id and self.shop_id:
            if self.customer.shop_id != self.shop_id:
                raise ValidationError({"customer": "Customer profile does not belong to the order's Shop."})

        # Payment invariant check: COMPLETED orders MUST be PAID
        if self.status == self.Status.COMPLETED and self.payment_status != self.PaymentStatus.PAID:
            raise ValidationError({"payment_status": "An order cannot be completed while UNPAID."})

        # Ensure amounts are quantized to 2 decimal places
        if self.items_subtotal is not None:
            self.items_subtotal = Decimal(str(self.items_subtotal)).quantize(Decimal("0.01"))
        if self.delivery_charge_snapshot is not None:
            self.delivery_charge_snapshot = Decimal(str(self.delivery_charge_snapshot)).quantize(Decimal("0.01"))
        if self.total_amount is not None:
            self.total_amount = Decimal(str(self.total_amount)).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def is_accepted(self) -> bool:
        return self.status == self.Status.ACCEPTED

    @property
    def is_preparing(self) -> bool:
        return self.status == self.Status.PREPARING

    @property
    def is_ready(self) -> bool:
        return self.status == self.Status.READY

    @property
    def is_completed(self) -> bool:
        return self.status == self.Status.COMPLETED

    @property
    def is_rejected(self) -> bool:
        return self.status == self.Status.REJECTED

    @property
    def is_paid(self) -> bool:
        return self.payment_status == self.PaymentStatus.PAID

    @property
    def is_unpaid(self) -> bool:
        return self.payment_status == self.PaymentStatus.UNPAID

    @property
    def is_pickup(self) -> bool:
        return self.fulfillment_type == self.FulfillmentType.PICKUP

    @property
    def is_home_delivery(self) -> bool:
        return self.fulfillment_type == self.FulfillmentType.HOME_DELIVERY

    @property
    def is_expired(self) -> bool:
        """Evaluates whether this pending order has exceeded its expiry timeout."""
        if self.status != self.Status.PENDING or not self.expires_at:
            return False
        return timezone.now() >= self.expires_at

    @property
    def can_customer_cancel(self) -> bool:
        """Customer may cancel only their own order while PENDING and not expired."""
        return self.status == self.Status.PENDING and not self.is_expired

    @property
    def can_merchant_cancel(self) -> bool:
        """Merchant may cancel an accepted order strictly before preparation."""
        return self.status == self.Status.ACCEPTED

    def recalculate_totals(self, save: bool = False) -> None:
        """
        Recalculates subtotal from constituent OrderItems and updates total_amount.
        Preserves delivery_charge_snapshot.
        """
        subtotal = Decimal("0.00")
        for item in self.items.all():
            if item.line_total is not None:
                subtotal += item.line_total
        self.items_subtotal = subtotal.quantize(Decimal("0.01"))
        self.total_amount = (self.items_subtotal + self.delivery_charge_snapshot).quantize(Decimal("0.01"))
        if save:
            self.save(update_fields=["items_subtotal", "total_amount", "updated_at"])


class OrderItem(models.Model):
    """
    Frozen line item snapshot in an Order.

    Holds immutable product titles, variant names, SKU, units, and checkout prices.
    Navigational foreign keys to ShopProduct and ProductVariant use SET_NULL so that
    deleting or altering a catalog product never alters or destroys historical line items.
    Supports merchant-controlled manual quantity reductions prior to acceptance.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "catalog.ShopProduct",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )

    # Immutable Checkout Product Snapshots
    product_name_snapshot = models.CharField(max_length=255)
    variant_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    sku_snapshot = models.CharField(max_length=128, blank=True, default="")
    unit_snapshot = models.CharField(max_length=32, blank=True, default="")
    attributes_snapshot = models.JSONField(default=dict, blank=True)

    # Quantities (supports up to 3 decimal places)
    ordered_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    # Unit Price and Line Total
    unit_price_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ["order", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(ordered_quantity__gt=0),
                name="orders_orderitem_ordered_qty_gt_zero",
            ),
            models.CheckConstraint(
                check=Q(quantity__gte=0),
                name="orders_orderitem_quantity_gte_zero",
            ),
            models.CheckConstraint(
                check=Q(quantity__lte=F("ordered_quantity")),
                name="orders_orderitem_qty_lte_ordered",
            ),
            models.CheckConstraint(
                check=Q(unit_price_snapshot__gte=0),
                name="orders_orderitem_price_gte_zero",
            ),
            models.CheckConstraint(
                check=Q(line_total__gte=0),
                name="orders_orderitem_line_total_gte_zero",
            ),
            models.CheckConstraint(
                check=~Q(product_name_snapshot=""),
                name="orders_orderitem_product_name_required",
            ),
        ]
        indexes = [
            models.Index(fields=["order", "product"], name="orders_oi_order_prod_idx"),
            models.Index(fields=["order", "variant"], name="orders_oi_order_var_idx"),
        ]

    def __str__(self) -> str:
        var_str = f" ({self.variant_name_snapshot})" if self.variant_name_snapshot else ""
        return f"{self.quantity}x {self.product_name_snapshot}{var_str} in Order #{self.order_id}"

    def clean(self) -> None:
        super().clean()
        # Quantize quantities to 3 decimal places
        if self.ordered_quantity is not None:
            self.ordered_quantity = Decimal(str(self.ordered_quantity)).quantize(Decimal("0.001"))
        if self.quantity is not None:
            self.quantity = Decimal(str(self.quantity)).quantize(Decimal("0.001"))
        if self.unit_price_snapshot is not None:
            self.unit_price_snapshot = Decimal(str(self.unit_price_snapshot)).quantize(Decimal("0.01"))

        # Quantity bound check
        if self.quantity is not None and self.ordered_quantity is not None:
            if self.quantity > self.ordered_quantity:
                raise ValidationError({"quantity": "Accepted quantity cannot exceed originally ordered quantity."})
            if self.quantity < Decimal("0.000"):
                raise ValidationError({"quantity": "Quantity cannot be negative."})

        # Multi-tenancy navigation check (if foreign rows are still present)
        if self.order_id:
            if self.product_id and self.product.shop_id != self.order.shop_id:
                raise ValidationError({"product": "Referenced product does not belong to the order's Shop."})
            if self.variant_id:
                if self.variant.product.shop_id != self.order.shop_id:
                    raise ValidationError({"variant": "Referenced variant does not belong to the order's Shop."})
                if self.product_id and self.variant.product_id != self.product_id:
                    raise ValidationError({"variant": "Referenced variant does not belong to the specified product."})

        # Calculate line total
        if self.unit_price_snapshot is not None and self.quantity is not None:
            self.line_total = (self.unit_price_snapshot * self.quantity).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)


class OrderDeliveryAddress(models.Model):
    """
    Frozen structured delivery address snapshot for Home Delivery orders.

    Tied 1-to-1 with Order. Created at checkout and immutable thereafter.
    Preserves historical destination regardless of customer profile updates or deletions.
    """

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_address",
    )
    recipient_name = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=16)

    address_line = models.CharField(max_length=255)
    area = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128)
    pincode = models.CharField(max_length=16)
    landmark = models.CharField(max_length=255, blank=True, default="")
    delivery_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Order Delivery Address"
        verbose_name_plural = "Order Delivery Addresses"
        constraints = [
            models.CheckConstraint(check=~Q(recipient_name=""), name="orders_address_recipient_required"),
            models.CheckConstraint(check=~Q(recipient_phone=""), name="orders_address_phone_required"),
            models.CheckConstraint(check=~Q(address_line=""), name="orders_address_line_required"),
            models.CheckConstraint(check=~Q(area=""), name="orders_address_area_required"),
            models.CheckConstraint(check=~Q(city=""), name="orders_address_city_required"),
            models.CheckConstraint(check=~Q(state=""), name="orders_address_state_required"),
            models.CheckConstraint(check=~Q(pincode=""), name="orders_address_pincode_required"),
        ]

    def __str__(self) -> str:
        return f"Delivery Address for Order #{self.order_id}: {self.address_line}, {self.city} - {self.pincode}"

    def clean(self) -> None:
        super().clean()
        # Enforce that pickup orders must not have a delivery address
        if self.order_id and self.order.fulfillment_type == Order.FulfillmentType.PICKUP:
            raise ValidationError({"order": "Pickup orders must not have a delivery address."})

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)
