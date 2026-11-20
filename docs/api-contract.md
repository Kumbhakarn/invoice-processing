# DocExtract API Contract

Base path: `/api`

The API is implemented by the FastAPI backend. JSON response fields and types below reflect the current Pydantic response models. All fields in extraction responses are nullable and are returned as `null` when no value is extracted.

The current API does not require authentication. Requests do not need an `Authorization` header.

## `GET /api/health`

Reports that the API process is responding.

### Success — `200 OK`

```json
{
  "status": "ok"
}
```

The endpoint returns `200 OK` while the API process is responding. It does not check
whether AI providers or OCR engines are configured. An unexpected server error returns
`500 Internal Server Error` using the common error envelope.

## `POST /api/extract`

Accepts one invoice or export document as `multipart/form-data` and returns extracted structured data.

### Request

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | file | Yes | PDF, JPEG, or PNG document. |

The default maximum upload size is 10 MiB (10,485,760 bytes), configurable with `MAX_UPLOAD_SIZE_BYTES`. Files at the configured limit are accepted. The default maximum PDF length is 50 pages (`MAX_PDF_PAGES`). The default maximum image width and height are each 10,000 pixels (`MAX_IMAGE_WIDTH` and `MAX_IMAGE_HEIGHT`). Documents exceeding any configured limit are rejected. The endpoint checks file content and compares its detected format with the filename extension and declared MIME type. A generic `application/octet-stream` MIME type is accepted when the filename extension identifies a supported format.

Example request from a shell with the API running locally:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/extract `
  -F "file=@invoice.pdf;type=application/pdf"
```

The multipart form field must be named `file`. No authentication header is required.

Supported extensions and MIME types:

| Format | Extensions | MIME type |
| --- | --- | --- |
| PDF | `.pdf` | `application/pdf` |
| JPEG | `.jpg`, `.jpeg` | `image/jpeg` |
| PNG | `.png` | `image/png` |

### Success — `200 OK`

Returns an `InvoiceExtractionData` JSON object. Fields not found in the document are `null`.

```json
{
  "document_type": "Commercial Invoice",
  "invoice_number": "INV-1001",
  "invoice_date": "2025-01-15",
  "buyer_name": "Example Buyer Ltd.",
  "buyer_address": "1 Example Street, Example City",
  "exporter_name": null,
  "exporter_address": null,
  "consignee_name": null,
  "consignee_address": null,
  "notify_party_name": null,
  "notify_party_address": null,
  "country_of_origin": null,
  "country_of_final_destination": null,
  "port_of_loading": null,
  "port_of_discharge": null,
  "final_destination": null,
  "shipping_marks": null,
  "line_items": [
    {
      "sr_no": 1,
      "marks_and_numbers": null,
      "number_of_packages": 2,
      "description_of_goods": "Example goods",
      "quantity": 10,
      "hsn_code": null,
      "unit_of_measurement": "pcs",
      "rate": 5.5,
      "amount": 55
    }
  ],
  "currency": "USD",
  "terms_of_delivery_and_payment": null,
  "payment_terms": null,
  "incoterms": null,
  "amount_in_words": null,
  "net_weight": null,
  "gross_weight": null,
  "weight_unit": null
}
```

`line_items` is either `null` or an array of objects with these nullable fields:

| Field | Type | Description |
| --- | --- | --- |
| `sr_no` | integer | Printed serial or row number. |
| `marks_and_numbers` | string | Marks printed for the line item or packages. |
| `number_of_packages` | number | Package count for the line item. |
| `description_of_goods` | string | Printed goods or service description. |
| `quantity` | number | Quantity shown for the line item. |
| `hsn_code` | string | Harmonized/tariff code when printed. |
| `unit_of_measurement` | string | Unit associated with the quantity. |
| `rate` | number | Per-unit rate. |
| `amount` | number | Extended amount printed for the line. |

Every line-item property is nullable. `sr_no` is an integer; package count, quantity, rate,
and amount are numbers; marks, description, HSN code, and unit are strings.

### Provider behavior

