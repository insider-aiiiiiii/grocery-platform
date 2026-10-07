# Users and authentication

## Super Admin creates a merchant

`POST /api/v1/super-admin/merchants/` creates a merchant login and its merchant
profile. The caller must be authenticated as a Super Admin. The request does
not create a shop; the merchant can create one later through `POST
/api/v1/shops/` after logging in.

Request body:

```json
{
  "username": "merchant-one",
  "mobile_number": "+911234567890",
  "email": "merchant@example.com",
  "initial_password": "a-strong-initial-password"
}
```

`username`, `mobile_number`, and `initial_password` are required. `email` is
optional. Usernames, mobile numbers, and non-empty email addresses must be
unique. The initial password is validated with Django's configured password
validators and is never returned in the response.
The response contains `merchant_id`, `user_id`, `username`, `mobile_number`,
`email`, `role`, `status`, and `must_change_password`.

The endpoint creates an active merchant with `must_change_password` enabled.
After logging in at `POST /api/v1/auth/login/`, the merchant must use
`POST /api/v1/auth/change-password/` before accessing other authenticated API
routes. A successful creation returns HTTP 201 and the new user and merchant
identifiers, role, status, and password-change requirement.
