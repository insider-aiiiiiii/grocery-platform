from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from customers.models import Customer
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from shops.models import Shop


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


def get_platform_shop_metrics(shop_id: int | None = None) -> dict:
    """
    Computes platform-level shop counts (total, active, deactivated).
    If shop_id is specified, computes status breakdown for that specific shop.
    """
    if shop_id is not None:
        shop = Shop.objects.filter(id=shop_id).first()
        if not shop:
            raise ValidationError(f"Shop with id {shop_id} does not exist.")
        return {
            "total_shops": 1,
            "active_shops": 1 if shop.status == Shop.Status.ACTIVE else 0,
            "deactivated_shops": 1 if shop.status == Shop.Status.DEACTIVATED else 0,
        }

    total_shops = Shop.objects.count()
    active_shops = Shop.objects.filter(status=Shop.Status.ACTIVE).count()
    deactivated_shops = Shop.objects.filter(status=Shop.Status.DEACTIVATED).count()

    return {
        "total_shops": total_shops,
        "active_shops": active_shops,
        "deactivated_shops": deactivated_shops,
    }


def get_platform_order_metrics(start_dt: datetime, end_dt: datetime, shop_id: int | None = None) -> dict:
    """
    Aggregates order metrics across the entire platform (or scoped to shop_id if provided).
    Strictly calculates realized sales and AOV only on COMPLETED orders.
    """
    qs = Order.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt)
    if shop_id is not None:
        qs = qs.filter(shop_id=shop_id)

    aggregates = qs.aggregate(
        total_orders=Count("id"),
        pending_orders=Count("id", filter=Q(status=Order.Status.PENDING)),
        accepted_orders=Count("id", filter=Q(status=Order.Status.ACCEPTED)),
        preparing_orders=Count("id", filter=Q(status=Order.Status.PREPARING)),
        ready_orders=Count("id", filter=Q(status=Order.Status.READY)),
        completed_orders=Count("id", filter=Q(status=Order.Status.COMPLETED)),
        rejected_orders=Count("id", filter=Q(status=Order.Status.REJECTED)),
        realized_sales=Coalesce(
            Sum("total_amount", filter=Q(status=Order.Status.COMPLETED)),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )

    total_orders = aggregates["total_orders"] or 0
    completed_orders = aggregates["completed_orders"] or 0
    rejected_orders = aggregates["rejected_orders"] or 0
    realized_sales = Decimal(str(aggregates["realized_sales"] or 0)).quantize(Decimal("0.01"))

    if completed_orders > 0:
        aov = (realized_sales / Decimal(completed_orders)).quantize(Decimal("0.01"))
    else:
        aov = Decimal("0.00")

    status_distribution = {
        Order.Status.PENDING: aggregates["pending_orders"] or 0,
        Order.Status.ACCEPTED: aggregates["accepted_orders"] or 0,
        Order.Status.PREPARING: aggregates["preparing_orders"] or 0,
        Order.Status.READY: aggregates["ready_orders"] or 0,
        Order.Status.COMPLETED: completed_orders,
        Order.Status.REJECTED: rejected_orders,
    }

    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "rejected_orders": rejected_orders,
        "status_distribution": status_distribution,
        "realized_sales": str(realized_sales),
        "average_order_value": str(aov),
    }


def get_platform_customer_metrics(start_dt: datetime, end_dt: datetime, shop_id: int | None = None) -> dict:
    """
    Computes distinct ordering customer count on completed orders across the platform
    (or scoped to shop_id if specified).
    Preserves strict platform privacy: returns only aggregated count with zero customer PII.
    """
    qs = Order.objects.filter(
        status=Order.Status.COMPLETED,
        created_at__gte=start_dt,
        created_at__lte=end_dt,
    )
    if shop_id is not None:
        qs = qs.filter(shop_id=shop_id)

    ordering_customers = qs.values("customer_id").distinct().count()

    return {
        "ordering_customers": ordering_customers,
    }


def get_platform_top_products(
    start_dt: datetime, end_dt: datetime, shop_id: int | None = None, limit: int = 10
) -> list[dict]:
    """
    Retrieves top-selling products across all shops on COMPLETED orders,
    grouped by immutable snapshot fields to preserve historical accuracy.
    """
    qs = OrderItem.objects.filter(
        order__status=Order.Status.COMPLETED,
        order__created_at__gte=start_dt,
        order__created_at__lte=end_dt,
    )
    if shop_id is not None:
        qs = qs.filter(order__shop_id=shop_id)

    items_qs = (
        qs.values(
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


def get_platform_top_shops(start_dt: datetime, end_dt: datetime, limit: int = 10) -> list[dict]:
    """
    Retrieves top performing shops ranked by realized sales and completed orders in the period.
    """
    shops_qs = (
        Order.objects.filter(
            status=Order.Status.COMPLETED,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        )
        .values("shop_id", "shop__name")
        .annotate(
            completed_orders=Count("id"),
            realized_sales=Sum("total_amount"),
        )
        .order_by("-realized_sales", "-completed_orders")[:limit]
    )

    top_shops = []
    for s in shops_qs:
        sales = Decimal(str(s["realized_sales"] or 0)).quantize(Decimal("0.01"))
        top_shops.append({
            "shop_id": s["shop_id"],
            "shop_name": s["shop__name"],
            "completed_orders": s["completed_orders"],
            "realized_sales": str(sales),
        })

    return top_shops


def get_platform_analytics_overview(query_params: dict) -> dict:
    """
    Coordinates direct domain queries to produce the complete Platform Analytics Overview
    for authorized Super Admins.
    """
    period, start_dt, end_dt = parse_date_range(query_params)
    shop_id = query_params.get("shop_id")
    if shop_id is not None:
        try:
            shop_id = int(shop_id)
        except (ValueError, TypeError) as exc:
            raise ValidationError("Invalid shop_id format.") from exc

    shop_metrics = get_platform_shop_metrics(shop_id=shop_id)
    order_metrics = get_platform_order_metrics(start_dt, end_dt, shop_id=shop_id)
    customer_metrics = get_platform_customer_metrics(start_dt, end_dt, shop_id=shop_id)
    top_products = get_platform_top_products(start_dt, end_dt, shop_id=shop_id, limit=5)
    top_shops = get_platform_top_shops(start_dt, end_dt, limit=5) if shop_id is None else []

    # Out of stock items count across platform
    inv_qs = InventoryItem.objects.filter(quantity__lte=F("reserved_quantity"))
    if shop_id is not None:
        inv_qs = inv_qs.filter(shop_id=shop_id)
    out_of_stock_count = inv_qs.count()

    response = {
        "period": period,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "shops": shop_metrics,
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
        "top_shops": top_shops,
    }

    if shop_id is not None:
        response["filtered_shop_id"] = shop_id

    return response