Configure `OPENAI_API_KEY`, `GEMINI_API_KEY`, or both. OpenAI is attempted first when
configured. Gemini is attempted next when configured if the preceding provider fails,
including on provider errors, rate limits, or invalid output. With no provider key, the
endpoint returns `503 MISSING_PROVIDER_CONFIGURATION`. Provider SDK calls have 60-second
timeouts. `/api/extract` returns extracted values only; provider usage and cost metadata
are logged internally and are not added to its response.

## `POST /api/extract/evidence` — interim endpoint contract

This is the **interim Feature 12 endpoint contract**. `POST /api/extract/evidence` is implemented for immediate field-level highlighting while the future document resource API is developed. It accepts one document as `multipart/form-data`, like `/api/extract`, and returns the original extraction data plus field-level evidence. The existing `/api/extract` endpoint and response remain unchanged. This interim route is intended to be replaced by the future document resource contract; clients should not treat it as the long-term evidence-storage API.

The evidence endpoint accepts PDF, JPEG, PNG, WEBP, and TIFF documents. A multipage TIFF contributes one page per frame. For PDFs, each page is processed independently because a document may mix text-layer and scanned pages.

### Success — `200 OK`

```json
{
  "data": {
    "invoice_number": "INV-1001",
    "line_items": [
      {
        "description_of_goods": "Example goods",
        "quantity": 10
      }
    ]
  },
  "fields": {
    "invoice_number": {
      "value": "INV-1001",
      "raw": null,
      "confidence": 0.94,
      "source": {
        "page": 1,
        "boxes": [[0.12, 0.08, 0.31, 0.10]],
        "estimated": false,
        "status": "located",
        "reason": null,
        "match_count": 1,
        "candidates": [],
        "evidence_text": "Invoice No: INV-1001"
      },
      "edited": false
    },
    "line_items[0].quantity": {
      "value": 10,
      "raw": null,
      "confidence": 0.88,
      "source": {
        "page": 1,
        "boxes": [[0.71, 0.42, 0.75, 0.44]],
        "estimated": false,
        "status": "located",
        "reason": null,
        "match_count": 1,
        "candidates": [],
        "evidence_text": "10"
      },
      "edited": false
    }
  },
  "pages": [{"page": 1, "width": 2550, "height": 3300}],
  "meta": {
    "timings_ms": {
      "validation": 2.1,
      "text_layer": 8.4,
      "ocr": 0,
      "llm": 620.0,
      "matching": 4.5,
      "total": 640.0
    },
    "provider_usage": [
      {
        "provider": "OpenAI",
        "model": "configured-model",
        "input_tokens": 720,
        "output_tokens": 180,
        "reasoning_tokens": 24
      }
    ]
  }
}
```

The `data` block above is abbreviated for readability. A response contains the complete `InvoiceExtractionData` schema, with nulls for values not extracted. `fields` is a flat map containing one entry for each top-level scalar field and each line-item scalar field, including null-valued fields; line-item paths use zero-based array indexes. It does not contain a separate wrapper for the `line_items` array itself. Each field entry has `value`, `raw`, `confidence`, `source`, and `edited`. Values are copied from `data`; the mapper does not normalize or replace them. `raw` is the printed form only when it differs and has been grounded in document text. The model is not asked to produce boxes or confidence. `edited` is false for extraction output and is reserved for later edited document fields.

All page numbers are **1-based**. `pages` lists every document page in order. `width` and `height` are the pixel dimensions used for highlighting: PDF pages are rendered at the configured DPI, and image dimensions are measured after orientation correction. Bounding boxes are arrays `[x0, y0, x1, y1]`, normalized to `[0, 1]` relative to that page, with a top-left origin. Multiple boxes represent multi-line values. `source.estimated` is true when a box was estimated from character proportions inside a larger OCR line box; otherwise it is false. Candidate entries carry the same `estimated` flag for their boxes.

`source.page` is null and `source.boxes` is empty when no single source is selected. `source.status` is `located`, `ambiguous`, or `unavailable`. `match_count` reports the candidate count; `candidates` contains every possible page/box and match score when disambiguation remains unresolved. Unavailable evidence uses one of `not_found`, `ambiguous`, `ocr_failed`, or `low_quality`. Evidence text is a quote from the document text layer or OCR output, not a claim that the extracted value is verified.

