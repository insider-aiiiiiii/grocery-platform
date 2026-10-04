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
| `shops` API | Partially implemented | Only authenticated Merchant Shop creation (`POST /api/v1/shops/`) is routed. There are no Shop read/update, Merchant deactivation, Shop deactivation, Super Admin reactivation, deletion, or public QR/link resolution endpoints. |
| `shops` tests | Present | `backend/shops/tests.py` contains tests. Execution and pass status were not verified here. |
| Shop deletion behavior | Implementation/documentation discrepancy | `Shop.delete()` removes the Merchant profile and associated User credentials. The reconciled business rules require the same Merchant to be able to create a replacement Shop, leaving credential survival unresolved for approval. The implementation does not yet satisfy a settled rule for this case. |
| `catalog` | Minimal partial implementation | `MasterCategory` model and `catalog.0001` migration exist. No Shop Product, Variant, category API, serializer, or business workflow was found. No catalog-specific tests were found. |
| `inventory`, `customers`, `cart`, `orders`, `campaigns`, `notifications`, `analytics` | Documentation-only / scaffolded | Apps and generated files exist, but no domain models, migrations, APIs, serializers, or business workflows were found. Test modules contain no verified domain tests. |
| API coverage | Partial | Auth and Shop creation endpoints are routed under `/api/v1/`. No customer, catalog, inventory, cart, order, campaign, notification, or analytics APIs were found. |
| Tenant authorization | Partial / incomplete | `IsActiveMerchant` protects Shop creation, and its serializer derives Merchant ownership from the authenticated user. A complete Shop-scoped permission/queryset strategy across domains is not implemented. |
| Database | Partial | Identity, Shop, and Master Category migrations exist. The rest of the domain schema is not implemented. No live database connection was verified. |
| Automated checks | Not verified | Tests/checks were not run as part of this documentation task; no CI workflow was found. Existing test files are not evidence of passing behavior. |
| Infrastructure | Not found | No Dockerfile/Compose setup, CI workflow, frontend, or external WhatsApp/payment integration was found. |

## 4. Business Decisions and Implementation Work

The documentation now records the approved MVP direction for direct Super Admin Merchant creation, one Shop at a time per Merchant with replacement Shop identity, Merchant Shop deactivation, Super Admin Shop reactivation, variant-authoritative stock, pending-order expiry, no-OTP repeat-customer intent with access mechanism unresolved, and analytics/retention exclusions.

Those decisions are not implemented across the platform. In particular, Shop status and deletion operations lack API workflows; inventory and Order lifecycle are unimplemented; and no customer-history access flow exists. Do not treat these documents as evidence of shipped functionality.

The following business decision requires approval before implementation: whether permanent Shop deletion removes or preserves the Merchant account/login credentials. Existing Shop deletion rules say the credentials are removed, while the approved Shop recreation rule requires the same Merchant account to create a replacement Shop.

Other implementation blockers include the privacy-safe customer Order-history mechanism consistent with no OTP; complete Merchant/Super Admin authorization; Shop deletion and retention mechanics; catalog/inventory/Order schema and stock transaction design; pending Order timeout default and existing-state expiry representation; notification-history retention; and the remaining documented API, provider, and technical decisions.

## 5. Repository Boundaries

The architecture remains a Django modular monolith. PostgreSQL is the intended primary database, with a local SQLite fallback in settings. No repository-local Docker or CI infrastructure was found. Keep implementation status separate from documented product requirements and do not infer completeness from generated files.
