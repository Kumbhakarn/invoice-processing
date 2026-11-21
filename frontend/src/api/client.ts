import type { paths } from './generated';

export type ApiError = { code: string; message: string; requestId?: string; status: number };
export class ApiRequestError extends Error {
  constructor(public readonly apiError: ApiError) { super(apiError.message); this.name = 'ApiRequestError'; }
}
export type RequestOptions = RequestInit & { timeoutMs?: number; onHeaders?: (headers: Headers) => void; responseType?: 'json' | 'blob' };
export type ApiPath = keyof paths | (string & {});
const mocked = import.meta.env.VITE_USE_MOCK !== 'false';
let mockHandler: ((path: string, init: RequestInit) => Promise<Response>) | undefined;
export const isMockMode = () => mocked;
export const setMockHandler = (handler?: typeof mockHandler) => { mockHandler = handler; };

export async function apiRequest<T>(path: ApiPath, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 120_000, signal, headers, onHeaders, responseType = 'json', ...init } = options;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(new DOMException('Request timed out', 'TimeoutError')), timeoutMs);
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener('abort', abort, { once: true });
  try {
    if (mocked && !mockHandler) throw new ApiRequestError({ code: 'MOCK_NOT_CONFIGURED', message: 'Mock mode is enabled but its local fixture handler is not configured.', status: 500 });
    const response = mocked
      ? await mockHandler!(path, { ...init, headers, signal: controller.signal })
      : await fetch(path, { ...init, headers, signal: controller.signal });
    onHeaders?.(response.headers);
    if (!response.ok) {
      let code = 'REQUEST_FAILED'; let message = 'The request could not be completed.'; let requestId: string | undefined;
      try { const body = await response.json() as { error?: { code?: string; message?: string; request_id?: string } }; code = body.error?.code ?? code; message = body.error?.message ?? message; requestId = body.error?.request_id; } catch { /* Keep safe generic message. */ }
      throw new ApiRequestError({ code, message, requestId, status: response.status });
    }
    return responseType === 'blob' ? await response.blob() as T : await response.json() as T;
  } catch (error) {
    if (error instanceof ApiRequestError) throw error;
    if (controller.signal.aborted) throw new ApiRequestError({ code: 'REQUEST_ABORTED', message: controller.signal.reason instanceof DOMException && controller.signal.reason.name === 'TimeoutError' ? 'The request timed out. Try again when you are ready.' : 'The request was cancelled.', status: 0 });
    throw new ApiRequestError({ code: 'NETWORK_ERROR', message: 'Could not reach DocExtract. Check the connection and try again.', status: 0 });
  } finally { window.clearTimeout(timeout); signal?.removeEventListener('abort', abort); }
}
export function uploadFile<T>(file: File, signal?: AbortSignal, onProgress?: (fraction: number) => void, onHeaders?: (headers: Headers) => void): Promise<T> {
  // Fetch cannot report upload progress; keep the progress UI indeterminate until completion.
  onProgress?.(0.1);
  const form = new FormData(); form.append('file', file);
  return apiRequest<T>('/api/extract/evidence', { method: 'POST', body: form, signal, timeoutMs: 300_000, onHeaders }).then((result) => { onProgress?.(1); return result; });
}
