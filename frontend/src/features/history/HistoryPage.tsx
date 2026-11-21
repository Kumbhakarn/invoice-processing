import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDown, ArrowLeft, ArrowUp, FileText, LoaderCircle, Trash2 } from 'lucide-react';
import { ApiRequestError, apiRequest } from '../../api/client';
import { adaptHistoryResponse, adaptStoredResult } from '../../api/adapter';
import type { ExtractionView, HistoryEntry } from '../../model/view-model';

type SortKey = 'created_at' | 'uploaded_at' | 'processed_at' | 'original_filename' | 'status';
type Filter = 'all' | 'succeeded' | 'failed';
const disabledMessage = 'History is disabled on this server. The service has not enabled invoice history for this environment.';
const isDisabled = (error: unknown) => error instanceof ApiRequestError && (error.apiError.status === 404 || error.apiError.status === 403 || error.apiError.code === 'INVOICE_HISTORY_DISABLED');

export interface HistoryPageProps { onBack: () => void; onOpen: (view: ExtractionView, documentUrl: string) => void }

export function HistoryPage({ onBack, onOpen }: HistoryPageProps) {
  const [page, setPage] = useState(1); const [filter, setFilter] = useState<Filter>('all'); const [sortBy, setSortBy] = useState<SortKey>('created_at'); const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [confirming, setConfirming] = useState<HistoryEntry | null>(null); const [notice, setNotice] = useState('');
  const query = useQuery({ queryKey: ['invoice-history', page, filter, sortBy, sortOrder], queryFn: () => apiRequest<unknown>(`/api/invoices?page=${page}&page_size=10${filter === 'all' ? '' : `&status=${filter}`}&sort_by=${sortBy}&sort_order=${sortOrder}`) });
  const history = adaptHistoryResponse(query.data);
  const rows = history.items;

  async function openInvoice(row: HistoryEntry) {
    const id = row.id;
    if (!id) { setNotice('This history record does not include an invoice identifier.'); return; }
    try {
      const result = await apiRequest<Record<string, unknown>>(`/api/invoices/${encodeURIComponent(id)}/result`);
      const data = (result.data && typeof result.data === 'object' ? result.data : result) as Record<string, unknown>;
      const name = row.filename;
      const view = adaptStoredResult(data, name, id);
      try {
        const original = await apiRequest<Blob>(`/api/invoices/${encodeURIComponent(id)}/document`, { responseType: 'blob' });
        onOpen(view, URL.createObjectURL(original));
      } catch (error) {
        if (error instanceof ApiRequestError && (error.apiError.code === 'DOCUMENT_NOT_FOUND' || error.apiError.status === 404)) {
          onOpen({ ...view, originalDeleted: true }, '');
          return;
        }
        throw error;
      }
    } catch (error) {
      setNotice(error instanceof ApiRequestError ? `${error.apiError.message}${error.apiError.requestId ? ` Request ID: ${error.apiError.requestId}` : ''}` : 'Could not open this saved invoice.');
    }
  }

  async function deleteOriginal() {
    if (!confirming) return;
    const id = confirming.id;
    try {
      await apiRequest<unknown>(`/api/invoices/${encodeURIComponent(id!)}/document`, { method: 'DELETE' });
      setNotice('Original document deleted. The history record and extraction result remain.');
      await query.refetch();
    } catch (error) { setNotice(error instanceof ApiRequestError ? error.apiError.message : 'Could not delete the original document.'); }
    setConfirming(null);
  }

  const disabled = isDisabled(query.error);
  return <main className="mx-auto min-h-[calc(100vh-72px)] w-full max-w-6xl px-5 py-9 sm:px-8">
    <button onClick={onBack} className="mb-7 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-ink"><ArrowLeft size={16} /> Back to upload</button>
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4"><div><p className="mb-2 text-xs font-semibold uppercase tracking-[.18em] text-forest">Your workspace</p><h1 className="text-3xl font-semibold tracking-tight">Invoice history</h1><p className="mt-2 text-sm text-slate-500">Saved extractions and their processing status.</p></div><label className="text-xs font-medium text-slate-500">Status <select value={filter} onChange={(e) => { setPage(1); setFilter(e.target.value as Filter); }} className="ml-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-ink"><option value="all">All statuses</option><option value="succeeded">Succeeded</option><option value="failed">Failed</option></select></label></div>
    {query.isLoading && <div className="flex min-h-56 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-500"><LoaderCircle className="mr-2 animate-spin" size={18} /> Loading history…</div>}
    {disabled && <section className="rounded-2xl border border-amber-200 bg-amber-50 px-6 py-7"><h2 className="font-semibold text-amber-950">History is disabled on this server</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-amber-900/80">{disabledMessage}</p></section>}
    {query.error && !disabled && !query.isLoading && <section role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6"><h2 className="font-semibold text-rose-900">Could not load invoice history</h2><p className="mt-2 text-sm text-rose-800">{query.error instanceof ApiRequestError ? query.error.apiError.message : 'Please try again.'}</p><button onClick={() => void query.refetch()} className="mt-4 rounded-lg border border-rose-300 px-3 py-2 text-sm font-semibold text-rose-900">Try again</button></section>}
    {!query.isLoading && !query.error && rows.length === 0 && <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center"><div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-50 text-slate-400"><FileText size={22} /></div><h2 className="mt-4 font-semibold">No saved invoices yet</h2><p className="mt-2 text-sm text-slate-500">When an extraction is stored, you’ll find it here.</p></div>}
    {rows.length > 0 && <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="overflow-x-auto"><table className="w-full min-w-[660px] border-collapse text-left"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Document</th><th className="px-5 py-3 font-semibold"><button onClick={() => { setSortBy('status'); setSortOrder((x) => x === 'asc' ? 'desc' : 'asc'); }}>Status <SortIcon active={sortBy === 'status'} order={sortOrder} /></button></th><th className="px-5 py-3 font-semibold"><button onClick={() => { setSortBy('created_at'); setSortOrder((x) => x === 'asc' ? 'desc' : 'asc'); }}>Added <SortIcon active={sortBy === 'created_at'} order={sortOrder} /></button></th><th className="px-5 py-3 font-semibold">Validation</th><th className="px-5 py-3" /></tr></thead><tbody className="divide-y divide-slate-100">{rows.map((row) => <tr key={row.id} className="group hover:bg-slate-50/70"><td className="px-5 py-4"><button onClick={() => void openInvoice(row)} className="inline-flex max-w-sm items-center gap-3 text-left"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-mint text-forest"><FileText size={17} /></span><span><span className="block truncate text-sm font-semibold text-ink group-hover:text-forest">{row.filename}</span><span className="mt-1 block text-xs text-slate-400">{row.id}</span></span></button></td><td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${row.status === 'succeeded' ? 'bg-emerald-50 text-emerald-800' : row.status === 'failed' ? 'bg-rose-50 text-rose-800' : 'bg-slate-100 text-slate-700'}`}>{row.status}</span></td><td className="px-5 py-4 text-sm text-slate-500">{formatDate(row.processedAt ?? row.createdAt ?? row.uploadedAt)}</td><td className="px-5 py-4 text-xs text-slate-400">{row.validationStatus ?? 'Not available'}</td><td className="px-5 py-4 text-right"><button aria-label={`Delete original for ${row.filename}`} onClick={() => setConfirming(row)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700"><Trash2 size={16} /></button></td></tr>)}</tbody></table></div><footer className="flex items-center justify-between border-t border-slate-100 px-5 py-3"><span className="text-xs text-slate-500">Page {history.page}{history.total != null ? ` · ${history.total} records` : ''}</span><div className="flex gap-2"><button disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40">Previous</button><button disabled={rows.length < history.pageSize} onClick={() => setPage((p) => p + 1)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40">Next</button></div></footer></div>}
    {notice && <p role="status" className="mt-4 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">{notice}</p>}
    {confirming && <div role="presentation" className="fixed inset-0 z-50 grid place-items-center bg-ink/35 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setConfirming(null); }}><section role="dialog" aria-modal="true" aria-labelledby="delete-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><h2 id="delete-title" className="text-lg font-semibold">Delete the original document?</h2><p className="mt-3 text-sm leading-6 text-slate-600">This removes only the uploaded file. The history entry and extracted result will stay available.</p><div className="mt-6 flex justify-end gap-2"><button onClick={() => setConfirming(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium">Keep document</button><button onClick={() => void deleteOriginal()} className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white">Delete original</button></div></section></div>}
  </main>;
}
function SortIcon({ active, order }: { active: boolean; order: 'asc' | 'desc' }) { return active ? order === 'asc' ? <ArrowUp className="ml-1 inline" size={12} /> : <ArrowDown className="ml-1 inline" size={12} /> : null; }
function formatDate(value?: string) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.valueOf()) ? '—' : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); }
