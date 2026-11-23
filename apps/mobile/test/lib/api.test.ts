import { checkBackendHealth, searchPlaces } from '@/lib/api';

describe('searchPlaces', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('encodes the query and returns the parsed response', async () => {
    const payload = {
      query: 'homagama',
      count: 1,
      results: [
        {
          entity_type: 'stop',
          entity_id: 'abc',
          name: 'Homagama Junction',
          matched_text: 'Homagama Junction',
          matched_language: 'canonical',
          score: 0.9,
          coordinates: { lon: 79.9777, lat: 6.844 },
          verification_status: 'unverified',
          locality: null,
          mode: 'bus',
        },
      ],
      note: 'candidates are listed for selection',
    };
    const fetchMock = jest.fn().mockResolvedValue({ ok: true, status: 200, json: async () => payload });

    const result = await searchPlaces('homagama', fetchMock as unknown as typeof fetch);

    expect(result).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/places/search?q=homagama',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('throws on error statuses instead of parsing an error envelope as data', async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    await expect(searchPlaces('x', fetchMock as unknown as typeof fetch)).rejects.toThrow(
      'search failed with status 500',
    );
  });
});

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
