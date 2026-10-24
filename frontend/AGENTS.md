# Frontend Agent Instructions

These instructions apply to work under `frontend/`. They supplement the repository-level `AGENTS.md`; the root task, branch, testing and PR rules remain mandatory.

## Required stack

Use the established frontend stack unless an approved architecture change says otherwise:

- Next.js 16 App Router
- React + TypeScript
- Tailwind CSS
- shadcn/ui for reusable UI primitives
- Lucide React
- Axios
- TanStack Query
- React Hook Form
- Zod
- Zustand only when shared client-only state is necessary
- Recharts for charts

Read `.ai/project-context/frontend-architecture.md` and `.ai/project-context/frontend-design-system.md` before substantial frontend implementation.

## Architecture rules

1. Django REST Framework is the backend and business-logic authority.
2. Do not implement duplicate business rules in Next.js.
3. Do not introduce a separate frontend authentication system.
4. Never hardcode backend deployment URLs; use environment configuration.
5. Shared API configuration and domain API functions belong under `lib/api/`.
6. Use TanStack Query for remote/server state.
7. Use React Hook Form + Zod for non-trivial forms.
8. Use Zustand only for justified shared client-only state; do not use it as a server-state cache.
9. Keep generic UI primitives free of domain logic.
10. Reuse existing design-system components before creating new variants.

## Google Stitch

Google Stitch is the UI design source, not an architecture source. Do not paste generated code blindly.

When implementing a Stitch design:

- preserve the approved visual intent;
- convert repeated patterns into reusable components;
- use existing design tokens/primitives;
- connect UI to documented backend contracts;
- add loading, empty, error, permission and disabled states;
- ensure responsive and accessible behavior.

If a Stitch design conflicts with backend/product rules, do not invent a new backend behavior. Surface the conflict in the task or PR.

## Folder placement

- `app/`: routes, layouts and route-local UI
- `components/ui/`: generic design-system primitives
- `components/layout/`: reusable shells/navigation
- `features/`: domain-specific frontend behavior and composed UI
- `lib/api/`: API client and domain API functions
- `lib/query/`: query-client infrastructure
- `hooks/`: genuinely shared hooks
- `types/`: shared types when they are not better kept feature-local

## Quality checks

Before submitting frontend code, run the applicable checks from `frontend/`:

```bash
npm run lint
npm run typecheck
npm run build
```

Run relevant tests once frontend test tooling/tests are present. Do not claim a check passed unless it was actually executed successfully.
