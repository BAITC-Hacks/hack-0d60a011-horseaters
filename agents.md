# Frontend Agent Contract

This file is the source of truth for AI agents and developers changing the frontend in `frontend/`. Product and database requirements remain documented in `AGENT.md` when present and `docs/database.md`.

## Project Vision & Stack

Stockwise is a procurement workspace for reviewing replenishment recommendations, correcting quantities, approving orders, and exporting data for 1C. The primary user is a procurement manager.

- Next.js App Router and React Server Components at route boundaries.
- TypeScript in strict mode.
- Tailwind CSS with semantic theme tokens.
- TanStack Query v5 for server state.
- Zustand v5 for session-only UI state.
- React Hook Form with Zod resolvers for all user input.
- FastAPI is the backend contract owner.

## Feature-Sliced Design Rules

Application modules live in `frontend/src`. Next.js routing stays in `frontend/app`.

Dependency direction is strictly top to bottom:

1. `app`
2. `pages-flat`
3. `widgets`
4. `features`
5. `entities`
6. `shared`

Rules:

- Slices on the same layer are isolated. A feature must not import another feature; a widget must not import another widget.
- A slice is imported only through its public `index.ts` API.
- Internal imports inside one slice may be relative.
- Standard slice segments are `ui/`, `model/`, `api/`, and `lib/`.
- Pages compose widgets and features. Widgets compose features, entities, and shared modules. Features compose entities and shared modules.
- `frontend/app/**/page.tsx` contains routing, server prefetch, hydration boundaries, and page composition only.
- Keep the existing ESLint FSD boundary rule passing.

## Data Fetching & Server Prefetching

- Do not fetch server data in `useEffect`.
- Define query keys and reusable `queryOptions` in `entities/**/api`.
- Create a request-scoped `QueryClient` in `app/**/page.tsx`, call `prefetchQuery`, and pass `dehydrate(queryClient)` to `HydrationBoundary`.
- Read hydrated data with `useQuery` in `pages-flat/**` or a lower client boundary.
- Mutations belong to the feature that performs the user action. Invalidate or update the relevant entity query keys on success.
- Do not duplicate TanStack Query data in Zustand. Zustand stores selections, modal state, drafts, and other session UI state only.
- Parse API responses with Zod and expose explicit errors for network, HTTP, and contract failures.

## Design System & Theme Standards

- Use semantic classes backed by CSS variables in `src/app/styles/globals.css`: `bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `border-border`, `bg-input`, and `bg-primary`.
- Dark is the default visual direction: deep neutral backgrounds, subtle borders, restrained neon accents, and high contrast typography.
- Light mode uses a soft slate canvas, white cards, slate borders, and slate text.
- Do not add component-specific CSS files. Global tokens and base behavior belong in `globals.css`; component styling stays in Tailwind classes.
- Primary surfaces use `rounded-2xl` or `rounded-3xl`. Controls use `rounded-xl` or `rounded-full`.
- KPI cards use a large value, a short muted caption, a compact delta badge, and a circular action button.
- Status badges are compact pills: emerald for normal/success, amber for warning/planned, red for critical/error, blue for informational, and violet for adjusted/secondary states.
- Tables use semantic card and border tokens, quiet row separators, a subtle hover state, and compact uppercase headers.
- Prefer the shared `Button`, `Input`, `Card`, `Badge`, and table primitives over local substitutes.
- Hex colors are allowed only in the global token definitions or for a documented one-off data visualization palette that cannot be represented by a semantic token.

## Form & Validation Patterns

- Every form uses React Hook Form with `zodResolver`.
- User input is validated by a strict Zod schema before submission.
- Schemas live in the owning feature or entity under `model/schema.ts` or `model/schemas.ts`.
- Show field-level errors and a form-level mutation error. Handle pending, success, and failure states explicitly.
- Number inputs must define valid bounds and use `valueAsNumber`.

## Agent Operating Contract

Do:

- Read this file and the nearest relevant documentation before editing.
- Preserve the FSD dependency direction and public APIs.
- Keep server state in TanStack Query and transient UI state in Zustand.
- Use semantic theme tokens and verify both themes.
- Run `npm run typecheck`, `npm run lint`, and `npm run build` after meaningful frontend changes.
- Handle loading, empty, error, disabled, and success states.

Do not:

- Add Redux.
- Add custom CSS files outside `globals.css`.
- Hardcode component colors without theme support.
- Import another slice from the same FSD layer.
- Deep-import another slice's internal files.
- Fetch API data in `useEffect`.
- Leave TODO placeholders, silent catch branches, or unhandled errors.
- Put interactive business UI into `frontend/app` route files.
