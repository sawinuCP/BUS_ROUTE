import { checkBackendHealth } from '@/lib/api';

describe('checkBackendHealth', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('returns the parsed health payload on 200', async () => {
    const payload = { status: 'ok', service: 'Sri Lanka Journey Planner API', version: '0.1.0', app_env: 'local' };
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    });

    const result = await checkBackendHealth(fetchMock as unknown as typeof fetch);

    expect(result).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/health',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('throws on non-200 responses instead of parsing an error envelope as health data', async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: false, status: 503 });

    await expect(checkBackendHealth(fetchMock as unknown as typeof fetch)).rejects.toThrow(
      'health check failed with status 503',
    );
  });
});
