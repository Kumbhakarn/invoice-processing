# Frontend guidance

The planned frontend stack is React, Vite, strict TypeScript, Tailwind, shadcn/ui, TanStack Query, and react-pdf (pdf.js). Treat this as planned architecture until frontend source/configuration is present; do not assume implementation exists.

## API integration

- The backend API contract in root `docs/api-contract.md` is the source of truth.
- Generate frontend API types from the backend OpenAPI schema. Do not hand-write duplicate API types.
- Coordinate contract changes with the backend and update `docs/api-contract.md` when a contract change is approved.
- Bounding boxes, if introduced by an approved feature, use normalized 0–1 coordinates and are converted to pixels only when rendered.

## Change rules

- Keep frontend changes small and scoped to user-approved work.
- Do not add frontend functionality as part of backend-only feature work.
- Follow the root `AGENTS.md` rules on secrets, tests, dependencies, and waiting for user review before starting another feature.
