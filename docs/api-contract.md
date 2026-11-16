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
