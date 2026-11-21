import { setMockHandler } from '../api/client';
import { ambiguousInvoice, digitalInvoice, disabledHistoryResponse, historyRecords, lowConfidenceInvoice, multiPageInvoice, noEvidenceInvoice, scannedInvoice } from './fixtures';

const records = new Map(historyRecords.map((row) => [row.id, { ...row }]));
const removedDocuments = new Set<string>();
const samplePdf = (() => {
  const objects = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 4 0 R >>\nendobj\n',
    '4 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n',
  ];
  let source = '%PDF-1.4\n'; const offsets = [0];
  for (const object of objects) { offsets.push(new TextEncoder().encode(source).length); source += object; }
  const xref = new TextEncoder().encode(source).length;
  source += `xref\n0 ${offsets.length}\n0000000000 65535 f \n${offsets.slice(1).map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')}trailer\n<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return new TextEncoder().encode(source);
})();
const delay = (milliseconds: number, signal?: AbortSignal) => new Promise<void>((resolve, reject) => {
  if (signal?.aborted) { reject(new DOMException('Cancelled', 'AbortError')); return; }
  const timer = window.setTimeout(resolve, milliseconds);
  signal?.addEventListener('abort', () => { window.clearTimeout(timer); reject(new DOMException('Cancelled', 'AbortError')); }, { once: true });
});
const json = (body: unknown, status = 200, headers?: HeadersInit) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...Object.fromEntries(new Headers(headers).entries()) } });
const apiError = (status: number, code: string, message: string) => json({ error: { code, message, request_id: 'mock-request-1234' } }, status);
const invoiceFor = (name: string) => /timeout|slow/i.test(name) ? null : /ambiguous/i.test(name) ? ambiguousInvoice : /unavailable|no-evidence/i.test(name) ? noEvidenceInvoice : /low-confidence/i.test(name) ? lowConfidenceInvoice : /multi-page|multipage/i.test(name) ? multiPageInvoice : /scan|photo/i.test(name) ? scannedInvoice : digitalInvoice;

export async function mockApiHandler(path: string, init: RequestInit = {}) {
  const url = new URL(path, 'http://localhost'); const signal = init.signal ?? undefined;
  if (init.method === 'POST' && url.pathname === '/api/extract/evidence') {
    const file = (init.body as FormData | null)?.get('file'); const name = file instanceof File ? file.name : 'digital-invoice.pdf';
    if (/timeout/i.test(name)) { await delay(900, signal); return json({ error: { ...disabledHistoryResponse.error, code: 'PROVIDER_TIMEOUT', message: 'AI provider request timed out.' } }, 504); }
    if (/slow/i.test(name)) await delay(8_000, signal);
    else await delay(450, signal);
    if (/too-large|oversized/i.test(name)) return apiError(413, 'FILE_TOO_LARGE', 'Uploaded file exceeds the maximum allowed size.');
    if (/unsupported/i.test(name)) return apiError(415, 'UNSUPPORTED_FORMAT', 'Upload a PDF, JPEG, PNG, WEBP, or TIFF file.');
    if (/failed-document|provider-error/i.test(name)) return apiError(502, 'PROVIDER_FAILURE', 'Invoice extraction failed with configured AI providers.');
    const fileId = `mock-file-${crypto.randomUUID()}`;
    return json(invoiceFor(name) ?? digitalInvoice, 200, { 'X-File-ID': fileId, 'X-Request-ID': 'mock-request-1234', 'X-Trace-ID': 'mock-trace-1234' });
  }
  if (url.pathname === '/api/validate' && init.method === 'POST') {
    await delay(120, signal);
    return json({ status: 'needs_review', issues: [
      { rule_id: 'required.invoice_number', field: 'invoice_number', severity: 'warning', message: 'Invoice number should be reviewed.' },
      { rule_id: 'line_item.amount_reconciliation', field: 'line_items[1].amount', severity: 'warning', line_item_index: 2, message: 'Quantity multiplied by rate differs from the line amount; discounts or adjustments may explain the difference.' },
    ] });
  }
  if (url.pathname === '/api/invoices') {
    if (url.searchParams.get('disabled') === 'true' || localStorage.getItem('docextract:mock-history-disabled') === 'true') return json(disabledHistoryResponse, 404);
    const page = Math.max(1, Number(url.searchParams.get('page') ?? 1)); const pageSize = Math.max(1, Number(url.searchParams.get('page_size') ?? 10));
    const status = url.searchParams.get('status'); const sortBy = url.searchParams.get('sort_by') ?? 'created_at'; const sortOrder = url.searchParams.get('sort_order') === 'asc' ? 1 : -1;
    const filtered = [...records.values()].filter((row) => !status || row.status === status).sort((a, b) => String(a[sortBy as keyof typeof a] ?? '').localeCompare(String(b[sortBy as keyof typeof b] ?? '')) * sortOrder);
    return json({ items: filtered.slice((page - 1) * pageSize, page * pageSize), total: filtered.length, page, page_size: pageSize });
  }
  const match = url.pathname.match(/^\/api\/invoices\/([^/]+)(?:\/(result|status|document))?$/);
  if (match) {
    const [, id, resource] = match;
    if (init.method === 'DELETE' && resource === 'document') { removedDocuments.add(id!); return json({ status: 'deleted' }); }
    if (!records.has(id!)) return apiError(404, 'INVOICE_NOT_FOUND', 'Invoice was not found.');
    if (resource === 'result') return json({ data: digitalInvoice.data }); // Stored results intentionally have no evidence boxes.
    if (resource === 'status') return json({ status: records.get(id!)!.status, updated_at: records.get(id!)!.created_at });
    if (resource === 'document') return removedDocuments.has(id!) ? apiError(404, 'DOCUMENT_NOT_FOUND', 'The original document was deleted.') : new Response(samplePdf, { headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="saved-invoice.pdf"' } });
    return json(records.get(id));
  }
  if (url.pathname === '/api/history-disabled') return apiError(404, 'INVOICE_HISTORY_DISABLED', 'Invoice history is disabled.');
  return apiError(404, 'NOT_FOUND', 'This mock API route is not available.');
}

export function installMocks() { setMockHandler(mockApiHandler); }
export function resetMocks() { records.clear(); for (const row of historyRecords) records.set(row.id, { ...row }); removedDocuments.clear(); installMocks(); }
