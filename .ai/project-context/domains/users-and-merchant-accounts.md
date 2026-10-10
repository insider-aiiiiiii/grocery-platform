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
- Merchant may log in from multiple devices. Logout invalidates the current session/refresh token.
- A deactivated Merchant cannot use existing sessions or tokens; deactivation takes effect immediately.
- Merchant may log in from multiple devices. Logout invalidates the current session/refresh token.
- A deactivated Merchant cannot use existing sessions or tokens; deactivation takes effect immediately.
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

The application uses a custom Django `User` model derived from `AbstractUser`. Its email and mobile fields have global uniqueness constraints across all User accounts, and a Super Admin must have at least one of those login identifiers. The configured Django authentication backend accepts Merchant mobile/password and Super Admin email/password or mobile/password. A separate Merchant profile stores status (`ACTIVE` or `DEACTIVATED`, default `ACTIVE`) and a first-login password-change flag (default true). Django stores password hashes on User. Phone/email normalization remains unspecified.

### JWT Technical Decisions

- Use `Authorization: Bearer <access_token>` for access-token authentication.
- Access tokens last 30 minutes and refresh tokens last 30 days, including local development. Refresh tokens rotate on every successful refresh.
- Require `JWT_SIGNING_KEY` from the process environment. Do not silently fall back to Django's `SECRET_KEY` or a hardcoded key.
- Access JWT strings are never stored server-side. Revocable per-login session metadata and refresh-token blacklist records support logout, password changes, and account deactivation.
- Refresh accepts only a valid, unexpired, non-blacklisted refresh token that matches the current active session. Successful refresh rotates the token and blacklists the submitted token. Expired, malformed, revoked, previously rotated, or session-mismatched tokens return HTTP `401` with `{"detail":"Invalid refresh token."}` and no tokens are issued; the user must authenticate again. An invalid refresh token is never renewed or exchanged for a replacement.
- `POST /api/v1/auth/logout/` requires the current Bearer access token and that login session's current refresh token. A valid pair blacklists that refresh token and revokes only its associated session, immediately rejecting that session's access tokens. Logout returns `204 No Content`; invalid, revoked, or mismatched refresh tokens return `401` without changing any session. Other device sessions remain active.
- `POST /api/v1/auth/change-password/` requires an authenticated Merchant Bearer access token; a temporary-password restricted token may use this endpoint. The request contains `current_password` and `new_password`. The current password must match, and the new password must pass the configured Django password validators (user-attribute similarity, minimum length, common-password, and numeric-password checks). Validation failures return `400` with field errors. Super Admins cannot use this Merchant password-change operation.
- On successful Merchant password change, Django updates the password hash and the Merchant first-login flag (`must_change_password=false`). No other User profile fields change and plaintext passwords are never stored. All of the user's refresh tokens are blacklisted and all per-login sessions are revoked, so existing access and refresh tokens stop working and the Merchant must log in again. Success returns `204 No Content`.

### Merchant Password Recovery

- `POST /api/v1/auth/merchant-password-recovery/` accepts `mobile_number` and responds with `202 Accepted` and the same generic message whether the number belongs to an active Merchant or not. Codes are sent only to active Merchants' registered mobile numbers.
- `POST /api/v1/auth/merchant-password-recovery/confirm/` accepts `mobile_number`, `otp`, and `new_password`. A valid code is single-use. Success updates the password using the configured Django password validators, clears `must_change_password`, blacklists every refresh token, revokes every session, and returns `204 No Content`.
- Recovery codes are seven numeric digits, generated with a cryptographically secure generator, stored only as a keyed hash, and expire after five minutes. A code permits five failed attempts and then becomes invalid. Resends have a 60-second cooldown and are limited to three per mobile number per hour; requests are also limited to ten per source IP per 15 minutes. Failed recovery attempts do not lock the Merchant account.
- OTP hashes and pseudonymous mobile/IP rate-limit keys use a dedicated `MERCHANT_PASSWORD_RECOVERY_OTP_PEPPER`. Plaintext codes and provider errors are not logged.
- SMS delivery is delegated to the callable configured by `MERCHANT_PASSWORD_RECOVERY_OTP_SENDER`. The adapter must enqueue delivery and return promptly so provider latency does not reveal whether the number belongs to a Merchant. Recovery returns `503` for all numbers until both settings are configured; deployment must supply an approved SMS adapter.

### Super Admin Password Recovery and Administrative Reset

Super Admin self-recovery and administrative reset are separate approved flows:

- **Self-recovery:** A Super Admin may request recovery using their registered email address or mobile number and must verify control of the selected channel with a one-time code. The code is single-use and expires after a configurable period. After verification, the Super Admin chooses a new password. Recovery responses must not reveal whether an email address or mobile number belongs to an account. Apply rate limits to requests and verification attempts.
- **Administrative reset:** Only an authenticated Super Admin may initiate a reset for another Super Admin. The initiator cannot reset their own password through this flow and must use self-recovery instead. The initiator re-enters their own password to confirm. Record the initiating Super Admin and reset-request time. Send the affected Super Admin a time-limited, single-use reset link or verification code through a registered contact channel. The affected Super Admin chooses their own new password; the initiator must not choose or receive it.
- **Session invalidation:** Once either flow successfully changes the password, invalidate all sessions and refresh tokens belonging to the affected Super Admin, including their associated access-token sessions. Apply the configured platform password validators. Do not change Merchant temporary-password or `must_change_password` behavior, add roles, or add another administrator approval step.
- **Delivery and security:** Use the configured email delivery provider for email recovery and the configured SMS/OTP provider for mobile recovery. Do not hardcode a provider. Keep provider credentials outside source code; protect verification/reset secrets, avoid logging credentials or codes, and apply server-side authentication, authorization, throttling, and appropriate audit logging.

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
| Authentication mechanism | JWT bearer authentication is approved with 30-minute access tokens, 30-day rotating refresh tokens, and the first-login restriction defined above. |
| Django User and Merchant profile | One custom `AbstractUser` with `SUPER_ADMIN` and `MERCHANT` roles, global email/mobile uniqueness, and a separate one-to-one Merchant profile is implemented under AUTH-001/AUTH-003. Django's `is_active` field controls whether a Super Admin can authenticate. |
| Password hashing implementation | Django's standard password hashing is used through `AbstractUser`. |
| Session/token implementation and exact logout mechanics | JWT sessions, refresh rotation/blacklisting, and current-session logout are implemented. Logout invalidates only the presented active session; a global logout-all-devices operation is not defined. |
| API contracts and database fields/constraints | Not specified. |
| Phone/email normalization | Not specified. |
| Super Admin recovery/reset implementation details | The approved flows are described above. The verification-code lifetime, rate-limit thresholds, reset-link/code format, delivery/provider configuration, secure persistence, and audit-record implementation remain technical decisions. Both reset links and verification codes are allowed for administrative reset. |

## 13. Explicit Non-Goals

This specification does not define unrelated domain APIs, frontend screens, or provider-specific integration details. Super Admin recovery and reset behavior and the existing JWT contract are approved; their detailed endpoint and implementation contracts remain technical work.