`confidence` is a heuristic score from 0 to 1, not a calibrated probability and never the model's self-reported confidence. It combines document grounding, match quality, OCR confidence where applicable, field-aligned provider logprobs when available, and applicable validation checks. Weights are configurable; the score is uncalibrated and should be checked against real invoices before being used for decisions.

`meta.timings_ms` reports validation, text-layer extraction, OCR, LLM, matching, and total processing time. `provider_usage` reports provider attempts' input, output, and reasoning tokens when returned by the provider; unavailable counts are null.

The confidence weights are configured by `EVIDENCE_CONFIDENCE_WEIGHTS_JSON`; defaults are grounding 0.35, match quality 0.25, OCR confidence 0.15, provider logprob 0.10, and validation 0.15. Missing components are omitted and remaining weights renormalized. These weights are uncalibrated heuristics, not probabilities. Raw printed text is returned only when it differs from the normalized extraction and an exact normalized occurrence is found in document text-layer or OCR output.

The interim evidence route also accepts WEBP and TIFF. OCR runs in a bounded worker pool using `EVIDENCE_OCR_WORKERS`, `EVIDENCE_OCR_TIMEOUT_SECONDS`, `EVIDENCE_RENDER_DPI`, and the configured `EVIDENCE_OCR_ENGINE`. The default RapidOCR ONNX CPU package includes its models, so it needs no first-run model download. PaddleOCR is an optional alternative selected through configuration and requires locally preinstalled models. The CPU container recipe is `backend/Dockerfile`; no GPU container is supplied.

The route returns `DOCUMENT_PAGE_LIMIT_EXCEEDED` when a document exceeds `MAX_PDF_PAGES`, `IMAGE_DIMENSION_LIMIT_EXCEEDED` when a decoded page exceeds configured dimensions, `OCR_ENGINE_UNAVAILABLE` when the selected engine cannot initialize, and `OCR_TIMEOUT` when its configured time limit is exceeded. Provider requests retain explicit 60-second SDK timeouts and report `PROVIDER_TIMEOUT` if all configured providers time out. A future GPU image would need a CUDA runtime and GPU-enabled OCR dependencies; that variant is not implemented.

## `POST /api/validate`

Checks business consistency for an already extracted `InvoiceExtractionData` JSON object. It does not call an AI provider, alter supplied values, or turn validation findings into extraction errors. Validation findings are returned separately from the invoice data.

### Request

The request body uses the same nullable fields and types as the `POST /api/extract` success response.

### Success — `200 OK`

```json
{
  "status": "needs_review",
  "issues": [
    {
      "rule_id": "line_item.amount_reconciliation",
      "field": "line_items[0].amount",
      "line_item_index": 1,
      "severity": "warning",
      "message": "Quantity multiplied by rate differs from the line amount beyond currency rounding tolerance; discounts, conversions, or other adjustments may explain the difference."
    }
  ]
}
```

`status` is `valid` when no findings exist, `needs_review` when findings are warnings only, and `invalid` when at least one error is reported. Validation errors are business findings in this `200` response; they do not indicate that extraction or the HTTP request failed. Line item indexes are one-based.

Current rules check required-field presence, ISO `YYYY-MM-DD` date shape, three-letter uppercase currency-code shape, non-negative net/gross weights and quantities/rates, gross weight not below net weight, line-item description/unit presence, and quantity × rate versus line amount using currency minor-unit rounding tolerance. A mismatch is a warning because discounts, conversions, and adjustments are not represented by the current schema. Currency codes are not verified against a live ISO registry.

The current extraction schema has no invoice-level numeric total, subtotal, tax, discount, or per-line currency fields. Therefore amount-in-words reconciliation, invoice totals reconciliation, tax/additional-charge reconciliation, and cross-currency line-total checks are not performed.

The top-level fields are:

