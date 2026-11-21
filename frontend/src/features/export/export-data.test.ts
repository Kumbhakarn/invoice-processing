import { describe, expect, it } from 'vitest';
import { buildEditedData, toCsv } from './export-data';
import type { Field } from '../../model/view-model';

const field: Field = { path: 'invoice_number', label: 'Invoice number', value: 'A-1', raw: null, confidence: 'High', status: 'unavailable', reason: 'not_found', sources: [], candidates: [], edited: false, originalValue: 'A-1' };
describe('export helpers', () => {
  it('exports locally edited values in structured JSON data', () => {
    const result = buildEditedData({ invoice_number: 'A-1' }, { invoice_number: field }, { invoice_number: 'A-2', unknown: 'ignored' });
    expect(result).toEqual({ invoice_number: 'A-2' });
  });
  it('quotes CSV cells safely', () => {
    expect(toCsv({ invoice_number: { ...field, value: 'A,"1' } }, {})).toContain('"Invoice number","A,""1","High","unavailable"');
  });
});
