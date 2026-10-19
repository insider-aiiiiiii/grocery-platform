# ADR 0003: Order Snapshots, Historical Immutability, and Reference Deletion Constraints

## Status
Approved

## Context

The Grocery Platform backend is a Django modular monolith serving multi-tenant grocery stores. The Orders domain owns historical purchase transactions following checkout.

Per `.ai/project-context/domains/orders.md` (§5, §6, §7, §8, §9, §10, §11, §12, §31, §37), `.ai/project-context/business-rules.md` (§4, §10, §14, §15, §16, §24, §25, §26), and `.ai/project-context/customer-order-history-access.md` (§12):
1. **Historical Immutability**:
   - An Order represents what was actually ordered and agreed upon at checkout.
   - Subsequent changes to product titles, variant attributes, catalog selling prices, merchant delivery fees, or customer profiles must **never** alter or corrupt existing orders.
2. **Catalog & Customer Evolution**:
   - Merchants may edit, discontinue, or permanently delete `ShopProduct` and `ProductVariant` records.
   - Customers may change their display name or update their saved addresses.
   - Merchants may update their delivery charge policy or fee amount.
3. **Shop Deletion Boundary**:
   - Super Admin permanent deletion of a Shop permanently deletes that Shop's Orders and Shop Products (`business-rules.md` §4, §26).
   - Shop deletion preserves the Merchant account and Customer identities.
4. **Fulfillment Distinction**:
   - Pickup requires customer name and WhatsApp contact, but **no delivery address**.
   - Home Delivery requires customer name, WhatsApp contact, and a **mandatory delivery address**.
5. **Gated Technical Implementation**:
   - While the business requirements for immutable snapshots were approved in concept, the exact schema fields, reference relationships, deletion constraints (`on_delete`), address snapshot structure, and retention boundaries remained open technical decisions.

## Problem

If the `Order` and `OrderItem` models rely on live joins to foreign tables (`catalog_shopproduct`, `catalog_productvariant`, `customers_customer`, `shops_shop`) to display purchase information:
1. **Data Corruption via Mutation**: If a merchant renames "Aashirvaad Atta 5kg" to "Aashirvaad Select Atta 5kg" or increases the price from ₹250 to ₹290, past orders would retroactively display the new name and distorted totals.
2. **Cascade Deletion Vulnerability**: If `OrderItem` foreign keys to `ShopProduct` or `ProductVariant` used `on_delete=models.CASCADE`, deleting a discontinued product from the merchant catalog would delete historical financial and accounting order records.
3. **Address Drift**: If Home Delivery orders reference a mutable customer address record, a customer updating their home address for a new order would retroactively change the delivery destination recorded on past delivered orders.
4. **Scope Desynchronization**: Redundant or uncoordinated foreign keys (e.g. independently specifying `shop_id` and `customer_id` where the customer belongs to a different shop) could compromise multi-tenant isolation.

## Alternatives Considered

### Alternative 1: Pure Relational Joins with Soft-Delete Everywhere
- **Mechanics**: Never delete catalog products, variants, or addresses. Use `is_deleted` flags everywhere and join live rows to render orders.
- **Drawbacks**: Does not solve price or title changes (requires versioned history tables for all catalog models). Adds query complexity, leaks soft-deleted items into active search unless filtered, and violates simplicity guidelines (Ponytail Minimalist Principle).

### Alternative 2: Raw Monolithic JSON Document Blob
- **Mechanics**: Store the entire order payload as a single unstructured `JSONField` blob on `Order` with no relational line items.
- **Drawbacks**: Prevents relational integrity, indexing, efficient merchant reporting (e.g. sales per product), database check constraints on decimal quantities/prices, and foreign-key navigation.

### Alternative 3: Hybrid Normalized Relations with Frozen Snapshot Fields (Selected)
- **Mechanics**:
  1. Maintain relational foreign keys for navigation, tenant scoping, and indexing, configured with safe deletion behaviors (`SET_NULL` for catalog items, `PROTECT` for customer profiles, `CASCADE` for shop-level deletion).
  2. Embed immutable snapshot fields directly into `Order` and `OrderItem` for all commercial data (product name, variant name, SKU, unit, unit price, quantity, delivery fee, customer name, WhatsApp number, and structured delivery address).
  3. Derive all order totals, line totals, customer history displays, and merchant fulfillment views exclusively from the snapshot fields.

