import { useCallback, useEffect, useRef, type ReactNode } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import type { ExtractionView } from '../../model/view-model';
import { useUiStore } from '../../store/ui-store';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();

export default function PdfDocument({ url, dimensions, zoom, selectedPage, onPage, onField, view, showAll }: { url: string; dimensions: ExtractionView['pages']; zoom: number; selectedPage: number; onPage: (page: number) => void; onField: (path: string) => void; view: ExtractionView; showAll: boolean }) {
  const selectedPath = useUiStore((s) => s.selectedPath);
  const hoveredPath = useUiStore((s) => s.hoveredPath);
  const activePath = selectedPath ?? hoveredPath;
  const candidateIndex = useUiStore((s) => activePath ? s.activeCandidates[activePath] ?? 0 : 0);
  const handlePageVisible = useCallback((entry: IntersectionObserverEntry) => {
    if (entry.isIntersecting) { const page = Number((entry.target as HTMLElement).dataset.page); if (page) onPage(page); }
  }, [onPage]);
  return <Document file={url} loading={<p className="mx-auto my-12 text-center text-sm text-slate-400">Opening PDF…</p>} error={<p className="mx-auto my-12 max-w-sm rounded-xl bg-white p-6 text-center text-sm text-slate-600">This PDF could not be displayed. You can still review the extracted fields.</p>} className="mx-auto flex w-fit flex-col items-center gap-5">
    {(dimensions.length ? dimensions : [{ page: 1, width: 850, height: 1100 }]).map((dimension) => <ObservedPage key={dimension.page} number={dimension.page} width={Math.min(850, dimension.width) * zoom} onVisible={handlePageVisible} selectedPage={selectedPage}>
      {Math.abs(dimension.page - selectedPage) <= 2 ? <Page pageNumber={dimension.page} width={Math.min(850, dimension.width) * zoom} renderTextLayer={false} renderAnnotationLayer={false} loading={<div className="animate-pulse bg-white" style={{ width: Math.min(850, dimension.width) * zoom, aspectRatio: `${dimension.width}/${dimension.height}` }}/>} /> : <div aria-hidden="true" className="bg-white" style={{ width: Math.min(850, dimension.width) * zoom, aspectRatio: `${dimension.width}/${dimension.height}` }} />}
      {Math.abs(dimension.page - selectedPage) <= 2 && <PageEvidence view={view} page={dimension.page} onField={onField} activePath={activePath} candidateIndex={candidateIndex} showAll={showAll}/ >}
    </ObservedPage>)}
  </Document>;
}

function ObservedPage({ number, width, selectedPage, onVisible, children }: { number: number; width: number; selectedPage: number; onVisible: (entry: IntersectionObserverEntry) => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current; if (!node) return;
    const observer = new IntersectionObserver(([entry]) => { if (entry) onVisible(entry); }, { threshold: 0.3 });
    observer.observe(node); return () => observer.disconnect();
  }, [onVisible]);
  return <div ref={ref} data-page={number} className={`relative mx-auto bg-white shadow-xl ${selectedPage === number ? 'ring-1 ring-forest/20' : ''}`} style={{ width }}>{children}</div>;
}

function PageEvidence({ view, page, onField, activePath, candidateIndex, showAll }: { view: ExtractionView; page: number; onField: (path: string) => void; activePath: string | null; candidateIndex: number; showAll: boolean }) {
  return <div className="pointer-events-none absolute inset-0">
    {Object.values(view.fields).map((field) => {
      const source = field.status === 'located' ? field.sources[0] : field.status === 'ambiguous' ? field.candidates[candidateIndex % Math.max(field.candidates.length, 1)] : undefined;
      if (!source || source.page !== page || (!showAll && field.path !== activePath)) return null;
      return source.boxes.map((box, index) => <button key={`${field.path}-${index}`} type="button" aria-label={`Focus ${field.label}`} className={`pointer-events-auto absolute rounded-sm border-2 transition-opacity ${field.path === activePath ? 'z-10 animate-[locator-in_.35s_ease-out] border-forest bg-emerald-300/20 shadow-[0_0_0_2px_rgba(255,255,255,.85)]' : 'border-amber-400/50 bg-amber-100/10'} ${source.estimated ? 'border-dashed' : ''}`} style={{ left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, width: `${(box[2] - box[0]) * 100}%`, height: `${(box[3] - box[1]) * 100}%`, pointerEvents: 'auto' }} onClick={() => onField(field.path)} />);
    })}
  </div>;
}
