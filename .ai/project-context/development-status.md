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
| `users` APIs | Partially implemented | `/api/v1/auth/` routes cover Merchant and Super Admin login, password change, Merchant recovery, Super Admin recovery and administrative reset, logout, and refresh. External delivery adapters for recovery are configuration callbacks, not provider integrations. |
| `users` tests | Present | `tests.py` and `test_migrations.py` contain test classes. Their execution and pass status were not verified in this documentation review. |
| `shops` model and migrations | Partially implemented | Shop model and migrations `shops.0001` and `shops.0002` exist. The model implements required profile fields, one-to-one Merchant linkage, status choices, delivery settings, a generated public slug, status helper methods, and custom deletion behavior. |
| `shops` API | Partially implemented | Authenticated Merchant Shop creation (`POST /api/v1/shops/`) and Merchant retrieval of their own Shop (`GET /api/v1/shops/me/`, alias `GET /api/v1/shops/`) are routed under SHOP-004 and SHOP-005. There are no Shop update, Merchant deactivation, Shop deactivation, Super Admin reactivation, deletion, or public QR/link resolution endpoints. |
| `shops` tests | Present | `backend/shops/tests.py` contains tests. Execution and pass status were not verified here. |
| Shop deletion behavior | Implementation does not satisfy approved rule | `Shop.delete()` removes the Merchant profile and associated User credentials. Approved behavior preserves the Merchant account and credentials, allowing the same Merchant to create a replacement Shop with a new identity and public QR/link. Shop deletion must remove the old Shop Products and Orders without associating old Shop data with the replacement. The model behavior has not been updated to satisfy this decision. |
| `catalog` | Minimal partial implementation | `MasterCategory` model and `catalog.0001` migration exist. No Shop Product, Variant, category API, serializer, or business workflow was found. No catalog-specific tests were found. |
| `inventory`, `customers`, `cart`, `orders`, `campaigns`, `notifications`, `analytics` | Documentation-only / scaffolded | Apps and generated files exist, but no domain models, migrations, APIs, serializers, or business workflows were found. Test modules contain no verified domain tests. |
| API coverage | Partial | Auth and Shop creation and retrieval endpoints are routed under `/api/v1/`. No customer, catalog, inventory, cart, order, campaign, notification, or analytics APIs were found. |
| Tenant authorization | Partial / incomplete | `IsActiveMerchant` protects Shop creation and retrieval, and its serializer/view derives Merchant ownership strictly from the authenticated user. A complete Shop-scoped permission/queryset strategy across domains is not implemented. |
| Database | Partial | Identity, Shop, and Master Category migrations exist. The rest of the domain schema is not implemented. No live database connection was verified. |
| Automated checks | Not verified | Tests/checks were not run as part of this documentation task; no CI workflow was found. Existing test files are not evidence of passing behavior. |
| Infrastructure | Not found | No Dockerfile/Compose setup, CI workflow, frontend, or external WhatsApp/payment integration was found. |

## 4. Business Decisions and Implementation Work

The documentation records the approved MVP direction for direct Super Admin Merchant creation, one Shop at a time per Merchant, Merchant account retention and a new isolated Shop identity after Shop deletion, Merchant Shop deactivation, Super Admin Shop reactivation, variant-authoritative stock, pending-order expiry, and customer-specific Order-history access links/tokens without OTP. Analytics/retention exclusions are also documented.

Those decisions are not implemented across the platform. In particular, Shop status and deletion operations lack API workflows; inventory and Order lifecycle are unimplemented; and no customer-history access flow exists. Do not treat these documents as evidence of shipped functionality.

The Shop-deletion and customer Order-history business decisions are approved but not implemented. The current Shop deletion code removes Merchant credentials, contrary to the approved account-retention rule; Shop deletion behavior must be changed before it is implemented as a supported workflow. No customer Order-history access flow exists.

Remaining technical design requirements include the Order-history access link/token expiry, revocation, generation, delivery, storage, and protections against unauthorized reuse; complete Merchant/Super Admin authorization; physical Shop deletion and tenant-isolation mechanics; catalog/inventory/Order schema and stock transaction design; pending Order timeout default and existing-state expiry representation; notification-history retention; and the remaining documented API, provider, and technical decisions.

## 5. Repository Boundaries

The architecture remains a Django modular monolith. PostgreSQL is the intended primary database, with a local SQLite fallback in settings. No repository-local Docker or CI infrastructure was found. Keep implementation status separate from documented product requirements and do not infer completeness from generated files.
