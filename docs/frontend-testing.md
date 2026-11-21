# Frontend testing

All automated tests run with `VITE_USE_MOCK=true`. They must not make real backend/provider requests or incur provider charges.

## Commands

From `frontend/`:

```powershell
npm ci
npm run typecheck
npm run lint
npm test
npm run test:e2e
```

Playwright starts Vite on port 4173 with mock mode forced on. Install browser binaries once with `npx playwright install chromium` if Playwright reports that the browser is missing.

## Mock catalog

`src/mocks/fixtures.ts` provides a digital invoice, lower-confidence/scanned invoice, three-page invoice, ambiguous invoice number with two candidate locations, unavailable fields with `not_found`, `ocr_failed`, and `low_quality` reasons, two line items, a warning-ready invoice, and a paginated history fixture containing succeeded and failed records. The mock API supports evidence upload, validation findings, history filtering/sorting/paging, stored results without evidence, status, document-deletion state, and safe errors. Filenames containing `slow` or `timeout` exercise cancellation; `too-large`, `unsupported`, and `failed-document` exercise upload errors.

## Optional manual real-backend checklist

This is never run by automated tests. Each upload calls an AI provider and may incur charges; test one file at a time. Start the backend from `backend/` with `uv run uvicorn docextract.main:app --reload`, then start Vite from `frontend/` with `$env:VITE_USE_MOCK = "false"; npm run dev`.

1. Digital PDF: compare invoice fields and highlights with printed text; check confidence is plausible.
2. Scanned PDF or photo: inspect OCR fields, low confidence and absent-evidence explanations.
3. Mixed PDF: check highlights and page navigation for both text and scanned pages.
4. Oversized file: verify a safe size-limit message.
5. Unsupported file: verify a safe format message.

## Known limitations

Evidence extraction currently does not return `invoice_id` in its response body; the upload response provides `X-File-ID`. Stored `/result` contains invoice data but no source boxes, so the adapter shows the fields without highlights. This checkout's main branch does not expose the history/document routes, so real history remains unavailable until the backend branch containing those routes is used. TIFF preview may be unsupported by the browser. Mock fixtures validate UI wiring, not OCR accuracy or provider confidence calibration.
