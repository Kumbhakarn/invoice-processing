import { afterEach, describe, expect, it } from 'vitest';
import { adaptEvidenceResponse, adaptStoredResult } from '../api/adapter';
import { apiRequest, setMockHandler } from '../api/client';
import { digitalInvoice, historyRecords } from './fixtures';
import { installMocks, mockApiHandler, resetMocks } from './mock-api';

afterEach(() => { setMockHandler(undefined); resetMocks(); });

describe('mock API', () => {
  it('returns evidence, metadata headers, and no invoice_id in the evidence body', async () => {
    installMocks(); let fileId: string | null = null;
    const result = await apiRequest<typeof digitalInvoice>('/api/extract/evidence', { method: 'POST', body: new FormData(), onHeaders: (headers) => { fileId = headers.get('X-File-ID'); } });
    expect(result).toHaveProperty('fields.invoice_number');
    expect(result).not.toHaveProperty('invoice_id');
    expect(fileId).toMatch(/^mock-file-/);
  });
  it('has representative histories with pagination and one failure', async () => {
    const result = await mockApiHandler('/api/invoices?page=2&page_size=10'); const body = await result.json() as { items: unknown[]; total: number };
    expect(body.items).toHaveLength(10); expect(body.total).toBe(historyRecords.length);
  });
  it('adapts missing stored evidence to unavailable fields with a reason', () => {
    const view = adaptStoredResult(digitalInvoice.data, 'stored.pdf', 'id-1');
    expect(view.fields.invoice_number?.status).toBe('unavailable');
    expect(view.fields.invoice_number?.reason).toBe('no_evidence');
    expect(view.meta.warnings[0]).toMatch(/do not include field evidence/i);
  });
  it('adapts field evidence to located and ambiguous view model states', () => {
    const view = adaptEvidenceResponse(digitalInvoice, 'digital.pdf');
    expect(view.fields.invoice_number?.status).toBe('located');
    expect(view.fields['line_items[0].amount']?.sources[0]?.boxes[0]).toHaveLength(4);
  });
  it('provides an explicit disabled-history server response', async () => {
    const response = await mockApiHandler('/api/invoices?disabled=true'); const body = await response.json() as { error: { code: string } };
    expect(response.status).toBe(404); expect(body.error.code).toBe('INVOICE_HISTORY_DISABLED');
  });
  it('honors abort during a slow mock upload', async () => {
    const controller = new AbortController(); const promise = mockApiHandler('/api/extract/evidence', { method: 'POST', body: new FormData(), signal: controller.signal });
    controller.abort(); await expect(promise).rejects.toBeInstanceOf(DOMException);
  });
});
