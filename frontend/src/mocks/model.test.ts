import { afterEach, describe, expect, it } from 'vitest';
import { adaptEvidenceResponse, adaptHistoryResponse, adaptStoredResult } from '../api/adapter';
import { confidenceBand } from '../model/confidence';
import { useUiStore } from '../store/ui-store';
import { boxToPixels } from '../features/locator/geometry';
import { digitalInvoice } from './fixtures';

afterEach(() => useUiStore.getState().reset());

describe('shared review model', () => {
  it('adapts evidence into fields and gracefully marks a stored field without boxes', () => {
    const extracted = adaptEvidenceResponse(digitalInvoice, 'invoice.pdf');
    expect(extracted.fields.invoice_number?.status).toBe('located');
    expect(extracted.fields['line_items[0].amount']?.status).toBe('located');
    const stored = adaptStoredResult(digitalInvoice.data, 'saved.pdf', 'invoice-1');
    expect(stored.fields.invoice_number?.status).toBe('unavailable');
    expect(stored.fields.invoice_number?.reason).toBe('no_evidence');
  });

  it('converts normalized boxes consistently at different zoom scales', () => {
    const box = [0.1, 0.2, 0.5, 0.6] as const;
    const base = boxToPixels(box, 1000, 2000); const zoomed = boxToPixels(box, 1000 * 1.5, 2000 * 1.5);
    expect(base.left).toBeCloseTo(100); expect(base.top).toBeCloseTo(400); expect(base.width).toBeCloseTo(400); expect(base.height).toBeCloseTo(800);
    expect(zoomed.left).toBeCloseTo(150); expect(zoomed.top).toBeCloseTo(600); expect(zoomed.width).toBeCloseTo(600); expect(zoomed.height).toBeCloseTo(1200);
  });

  it('uses the configured confidence bands and qualitative API values', () => {
    expect(confidenceBand(0.9)).toBe('high'); expect(confidenceBand(0.7)).toBe('medium');
    expect(confidenceBand(0.69)).toBe('low'); expect(confidenceBand('High')).toBe('high'); expect(confidenceBand(null)).toBe('unknown');
  });

  it('maps history response records to the internal view model', () => {
    const history = adaptHistoryResponse({ items: [{ id: 'x', original_filename: 'invoice.pdf', status: 'succeeded', created_at: '2026-11-20' }], total: 1, page: 2, page_size: 10 });
    expect(history).toEqual({ items: [{ id: 'x', filename: 'invoice.pdf', status: 'succeeded', createdAt: '2026-11-20', uploadedAt: undefined, processedAt: undefined, validationStatus: undefined }], total: 1, page: 2, pageSize: 10 });
  });

  it('supports local edit, undo, redo, and revert without saving', () => {
    const field = adaptEvidenceResponse(digitalInvoice, 'invoice.pdf').fields.invoice_number!;
    const store = useUiStore.getState(); store.edit(field, 'LOCAL-1');
    expect(useUiStore.getState().edits.invoice_number).toBe('LOCAL-1');
    useUiStore.getState().undo(); expect(useUiStore.getState().edits.invoice_number).toBeUndefined();
    useUiStore.getState().redo(); expect(useUiStore.getState().edits.invoice_number).toBe('LOCAL-1');
    useUiStore.getState().revert(field); expect(useUiStore.getState().edits.invoice_number).toBeUndefined();
  });
});
