# Users & Merchant Accounts Domain Specification

## 1. Domain Purpose

This domain defines the business concepts for platform identity, Merchant accounts, Merchant access to a Shop, and account lifecycle. It documents approved behavior without selecting implementation details.

It does not own Shop profiles or the business data owned by Catalog, Inventory, Customers, Cart, Orders, Campaigns, Notifications, or Analytics.

## 2. Actors

### Super Admin

A platform-level actor. A Super Admin can create additional Super Admin accounts and Merchant accounts. Super Admin login accepts email or mobile number with a password. Email and mobile number are each globally unique across all User accounts. Super Admin identity does not imply Shop ownership. After creating a Merchant, a Super Admin cannot update Merchant information or Shop information.

### Merchant

Merchant means the Shop Owner / business owner. Merchant is a business entity separate from User and Shop. The MVP has one Merchant login/account for each business owner. The Merchant may share its credentials with employees or staff; individual employee accounts, roles, and permissions are not required in MVP. Future individual accounts and roles may be introduced later.

### Customer

Customer identity is Shop-specific and belongs to the Customers domain. Customer authentication is outside this specification.

## 3. User, Merchant, and Shop Concepts

```text
User = platform identity / person accessing the system
Merchant = Shop Owner / business entity
Shop = store and primary tenant boundary
```

These are separate business concepts. MVP Merchant access uses Merchant login credentials for the Merchant's Shop. Employees or staff may share those credentials; they are not modeled as separate Merchant memberships in MVP.

## 4. Merchant–Shop Relationship

```text
Merchant 1 ─── 1 Shop
```

- Meaning: the Merchant owns and operates their Shop.
- Each Merchant may create and own exactly one Shop in MVP; a Merchant with no Shop may log in and create one.
- Each Shop belongs to exactly one Merchant.
- A Merchant cannot create or own multiple Shops. If another Shop is required, a separate Merchant account is created.
- Ownership transfer between Merchants is not supported in MVP.
- Merchant and Shop remain separate business concepts. Shop remains the primary tenant boundary for merchant-owned business data; Merchant is not the tenant boundary.

## 5. Merchant Account Creation and Shop Setup

There is no Merchant application flow in MVP. The approved flow is:

```text
Super Admin creates Merchant
        ↓
System generates initial / temporary password
        ↓
Merchant logs in using mobile number
        ↓
Merchant changes temporary password
        ↓
Merchant creates their Shop
        ↓
Shop becomes ACTIVE immediately
```

Merchant exists before Shop creation and can log in without a Shop. When no Shop exists, the Merchant is shown the Create Shop flow. The Merchant creates their own Shop; the Super Admin does not create it in this flow. Shop activation is immediate after Merchant creates it.

Merchant application, review, approval, rejection, re-application, and application statuses are not MVP functionality.

## 6. Login and Credentials

- Merchant logs in using a mobile number that is unique across Merchant accounts.
- Email is also unique across Merchant accounts and is used for contact and recovery; it is not the login identifier.
- Super Admin logs in using either email or mobile number with a password. Each identifier is globally unique across all User accounts.
- Multiple Super Admin accounts are allowed; a Super Admin may create another Super Admin account.
- The system generates the initial temporary password when the Super Admin creates the Merchant account. The Merchant must change it on first login.
- Both the Merchant and Super Admin can change or reset the Merchant password.
- Standard platform password rules apply.
- Merchant credentials may be shared with employees/staff in MVP. Separate employee accounts, roles, and individual staff permissions are not required.
- Merchant may log in from multiple devices. Logging out invalidates the current session/token according to the eventual authentication implementation.
- Failed login attempts have no special application-level lockout rule in MVP. Normal authentication security still applies.
- Failed login attempts have no special application-level lockout rule in MVP. Normal authentication security still applies.

Merchant mobile number and email uniqueness are business rules. Their fields, normalization, and database enforcement remain technical decisions. Super Admin email and mobile uniqueness apply globally across all User accounts.

