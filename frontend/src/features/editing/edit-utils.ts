import type { Field } from '../../model/view-model';

export function editedFields(fields: Record<string, Field>, edits: Record<string, unknown>) {
  return Object.fromEntries(Object.entries(fields).map(([path, field]) => [path, { ...field, value: path in edits ? edits[path] : field.value, edited: path in edits }]));
}

export function setPathValue(source: Record<string, unknown>, path: string, value: unknown): Record<string, unknown> {
  const result = structuredClone(source);
  const parts = path.replace(/\[(\d+)\]/g, '.$1').split('.');
  let current: Record<string, unknown> | unknown[] = result;
  for (const part of parts.slice(0, -1)) {
    const key: string | number = /^\d+$/.test(part) ? Number(part) : part;
    const next = (current as Record<string | number, unknown>)[key];
    current = next as Record<string, unknown> | unknown[];
  }
  const final = parts.at(-1)!;
  (current as Record<string | number, unknown>)[/^\d+$/.test(final) ? Number(final) : final] = value;
  return result;
}