| Field | Type | Description |
| --- | --- | --- |
| `document_type` | string | Printed document category, such as invoice or commercial invoice. |
| `invoice_number` | string | Invoice identifier as printed. |
| `invoice_date` | string | Invoice date; normalized to `YYYY-MM-DD` only when unambiguous. |
| `buyer_name`, `buyer_address` | string | Buyer name and address as printed. |
| `exporter_name`, `exporter_address` | string | Exporter/seller name and address as printed. |
| `consignee_name`, `consignee_address` | string | Consignee name and address when shown. |
| `notify_party_name`, `notify_party_address` | string | Notify-party name and address when shown. |
| `country_of_origin` | string | Country where the goods originate, when stated. |
| `country_of_final_destination` | string | Country of final destination, when stated. |
| `port_of_loading` | string | Port from which the goods are loaded. |
| `port_of_discharge` | string | Port where the goods are discharged. |
| `final_destination` | string | Final destination shown on the document. |
| `shipping_marks` | string | Shipment/package marks as printed. |
| `line_items` | array of line-item objects | Printed item rows in document order, or `null`. |
| `currency` | string | Currency code or label as printed; extraction does not validate it. |
| `terms_of_delivery_and_payment` | string | Combined delivery and payment terms, when shown. |
| `payment_terms` | string | Payment terms as printed. |
| `incoterms` | string | Incoterms value as printed. |
| `amount_in_words` | string | Printed total amount in words, when present. |
| `net_weight`, `gross_weight` | number | Net and gross weights as JSON numbers. |
| `weight_unit` | string | Unit used for the weights. |

### Errors

The API returns an `X-Request-ID` response header on successful and failed requests.
The server generates a new UUID for each request and uses it to correlate application
logs. Error responses include the same ID in the error object. The extraction success
body remains unchanged.

Errors use a consistent JSON shape. The `code` is stable for client handling; the
`message` is safe for display and does not include provider exception details.

