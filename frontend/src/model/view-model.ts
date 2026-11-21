export type ConfidenceBand = 'high' | 'medium' | 'low' | 'unknown';
export type FieldStatus = 'located' | 'ambiguous' | 'unavailable';
export type FieldReason = 'not_found' | 'ambiguous' | 'ocr_failed' | 'low_quality' | 'no_evidence';
export type Box = readonly [number, number, number, number];
export interface FieldSource { page: number; boxes: Box[]; estimated?: boolean }
export interface FieldCandidate extends FieldSource { matchScore?: number; evidenceText?: string }
export interface Field {
  path: string; label: string; value: unknown; raw: string | null; confidence: string | null;
  status: FieldStatus; reason: FieldReason | null; sources: FieldSource[]; candidates: FieldCandidate[];
  edited: boolean; originalValue: unknown;
}
export interface ExtractionView {
  filename: string; data: Record<string, unknown>; fields: Record<string, Field>;
  pages: { page: number; width: number; height: number }[];
  meta: { timingsMs: Record<string, number>; providerUsage: { provider: string; model: string; inputTokens: number | null; outputTokens: number | null; reasoningTokens: number | null }[]; warnings: string[] };
  invoiceId?: string; originalDeleted?: boolean;
}
export interface HistoryEntry {
  id: string; filename: string; status: 'succeeded' | 'failed' | 'unknown'; createdAt?: string;
  uploadedAt?: string; processedAt?: string; validationStatus?: 'valid' | 'needs_review' | 'invalid';
}
export interface HistoryPageView { items: HistoryEntry[]; total: number; page: number; pageSize: number }
