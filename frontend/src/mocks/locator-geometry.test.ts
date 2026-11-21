import { describe, expect, it } from 'vitest';
import type { Box } from '../model/view-model';
import { boxToPixels, getCalloutPlacement, getDirection, unionBoxes, type Rect } from '../features/locator/geometry';

const viewport: Rect = { left: 0, top: 0, right: 1000, bottom: 800 };

describe('locator geometry', () => {
  it.each([
    ['fully visible', { left: 100, top: 120, right: 200, bottom: 150 }, 'visible'],
    ['above', { left: 100, top: -60, right: 200, bottom: -20 }, 'up'],
    ['below', { left: 100, top: 820, right: 200, bottom: 860 }, 'down'],
    ['left', { left: -80, top: 120, right: -20, bottom: 150 }, 'left'],
    ['right', { left: 1020, top: 120, right: 1080, bottom: 150 }, 'right'],
  ] as const)('chooses direction for a target %s', (_name, target, expected) => {
    expect(getDirection(target, viewport)).toBe(expected);
  });

  it('handles partially visible targets using the greatest overflow', () => {
    expect(getDirection({ left: 990, top: 790, right: 1040, bottom: 840 }, viewport)).toBe('down');
    expect(getDirection({ left: 10, top: -70, right: 1010, bottom: 810 }, viewport)).toBe('up');
  });

  it('unions multiple source boxes into one target extent', () => {
    const boxes: Box[] = [[0.1, 0.2, 0.25, 0.3], [0.18, 0.4, 0.55, 0.48], [0.6, 0.1, 0.8, 0.15]];
    expect(unionBoxes(boxes)).toEqual([0.1, 0.1, 0.8, 0.48]);
    expect(unionBoxes([])).toBeNull();
  });

  it('places a callout in available space and clamps it inside the viewport', () => {
    const placement = getCalloutPlacement({ left: 450, top: 340, right: 490, bottom: 360 }, viewport);
    expect(placement.direction).toBe('right');
    expect(placement.left).toBeGreaterThanOrEqual(4);
    expect(placement.top).toBeGreaterThanOrEqual(4);
    expect(placement.left + 184).toBeLessThanOrEqual(996);
    expect(placement.top + 38).toBeLessThanOrEqual(796);
    const clamped = getCalloutPlacement({ left: 0, top: 0, right: 8, bottom: 8 }, viewport, 184, 38);
    expect(clamped.left).toBe(20);
    expect(clamped.top).toBe(4);
  });

  it('converts normalized coordinates to pixels at different zoomed page sizes', () => {
    const box: Box = [0.1, 0.2, 0.35, 0.4];
    expect(boxToPixels(box, 500, 700)).toMatchObject({ left: 50, top: 140, height: 140 });
    expect(boxToPixels(box, 500, 700).width).toBeCloseTo(125);
    expect(boxToPixels(box, 1000, 1400)).toMatchObject({ left: 100, top: 280, height: 280 });
    expect(boxToPixels(box, 1000, 1400).width).toBeCloseTo(250);
    expect(boxToPixels(box, 250, 350)).toMatchObject({ left: 25, top: 70, height: 70 });
    expect(boxToPixels(box, 250, 350).width).toBeCloseTo(62.5);
  });

  it('keeps direction math valid at the first and last page viewport positions', () => {
    const firstPageTarget = { left: 160, top: 30, right: 220, bottom: 48 };
    const lastPageTarget = { left: 160, top: 920, right: 220, bottom: 950 };
    expect(getDirection(firstPageTarget, viewport)).toBe('visible');
    expect(getDirection(lastPageTarget, viewport)).toBe('down');
  });
});
