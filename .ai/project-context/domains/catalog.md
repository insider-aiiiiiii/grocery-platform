# Catalog Domain Specification

## 1. Purpose and Ownership

The Catalog domain owns platform Master Catalog products and Shop Catalog products, product and variant information, Shop-specific pricing, categories, brands, custom attributes, product images, visibility, and catalog availability behavior.

Inventory owns quantities and stock movements. Catalog availability rules consume stock state without defining inventory implementation. Orders own order records and must retain the historical product information/references required for existing orders when a Shop Product is deleted.

## 2. Master Catalog and Shop Catalog

The **Master Catalog** is a platform-level reusable product library managed by Super Admin. The **Shop Catalog** is an independent catalog for each Shop, fully controlled by its Merchant. A Master Product is not itself a Shop's sellable product, and a Shop need not offer every Master Product.

A Merchant can add a product by selecting a Master Product or by creating a product directly in the Shop Catalog. Directly created products need no Super Admin approval and can be used and sold by that Shop. Super Admin may view product information on the dashboard and may promote a Merchant-created product into the Master Catalog. Promotion makes it available for other Merchants to select; it does not link, replace, or update the originating Shop Product.

Each Shop Product is an independent Shop-specific representation. A Master Product may be selected by multiple Shops, but its information does not control or automatically synchronize to their Shop Products. Merchants can independently customize all Shop Product information, including name, description, image, category, brand, attributes, price, variants, SKU, availability, and visibility. Deleting a Master Product does not delete or impair existing Shop Products.

Do not infer identity or automatically merge products from name, brand, category, or SKU. Master Products are identified by Master Product ID. Duplicate product names are allowed, and selecting a Master Product does not automatically merge it with a separately created Merchant product.

## 3. Products and Variants

A Shop Product may be directly sellable without variants or may have multiple variants. Both product-level and variant-level information are supported. Merchants can create, edit, and delete variants, including variant name, image, price, SKU, and custom attributes. A Merchant may add Shop-specific variants to a Shop Product selected from the Master Catalog.

Products support name, description, image, category, and brand. A product may exist without an image. No product-name uniqueness rule is defined.

## 4. Product Images

MVP supports one image per product and an optional image per variant. When a variant has no image, it can use the product image. Merchants can replace or delete images. A primary image is supported when an image exists. Image galleries are not part of the finalized requirements.

## 5. Shop-specific Product Data

### SKU

The Merchant enters and may change SKU values. SKUs do not need to be unique; duplicate SKUs, including across variants, are allowed.

### Pricing

Pricing is Shop-specific and controlled by the Merchant. A non-variant product can have a price; variant products support prices at both product and variant level. Prices support decimal values. Different Shops may set different prices for the same Master Product. Master Catalog pricing does not control Shop prices.

### Categories

Categories belong to the Shop Catalog. Merchants have CRUD control and can create subcategories. A product may belong to multiple categories. A Merchant may delete a category that has assigned products; those products remain and become uncategorized.

### Brands and custom attributes

Merchants control brands within their Shop Catalog and may customize a selected Master Product's brand independently. Merchants can create and manage custom attributes. Products may have multiple attributes with multiple values; variants may also have their own custom attributes. No fixed global attribute system is defined.

## 6. Visibility, Availability, and Stock

The Merchant controls product visibility and may temporarily hide or re-show a product. Hidden products are not visible to customers and cannot be ordered.

Manual availability is separate from inventory quantity. A Merchant may mark a product manually unavailable; it remains in the catalog but cannot be ordered.

An out-of-stock product remains visible, is shown as **Out of Stock**, and cannot be ordered. For products with variants, customers see only available variants. If all variants are unavailable or out of stock, the main product shows **Out of Stock**. Do not hide the entire product only because its inventory is zero.

## 7. Customer-facing Catalog

Customers can see a Shop Product's name, description, brand, attributes, SKU, images, available variants, and applicable price. Hidden products are not shown. Out-of-stock and manually unavailable products cannot be ordered.

Customer-facing catalog requests resolve within the intended Shop. A Shop's catalog information must not expose another Shop's products or private catalog data.

## 8. Product Deletion and Historical Orders

Merchants can delete Shop Products. Deletion does not affect the Master Product or another Shop's product. Historical Orders must retain the product information or references they require after the current Shop Product is deleted. The physical retention and snapshot strategy remains an implementation decision.

## 9. Permissions and Governance

Super Admin manages the platform Master Catalog and may view dashboard information about Merchant-created products and choose to promote them. No product approval, rejection, or resubmission workflow exists. Merchants have full control over their own Shop Catalog, subject to Shop tenant isolation. These business rules do not select an authentication or authorization implementation.

## 10. Related Domains

- **Shops** owns Shop identity and tenancy; each Shop has its own Catalog.
- **Inventory** owns stock quantities and movements; manual availability is a separate Catalog concept.
- **Cart** consumes Shop-specific products, variants, and applicable prices.
- **Orders** preserve historical product information/references needed for existing Orders.
- **Customers** access only the intended Shop's customer-facing Catalog.

## 11. Decisions Finalized and Implementation Status

Catalog business decisions described in this document are finalized. This document does not prescribe model names, database cardinalities beyond stated business relationships, field types, storage mechanisms, APIs, authentication, authorization implementation, or migration design. Catalog implementation has not started; do not infer that models, migrations, APIs, tests, or frontend work are complete.

Remaining technical details include the physical representation of independent Shop Products and optional Master Product selection, product/variant schema, attribute representation, image storage, inventory mapping, and historical Order snapshot/reference strategy.
