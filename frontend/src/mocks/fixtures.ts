import type { components } from '../api/generated';

export const invoiceData = {
  document_type: 'Commercial Invoice', invoice_number: 'CI-2048-17', invoice_date: '2026-10-08',
  exporter_name: 'Northstar Components Ltd.', exporter_address: '18 Harbour Road, Rotterdam, Netherlands',
  buyer_name: 'Cedar Ridge Trading Inc.', buyer_address: '240 King Street West, Toronto, ON M5V 1H8, Canada',
  consignee_name: 'Cedar Ridge Distribution', consignee_address: '88 Lakeview Avenue, Toronto, Ontario, Canada',
  notify_party_name: 'Cedar Ridge Distribution', notify_party_address: '88 Lakeview Avenue, Toronto, Ontario, Canada',
  country_of_origin: 'Netherlands', country_of_final_destination: 'Canada', port_of_loading: 'Rotterdam', port_of_discharge: 'Toronto', final_destination: 'Toronto, Canada',
  shipping_marks: 'CR / TORONTO / 1-24', currency: 'USD', terms_of_delivery_and_payment: 'Net 30 days', payment_terms: 'Net 30', incoterms: 'CIF Toronto',
  amount_in_words: 'Four thousand two hundred seventy five US dollars', net_weight: 82.4, gross_weight: 91.2, weight_unit: 'kg',
  line_items: [
    { sr_no: 1, marks_and_numbers: 'CR-01', number_of_packages: 12, description_of_goods: 'Precision valve assemblies', quantity: 24, hsn_code: '848180', unit_of_measurement: 'pcs', rate: 125, amount: 3000 },
    { sr_no: 2, marks_and_numbers: 'CR-02', number_of_packages: 12, description_of_goods: 'Replacement seal kits', quantity: 17, hsn_code: '401693', unit_of_measurement: 'sets', rate: 75, amount: 1275 },
  ],
};

type Source = components['schemas']['FieldSource'];
type Field = components['schemas']['MappedField'];
type Box = NonNullable<Source['boxes']>[number];
const located = (page: number, boxes: Box[], confidence: Field['confidence'] = 'High'): Field => ({ value: null, raw: null, confidence, source: { page, boxes, status: 'located', reason: null, match_count: 1, candidates: [], estimated: false }, edited: false });
const unavailable = (reason: NonNullable<Source['reason']>): Field => ({ value: null, raw: null, confidence: 'Low', source: { page: null, boxes: [], status: 'unavailable', reason, match_count: 0, candidates: [], estimated: false }, edited: false });

