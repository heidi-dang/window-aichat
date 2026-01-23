import { describe, expect, it, vi } from 'vitest';

import { ApiError, apiFetchJson } from './client';

describe('apiFetchJson', () => {
  it('throws ApiError when backend returns error envelope', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ error: { code: 'validation_error', message: 'Invalid' }, requestId: 'req123' })
    })) as any);

    await expect(apiFetchJson('/api/test')).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetchJson('/api/test')).rejects.toMatchObject({
      code: 'validation_error',
      requestId: 'req123',
      status: 400
    });
  });
});

