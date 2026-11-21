import { useRef, useState } from 'react';
import { ArrowUpFromLine, Check, FileText, Image, LoaderCircle, ShieldCheck, X } from 'lucide-react';
import { ApiRequestError, isMockMode, uploadFile } from '../../api/client';
import { adaptEvidenceResponse } from '../../api/adapter';
import { validateUploadFile } from '../../api/upload-preflight';
import type { ExtractionView } from '../../model/view-model';

type QueueFile = { id: string; file: File; state: 'checking' | 'queued' | 'processing' | 'done' | 'error' | 'cancelled'; error?: string };
type EvidencePayload = Parameters<typeof adaptEvidenceResponse>[0];
const extension = (name: string) => name.toLowerCase().slice(name.lastIndexOf('.'));

export interface UploadPageProps {
  onComplete: (view: ExtractionView, file: File, documentUrl: string) => void;
  onHistory: () => void;
}

export function UploadPage({ onComplete, onHistory }: UploadPageProps) {
  const [queue, setQueue] = useState<QueueFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const controllerRef = useRef<AbortController | null>(null);

  function addFiles(list: FileList | File[]) {
    const incoming = Array.from(list).map((file): QueueFile => ({ id: crypto.randomUUID(), file, state: 'checking' }));
    setQueue((current) => [...current, ...incoming]);
    setMessage('');
    for (const item of incoming) void validateUploadFile(item.file).then((error) => update(item.id, error ? { state: 'error', error } : { state: 'queued' })).catch(() => update(item.id, { state: 'error', error: 'This file could not be checked in the browser.' }));
  }

  function update(id: string, changes: Partial<QueueFile>) { setQueue((items) => items.map((item) => item.id === id ? { ...item, ...changes } : item)); }

  async function processQueue() {
    if (busy) return;
    const first = queue.find((item) => item.state === 'queued');
    if (!first) return;
    setBusy(true);
    const controller = new AbortController(); controllerRef.current = controller;
    let fileId: string | undefined;
    update(first.id, { state: 'processing' });
    try {
      const payload = await uploadFile<EvidencePayload>(first.file, controller.signal, undefined, (headers) => { fileId = headers.get('X-File-ID') ?? undefined; });
      const view = adaptEvidenceResponse(payload, first.file.name);
      update(first.id, { state: 'done' });
      onComplete({ ...view, invoiceId: fileId ?? view.invoiceId }, first.file, URL.createObjectURL(first.file));
    } catch (error) {
      const apiError = error instanceof ApiRequestError ? error.apiError : undefined;
      update(first.id, { state: apiError?.code === 'REQUEST_ABORTED' ? 'cancelled' : 'error', error: apiError?.message ?? 'The document could not be processed.' });
      setMessage(apiError ? `${apiError.message}${apiError.requestId ? ` Request ID: ${apiError.requestId}` : ''}` : 'The document could not be processed.');
    } finally { controllerRef.current = null; setBusy(false); }
  }

  const acceptedCount = queue.filter((item) => item.state === 'queued').length;
  return <main className="mx-auto flex min-h-[calc(100vh-72px)] w-full max-w-6xl flex-col px-5 pb-12 pt-12 sm:px-8 lg:pt-16">
    <div className="mb-10 flex flex-wrap items-end justify-between gap-5">
      <div><p className="mb-3 text-xs font-semibold uppercase tracking-[.18em] text-forest">Document review</p><h1 className="max-w-xl text-4xl font-semibold tracking-[-.04em] text-ink sm:text-5xl">A clearer view of every invoice.</h1><p className="mt-4 max-w-lg text-base leading-7 text-slate-600">Bring a document in, review what was found, and trace each field back to its source.</p></div>
      <button onClick={onHistory} className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition hover:border-forest/40 hover:text-forest">Browse history <span aria-hidden="true">↗</span></button>
    </div>
    <section aria-label="Upload documents" onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={(event) => { if (event.currentTarget === event.target) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files); }} onClick={() => inputRef.current?.click()} className={`group cursor-pointer rounded-[28px] border-2 border-dashed px-6 py-12 text-center transition sm:px-12 sm:py-16 ${dragging ? 'border-forest bg-mint/70' : 'border-slate-300 bg-white/80 hover:border-forest/55 hover:bg-white'}`}>
      <input ref={inputRef} aria-label="Choose invoice documents" type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.webp,.tif,.tiff" className="sr-only" onChange={(event) => { if (event.target.files) addFiles(event.target.files); event.target.value = ''; }} />
      <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-mint text-forest transition group-hover:-translate-y-0.5"><ArrowUpFromLine size={25} /></div>
      <h2 className="text-xl font-semibold tracking-tight text-ink">Drop your documents here</h2>
      <p className="mt-2 text-sm text-slate-500">or <span className="font-semibold text-forest underline underline-offset-4">browse files</span> on your device</p>
      <div className="mt-7 flex flex-wrap justify-center gap-2 text-xs font-medium text-slate-500"><span className="rounded-full bg-slate-100 px-3 py-1.5">PDF</span><span className="rounded-full bg-slate-100 px-3 py-1.5">JPG / PNG</span><span className="rounded-full bg-slate-100 px-3 py-1.5">WEBP / TIFF</span><span className="rounded-full bg-slate-100 px-3 py-1.5">10 MiB max</span><span className="rounded-full bg-slate-100 px-3 py-1.5">50 pages max</span></div>
    </section>
    {queue.length > 0 && <section aria-label="Upload queue" className="mt-7 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
      <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="font-semibold">Upload queue</h2><p className="mt-0.5 text-xs text-slate-500">{acceptedCount} ready to process · files are processed one at a time</p></div><button disabled={busy || acceptedCount === 0} onClick={(event) => { event.stopPropagation(); void processQueue(); }} className="inline-flex items-center gap-2 rounded-xl bg-forest px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-forest/90 disabled:cursor-not-allowed disabled:opacity-45">{busy ? <LoaderCircle className="animate-spin" size={16} /> : <ArrowUpFromLine size={16} />} {busy ? 'Processing' : 'Start review'}</button></header>
      <ul className="divide-y divide-slate-100">{queue.map((item) => <li key={item.id} className="flex flex-wrap items-center gap-3 px-5 py-4"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-50 text-slate-500">{extension(item.file.name) === '.pdf' ? <FileText size={19} /> : <Image size={19} />}</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{item.file.name}</p><p className={`mt-1 text-xs ${item.error ? 'text-rose-700' : 'text-slate-500'}`}>{item.error ?? `${(item.file.size / 1024 / 1024).toFixed(2)} MiB · ${item.state === 'checking' ? 'Checking file…' : item.state === 'queued' ? 'Ready' : item.state === 'processing' ? 'Extracting fields…' : item.state === 'done' ? 'Review opened' : item.state}`}</p>{item.state === 'processing' && <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full animate-pulse rounded-full bg-forest" style={{ width: '38%' }} /></div>}</div><div className="flex items-center gap-2">{item.state === 'done' && <Check className="text-forest" size={18} aria-label="Complete" />}{item.state === 'error' && <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">Needs attention</span>}{item.state === 'queued' && <button aria-label={`Remove ${item.file.name}`} onClick={(event) => { event.stopPropagation(); setQueue((items) => items.filter((row) => row.id !== item.id)); }} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"><X size={16} /></button>}</div></li>)}</ul>
      {busy && <button onClick={(event) => { event.stopPropagation(); controllerRef.current?.abort(); }} className="w-full border-t border-slate-100 px-5 py-3 text-sm font-medium text-rose-700 hover:bg-rose-50">Cancel upload</button>}
    </section>}
    {message && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{message}</p>}
    <div className="mt-8 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-center text-xs text-slate-500"><ShieldCheck size={15} className="text-forest" /> {isMockMode() ? 'Mock mode is on — no AI provider requests are made.' : 'Uploads call AI providers and may incur charges.'}</div>
    <p className="mt-auto pt-14 text-center text-xs leading-5 text-slate-400">Local development only · No authentication · Not for public deployment</p>
  </main>;
}
