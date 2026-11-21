import { describe, expect, it } from 'vitest';
import { setPathValue } from './edit-utils';

describe('local edit path updates', () => {
  it('updates nested line item values without mutating the extraction', () => {
    const source = { line_items: [{ amount: 12, label: 'Tea' }] };
    const changed = setPathValue(source, 'line_items[0].amount', '14');
    expect(changed.line_items).toEqual([{ amount: '14', label: 'Tea' }]);
    expect(source.line_items[0].amount).toBe(12);
  });
});
