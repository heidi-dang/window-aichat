import { getToken } from '../utils/authStorage';

export type ApiErrorEnvelope = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
  requestId?: string | null;
};

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId?: string | null;
  readonly details?: unknown;

  constructor(opts: { code: string; message: string; status: number; requestId?: string | null; details?: unknown }) {
    super(opts.message);
    this.name = 'ApiError';
    this.code = opts.code;
    this.status = opts.status;
    this.requestId = opts.requestId;
    this.details = opts.details;
  }
}

export const API_BASE =
  (import.meta as { env: Record<string, string | undefined> }).env?.VITE_API_BASE?.replace(/\/$/, '') || '';

function withAuthHeaders(init?: RequestInit): RequestInit {
  const token = getToken();
  if (!token) return init ?? {};
  const headers = new Headers(init?.headers ?? undefined);
  if (!headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return { ...init, headers };
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  if (!v.error || typeof v.error !== 'object') return false;
  const err = v.error as Record<string, unknown>;
  return typeof err.code === 'string' && typeof err.message === 'string';
}

async function readBodyText(res: Response): Promise<string> {
  try {
    const text = await res.text();
    return text || `${res.status} ${res.statusText}`;
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}

export async function apiFetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, withAuthHeaders(init));
  if (res.ok) {
    return (await res.json()) as T;
  }

  let parsed: unknown = undefined;
  try {
    parsed = await res.json();
  } catch {
    parsed = undefined;
  }

  if (isApiErrorEnvelope(parsed)) {
    throw new ApiError({
      code: parsed.error.code,
      message: parsed.error.message,
      status: res.status,
      requestId: parsed.requestId,
      details: parsed.error.details
    });
  }

  const text = await readBodyText(res);
  throw new ApiError({ code: 'http_error', message: text, status: res.status });
}

