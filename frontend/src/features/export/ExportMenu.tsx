import { Download, FileJson, FileSpreadsheet } from 'lucide-react';
import type { Field } from '../../model/view-model';
import { exportCsv, exportJson } from './export-data';

export function ExportMenu({ filename, data, fields, edits }: { filename: string; data: Record<string, unknown>; fields: Record<string, Field>; edits: Record<string, unknown> }) {
  const stem = filename.replace(/\.[^.]+$/, '').replace(/[^\w-]+/g, '-').toLowerCase() || 'invoice';
  return <details className="relative"><summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg border border-black/10 bg-white px-3 py-2 text-sm font-medium shadow-sm dark:border-white/10 dark:bg-white/5"><Download className="h-4 w-4" />Export</summary><div className="absolute right-0 z-30 mt-2 w-48 rounded-xl border border-black/10 bg-white p-1 shadow-xl dark:border-white/10 dark:bg-[#17201d]"><button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-black/5" onClick={() => exportJson(data, fields, edits, `${stem}.json`)}><FileJson className="h-4 w-4" />Export JSON</button><button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-black/5" onClick={() => exportCsv(fields, edits, `${stem}.csv`)}><FileSpreadsheet className="h-4 w-4" />Export CSV</button></div></details>;
}
