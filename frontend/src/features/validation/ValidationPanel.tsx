import { AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { useValidation } from './use-validation';

export function ValidationPanel({ data, onSelectField }: { data: Record<string, unknown> | null; onSelectField?: (field: string) => void }) {
  const query = useValidation(data);
  if (!data) return <div className="rounded-xl border border-black/10 bg-white p-4 text-sm text-black/50">Validation appears when extraction data is available.</div>;
  if (query.isPending) return <div className="animate-pulse rounded-xl border border-black/10 bg-white p-4 text-sm text-black/50">Checking business rules…</div>;
  if (query.isError) return <div role="status" className="rounded-xl border border-amber/20 bg-amber/5 p-4 text-sm text-amber">Validation is temporarily unavailable. Your extracted data is unchanged.</div>;
  const result = query.data;
  const errors = result.issues.filter((item) => item.severity === 'error'); const warnings = result.issues.filter((item) => item.severity === 'warning');
  const status = result.status;
  return <section aria-label="Business validation" className="rounded-xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-[#17201d]"><div className="flex items-start gap-3">{status === 'valid' ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-forest" /> : status === 'invalid' ? <AlertCircle className="mt-0.5 h-5 w-5 text-red-600" /> : <Info className="mt-0.5 h-5 w-5 text-amber" />}<div><h3 className="font-semibold">{status === 'valid' ? 'Business checks passed' : status === 'invalid' ? 'Review required fields' : 'Needs review'}</h3><p className="mt-1 text-xs text-black/55">These checks do not change extracted values.</p></div></div>
    {errors.length > 0 && <IssueGroup title="Errors" issues={errors} onSelectField={onSelectField} />}{warnings.length > 0 && <IssueGroup title="Warnings" issues={warnings} onSelectField={onSelectField} />}
  </section>;
}
function IssueGroup({ title, issues, onSelectField }: { title: string; issues: { rule_id: string; field: string; severity: string; message: string }[]; onSelectField?: (field: string) => void }) {
  return <div className="mt-4"><h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-black/50">{title} · {issues.length}</h4><ul className="space-y-2">{issues.map((issue) => <li key={issue.rule_id + issue.field}><button onClick={() => onSelectField?.(issue.field)} className="w-full rounded-lg bg-paper px-3 py-2 text-left text-sm hover:ring-1 hover:ring-forest/40"><span className="font-medium">{issue.field.replaceAll('_', ' ')}</span><span className="mt-0.5 block text-xs leading-relaxed text-black/60">{issue.message}</span></button></li>)}</ul></div>;
}
