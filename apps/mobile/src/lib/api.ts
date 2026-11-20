/**
 * Minimal typed API client (Phase 0.4 skeleton).
 *
 * Endpoint coverage grows with the backend phases. Every call goes through
 * this module so timeouts, error mapping and request IDs are handled in one
 * place. The backend's stable error envelope shape is mirrored here.
 */

import { apiBaseUrl } from '@/lib/config';

export interface HealthResponse {
  status: 'ok';
  service: string;
  version: string;
  app_env: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}

export interface SearchHit {
  entity_type: 'stop' | 'place' | 'locality' | 'route';
  entity_id: string;
  name: string;
  matched_text: string;
  matched_language: string;
  score: number;
  coordinates: { lon: number; lat: number } | null;
  verification_status: string | null;
  locality: string | null;
  mode: string | null;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchHit[];
  note: string;
}

/** One stop marker from `GET /api/v1/stops?bbox=` (map overlay). */
export interface StopMarker {
  entity_type: 'stop';
  entity_id: string;
  name: string;
  coordinates: { lon: number; lat: number };
  stop_type: string | null;
  mode: string | null;
  verification_status: string | null;
}

export interface StopsBboxResponse {
  bbox: string;
  count: number;
  stops: StopMarker[];
}

const DEFAULT_TIMEOUT_MS = 10_000;

export async function checkBackendHealth(fetchImpl: typeof fetch = fetch): Promise<HealthResponse> {
  const response = await fetchImpl(`${apiBaseUrl}/api/v1/health`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new Error(`health check failed with status ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

export async function searchPlaces(
  query: string,
  fetchImpl: typeof fetch = fetch,
): Promise<SearchResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/api/v1/places/search?q=${encodeURIComponent(query)}`,
    {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
    },
  );
  if (!response.ok) {
    throw new Error(`search failed with status ${response.status}`);
  }
  return (await response.json()) as SearchResponse;
}

/** Fetches stop markers inside a WGS84 bbox (`south,west,north,east`). */
export async function fetchStopsInBbox(
  bbox: string,
  fetchImpl: typeof fetch = fetch,
): Promise<StopsBboxResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/api/v1/stops?bbox=${encodeURIComponent(bbox)}`,
    {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
    },
  );
  if (!response.ok) {
    throw new Error(`stops fetch failed with status ${response.status}`);
  }
  return (await response.json()) as StopsBboxResponse;
}
