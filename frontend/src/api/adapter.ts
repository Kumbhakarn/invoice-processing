import type { ExtractionView, Field, FieldCandidate, HistoryEntry, HistoryPageView } from '../model/view-model';
import type { components } from './generated';

type EvidenceResponse = components['schemas']['EvidenceExtractionResponse'];
type EvidenceField = components['schemas']['MappedField'];

const labels: Record<string, string> = {
  document_type: 'Document type', invoice_number: 'Invoice number', invoice_date: 'Invoice date', buyer_name: 'Buyer name', buyer_address: 'Buyer address', exporter_name: 'Exporter name', exporter_address: 'Exporter address', consignee_name: 'Consignee name', consignee_address: 'Consignee address', notify_party_name: 'Notify party', notify_party_address: 'Notify party address', country_of_origin: 'Country of origin', country_of_final_destination: 'Final destination country', port_of_loading: 'Port of loading', port_of_discharge: 'Port of discharge', final_destination: 'Final destination', shipping_marks: 'Shipping marks', currency: 'Currency', terms_of_delivery_and_payment: 'Delivery and payment terms', payment_terms: 'Payment terms', incoterms: 'Incoterms', amount_in_words: 'Amount in words', net_weight: 'Net weight', gross_weight: 'Gross weight', weight_unit: 'Weight unit',
};
const labelFor = (path: string) => labels[path] ?? path.split(/[._]/).at(-1)?.replaceAll('_', ' ').replace(/\b\w/g, (x) => x.toUpperCase()) ?? path;
const asBox = (box: number[]) => box as unknown as FieldCandidate['boxes'][number];
function makeField(path: string, value: unknown, evidence?: EvidenceField): Field {
  const source = evidence?.source;
  const candidates = (source?.candidates ?? []).map((c) => ({ page: c.page, boxes: (c.boxes ?? []).map(asBox), matchScore: c.match_score, evidenceText: c.evidence_text ?? undefined, estimated: c.estimated }));
  const status = source?.status === 'located' && source.page && source.boxes?.length ? 'located' : source?.status === 'ambiguous' || candidates.length > 1 ? 'ambiguous' : 'unavailable';
  const sources = status === 'located' ? [{ page: source!.page!, boxes: (source!.boxes ?? []).map(asBox), estimated: source!.estimated }] : [];
  return { path, label: labelFor(path), value, raw: evidence?.raw ?? null, confidence: evidence?.confidence ?? null, status, reason: status === 'unavailable' ? source?.reason as Field['reason'] ?? 'no_evidence' : status === 'ambiguous' ? 'ambiguous' : null, sources, candidates, edited: evidence?.edited ?? false, originalValue: value };
}
function flatten(data: Record<string, unknown>, prefix = ''): [string, unknown][] {
  return Object.entries(data).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (Array.isArray(value)) return value.flatMap((item, index) => item && typeof item === 'object' ? flatten(item as Record<string, unknown>, `${path}[${index}]`) : [[`${path}[${index}]`, item] as [string, unknown]]);
    return value && typeof value === 'object' ? flatten(value as Record<string, unknown>, path) : [[path, value] as [string, unknown]];
  });
}
export function adaptEvidenceResponse(response: EvidenceResponse, filename: string): ExtractionView {
  const data = response.data as Record<string, unknown>;
  const fields = Object.fromEntries(flatten(data).map(([path, value]) => [path, makeField(path, value, response.fields?.[path])]));
  return { filename, data, fields, pages: response.pages, meta: { timingsMs: response.meta.timings_ms ?? {}, providerUsage: (response.meta.provider_usage ?? []).map((u) => ({ provider: u.provider, model: u.model, inputTokens: u.input_tokens ?? null, outputTokens: u.output_tokens ?? null, reasoningTokens: u.reasoning_tokens ?? null })), warnings: [] } };
}
export function adaptStoredResult(data: Record<string, unknown>, filename: string, invoiceId: string, pages: ExtractionView['pages'] = []): ExtractionView {
  return { ...adaptEvidenceResponse({ data: data as components['schemas']['InvoiceExtractionData'], fields: {}, pages, meta: {} }, filename), invoiceId, meta: { timingsMs: {}, providerUsage: [], warnings: ['Stored results do not include field evidence; highlights are unavailable.'] } };
}

const asRecord = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const asString = (value: unknown) => typeof value === 'string' ? value : undefined;
export function adaptHistoryResponse(response: unknown): HistoryPageView {
  const page = asRecord(response);
  const rows = Array.isArray(page.items) ? page.items : Array.isArray(page.invoices) ? page.invoices : [];
  const items: HistoryEntry[] = rows.map((unknownRow) => {
    const row = asRecord(unknownRow);
    const status: HistoryEntry['status'] = row.status === 'succeeded' || row.status === 'failed' ? row.status : 'unknown';
    const validationStatus: HistoryEntry['validationStatus'] = row.validation_status === 'valid' || row.validation_status === 'needs_review' || row.validation_status === 'invalid' ? row.validation_status : undefined;
    return {
      id: asString(row.id) ?? asString(row.invoice_id) ?? '',
      filename: asString(row.original_filename) ?? asString(row.filename) ?? 'Untitled document',
      status,
      createdAt: asString(row.created_at), uploadedAt: asString(row.uploaded_at), processedAt: asString(row.processed_at),
      validationStatus,
    };
  }).filter((row) => Boolean(row.id));
  return { items, total: typeof page.total === 'number' ? page.total : items.length, page: typeof page.page === 'number' ? page.page : 1, pageSize: typeof page.page_size === 'number' ? page.page_size : items.length };
}