## Decision

We adopt **Alternative 3: Hybrid Normalized Relations with Frozen Snapshot Fields**.

### 1. Product & Variant Identity and Snapshot Architecture

`OrderItem` captures the exact commercial state of the ordered product at checkout:

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `order` | `ForeignKey('Order', on_delete=models.CASCADE, related_name='items')` | Owning order. |
| `product` | `ForeignKey('catalog.ShopProduct', on_delete=models.SET_NULL, null=True, blank=True)` | Navigational link. Deleting the product does not delete historical line items. |
| `variant` | `ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)` | Optional navigational link. Deleting the variant does not delete historical line items. |
| `product_name_snapshot` | `CharField(max_length=255)` | Frozen product title at purchase. |
| `variant_name_snapshot` | `CharField(max_length=255, blank=True, default='')` | Frozen variant label (e.g., "1 kg", "Pack of 2") or empty string if non-variant. |
| `sku_snapshot` | `CharField(max_length=128, blank=True, default='')` | Merchant SKU at purchase. |
| `unit_snapshot` | `CharField(max_length=32, blank=True, default='')` | Sellable unit (e.g., "kg", "g", "piece", "packet"). |
| `attributes_snapshot` | `JSONField(default=dict, blank=True)` | Key-value dictionary of variant attribute snapshots (e.g. `{"weight": "500g", "brand": "Fortune"}`). |

### 2. Quantities, Prices, and Recalculation Mechanics

- **Quantity Fields**:
  - `ordered_quantity`: `DecimalField(max_digits=12, decimal_places=3)`. The original quantity ordered at checkout. Immutable.
  - `quantity`: `DecimalField(max_digits=12, decimal_places=3)`. The active fulfillable quantity. Initialized to `ordered_quantity`. If Merchant manually performs a partial quantity reduction before acceptance, `quantity` is adjusted (`0 <= quantity <= ordered_quantity`).
- **Pricing Fields**:
  - `unit_price_snapshot`: `DecimalField(max_digits=10, decimal_places=2)`. Unit selling price at checkout time.
  - `line_total`: `DecimalField(max_digits=12, decimal_places=2)`. Computed as `(unit_price_snapshot * quantity).quantize(Decimal('0.01'))`.
- **Order Totals**:
  - `items_subtotal`: `DecimalField(max_digits=12, decimal_places=2)`. Sum of all item `line_total` amounts. Recalculated if Merchant reduces quantities.
  - `delivery_charge_snapshot`: `DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))`.
  - `total_amount`: `DecimalField(max_digits=12, decimal_places=2)`. Computed as `items_subtotal + delivery_charge_snapshot`.
  - **No Tax or Discounts**: MVP excludes tax calculations and discount engines per canonical rules.

### 3. Delivery Charge Snapshot

`Order` preserves the shop's delivery policy and fee at checkout:
- `delivery_fee_type_snapshot`: `CharField(max_length=24, choices=[('FIXED', 'Fixed Fee'), ('CONFIRMED_ON_WHATSAPP', 'Fee Confirmed on WhatsApp')])`.
- `delivery_charge_snapshot`: `DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))`.
  - If `FIXED`: Preserves the shop's delivery charge (including ₹0.00 for free delivery).
  - If `CONFIRMED_ON_WHATSAPP`: Recorded as `Decimal('0.00')`; checkout displays notice that fee will be communicated directly via WhatsApp, and fee is settled out of band.
- Subsequent changes to Shop delivery fee settings have zero impact on existing orders.

### 4. Customer Contact and Fulfillment Snapshots

- **Customer References**:
  - `shop`: `ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='orders')`.
  - `customer`: `ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='orders')`.
  - Multi-tenant constraint: `customer.shop_id == order.shop_id`.
