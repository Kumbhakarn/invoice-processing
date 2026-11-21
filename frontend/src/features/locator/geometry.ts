import type { Box } from '../../model/view-model';

export interface Rect { left: number; top: number; right: number; bottom: number }
export type Direction = 'up' | 'down' | 'left' | 'right';
export type Placement = { direction: Direction; left: number; top: number };

export function boxToPixels(box: Box, width: number, height: number) {
  return { left: box[0] * width, top: box[1] * height, width: (box[2] - box[0]) * width, height: (box[3] - box[1]) * height };
}

export function getDirection(target: Rect, viewport: Rect): Direction | 'visible' {
  if (target.left >= viewport.left && target.right <= viewport.right && target.top >= viewport.top && target.bottom <= viewport.bottom) return 'visible';
  const overflow = { up: Math.max(0, viewport.top - target.top), down: Math.max(0, target.bottom - viewport.bottom), left: Math.max(0, viewport.left - target.left), right: Math.max(0, target.right - viewport.right) };
  const relevant: Direction[] = [];
  if (target.top < viewport.top) relevant.push('up');
  if (target.bottom > viewport.bottom) relevant.push('down');
  if (target.left < viewport.left) relevant.push('left');
  if (target.right > viewport.right) relevant.push('right');
  return relevant.sort((a, b) => overflow[b] - overflow[a])[0] ?? 'down';
}

export function getCalloutPlacement(target: Rect, viewport: Rect, width = 184, height = 38, gap = 12): Placement {
  const spaces: Record<Direction, number> = { up: target.top - viewport.top, down: viewport.bottom - target.bottom, left: target.left - viewport.left, right: viewport.right - target.right };
  const verticalFits = { up: spaces.up >= height + gap, down: spaces.down >= height + gap };
  const horizontalFits = { left: spaces.left >= width + gap, right: spaces.right >= width + gap };
  const direction: Direction = (Object.keys(spaces) as Direction[]).sort((a, b) => spaces[b] - spaces[a]).find((side) => side === 'up' || side === 'down' ? verticalFits[side] : horizontalFits[side]) ?? (Object.keys(spaces) as Direction[]).sort((a, b) => spaces[b] - spaces[a])[0]!;
  let left = target.left + (target.right - target.left - width) / 2;
  let top = target.top + (target.bottom - target.top - height) / 2;
  if (direction === 'up') top = target.top - height - gap;
  if (direction === 'down') top = target.bottom + gap;
  if (direction === 'left') left = target.left - width - gap;
  if (direction === 'right') left = target.right + gap;
  return { direction, left: Math.max(viewport.left + 4, Math.min(left, viewport.right - width - 4)), top: Math.max(viewport.top + 4, Math.min(top, viewport.bottom - height - 4)) };
}

export function unionBoxes(boxes: readonly Box[]): Box | null {
  if (!boxes.length) return null;
  return [Math.min(...boxes.map((box) => box[0])), Math.min(...boxes.map((box) => box[1])), Math.max(...boxes.map((box) => box[2])), Math.max(...boxes.map((box) => box[3]))];
}
