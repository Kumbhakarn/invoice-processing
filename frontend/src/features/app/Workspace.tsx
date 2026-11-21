import { useEffect, useMemo, useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { FileText, Rows3 } from 'lucide-react';
import type { WorkspaceRenderProps } from './App';
import { DocumentViewer } from '../viewer/DocumentViewer';
import { FieldsPanel } from '../fields/FieldsPanel';
import { ValidationPanel } from '../validation/ValidationPanel';
import { ExportMenu } from '../export/ExportMenu';
import { editedFields, setPathValue } from '../editing/edit-utils';
import { useUiStore } from '../../store/ui-store';

export function Workspace({ view, file, documentUrl }: WorkspaceRenderProps) {
  const [mobileTab, setMobileTab] = useState<'document' | 'fields'>('document');
  const [narrow, setNarrow] = useState(() => window.matchMedia('(max-width: 767px)').matches);
  const edits = useUiStore((state) => state.edits);
  const setPanelSizes = useUiStore((state) => state.setPanelSizes);
  const panelSizes = useUiStore((state) => state.panelSizes);
  const select = useUiStore((state) => state.select);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return;
      if (event.key !== 'j' && event.key !== 'k') return;
      const needsReview = Object.values(view.fields).filter((field) => field.status !== 'located' || field.confidence?.toLowerCase() === 'low');
      if (!needsReview.length) return;
      event.preventDefault();
      const current = needsReview.findIndex((field) => field.path === useUiStore.getState().selectedPath);
      const next = event.key === 'j' ? (current + 1) % needsReview.length : (current - 1 + needsReview.length) % needsReview.length;
      select(needsReview[next]!.path);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [select, view.fields]);
  const currentData = useMemo(() => Object.entries(edits).reduce((data, [path, value]) => setPathValue(data, path, value), view.data), [edits, view.data]);
  const currentFields = useMemo(() => editedFields(view.fields, edits), [edits, view.fields]);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 767px)');
    const update = () => setNarrow(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  return <div className="mx-auto flex min-h-[calc(100vh-240px)] w-full max-w-[1800px] flex-col px-3 pb-5 sm:px-5">
      <div className="mb-2 flex items-center justify-end pt-1"><ExportMenu filename={view.filename} data={currentData} fields={currentFields} edits={edits} /></div>
      {narrow ? <>
        <div className="flex gap-1 border-b border-slate-200 px-4 dark:border-white/10" role="tablist" aria-label="Review panels">
          <button role="tab" aria-selected={mobileTab === 'document'} onClick={() => setMobileTab('document')} className={`flex flex-1 items-center justify-center gap-2 border-b-2 py-3 text-sm font-semibold ${mobileTab === 'document' ? 'border-forest text-forest' : 'border-transparent text-slate-500'}`}><FileText size={16}/>Document</button>
          <button role="tab" aria-selected={mobileTab === 'fields'} onClick={() => setMobileTab('fields')} className={`flex flex-1 items-center justify-center gap-2 border-b-2 py-3 text-sm font-semibold ${mobileTab === 'fields' ? 'border-forest text-forest' : 'border-transparent text-slate-500'}`}><Rows3 size={16}/>Fields</button>
        </div>
        <div className="min-h-[620px] flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel dark:border-white/10 dark:bg-[#17201d]">
          {mobileTab === 'document' ? <DocumentViewer view={view} file={file} documentUrl={documentUrl}/> : <div className="flex h-full flex-col"><div className="min-h-0 flex-1"><FieldsPanel fields={view.fields}/></div><div className="max-h-[32%] shrink-0 overflow-auto border-t border-slate-200 p-3"><ValidationPanel data={currentData} onSelectField={select}/></div></div>}
        </div>
      </> : <div className="flex min-h-[680px] flex-1 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel dark:border-white/10 dark:bg-[#17201d]">
        <PanelGroup direction="horizontal" autoSaveId="docextract-review-panels" onLayout={setPanelSizes}>
          <Panel defaultSize={panelSizes[0] ?? 54} minSize={32} className="flex min-w-0 flex-col"><DocumentViewer view={view} file={file} documentUrl={documentUrl}/></Panel>
          <PanelResizeHandle aria-label="Resize review panels" className="w-1.5 bg-slate-100 transition-colors hover:bg-forest/40 focus-visible:bg-forest dark:bg-white/5" />
          <Panel defaultSize={panelSizes[1] ?? 46} minSize={28} className="flex min-w-0 flex-col overflow-hidden border-l border-slate-200 dark:border-white/10"><div className="min-h-0 flex-1"><FieldsPanel fields={view.fields}/></div><div className="max-h-[34%] shrink-0 overflow-auto border-t border-slate-200 p-3 dark:border-white/10"><ValidationPanel data={currentData} onSelectField={select}/></div></Panel>
        </PanelGroup>
      </div>}
      <p className="px-2 pt-2 text-right text-[11px] text-slate-400">Edits are local to this browser session and are not saved on the server.</p>
    </div>;
}