- **Customer Snapshots**:
  - `customer_name_snapshot`: `CharField(max_length=255)`. Name supplied at checkout.
  - `customer_phone_snapshot`: `CharField(max_length=16)`. Normalized E.164 WhatsApp number at checkout.
- **Fulfillment Choice**:
  - `fulfillment_type`: `CharField(max_length=16, choices=[('PICKUP', 'Pickup'), ('HOME_DELIVERY', 'Home Delivery')])`.

### 5. Delivery Address Snapshot Architecture

- **Pickup**:
  - Does **not** require and does **not** store an address snapshot (`delivery_address` is null).
- **Home Delivery**:
  - Requires an immutable delivery address snapshot.
  - Modeled as an immutable `OrderDeliveryAddress` model 1-to-1 with `Order` (`on_delete=models.CASCADE`):
    - `order`: `OneToOneField('Order', on_delete=models.CASCADE, related_name='delivery_address')`
    - `recipient_name`: `CharField(max_length=255)`
    - `recipient_phone`: `CharField(max_length=16)`
    - `address_line`: `CharField(max_length=255)` (Street address, flat, house number)
    - `area`: `CharField(max_length=128)` (Locality, neighborhood)
    - `city`: `CharField(max_length=128)`
    - `state`: `CharField(max_length=128)`
    - `pincode`: `CharField(max_length=16)`
    - `landmark`: `CharField(max_length=255, blank=True, default='')`
    - `delivery_notes`: `TextField(blank=True, default='')`
  - This record is created strictly upon checkout and is never updated thereafter.

### 6. Deletion Constraints Matrix

| Parent Model | Relational Field | `on_delete` Setting | Business Justification |
| :--- | :--- | :--- | :--- |
| `shops.Shop` | `Order.shop` | `CASCADE` | Approved lifecycle rule (`business-rules.md` §4, §26): Super Admin permanent deletion of a Shop permanently removes its Orders and Shop Products. |
| `customers.Customer` | `Order.customer` | `PROTECT` | Prevents deleting an active customer profile while historical order records exist (unless the entire Shop is deleted). |
| `catalog.ShopProduct` | `OrderItem.product` | `SET_NULL` (`null=True`) | Deleting a catalog product disassociates the FK but preserves the line item; snapshots retain full historical meaning. |
| `catalog.ProductVariant` | `OrderItem.variant` | `SET_NULL` (`null=True`) | Deleting a variant disassociates the FK but preserves the line item; snapshots retain full historical meaning. |
| `Order` | `OrderItem.order` | `CASCADE` | Deleting an order removes its constituent line items. |
| `Order` | `OrderDeliveryAddress.order`| `CASCADE` | The address snapshot is owned by and tied to the lifecycle of the order. |

### 7. Unresolved Fields and Lifecycle Retention Recorded

The following are explicitly recorded as open items for future phases:
1. **GPS Coordinates**: Optional `latitude` and `longitude` fields on delivery addresses are deferred until map/routing integration is approved.
2. **Multi-Currency**: Fixed to Indian Rupee (INR / ₹) for MVP.
3. **Statutory Data Retention**: Orders are retained as long as the Shop exists. Specific statutory data archiving or purging policies (e.g. 7-year tax retention) remain pending Product Owner and Legal review.
4. **Saved Address Management**: The Customers domain may optionally support saved addresses in future tasks, but Order delivery address snapshots remain strictly immutable copies independent of saved address CRUD.

## Consequences

### Positive
- Guarantees 100% immutable historical purchase data across product renaming, price adjustments, catalog deletions, and customer profile updates.
- Protects historical accounting and fulfillment records from accidental cascade deletions when catalog products or variants are removed.
- Prevents cross-shop tenant contamination by enforcing strict Shop ownership.
- Clean separation between Pickup (zero address storage) and Home Delivery (structured immutable snapshot).

### Trade-offs / Limitations
- Duplicate storage of text strings (names, SKUs, addresses) in snapshot columns; negligible storage cost in modern PostgreSQL compared to the safety of immutable historical records.
- When a product is deleted, navigational links from historical orders to catalog management pages become `null` (by design, to reflect that the live product no longer exists).
