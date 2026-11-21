import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '../../api/client';
import type { components } from '../../api/generated';

type InvoiceData = components['schemas']['InvoiceExtractionData'];
type Validation = components['schemas']['InvoiceValidationResult'];
export function useValidation(data: Record<string, unknown> | null, debounceMs = 450) {
  const [settled, setSettled] = useState<Record<string, unknown> | null>(data);
  const fingerprint = data ? JSON.stringify(data) : '';
  useEffect(() => { const timer = window.setTimeout(() => setSettled(fingerprint ? JSON.parse(fingerprint) as Record<string, unknown> : null), debounceMs); return () => window.clearTimeout(timer); }, [fingerprint, debounceMs]);
  return useQuery({
    queryKey: ['invoice-validation', fingerprint],
    enabled: Boolean(settled), retry: false, refetchOnWindowFocus: false,
    queryFn: () => apiRequest<Validation>('/api/validate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settled as InvoiceData) }),
  });
}
