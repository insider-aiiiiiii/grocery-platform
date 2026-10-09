# Grocery Platform Frontend

Next.js frontend for the Grocery Platform Django REST Framework backend.

## Development

1. Copy `.env.example` to `.env.local`.
2. Install dependencies with `npm install`.
3. Start development with `npm run dev`.

## Merchant workspace

- `/merchant/login` — merchant sign-in
- `/merchant` — shop overview
- `/merchant/orders`, `/merchant/catalog`, `/merchant/inventory`, `/merchant/customers`, `/merchant/analytics`, `/merchant/settings` — shop operations
- `/merchant/setup` — create the merchant's shop when one does not exist
- `/merchant/change-password` — required first-login password change
- `/merchant/recover` — merchant password recovery

The merchant workspace uses the shop-scoped Django API under `NEXT_PUBLIC_API_BASE_URL`. It keeps the current merchant session in tab-scoped browser storage and uses the backend refresh and logout endpoints.

## Checks

- `npm run lint`
- `npm run typecheck`
- `npm run build`

The Django REST API remains the source of truth for authentication, authorization, business rules, and persistence.
