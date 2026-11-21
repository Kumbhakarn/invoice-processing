# DocExtract reviewer guide

DocExtract helps you inspect invoice and export-document extraction. It does not certify an invoice or save edits back to the server.

## Upload and review

Drop a PDF or supported image into the upload queue, or choose a file. The browser checks the file type and the 10 MiB size limit before sending it. The upload is synchronous; in real mode, each upload calls an AI provider and may incur charges. You can cancel a request while it is running. When processing finishes, the review workspace opens with the source document and extracted fields.

PDFs and supported images appear in the document pane. Navigate pages and zoom to inspect details. Selecting a field shows its evidence box when the API returned a usable location. A field without evidence remains visible in the field list and explains why no highlight can be shown. Ambiguous evidence can have multiple candidate locations.

## Read fields and confidence

Fields are grouped by document, parties, shipping, terms, weights, totals, and line items. Search or filter the list to find fields needing attention, locally edited fields, or fields with no location. Confidence is the extraction model's qualitative self-assessment, not a probability or guarantee. Location status and confidence describe different things: a high-confidence field can still have no source box.

## Edit, validate, export

You may edit values for review. Edits are **local only**, are not saved to the server, and are labeled accordingly. Revert an individual value or use undo/redo. Business validation checks the current values without calling an AI provider; its findings are review guidance. Export the current data as JSON or CSV when ready.

## History and original documents

When the server exposes history APIs, the history page lets you filter, sort, page through, and reopen stored results. The result may lack field evidence, so fields can be shown without highlights. If the original file has been deleted, the extracted fields remain available. Deleting a document removes only the original bytes; history and results remain. History/document features may be disabled by the server.

## Local use and privacy

Mock mode is the default for local development and automated tests. Real mode connects through the Vite `/api` proxy to the local backend; it has no authentication. This application is for local development and must not be deployed publicly as-is.