```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "Uploaded file exceeds the maximum allowed size.",
    "request_id": "2b4f162b-6868-4618-8a2a-79da3fc4fdad"
  }
}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `EMPTY_FILE` | Uploaded file is empty. |
| `400 Bad Request` | `INVALID_DOCUMENT` | Supported document content is malformed or incomplete. |
| `413 Content Too Large` | `FILE_TOO_LARGE` | File exceeds `MAX_UPLOAD_SIZE_BYTES`. |
| `413 Content Too Large` | `PDF_PAGE_LIMIT_EXCEEDED` | PDF exceeds `MAX_PDF_PAGES`. |
| `413 Content Too Large` | `DOCUMENT_PAGE_LIMIT_EXCEEDED` | Evidence endpoint document exceeds `MAX_PDF_PAGES`. |
| `413 Content Too Large` | `IMAGE_DIMENSION_LIMIT_EXCEEDED` | Image exceeds `MAX_IMAGE_WIDTH` or `MAX_IMAGE_HEIGHT`. |
| `415 Unsupported Media Type` | `UNSUPPORTED_FORMAT` | Unsupported format/extension or extension/MIME type does not match file content. |
| `422 Unprocessable Entity` | `INVALID_REQUEST` | Required multipart field is missing or the request cannot be parsed. |
| `502 Bad Gateway` | `PROVIDER_AUTHENTICATION_FAILURE` | An AI provider rejected its configured credentials and extraction failed. |
| `502 Bad Gateway` | `INVALID_AI_RESPONSE` | Configured providers returned empty or invalid structured data. |
| `502 Bad Gateway` | `PROVIDER_FAILURE` | Configured providers failed for another upstream reason. |
| `503 Service Unavailable` | `MISSING_PROVIDER_CONFIGURATION` | No AI extraction provider is configured. |
| `503 Service Unavailable` | `PROVIDER_RATE_LIMIT` | Configured providers could not process the request due to rate limiting. |
| `503 Service Unavailable` | `OCR_ENGINE_UNAVAILABLE` | Configured OCR engine or its local models are unavailable. |
| `504 Gateway Timeout` | `PROVIDER_TIMEOUT` | Configured provider requests timed out. |
| `504 Gateway Timeout` | `OCR_TIMEOUT` | OCR exceeded `EVIDENCE_OCR_TIMEOUT_SECONDS`. |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | An unexpected server error occurred. |

Other generic HTTP errors use `404 NOT_FOUND`, `405 METHOD_NOT_ALLOWED`, or
`400 INVALID_REQUEST` where applicable. The API does not currently return `401` or `403`
because authentication is not implemented.

This error envelope replaces the previous FastAPI `{"detail": "..."}` response,
so clients that read `detail` should migrate to `error.code` and `error.message`.

## Environment variables

Settings are loaded from environment variables and `backend/.env`. Names below are the
uppercase environment forms of the backend settings. Copy `backend/.env.example` to
`backend/.env` for local configuration; keep the `.env` file private. Provider keys are
optional individually, but at least one must be set to use extraction.

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | unset | OpenAI credential. OpenAI is tried first when configured. |
| `GEMINI_API_KEY` | unset | Gemini credential and fallback when configured. |
| `OPENAI_MODEL` | `gpt-6-luna` | OpenAI model name. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Gemini model name. |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | Maximum upload size in bytes (10 MiB). |
| `MAX_PDF_PAGES` | `50` | Maximum page/frame count used by PDF and evidence processing. |
| `MAX_IMAGE_WIDTH` | `10000` | Maximum image width in pixels for document validation. |
| `MAX_IMAGE_HEIGHT` | `10000` | Maximum image height in pixels for document validation. |
| `EVIDENCE_RENDER_DPI` | `200` | Render resolution for evidence page images. |
| `EVIDENCE_TEXT_LAYER_MIN_CHARS` | `20` | Minimum usable text length for a PDF page's text layer. |
| `EVIDENCE_OCR_ENGINE` | `rapidocr` | OCR engine: `rapidocr` or `paddleocr`. |
| `EVIDENCE_OCR_WORKERS` | `2` | Maximum concurrent OCR workers (1–8). |
| `EVIDENCE_OCR_TIMEOUT_SECONDS` | `30` | Evidence OCR timeout in seconds. |
| `EVIDENCE_OCR_MODEL_DIR` | unset | Local PaddleOCR model directory; only needed with PaddleOCR. |
| `EVIDENCE_MATCH_THRESHOLD` | `0.82` | Minimum evidence text match score. |
| `EVIDENCE_MATCH_AMBIGUITY_MARGIN` | `0.05` | Score margin used to identify ambiguous evidence matches. |
| `EVIDENCE_CONFIDENCE_WEIGHTS_JSON` | See below | Weights for the uncalibrated evidence confidence heuristic. |
| `LOG_LEVEL` | `INFO` | Minimum application log level. |
| `PROVIDER_PRICING_JSON` | `{}` | Optional provider/model token rates used for internal cost estimates. |
| `PROVIDER_PRICING_VERSION` | `unconfigured` | Label identifying the configured provider pricing table. |

The default confidence weights are:

```json
{"grounding":0.35,"match_quality":0.25,"ocr_confidence":0.15,"provider_logprob":0.10,"validation":0.15}
```

Weights are uncalibrated heuristic inputs, not probabilities. Missing components are
omitted and the remaining weights are renormalized. `PROVIDER_PRICING_JSON` maps `OpenAI`
or `Gemini` model names to `input_per_million_usd` and `output_per_million_usd` values.
Unknown models and missing token counts do not produce a cost estimate. The server host,
port, and reload behavior are selected in the Uvicorn command; they are not application
environment settings.

## Compatibility notes

- The extraction response schema is defined by `backend/src/docextract/schemas.py` and is the source of truth for generated API types.
- PDF page counting uses `pypdf` without rendering pages. PNG and JPEG dimensions are read from encoded image headers; PNG compressed data is validated in bounded output chunks without retaining decoded pixels.
- Upload format checks are lightweight integrity checks, not full document rendering. Multipart parsing occurs before the route's bounded file read.
- Application logs are newline-delimited JSON. `LOG_LEVEL` controls the minimum level and defaults to `INFO`. Logs include request/provider metadata and traceback frames but omit raw exception messages, credentials, uploaded contents, and extracted invoice data.
- Provider token counts are logged only when reported by the SDK. Estimated USD costs use `PROVIDER_PRICING_JSON` and `PROVIDER_PRICING_VERSION`; unknown models or missing token counts produce no cost estimate. Usage metadata remains internal and is not added to the extraction response.
- Pricing JSON maps provider names (`OpenAI`, `Gemini`) to model names and `input_per_million_usd` / `output_per_million_usd` rates. Set the version alongside any pricing update; no default provider prices are assumed.
