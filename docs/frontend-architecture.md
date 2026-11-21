# Frontend architecture

## Stack and licenses

Pinned direct dependencies: React/React DOM (MIT), Vite and its React plugin (MIT), TypeScript and typescript-eslint (Apache-2.0), Tailwind CSS/autoprefixer/PostCSS (MIT), TanStack Query (MIT), Zustand (MIT), react-pdf and pdfjs-dist (Apache-2.0), react-resizable-panels (MIT), React Hook Form and resolvers (MIT), Zod (MIT), lucide-react (ISC), clsx and tailwind-merge (MIT), openapi-typescript (MIT), Vitest (MIT), Testing Library packages (MIT), Playwright (Apache-2.0), ESLint and plugins (MIT), jsdom (MIT). Versions are exact in `frontend/package.json`. Confirmed package metadata licenses at selection time; transitive license details are npm's lockfile/package metadata.

## Layout and ownership

- `src/api/`: generated OpenAPI types, fetch wrapper and API-to-view-model adapter.
- `src/model/`: shared UI view model and confidence bands.
- `src/store/`: cross-feature selection, viewer state and local edit history.
- `src/features/viewer`, `locator`, `fields`, `editing`, `validation`, `upload`, `history`: feature-owned UI.
- `src/mocks`, `src/app`: fixtures/tests and application shell/routes.

Feature components consume `ExtractionView` and `Field`; only the adapter interprets raw API responses. `POST /api/extract/evidence` has no `invoice_id` in the current OpenAPI response. Stored `/result` is ordinary invoice JSON and contains no field boxes, so the adapter emits unavailable locations with a reason. This is a graceful no-highlight state.

TanStack Query owns remote requests; Zustand owns selection, filters, zoom, sizes, local edits and undo/redo. Confidence levels from the current backend are qualitative (`High`, `Medium`, `Low`), not percentages; the UI's single threshold config also accepts numeric values should the API later provide a calibrated score.

The locator should derive pixel geometry from normalized boxes and page layout math, with scroll updates handled outside React render. The Vite proxy keeps local API calls same-origin. Mock mode is the default and must be used for all automated tests.

## Limits

No authentication, invoice update API, evidence persistence API, or production storage guarantee exists. Local edits must never be represented as server-saved. The current main branch OpenAPI has no history routes; the history UI must handle their disabled/unavailable state until a backend exposing the described routes is used. `docs/document-storage.md` is absent from this checkout; storage behavior is summarized in `docs/api-contract.md` and the UI must treat missing originals as expected.
