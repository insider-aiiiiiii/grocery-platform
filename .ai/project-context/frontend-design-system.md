# Frontend Design System and Google Stitch Workflow

## Purpose

Google Stitch is the primary UI design source for frontend screens. Stitch output defines intended visual design and interaction direction; it does not override repository architecture, backend contracts, accessibility requirements, or the shared component system.

## Stitch-to-code workflow

For each approved Stitch screen:

1. Identify the user role, route and task represented by the screen.
2. Compare the design with existing shared components and tokens.
3. Identify reusable patterns before writing page-specific markup.
4. Map data shown in the design to documented backend API contracts.
5. Implement the design using the approved frontend stack.
6. Add loading, empty, error, disabled and permission states that may not appear in the design mockup.
7. Verify responsive behavior and keyboard/accessibility behavior.
8. Review the result against the Stitch design before PR submission.

Do not blindly paste generated Stitch code into the application. Generated code must be adapted to this repository's architecture and component conventions.

## Design-system foundation

The design system should standardize at least:

- typography
- color tokens
- spacing
- border radius
- elevation/shadows where required
- buttons
- form controls
- cards
- tables
- dialogs/drawers
- badges/status indicators
- tabs
- navigation
- toasts/feedback
- skeleton/loading states
- empty states
- error states

Use Tailwind CSS tokens/utilities and shadcn/ui primitives where appropriate. Customize primitives to match the approved Stitch design rather than creating parallel component libraries for individual screens.

## Component ownership

`components/ui/` contains generic primitives and must not contain grocery business rules.

`components/layout/` contains reusable shells/navigation/layout structures.

Domain-specific composed UI belongs with its feature or route. A component should move into shared UI only after it represents a reusable visual/interaction primitive.

## Consistency rules

- Do not create a new button/input/card implementation when an existing primitive satisfies the requirement.
- Do not hardcode repeated design values when a shared token is appropriate.
- Use Lucide React for standard interface icons instead of mixing icon libraries.
- Avoid arbitrary one-off visual variants unless required by an approved design.
- Preserve consistent focus, hover, disabled, validation and loading behavior.

## Responsive design

Implement approved screens for practical desktop, tablet and mobile layouts. Merchant and Super Admin experiences may be desktop-first, but they must remain usable at narrower widths. Customer shop flows must be treated as mobile-critical because customers may enter through QR/shop links.

## Accessibility

Use semantic HTML, associated form labels, keyboard-accessible controls, visible focus states, meaningful alt text where needed, and accessible dialog/menu behavior. Do not sacrifice accessibility to reproduce a visual mockup exactly.

## Design changes

When a Stitch design conflicts with an established shared component or product/backend rule, do not silently invent behavior. Preserve the product/backend rule and document the design discrepancy in the task/PR so it can be resolved explicitly.
