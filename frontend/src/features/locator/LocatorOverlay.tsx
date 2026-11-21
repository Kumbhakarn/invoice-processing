import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp } from 'lucide-react';
import { useUiStore } from '../../store/ui-store';
import type { ExtractionView, Field } from '../../model/view-model';
import { boxToPixels, getCalloutPlacement, getDirection, unionBoxes } from './geometry';

const arrows = { up: ArrowUp, down: ArrowDown, left: ArrowLeft, right: ArrowRight };

export function LocatorOverlay({ view, onPageRequest }: { view: ExtractionView; onPageRequest: (page: number) => void }) {
  const selectedPath = useUiStore((s) => s.selectedPath);
  const activeCandidates = useUiStore((s) => s.activeCandidates);
  const [edge, setEdge] = useState<{ direction: keyof typeof arrows; label: string; page: number } | null>(null);
  const [callout, setCallout] = useState<{ left: number; top: number; direction: 'up' | 'down' | 'left' | 'right'; label: string } | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const active = useMemo(() => {
    if (!selectedPath) return null;
    const field = view.fields[selectedPath];
    if (!field) return null;
    return activeLocation(field, activeCandidates[selectedPath] ?? 0);
  }, [selectedPath, view.fields, activeCandidates]);

  useEffect(() => {
    if (!active?.source) { setEdge(null); setCallout(null); return; }
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const host = root.current;
        if (!host) return;
        const page = document.querySelector<HTMLElement>(`[data-page="${active.source!.page}"]`);
        if (!page) { setEdge({ direction: 'down', label: `${active.field.label} · page ${active.source.page}`, page: active.source.page }); return; }
        const box = unionBoxes(active.source!.boxes);
        if (!box) return;
        const pageRect = page.getBoundingClientRect();
        const pixels = boxToPixels(box, pageRect.width, pageRect.height);
        const rect = { left: pageRect.left + pixels.left, top: pageRect.top + pixels.top, right: pageRect.left + pixels.left + pixels.width, bottom: pageRect.top + pixels.top + pixels.height };
        const viewportRect = { left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight };
        const direction = getDirection(rect, viewportRect);
        if (direction === 'visible') {
          setEdge(null);
          const placement = getCalloutPlacement(rect, viewportRect);
          setCallout({ left: placement.left, top: placement.top, direction: placement.direction, label: active.field.label });
        } else {
          setCallout(null);
          setEdge({ direction, label: `${active.field.label} · page ${active.source!.page}`, page: active.source!.page });
        }
      });
    };
    const resize = new ResizeObserver(update);
    if (root.current) resize.observe(root.current);
    window.addEventListener('scroll', update, { passive: true, capture: true });
    window.addEventListener('resize', update);
    update();
    return () => { cancelAnimationFrame(frame); resize.disconnect(); window.removeEventListener('scroll', update, true); window.removeEventListener('resize', update); };
  }, [active]);

  return <div ref={root} className="pointer-events-none absolute inset-0 z-20" aria-live="polite" aria-atomic="true">
    {edge && (() => { const Icon = arrows[edge.direction]; const position = edge.direction === 'up' ? 'left-1/2 top-3 -translate-x-1/2' : edge.direction === 'down' ? 'bottom-3 left-1/2 -translate-x-1/2' : edge.direction === 'left' ? 'left-3 top-1/2 -translate-y-1/2' : 'right-3 top-1/2 -translate-y-1/2'; return <button type="button" className={`pointer-events-auto fixed ${position} z-50 flex items-center gap-2 rounded-full bg-ink px-3 py-2 text-sm font-medium text-white shadow-lg`} onClick={() => { onPageRequest(edge.page); document.querySelector(`[data-page="${edge.page}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }}><Icon size={15} aria-hidden="true" />{edge.label}</button>; })()}
    {callout && (() => { const Icon = arrows[{ up: 'down', down: 'up', left: 'right', right: 'left' }[callout.direction] as keyof typeof arrows]; return <div className="fixed z-40 flex items-center gap-1.5 rounded-full border border-forest/20 bg-white/95 px-3 py-1.5 text-xs font-semibold text-forest shadow-md" style={{ left: callout.left, top: callout.top }}><Icon size={13} aria-hidden="true"/><span>{callout.label}</span><span className="sr-only">highlighted on document</span></div>; })()}
    <span className="sr-only">{edge ? `${edge.label} is ${edge.direction} of the viewport` : callout ? `${callout.label} is visible on page` : ''}</span>
  </div>;
}

function activeLocation(field: Field, candidateIndex: number) {
  if (field.status === 'located' && field.sources[0]) return { field, source: field.sources[0] };
  if (field.status === 'ambiguous' && field.candidates.length) return { field, source: field.candidates[candidateIndex % field.candidates.length] };
  return { field, source: null };
}
