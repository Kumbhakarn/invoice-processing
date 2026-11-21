import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Maximize, Minus, Plus, RotateCcw } from 'lucide-react';
import type { ExtractionView } from '../../model/view-model';
import { useUiStore } from '../../store/ui-store';
import { LocatorOverlay } from '../locator/LocatorOverlay';

const PdfDocument = lazy(() => import('./PdfDocument'));

export function DocumentViewer({ view, file, documentUrl }: { view: ExtractionView; file?: File | null; documentUrl?: string | null }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const zoom = useUiStore((s) => s.zoom); const setZoom = useUiStore((s) => s.setZoom);
  const page = useUiStore((s) => s.page); const setPage = useUiStore((s) => s.setPage);
  const select = useUiStore((s) => s.select);
  useEffect(() => {
    if (!file) { setObjectUrl(null); return; }
    const url = URL.createObjectURL(file); setObjectUrl(url); return () => URL.revokeObjectURL(url);
  }, [file]);
  const url = documentUrl ?? objectUrl;
  const maxPage = Math.max(1, view.pages.length || 1);
  const isPdf = file?.type === 'application/pdf' || view.filename.toLowerCase().endsWith('.pdf');
  const isTiff = /\.tiff?$/i.test(view.filename);
  const dimensions = useMemo(() => view.pages.length ? view.pages : [{ page: 1, width: 850, height: 1100 }], [view.pages]);
  function movePage(next: number) { const bounded = Math.max(1, Math.min(maxPage, next)); setPage(bounded); document.querySelector(`[data-page="${bounded}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
  function zoomBy(factor: number) { setZoom(zoom * factor); }
  return <section className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-[#eceeeb]" aria-label="Document viewer">
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-black/5 bg-white px-3 text-xs text-slate-600">
      <div className="flex items-center gap-1"><button aria-label="Previous page" className="rounded p-2 hover:bg-slate-100 disabled:opacity-40" disabled={page <= 1} onClick={() => movePage(page - 1)}><ChevronLeft size={16}/></button><span className="min-w-16 text-center">Page {page} / {maxPage}</span><button aria-label="Next page" className="rounded p-2 hover:bg-slate-100 disabled:opacity-40" disabled={page >= maxPage} onClick={() => movePage(page + 1)}><ChevronRight size={16}/></button></div>
      <div className="flex items-center gap-1"><button aria-label="Zoom out" className="rounded p-2 hover:bg-slate-100" onClick={() => zoomBy(.9)}><Minus size={15}/></button><span className="w-11 text-center">{Math.round(zoom * 100)}%</span><button aria-label="Zoom in" className="rounded p-2 hover:bg-slate-100" onClick={() => zoomBy(1.1)}><Plus size={15}/></button><button aria-label="Fit page" className="rounded p-2 hover:bg-slate-100" onClick={() => setZoom(1)}><Maximize size={15}/></button><button aria-label="Reset zoom" className="rounded p-2 hover:bg-slate-100" onClick={() => setZoom(1)}><RotateCcw size={14}/></button></div>
    </div>
    <div ref={scrollRef} data-document-scroll className="min-h-0 flex-1 overflow-auto px-4 py-6" onWheel={(event) => { if (event.ctrlKey) { event.preventDefault(); zoomBy(event.deltaY < 0 ? 1.05 : .95); } }}>
      {!url ? <div className="mx-auto mt-20 max-w-md rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{view.originalDeleted ? 'Original document was deleted. Extracted fields are still available; highlights cannot be shown.' : 'No original document is available. Extracted fields are shown without highlights.'}</div> : isTiff ? <div className="mx-auto mt-20 max-w-md rounded-2xl bg-white p-8 text-center text-sm text-slate-600">This browser cannot preview TIFF files yet. The extracted fields remain available for review.</div> : isPdf ? <Suspense fallback={<div className="mx-auto mt-12 animate-pulse rounded bg-white p-16 text-center text-slate-400">Loading document pages…</div>}><PdfDocument url={url} dimensions={dimensions} zoom={zoom} selectedPage={page} onPage={setPage} onField={select} view={view} showAll={showAll}/></Suspense> : <div className="relative mx-auto w-fit shadow-xl" style={{ width: `${Math.min(850, Math.max(400, dimensions[0]?.width ?? 850)) * zoom}px` }} data-page="1"><img src={url} alt={`Uploaded document ${view.filename}`} className="block h-auto w-full bg-white" onError={(event) => { event.currentTarget.hidden = true; }} /><FieldBoxes view={view} pageNumber={1} onSelect={select} showAll={showAll}/></div>}
    </div>
    <div className="absolute bottom-4 right-4 z-30 flex items-center gap-2"><button onClick={() => setShowAll((state) => !state)} aria-pressed={showAll} className="rounded-full border border-slate-200 bg-white/95 px-3 py-2 text-xs font-medium text-slate-600 shadow hover:text-ink">{showAll ? 'Hide all fields' : 'Show all fields'}</button></div>
    <LocatorOverlay view={view} onPageRequest={movePage}/>
  </section>;
}

function FieldBoxes({ view, pageNumber, onSelect, showAll }: { view: ExtractionView; pageNumber: number; onSelect: (path: string) => void; showAll: boolean }) {
  const selectedPath = useUiStore((s) => s.selectedPath); const hoveredPath = useUiStore((s) => s.hoveredPath); const activePath = selectedPath ?? hoveredPath; const candidate = useUiStore((s) => activePath ? s.activeCandidates[activePath] ?? 0 : 0);
  return <div className="pointer-events-none absolute inset-0">{Object.values(view.fields).flatMap((field) => {
    const source = field.status === 'located' ? field.sources[0] : field.status === 'ambiguous' ? field.candidates[candidate % Math.max(field.candidates.length, 1)] : undefined;
    return source?.page === pageNumber && (showAll || field.path === activePath) ? source.boxes.map((box, index) => <button key={`${field.path}-${index}`} aria-label={`Focus ${field.label}`} className={`pointer-events-auto absolute rounded-sm border-2 ${field.path === activePath ? 'z-10 border-forest bg-emerald-400/20 shadow-[0_0_0_2px_rgba(255,255,255,.8)]' : 'border-amber-400/50 bg-amber-100/10 opacity-0 hover:opacity-100'} ${source.estimated ? 'border-dashed' : ''}`} style={{ left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, width: `${(box[2] - box[0]) * 100}%`, height: `${(box[3] - box[1]) * 100}%`, pointerEvents: 'auto' }} onClick={() => onSelect(field.path)}/>) : [];
  })}</div>;
}
