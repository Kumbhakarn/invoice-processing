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

Errors use FastAPI's standard JSON shape: `{"detail": "..."}`.

| Status | Meaning |
| --- | --- |
| `400 Bad Request` | Empty file or invalid/incomplete PDF, JPEG, or PNG content. |
| `413 Content Too Large` | File exceeds `MAX_UPLOAD_SIZE_BYTES`, a PDF exceeds `MAX_PDF_PAGES`, or an image exceeds `MAX_IMAGE_WIDTH` or `MAX_IMAGE_HEIGHT`. |
| `415 Unsupported Media Type` | Unsupported format/extension, or extension/MIME type does not match file content. |
| `422 Unprocessable Entity` | Required multipart field is missing or the request cannot be parsed. |
| `502 Bad Gateway` | All configured extraction providers failed. |
| `503 Service Unavailable` | No extraction provider is configured. |

## Compatibility notes

- The extraction response schema is defined by `backend/src/docextract/schemas.py` and is the source of truth for generated API types.
- PDF page counting uses `pypdf` without rendering pages. PNG and JPEG dimensions are read from encoded image headers; PNG compressed data is validated in bounded output chunks without retaining decoded pixels.
- Upload format checks are lightweight integrity checks, not full document rendering. Multipart parsing occurs before the route's bounded file read.
