# Grocery Platform Development Status

## 1. Purpose

This document records the checked-out repository's verified implementation state. A model, route, or test file existing does not mean its domain behavior is complete or approved. Business decisions remain governed by `business-rules.md` and the relevant domain specifications.

## 2. Current Stage

The project has a Django modular-monolith foundation and partial identity and Shop implementation. Catalog has a single Master Category model. Most business domains remain documentation-only or empty scaffolds. No end-to-end grocery ordering workflow is implemented.

The project uses Python, Django, and DRF. `backend/config/settings.py` uses PostgreSQL when `POSTGRES_DB` is set and otherwise falls back to SQLite. A live PostgreSQL connection was not verified. JWT configuration requires `JWT_SIGNING_KEY` at startup. An `.env.example` exists; no `.env` file is included in the repository. No dotenv-loading behavior was verified.

## 3. Verified Repository and Application State

| Area | Status | Verified state |
|---|---|---|
| Django project and app registration | Implemented foundation | `backend/config` and ten domain apps exist; Django, DRF, and apps are registered. |
| `users` models and migrations | Partially implemented | Custom `User`, `Merchant`, authenticated-session, Merchant recovery, and Super Admin recovery/throttle models exist. Migrations `users.0001` through `users.0007` exist. |
| `users` APIs | Partially implemented | `/api/v1/auth/` routes cover Merchant and Super Admin login, password change, Merchant recovery, Super Admin recovery and administrative reset, logout, and refresh. Merchant password change and the Super Admin administrative-reset request use explicit role permissions. External delivery adapters for recovery are configuration callbacks, not provider integrations. |
| `users` tests | Present | `tests.py` and `test_migrations.py` contain test classes, including role-denial coverage. Targeted tests could not execute under the local Django 5.0.6 because the existing Shops migration uses `CheckConstraint(condition=...)`, which that version does not accept. |
| `shops` model and migrations | Partially implemented | Shop model and migrations `shops.0001` and `shops.0002` exist. The model implements required profile fields, one-to-one Merchant linkage, status choices, delivery settings, a generated public slug, and status helper methods. Deleting a Shop removes the Shop row and preserves its Merchant profile and User credentials. |
| `shops` API | Partially implemented | Authenticated Merchant Shop creation (`POST /api/v1/shops/`), Merchant retrieval of their own Shop (`GET /api/v1/shops/me/`, alias `GET /api/v1/shops/`), and Merchant Shop profile updates (`PATCH`/`PUT` `/api/v1/shops/me/`, alias `PATCH`/`PUT` `/api/v1/shops/`) are routed under SHOP-004, SHOP-005, and SHOP-006 with strict server-derived context, field restrictions, and business-hours/fulfillment validation. There are no Merchant deactivation, Shop deactivation, Super Admin reactivation, deletion, or public QR/link resolution endpoints. |
| `shops` tests | Present | `backend/shops/tests.py` covers Shop creation, retrieval, and role denial. All 34 Shop tests, including deletion retention and replacement creation, passed under Django 5.2.5. The globally installed Django 5.0.6 cannot load the Shops migrations because it does not accept their `CheckConstraint(condition=...)` argument. |
| Shop deletion behavior | Partially implemented | Shop deletion preserves the Merchant profile and User credentials; the same Merchant can create a replacement Shop with a newly generated identity and public slug. No Shop Product, Order, or Customer models/relations exist in this checkout, so their deletion/retention behavior cannot yet be verified. No Super Admin deletion API is routed. |
| `catalog` | Minimal partial implementation | `MasterCategory` model and `catalog.0001` migration exist. No Shop Product, Variant, category API, serializer, or business workflow was found. No catalog-specific tests were found. |
| `inventory`, `customers`, `cart`, `orders`, `campaigns`, `notifications`, `analytics` | Documentation-only / scaffolded | Apps and generated files exist, but no domain models, migrations, APIs, serializers, or business workflows were found. Test modules contain no verified domain tests. |
| API coverage | Partial | Auth and Shop creation, retrieval, and update endpoints are routed under `/api/v1/`. No customer, catalog, inventory, cart, order, campaign, notification, or analytics APIs were found. |
| Role and tenant authorization | Partial / implemented for current Merchant Shop APIs | Shared `IsMerchant` and `IsSuperAdmin` permissions protect role-specific password-change and administrative-reset APIs; `IsActiveMerchant` protects Shop creation, retrieval, and updates. Current Merchant Shop reads and updates resolve through a database query constrained to the authenticated user's Merchant, and creation binds ownership server-side. Client `shop_id` values do not select or authorize a Shop. No public Shop API or Shop delete API is routed; other domain APIs and their tenant-scoped authorization are not implemented. |
| Authorization policy documentation | Documented | `.ai/project-context/authorization-matrix.md` consolidates actor/resource boundaries and distinguishes approved policy from implemented enforcement. Customer history-link authorization and most domain operations remain unimplemented; see the matrix for tests and open technical boundaries. |
| Database | Partial | Identity, Shop, and Master Category migrations exist. The rest of the domain schema is not implemented. No live database connection was verified. |
| Automated checks | Partial | `python manage.py check`, Python compilation, and the full Shops test module (34 tests) passed using Django 5.2.5 installed in a temporary directory outside the repository. The globally installed Django 5.0.6 is incompatible with the existing Shops migrations. No CI workflow was found. |
| Infrastructure | Not found | No Dockerfile/Compose setup, CI workflow, frontend, or external WhatsApp/payment integration was found. |

## 4. Business Decisions and Implementation Work

The documentation records the approved MVP direction for direct Super Admin Merchant creation, one Shop at a time per Merchant, Merchant account retention and a new isolated Shop identity after Shop deletion, Merchant Shop deactivation, Super Admin Shop reactivation, variant-authoritative stock, pending-order expiry, and customer-specific Order-history access links/tokens without OTP. Analytics/retention exclusions are also documented.

Those decisions are not implemented across the platform. In particular, Shop status and permanent deletion lack API workflows; Shop Product and Order deletion cannot be applied to absent models; inventory and Order lifecycle are unimplemented; and no customer-history access flow exists. Do not treat these documents as evidence of shipped functionality.

The Shop-deletion model behavior now preserves Merchant credentials, and tests cover Merchant account retention and replacement Shop creation. The approved deletion authority and safeguards are not exposed through an API, and domain models for Shop Products, Orders, and Customers are absent, so related data cleanup and Customer retention are not yet implemented or verified. No customer Order-history access flow exists.

Remaining technical design requirements include the Order-history access link/token expiry, revocation, generation, delivery, storage, and protections against unauthorized reuse; resource enforcement for unimplemented domain APIs; physical Shop deletion and tenant-isolation mechanics; catalog/inventory/Order schema and stock transaction design; pending Order timeout default and existing-state expiry representation; notification-history retention; and the remaining documented API, provider, and technical decisions. See `.ai/project-context/authorization-matrix.md` for the actor/resource policy and required future authorization tests.

## 5. Repository Boundaries

The architecture remains a Django modular monolith. PostgreSQL is the intended primary database, with a local SQLite fallback in settings. No repository-local Docker or CI infrastructure was found. Keep implementation status separate from documented product requirements and do not infer completeness from generated files.
