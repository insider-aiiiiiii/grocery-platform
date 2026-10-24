# Frontend Architecture

## Purpose

This document is the source of truth for frontend implementation decisions in Grocery Platform. Human developers and AI coding agents must follow it when changing `frontend/`.

## Technology stack

- Next.js 16 with App Router
- React + TypeScript
- Tailwind CSS
- shadcn/ui for reusable UI primitives when the design system is initialized
- Lucide React for icons
- Axios for HTTP/API communication
- TanStack Query for server/API state
- React Hook Form for forms
- Zod for client-side schema validation
- Zustand only when shared client-only state is genuinely required
- Recharts for analytics visualizations

## System boundary

The frontend is an application/UI layer. Django REST Framework remains the source of truth for authentication, authorization, tenancy, persistence, validation that affects business correctness, and business rules.

Do not reimplement Django domain logic in Next.js. Do not introduce a second authentication system unless an approved architecture decision explicitly changes this rule.

## Application areas

The frontend will evolve around three product surfaces:

1. Merchant application
2. Super Admin application
3. Customer shop experience

Keep role-specific routes and layouts separated. Shared visual primitives may be reused, but role authorization and domain behavior must follow backend contracts.

## Recommended structure

```text
frontend/
  app/                 # Next.js routes, layouts and route-local UI
  components/
    ui/                # generic design-system primitives
    layout/            # reusable application layout components
  features/            # domain-specific frontend modules
  hooks/               # genuinely shared React hooks
  lib/
    api/                # HTTP client and domain API modules
    query/              # TanStack Query infrastructure
    utils/              # framework-agnostic utilities
  types/                # shared frontend/API types when not feature-local
  public/
```

Feature modules should align with backend domains where practical: auth, shops, catalog, inventory, customers, cart, orders, campaigns, notifications and analytics.

## API rules

- Use `NEXT_PUBLIC_API_BASE_URL`; never hardcode deployment-specific backend URLs.
- Shared Axios configuration belongs in `lib/api/`.
- Domain API functions belong in domain-specific API modules rather than presentational components.
- TanStack Query owns remote/server state and cache behavior.
- Components must not duplicate backend authorization or business rules.
- Define typed request/response contracts for API integration.
- Treat backend API responses as external input; handle loading, empty, error and unauthorized states explicitly.

## State management

Use the smallest appropriate state mechanism:

- component-local UI state: React state
- forms: React Hook Form + Zod
- remote/server state: TanStack Query
- cross-feature client-only state: Zustand only when necessary

Do not add Redux or another global state framework without an approved architecture change.

## Authentication

Django remains the authentication authority. Frontend work must integrate with the existing backend login, refresh, logout, password-change and recovery flows rather than creating an independent Next.js authentication system.

Token/session storage and browser credential handling must be designed with the backend contract and security model before authentication implementation. Do not default long-lived credentials to localStorage.

## Component rules

- Prefer reusable primitives over duplicated markup.
- Keep generic UI components free of grocery-domain business logic.
- Keep domain behavior in `features/` or route/domain modules.
- Keep route-only components near their route when they are not reusable.
- Avoid oversized page components; extract coherent sections and behaviors.
- Accessibility and responsive behavior are required, not optional cleanup work.

## Change discipline

Frontend work follows the repository task/branch/PR workflow in root `AGENTS.md`. Agents must inspect relevant backend/domain documentation and API contracts before implementing connected frontend behavior.