## 7. Merchant Profile and Shop Profile

- Merchant can manage their Merchant personal information and their Shop profile.
- Super Admin can create Merchant accounts but cannot update Merchant information after creation.
- Super Admin cannot update Shop information after creation.

Exact profile fields and update behavior beyond these rules are not specified here.

## 8. Merchant Status and Deactivation

Merchant status is `ACTIVE` or `DEACTIVATED`.

- A deactivated Merchant cannot log in or access the platform through that account, effective immediately.
- Merchant data is not permanently deleted in MVP when the account is deactivated.
- A deactivated Merchant cannot be reactivated in MVP. No reactivation workflow is defined.
- If the same business owner needs access again, a new Merchant account or application process would be required under future approved onboarding rules; this does not establish a current reactivation flow.
- If the Merchant's Shop is deactivated, Merchant login immediately stops working.

## 9. Roles and Access

The authenticated platform roles are `SUPER_ADMIN` and `MERCHANT`, represented on one custom Django `User` model. The User stores globally unique email and mobile identifiers. Each Merchant has a separate Merchant profile linked one-to-one to its `MERCHANT` User. The profile stores account status and whether the initial password must be changed; it contains no Shop fields. A User with the `SUPER_ADMIN` role has no automatic Shop ownership. Customer identities remain shop-specific records in the Customers domain and are not authenticated `User` records. This does not create separate employee or staff accounts. Role-based authorization and the permission implementation are not defined.

Merchant access is limited to the Merchant's Shop. Server-side authorization must preserve Shop-level tenant isolation. Client-provided Shop identifiers are not proof of authorization.

## 10. Authentication and Technical Boundaries

The application uses a custom Django `User` model derived from `AbstractUser`. Its email and mobile fields have global uniqueness constraints across all User accounts, and a Super Admin must have at least one of those login identifiers. The configured Django authentication backend accepts Merchant mobile/password and Super Admin email/password or mobile/password. A separate Merchant profile stores status (`ACTIVE` or `DEACTIVATED`, default `ACTIVE`) and a first-login password-change flag (default true). Django stores password hashes on User. Phone/email normalization, session/token behavior, APIs, and other profile fields remain unspecified.

## 11. Approved Business Invariants

- Merchant is the Shop Owner / business entity, separate from User and Shop.
- One Merchant owns exactly one Shop in MVP; one Shop belongs to exactly one Merchant.
- Shop is the primary tenant boundary.
- Only Super Admin creates a Merchant account; the Merchant creates their own Shop.
- Merchant may log in before creating a Shop.
- The system generates a temporary password and the Merchant changes it on first login.
- Merchant may share credentials with staff in MVP; individual staff accounts, roles, and permissions are not required.
- A deactivated Merchant cannot log in and cannot be reactivated in MVP.
- Shop deactivation immediately stops Merchant login.
- Merchant may manage Merchant personal information and Shop profile; Super Admin cannot edit either after creation.
- Merchant application flow and ownership transfer are not supported in MVP.

## 12. Unresolved Technical Decisions

The following remain unresolved because they concern technical representation or implementation, not approved business behavior:

| Decision | Current boundary |
|---|---|
| Authentication mechanism | Django authentication backend supports the approved email/mobile and password identifiers; session/token behavior remains unselected. |
| Django User and Merchant profile | One custom `AbstractUser` with `SUPER_ADMIN` and `MERCHANT` roles, global email/mobile uniqueness, and a separate one-to-one Merchant profile is implemented under AUTH-001/AUTH-003. |
| Password hashing implementation | Django's standard password hashing is used through `AbstractUser`. |
| Session/token implementation and exact logout mechanics | Must implement the approved invalidation behavior once auth is selected. |
| API contracts and database fields/constraints | Not specified. |
| Phone/email normalization | Not specified. |

## 13. Explicit Non-Goals

This specification does not define Django models, schema, migrations, APIs, serializers, views, authentication or authorization implementation, frontend screens, password hashing, OTP, or other technical mechanisms.
