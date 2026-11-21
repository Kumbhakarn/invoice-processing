export interface paths {
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health Check
         * @description Report that the API process is responding.
         */
        get: operations["health_check_api_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Readiness Check
         * @description Report whether the API and configured PostgreSQL database can serve requests.
         */
        get: operations["readiness_check_api_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/extract": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Extract Invoice
         * @description Accept an invoice document and return AI-extracted structured data.
         */
        post: operations["extract_invoice_api_extract_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/extract/evidence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Extract Invoice Evidence
         * @description Return extraction values with grounded field evidence for review.
         */
        post: operations["extract_invoice_evidence_api_extract_evidence_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/validate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Validate Extracted Invoice
         * @description Check business consistency without changing the supplied invoice values.
         */
        post: operations["validate_extracted_invoice_api_validate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Body_extract_invoice_api_extract_post */
        Body_extract_invoice_api_extract_post: {
            /**
             * File
             * @description An invoice PDF or image file
             */
            file: string;
        };
        /** Body_extract_invoice_evidence_api_extract_evidence_post */
        Body_extract_invoice_evidence_api_extract_evidence_post: {
            /**
             * File
             * @description An invoice PDF or image document
             */
            file: string;
        };
        /**
         * DocumentPage
         * @description One-based document page and dimensions used for highlighting.
         */
        DocumentPage: {
            /** Page */
            page: number;
            /** Width */
            width: number;
            /** Height */
            height: number;
        };
        /**
         * EvidenceExtractionResponse
         * @description Interim evidence endpoint response, separate from `/api/extract`.
         */
        EvidenceExtractionResponse: {
            data: components["schemas"]["InvoiceExtractionData"];
            /** Fields */
            fields: {
                [key: string]: components["schemas"]["MappedField"];
            };
            /** Pages */
            pages: components["schemas"]["DocumentPage"][];
            meta: components["schemas"]["EvidenceMetadata"];
        };
        /**
         * EvidenceMetadata
         * @description Processing timings and provider usage for an evidence extraction.
         */
        EvidenceMetadata: {
            /** Timings Ms */
            timings_ms?: {
                [key: string]: number;
            };
            /** Provider Usage */
            provider_usage?: components["schemas"]["ProviderUsageMetadata"][];
        };
        /**
         * FieldSource
         * @description Selected or unavailable source location, with ambiguity details.
         */
        FieldSource: {
            /** Page */
            page?: number | null;
            /** Boxes */
            boxes?: [
                number,
                number,
                number,
                number
            ][];
            /**
             * Status
             * @default unavailable
             * @enum {string}
             */
            status: "located" | "unavailable" | "ambiguous";
            /**
             * Reason
             * @default not_found
             */
            reason: ("not_found" | "ambiguous" | "ocr_failed" | "low_quality") | null;
            /**
             * Match Count
             * @default 0
             */
            match_count: number;
            /** Candidates */
            candidates?: components["schemas"]["SourceCandidate"][];
            /** Evidence Text */
            evidence_text?: string | null;
            /**
             * Estimated
             * @default false
             */
            estimated: boolean;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * HealthResponse
         * @description Service health response.
         */
        HealthResponse: {
            /** Status */
            status: string;
        };
        /**
         * InvoiceExtractionData
         * @description Invoice and export document fields requested by the DocExtract workflow.
         */
        InvoiceExtractionData: {
            /** Document Type */
            document_type?: string | null;
            /** Invoice Number */
            invoice_number?: string | null;
            /** Invoice Date */
            invoice_date?: string | null;
            /** Buyer Name */
            buyer_name?: string | null;
            /** Buyer Address */
            buyer_address?: string | null;
            /** Exporter Name */
            exporter_name?: string | null;
            /** Exporter Address */
            exporter_address?: string | null;
            /** Consignee Name */
            consignee_name?: string | null;
            /** Consignee Address */
            consignee_address?: string | null;
            /** Notify Party Name */
            notify_party_name?: string | null;
            /** Notify Party Address */
            notify_party_address?: string | null;
            /** Country Of Origin */
            country_of_origin?: string | null;
            /** Country Of Final Destination */
            country_of_final_destination?: string | null;
            /** Port Of Loading */
            port_of_loading?: string | null;
            /** Port Of Discharge */
            port_of_discharge?: string | null;
            /** Final Destination */
            final_destination?: string | null;
            /** Shipping Marks */
            shipping_marks?: string | null;
            /** Line Items */
            line_items?: components["schemas"]["InvoiceLineItem"][] | null;
            /** Currency */
            currency?: string | null;
            /** Terms Of Delivery And Payment */
            terms_of_delivery_and_payment?: string | null;
            /** Payment Terms */
            payment_terms?: string | null;
            /** Incoterms */
            incoterms?: string | null;
            /** Amount In Words */
            amount_in_words?: string | null;
            /** Net Weight */
            net_weight?: number | null;
            /** Gross Weight */
            gross_weight?: number | null;
            /** Weight Unit */
            weight_unit?: string | null;
        };
        /**
         * InvoiceLineItem
         * @description A single goods row from the invoice line items table.
         */
        InvoiceLineItem: {
            /** Sr No */
            sr_no?: number | null;
            /** Marks And Numbers */
            marks_and_numbers?: string | null;
            /** Number Of Packages */
            number_of_packages?: number | null;
            /** Description Of Goods */
            description_of_goods?: string | null;
            /** Quantity */
            quantity?: number | null;
            /** Hsn Code */
            hsn_code?: string | null;
            /** Unit Of Measurement */
            unit_of_measurement?: string | null;
            /** Rate */
            rate?: number | null;
            /** Amount */
            amount?: number | null;
        };
        /**
         * InvoiceValidationResult
         * @description Validation outcome kept separate from extracted invoice values.
         */
        InvoiceValidationResult: {
            /**
             * Status
             * @enum {string}
             */
            status: "valid" | "needs_review" | "invalid";
            /** Issues */
            issues: components["schemas"]["ValidationIssue"][];
        };
        /**
         * MappedField
         * @description Per-field public mapping that preserves the original extraction value.
         */
        MappedField: {
            /** Value */
            value: unknown;
            /** Raw */
            raw: string | null;
            /** Confidence */
            confidence?: ("High" | "Medium" | "Low") | null;
            source: components["schemas"]["FieldSource"];
            /** Edited */
            edited: boolean;
        };
        /**
         * ProviderUsageMetadata
         * @description Token usage returned by one provider attempt.
         */
        ProviderUsageMetadata: {
            /** Provider */
            provider: string;
            /** Model */
            model: string;
            /** Input Tokens */
            input_tokens?: number | null;
            /** Output Tokens */
            output_tokens?: number | null;
            /** Reasoning Tokens */
            reasoning_tokens?: number | null;
        };
        /**
         * ReadinessResponse
         * @description Application and database readiness status.
         */
        ReadinessResponse: {
            /** Status */
            status: string;
            /** Database */
            database: string;
        };
        /**
         * SourceCandidate
         * @description One possible source location for an extracted field.
         */
        SourceCandidate: {
            /** Page */
            page: number;
            /** Boxes */
            boxes: [
                number,
                number,
                number,
                number
            ][];
            /** Match Score */
            match_score: number;
            /** Evidence Text */
            evidence_text?: string | null;
            /**
             * Estimated
             * @default false
             */
            estimated: boolean;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /**
         * ValidationIssue
         * @description One non-mutating business rule finding.
         */
        ValidationIssue: {
            /** Rule Id */
            rule_id: string;
            /** Field */
            field: string;
            /** Line Item Index */
            line_item_index?: number | null;
            /**
             * Severity
             * @enum {string}
             */
            severity: "warning" | "error";
            /** Message */
            message: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_check_api_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    readiness_check_api_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadinessResponse"];
                };
            };
            /** @description Database is unavailable. */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadinessResponse"];
                };
            };
        };
    };
    extract_invoice_api_extract_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_extract_invoice_api_extract_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvoiceExtractionData"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    extract_invoice_evidence_api_extract_evidence_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_extract_invoice_evidence_api_extract_evidence_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EvidenceExtractionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    validate_extracted_invoice_api_validate_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InvoiceExtractionData"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvoiceValidationResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