function makeFields(options: { multiPage?: boolean; scanned?: boolean; ambiguous?: boolean; unavailableAll?: boolean; lowConfidence?: boolean } = {}) {
  const fields: Record<string, Field> = {};
  for (const path of ['document_type', 'invoice_number', 'invoice_date', 'exporter_name', 'exporter_address', 'buyer_name', 'buyer_address', 'consignee_name', 'consignee_address', 'notify_party_name', 'notify_party_address', 'country_of_origin', 'country_of_final_destination', 'port_of_loading', 'port_of_discharge', 'final_destination', 'shipping_marks', 'currency', 'terms_of_delivery_and_payment', 'payment_terms', 'incoterms', 'amount_in_words', 'net_weight', 'gross_weight', 'weight_unit']) {
    const y = path === 'invoice_number' ? 0.12 : path === 'invoice_date' ? 0.16 : path.includes('address') ? 0.28 : 0.22;
    const page = options.multiPage && path.startsWith('line_items') ? 2 : 1;
    const boxes: Box[] = path.includes('address') ? [[0.08, y, 0.58, y + 0.02], [0.08, y + 0.025, 0.42, y + 0.045]] : [[0.08, y, 0.64, y + 0.025]];
    let field = options.unavailableAll ? unavailable(path === 'buyer_name' ? 'ocr_failed' : 'not_found') : located(page, boxes, options.lowConfidence ? 'Low' : options.scanned ? 'Medium' : 'High');
    if (options.ambiguous && path === 'invoice_number') field = { ...field, source: { page: null, boxes: [], status: 'ambiguous', reason: 'ambiguous', match_count: 2, candidates: [{ page: 1, boxes: [[0.07, 0.12, 0.3, 0.15]], match_score: 0.68, evidence_text: 'Invoice No. CI-2048-17', estimated: false }, { page: 1, boxes: [[0.55, 0.82, 0.8, 0.85]], match_score: 0.61, evidence_text: 'Reference: CI-2048-17', estimated: false }], estimated: false } };
    field.value = (invoiceData as Record<string, unknown>)[path];
    fields[path] = field;
  }
  (invoiceData.line_items as Record<string, unknown>[]).forEach((item, index) => {
    for (const [key, value] of Object.entries(item)) {
      const path = `line_items[${index}].${key}`;
      const y = 0.45 + index * 0.035;
      const field = options.unavailableAll ? unavailable(key === 'hsn_code' ? 'low_quality' : 'not_found') : located(options.multiPage && index > 0 ? 2 : 1, [[0.1 + (index % 3) * 0.2, y, 0.28 + (index % 3) * 0.2, y + 0.02]], options.lowConfidence ? 'Low' : 'Medium');
      field.value = value; fields[path] = field;
    }
  });
  if (options.multiPage) {
    for (const path of Object.keys(fields).filter((key) => key.startsWith('line_items[1]'))) fields[path]!.source.page = 2;
  }
  return fields;
}

function evidence(fields: Record<string, Field>, pages = [{ page: 1, width: 1275, height: 1650 }]) {
  for (const [path, field] of Object.entries(fields)) {
    const basePath = path.startsWith('line_items[') ? path.slice(0, path.lastIndexOf('.')) : path;
    const itemIndex = path.match(/^line_items\[(\d+)\]/)?.[1];
    field.value = itemIndex === undefined ? (invoiceData as Record<string, unknown>)[basePath] : (invoiceData.line_items[Number(itemIndex)] as Record<string, unknown>)[path.split('.').at(-1)!];
  }
  return {
    data: invoiceData as components['schemas']['InvoiceExtractionData'],
    fields,
    pages,
    meta: { timings_ms: { validation: 5, text_layer: 44, ocr: 0, llm: 810, matching: 23, total: 882 }, provider_usage: [{ provider: 'OpenAI', model: 'gpt-4o-mini', input_tokens: 1310, output_tokens: 442, reasoning_tokens: 0 }] },
  };
}

export const digitalInvoice = evidence(makeFields());
export const scannedInvoice = evidence(makeFields({ scanned: true, lowConfidence: true }));
export const multiPageInvoice = evidence(makeFields({ multiPage: true }), [{ page: 1, width: 1275, height: 1650 }, { page: 2, width: 1275, height: 1650 }, { page: 3, width: 1275, height: 1650 }]);
export const ambiguousInvoice = evidence(makeFields({ ambiguous: true }));
export const noEvidenceInvoice = evidence(makeFields({ unavailableAll: true }));
export const lowConfidenceInvoice = evidence(makeFields({ lowConfidence: true, scanned: true }));
export const fixtures = { digitalInvoice, scannedInvoice, multiPageInvoice, ambiguousInvoice, noEvidenceInvoice, lowConfidenceInvoice };

export const historyRecords = Array.from({ length: 23 }, (_, index) => ({
  id: `mock-invoice-${String(index + 1).padStart(3, '0')}`,
  original_filename: ['Northstar-commercial-invoice.pdf', 'cedar-ridge-export.jpg', 'monthly-parts-invoice.png'][index % 3],
  status: index === 7 ? 'failed' : 'succeeded', created_at: new Date(Date.UTC(2026, 9, 20 - index, 9, 30)).toISOString(),
}));
export const disabledHistoryResponse = { error: { code: 'INVOICE_HISTORY_DISABLED', message: 'Invoice history is disabled.', request_id: 'mock-request-1234' } };
