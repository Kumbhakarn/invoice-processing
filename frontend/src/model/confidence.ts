export const CONFIDENCE_BANDS = { high: 0.9, medium: 0.7 } as const;
export function confidenceBand(value: string | number | null | undefined) {
  const score = typeof value === 'number' ? value : value?.toLowerCase();
  if (score === 'high' || (typeof score === 'number' && score >= CONFIDENCE_BANDS.high)) return 'high' as const;
  if (score === 'medium' || (typeof score === 'number' && score >= CONFIDENCE_BANDS.medium)) return 'medium' as const;
  if (score === 'low' || typeof score === 'number') return 'low' as const;
  return 'unknown' as const;
}
