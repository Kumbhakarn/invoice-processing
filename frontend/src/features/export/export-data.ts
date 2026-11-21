import type { Field } from '../../model/view-model';

export function buildEditedData(data: Record<string, unknown>, fields: Record<string, Field>, edits: Record<string, unknown>): Record<string, unknown> {
  const copy = structuredClone(data);
  for (const [path, value] of Object.entries(edits)) {
    if (!fields[path]) continue;
    const tokens = path.replace(/\[(\d+)\]/g, '.$1').split('.');
    let cursor: Record<string, unknown> | unknown[] = copy;
    for (const token of tokens.slice(0, -1)) cursor = (cursor as Record<string | number, unknown>)[/^\d+$/.test(token) ? Number(token) : token] as Record<string, unknown> | unknown[];
    const end = tokens.at(-1)!;
    (cursor as Record<string | number, unknown>)[/^\d+$/.test(end) ? Number(end) : end] = value;
  }
  return copy;
}
export function toCsv(fields: Record<string, Field>, edits: Record<string, unknown>): string {
  const quote = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`;
  return ['Field,Value,Confidence,Location status', ...Object.values(fields).map((f) => [f.label, edits[f.path] ?? f.value, f.confidence ?? '', f.status].map(quote).join(','))].join('\r\n');
}
export function downloadText(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}
export function exportJson(data: Record<string, unknown>, fields: Record<string, Field>, edits: Record<string, unknown>, filename = 'invoice.json') { downloadText(filename, JSON.stringify(buildEditedData(data, fields, edits), null, 2), 'application/json'); }
export function exportCsv(fields: Record<string, Field>, edits: Record<string, unknown>, filename = 'invoice.csv') { downloadText(filename, toCsv(fields, edits), 'text/csv;charset=utf-8'); }
