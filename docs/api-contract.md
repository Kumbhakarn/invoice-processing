# DocExtract API Contract

Base path: `/api`

The API is implemented by the FastAPI backend. JSON response fields and types below reflect the current Pydantic response models. All fields in extraction responses are nullable and are returned as `null` when no value is extracted.

## `GET /api/health`

Reports that the API process is responding.

### Success — `200 OK`

```json
{
  "status": "ok"
}
```

## `POST /api/extract`

Accepts one invoice or export document as `multipart/form-data` and returns extracted structured data.

### Request

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | file | Yes | PDF, JPEG, or PNG document. |

The default maximum upload size is 10 MiB (10,485,760 bytes), configurable with `MAX_UPLOAD_SIZE_BYTES`. Files at the configured limit are accepted. The default maximum PDF length is 50 pages (`MAX_PDF_PAGES`). The default maximum image width and height are each 10,000 pixels (`MAX_IMAGE_WIDTH` and `MAX_IMAGE_HEIGHT`). Documents exceeding any configured limit are rejected. The endpoint checks file content and compares its detected format with the filename extension and declared MIME type. A generic `application/octet-stream` MIME type is accepted when the filename extension identifies a supported format.

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

| Field | Type |
| --- | --- |
| `sr_no` | integer |
| `marks_and_numbers` | string |
| `number_of_packages` | number |
| `description_of_goods` | string |
| `quantity` | number |
| `hsn_code` | string |
| `unit_of_measurement` | string |
| `rate` | number |
| `amount` | number |

## `POST /api/extract/evidence` — interim endpoint contract

This is the **interim Feature 12 endpoint contract**. It is not registered in the API yet; implementation is scheduled for a later Feature 12 step. It accepts one document as `multipart/form-data`, like `/api/extract`, and returns the original extraction data plus field-level evidence. The existing `/api/extract` endpoint and response remain unchanged. This interim route is intended to be replaced by the future document resource contract; clients should not treat it as the long-term evidence-storage API.

The evidence endpoint accepts PDF, JPEG, PNG, WEBP, and TIFF documents. A multipage TIFF contributes one page per frame. For PDFs, each page is processed independently because a document may mix text-layer and scanned pages.

### Planned success — `200 OK`

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

All page numbers are **1-based**. `pages` lists every document page in order. `width` and `height` are the pixel dimensions used for highlighting: PDF pages are rendered at the configured DPI, and image dimensions are measured after orientation correction. Bounding boxes are arrays `[x0, y0, x1, y1]`, normalized to `[0, 1]` relative to that page, with a top-left origin. Multiple boxes represent multi-line values. Estimated sub-line boxes are permitted for values located inside OCR line boxes and must be identified as estimates in implementation metadata or evidence diagnostics.

`source.page` is null and `source.boxes` is empty when no single source is selected. `source.status` is `located`, `ambiguous`, or `unavailable`. `match_count` reports the candidate count; `candidates` contains every possible page/box and match score when disambiguation remains unresolved. Unavailable evidence uses one of `not_found`, `ambiguous`, `ocr_failed`, or `low_quality`. Evidence text is a quote from the document text layer or OCR output, not a claim that the extracted value is verified.

`confidence` is a heuristic score from 0 to 1, not a calibrated probability and never the model's self-reported confidence. It combines document grounding, match quality, OCR confidence where applicable, field-aligned provider logprobs when available, and applicable validation checks. Weights are configurable; the score is uncalibrated and should be checked against real invoices before being used for decisions.

`meta.timings_ms` reports validation, text-layer extraction, OCR, LLM, matching, and total processing time. `provider_usage` reports provider attempts' input, output, and reasoning tokens when returned by the provider; unavailable counts are null.

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

| Field | Type |
| --- | --- |
| `document_type`, `invoice_number`, `invoice_date` | string |
| `buyer_name`, `buyer_address` | string |
| `exporter_name`, `exporter_address` | string |
| `consignee_name`, `consignee_address` | string |
| `notify_party_name`, `notify_party_address` | string |
| `country_of_origin`, `country_of_final_destination` | string |
| `port_of_loading`, `port_of_discharge`, `final_destination` | string |
| `shipping_marks` | string |
| `line_items` | array of line-item objects |
| `currency`, `terms_of_delivery_and_payment`, `payment_terms`, `incoterms` | string |
| `amount_in_words` | string |
| `net_weight`, `gross_weight` | number |
| `weight_unit` | string |

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
| `413 Content Too Large` | `IMAGE_DIMENSION_LIMIT_EXCEEDED` | Image exceeds `MAX_IMAGE_WIDTH` or `MAX_IMAGE_HEIGHT`. |
| `415 Unsupported Media Type` | `UNSUPPORTED_FORMAT` | Unsupported format/extension or extension/MIME type does not match file content. |
| `422 Unprocessable Entity` | `INVALID_REQUEST` | Required multipart field is missing or the request cannot be parsed. |
| `502 Bad Gateway` | `PROVIDER_AUTHENTICATION_FAILURE` | An AI provider rejected its configured credentials and extraction failed. |
| `502 Bad Gateway` | `INVALID_AI_RESPONSE` | Configured providers returned empty or invalid structured data. |
| `502 Bad Gateway` | `PROVIDER_FAILURE` | Configured providers failed for another upstream reason. |
| `503 Service Unavailable` | `MISSING_PROVIDER_CONFIGURATION` | No AI extraction provider is configured. |
| `503 Service Unavailable` | `PROVIDER_RATE_LIMIT` | Configured providers could not process the request due to rate limiting. |
| `504 Gateway Timeout` | `PROVIDER_TIMEOUT` | Configured provider requests timed out. |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | An unexpected server error occurred. |

This error envelope replaces the previous FastAPI `{"detail": "..."}` response,
so clients that read `detail` should migrate to `error.code` and `error.message`.

## Compatibility notes

- The extraction response schema is defined by `backend/src/docextract/schemas.py` and is the source of truth for generated API types.
- PDF page counting uses `pypdf` without rendering pages. PNG and JPEG dimensions are read from encoded image headers; PNG compressed data is validated in bounded output chunks without retaining decoded pixels.
- Upload format checks are lightweight integrity checks, not full document rendering. Multipart parsing occurs before the route's bounded file read.
- Application logs are newline-delimited JSON. `LOG_LEVEL` controls the minimum level and defaults to `INFO`. Logs include request/provider metadata and traceback frames but omit raw exception messages, credentials, uploaded contents, and extracted invoice data.
- Provider token counts are logged only when reported by the SDK. Estimated USD costs use `PROVIDER_PRICING_JSON` and `PROVIDER_PRICING_VERSION`; unknown models or missing token counts produce no cost estimate. Usage metadata remains internal and is not added to the extraction response.
- Pricing JSON maps provider names (`OpenAI`, `Gemini`) to model names and `input_per_million_usd` / `output_per_million_usd` rates. Set the version alongside any pricing update; no default provider prices are assumed.
