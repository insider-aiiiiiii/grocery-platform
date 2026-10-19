from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem


def parse_date_range(query_params: dict) -> tuple[str, datetime, datetime]:
    """
    Parses and standardizes query parameters into inclusive UTC datetime boundaries.
    Supported periods:
    - 'today': Current UTC day 00:00:00 to 23:59:59.999999.
    - 'yesterday': Previous UTC day 00:00:00 to 23:59:59.999999.
    - 'this_week': Monday 00:00:00 to Sunday 23:59:59.999999 of current week UTC.
    - 'this_month': 1st of current month to last day of current month in UTC.
    - 'custom': Explicit start_date and end_date (YYYY-MM-DD).

    Defaults to 'today' if period is omitted or empty.
    """
    period = (query_params.get("period") or "today").strip().lower()
    now_utc = timezone.now()
    today_utc = now_utc.date()

    if period == "today":
        start_date = today_utc
        end_date = today_utc
    elif period == "yesterday":
        start_date = today_utc - timedelta(days=1)
        end_date = start_date
    elif period == "this_week":
        # Monday is 0, Sunday is 6
        start_date = today_utc - timedelta(days=today_utc.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == "this_month":
        start_date = today_utc.replace(day=1)
        # Find next month 1st day then subtract 1 day
        if start_date.month == 12:
            next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
        else:
            next_month = start_date.replace(month=start_date.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
    elif period == "custom":
        start_val = query_params.get("start_date")
        end_val = query_params.get("end_date")

        if not start_val or not end_val:
            raise ValidationError("Both 'start_date' and 'end_date' are required when period='custom'.")

        try:
            if isinstance(start_val, date):
                start_date = start_val
            else:
                start_date = date.fromisoformat(str(start_val).strip())

            if isinstance(end_val, date):
                end_date = end_val
            else:
                end_date = date.fromisoformat(str(end_val).strip())
        except (ValueError, TypeError) as exc:
            raise ValidationError("Dates must be in ISO-8601 format (YYYY-MM-DD).") from exc

        if start_date > end_date:
            raise ValidationError("'start_date' cannot be after 'end_date'.")
    else:
        raise ValidationError(
            f"Unsupported period '{period}'. Supported periods are: today, yesterday, this_week, this_month, custom."
        )

    # Convert date boundaries to inclusive timezone-aware UTC datetimes
    start_dt = datetime.combine(start_date, time.min, tzinfo=dt_timezone.utc)
    end_dt = datetime.combine(end_date, time.max, tzinfo=dt_timezone.utc)

    return period, start_dt, end_dt


def get_merchant_order_metrics(shop_id: int, start_dt: datetime, end_dt: datetime) -> dict:
    """
    Computes order volume, status breakdown, realized sales, and average order value (AOV)
    for the designated shop within the specified time boundaries.
    """
    zero_dec = Decimal("0.00")

    agg = Order.objects.filter(
        shop_id=shop_id,
        created_at__gte=start_dt,
        created_at__lte=end_dt,
    ).aggregate(
        total_orders=Count("id"),
        pending_orders=Count("id", filter=Q(status=Order.Status.PENDING)),
        accepted_orders=Count("id", filter=Q(status=Order.Status.ACCEPTED)),
        preparing_orders=Count("id", filter=Q(status=Order.Status.PREPARING)),
        ready_orders=Count("id", filter=Q(status=Order.Status.READY)),
        completed_orders=Count("id", filter=Q(status=Order.Status.COMPLETED)),
        rejected_orders=Count("id", filter=Q(status=Order.Status.REJECTED)),
        realized_sales=Coalesce(
            Sum("total_amount", filter=Q(status=Order.Status.COMPLETED)),
            zero_dec,
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )

    completed_count = agg["completed_orders"] or 0
    realized_sales = Decimal(str(agg["realized_sales"] or 0)).quantize(Decimal("0.01"))

    if completed_count > 0:
        aov = (realized_sales / Decimal(completed_count)).quantize(Decimal("0.01"))
    else:
        aov = Decimal("0.00")

    return {
        "total_orders": agg["total_orders"] or 0,
        "completed_orders": completed_count,
        "rejected_orders": agg["rejected_orders"] or 0,
        "status_distribution": {
            Order.Status.PENDING: agg["pending_orders"] or 0,
            Order.Status.ACCEPTED: agg["accepted_orders"] or 0,
            Order.Status.PREPARING: agg["preparing_orders"] or 0,
            Order.Status.READY: agg["ready_orders"] or 0,
            Order.Status.COMPLETED: completed_count,
            Order.Status.REJECTED: agg["rejected_orders"] or 0,
        },
        "realized_sales": str(realized_sales),
        "average_order_value": str(aov),
    }


def get_merchant_customer_metrics(shop_id: int, start_dt: datetime, end_dt: datetime) -> dict:
    """
    Computes active ordering customers in the period and returning customer counts
    strictly scoped to the specified shop.
    """
    # Distinct customers who placed at least one COMPLETED order in the period
    ordering_customers = (
        Order.objects.filter(
            shop_id=shop_id,
            status=Order.Status.COMPLETED,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        )
        .values("customer_id")
        .distinct()
        .count()
    )

    # Distinct customers with 2 or more lifetime COMPLETED orders in this shop
    returning_customers = (
        Customer.objects.filter(
            shop_id=shop_id,
            orders__status=Order.Status.COMPLETED,
        )
        .annotate(completed_orders_count=Count("orders"))
        .filter(completed_orders_count__gte=2)
        .count()
    )

    return {
        "ordering_customers": ordering_customers,
        "returning_customers": returning_customers,
    }


def get_merchant_top_products(shop_id: int, start_dt: datetime, end_dt: datetime, limit: int = 5) -> list[dict]:
    """
    Retrieves the top-selling products for the shop by quantity sold on COMPLETED orders,
    grouped by immutable snapshot fields to guarantee historical accuracy.
    """
    items_qs = (
        OrderItem.objects.filter(
            order__shop_id=shop_id,
            order__status=Order.Status.COMPLETED,
            order__created_at__gte=start_dt,
            order__created_at__lte=end_dt,
        )
        .values(
            "product_id",
            "variant_id",
            "product_name_snapshot",
            "variant_name_snapshot",
            "sku_snapshot",
        )
        .annotate(
            units_sold=Sum("quantity"),
            total_revenue=Sum("line_total"),
        )
        .order_by("-units_sold")[:limit]
    )

    top_products = []
    for item in items_qs:
        units = Decimal(str(item["units_sold"] or 0)).quantize(Decimal("0.001"))
        rev = Decimal(str(item["total_revenue"] or 0)).quantize(Decimal("0.01"))
        top_products.append({
            "product_id": item["product_id"],
            "variant_id": item["variant_id"],
            "product_name": item["product_name_snapshot"],
            "variant_name": item["variant_name_snapshot"] or "",
            "sku": item["sku_snapshot"] or "",
            "units_sold": str(units),
            "total_revenue": str(rev),
        })

    return top_products


def get_merchant_low_stock_items(shop_id: int) -> list[dict]:
    """
    Returns items currently Out of Stock (available_quantity <= 0.000).
    Strictly follows MVP rule: no arbitrary low-stock threshold is invented.
    """
    low_stock_qs = InventoryItem.objects.filter(
        shop_id=shop_id,
        quantity__lte=F("reserved_quantity"),
    ).select_related("product", "variant").order_by("id")

    items = []
    for inv in low_stock_qs:
        if inv.variant is not None:
            name = f"{inv.product.name} ({inv.variant.name})"
            sku = inv.variant.sku
        else:
            name = inv.product.name
            sku = inv.product.sku

        items.append({
            "inventory_id": inv.id,
            "product_id": inv.product_id,
            "variant_id": inv.variant_id,
            "name": name,
            "sku": sku,
            "quantity": str(inv.quantity),
            "reserved_quantity": str(inv.reserved_quantity),
            "available_quantity": str(inv.available_quantity),
            "is_out_of_stock": True,
        })

    return items


def get_merchant_analytics_overview(shop_id: int, query_params: dict) -> dict:
    """
    Coordinates direct domain queries to produce the complete Merchant Shop Analytics Overview.
    """
    period, start_dt, end_dt = parse_date_range(query_params)
    order_metrics = get_merchant_order_metrics(shop_id, start_dt, end_dt)
    customer_metrics = get_merchant_customer_metrics(shop_id, start_dt, end_dt)
    top_products = get_merchant_top_products(shop_id, start_dt, end_dt, limit=5)

    # Low-stock count reflects current real-time out of stock items
    out_of_stock_count = InventoryItem.objects.filter(
        shop_id=shop_id,
        quantity__lte=F("reserved_quantity"),
    ).count()

    return {
        "period": period,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "orders": {
            "total_orders": order_metrics["total_orders"],
            "completed_orders": order_metrics["completed_orders"],
            "rejected_orders": order_metrics["rejected_orders"],
            "status_distribution": order_metrics["status_distribution"],
        },
        "sales": {
            "realized_sales": order_metrics["realized_sales"],
            "average_order_value": order_metrics["average_order_value"],
        },
        "customers": customer_metrics,
        "inventory": {
            "out_of_stock_items_count": out_of_stock_count,
        },
        "top_products": top_products,
    }
