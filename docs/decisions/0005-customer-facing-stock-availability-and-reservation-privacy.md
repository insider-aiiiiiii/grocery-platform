# ADR 0005: Customer-Facing Stock Availability, Out-of-Stock Catalog Behavior, and Reservation Privacy

## Status
Approved

## Context

The grocery platform backend is a Django modular monolith serving multi-tenant grocery stores.
- Catalog owns Shop Product and Variant definitions, visibility, and presentation.
- Inventory owns stock quantities, reservation state, and availability calculation.
- Customers interact with the platform through public catalog endpoints addressed by a Shop's `public_slug`.

Per `.ai/project-context/domains/inventory.md` (§7, §10), `.ai/project-context/domains/catalog.md` (§6, §7), and `.ai/project-context/domains/cart.md`:
1. **Exact Available Stock Exposure**:
   - Customers must see the exact available quantity: $\text{Available Quantity} = \max(0, \text{Quantity} - \text{Reserved Quantity})$.
   - Product-level stock for variant-based products is an aggregate derived from visible variant available quantities.
2. **Out of Stock Behavior**:
   - When available quantity reaches zero, the product is displayed as **Out of Stock**.
   - Out-of-stock products **remain visible** in public catalog listings and detail views; they are not hidden from the catalog.
   - Ordering is blocked when available quantity is zero (`is_orderable = False`).
   - For products with variants: customers see available variants; if all variants are out of stock (or manually unavailable), the parent product shows **Out of Stock** while remaining visible in the catalog.
3. **Reservation Confidentiality**:
   - Internal `reserved_quantity` is strictly merchant/internal data.
   - Customers must never see how much stock is reserved by other customers' pending orders, nor raw unreserved on-hand balances.

## Problem

1. **Information Leakage**: Exposing `reserved_quantity` or raw on-hand `quantity` would reveal commercial business data (e.g. pending order volume or total warehouse stock) to competitors and customers.
2. **Conflation of Visibility and Availability**: Hiding products when stock reaches zero would break customer discovery, bookmarking, and repeat browsing. Catalog visibility (`is_visible`) must remain strictly decoupled from inventory availability.
3. **Overselling Prevention**: If customer endpoints or cart workflows do not enforce available stock checks, customers could order goods that are already reserved by earlier shoppers.

## Decision

We adopt **Decoupled Customer-Facing Available Stock Exposure with Reservation Privacy and Out-of-Stock Catalog Retention**:

### 1. Representation & Attributes
- Public serializers (`PublicShopProductSerializer` and `PublicProductVariantSerializer`) expose:
  - `available_quantity`: Exact real-time available stock ($\max(0, Q - R)$).
  - `stock_quantity`: String representation matching `available_quantity` (for backward compatibility).
  - `is_out_of_stock`: Boolean indicator (`available_quantity <= 0.000`).
  - `display_status`: String enum: `"AVAILABLE"`, `"OUT_OF_STOCK"`, `"UNAVAILABLE"`, `"HIDDEN"`.
  - `is_orderable`: Boolean indicator (`is_visible and is_available and available_quantity > 0`).
- Public serializers **strictly omit**:
  - `reserved_quantity`
  - `reserved_stock`
  - raw on-hand `quantity`

### 2. Catalog Retention for Out-of-Stock Items
- Customer queries (`PublicShopProductListView`, `PublicShopProductDetailView`, `PublicShopCatalogSummaryView`) filter exclusively on `is_visible=True` and `shop.status == ACTIVE`.
- Products with `available_quantity == 0` remain visible in list and detail views with `display_status="OUT_OF_STOCK"` and `is_out_of_stock=True`.
- For variant products, if all variants have zero available stock, the product remains visible with `display_status="OUT_OF_STOCK"` and `is_out_of_stock=True`.

### 3. Order Blocking
- When `available_quantity == 0`, `is_orderable` is `False`.
- Cart addition and cart validation (`validate_product_orderable_and_available` and `validate_cart_state`) reject any item whose requested quantity exceeds available stock or if the item is out of stock.

## Consequences

### Positive
- Transparent stock visibility for shoppers without revealing private commercial reservation metrics.
- Preserves catalog discovery for out-of-stock items without allowing unfulfillable orders.
- Prevents race conditions and overselling by grounding availability strictly in $\max(0, Q - R)$.
- Multi-tenant isolation is preserved.

### Trade-offs / Limitations
- Requires joining or mapping `InventoryItem` records during public catalog serialization. Optimized through batch dictionary lookups (`stock_map`).
