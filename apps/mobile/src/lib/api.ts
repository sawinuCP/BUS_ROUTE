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

/* ------------------------------------------------------------------ */
/* Journey planning (Phase 4/5 — POST /api/v1/journeys/plan).          */
/* Shapes mirror the backend contract exactly; no field is invented.    */
/* ------------------------------------------------------------------ */

/** A planning endpoint: an exact stop or a coordinate. */
export type PlanEndpoint =
  | { type: 'stop'; stop_id: string }
  | { type: 'coordinates'; lon: number; lat: number };

export interface PlanPreferences {
  priority?: 'fastest' | 'least_walking' | 'fewest_transfers' | 'simplest';
  max_walking_m?: number;
  max_transfers?: number;
}

export interface PlanStep {
  action:
    | 'WALK_TO_STOP'
    | 'BOARD_TRANSIT'
    | 'RIDE_TRANSIT'
    | 'ALIGHT_TRANSIT'
    | 'WALK_TRANSFER'
    | 'WALK_TO_DESTINATION';
  text: string;
  facts: Record<string, unknown>;
  confidence: string;
}

export interface WalkLegPayload {
  type: 'walk';
  purpose: string;
  distance_m: number;
  duration_s: number;
  geometry: [number, number][];
  walking_provider: string | null;
  instruction_code: string;
}

export interface TransitLegPayload {
  type: 'transit';
  mode: string;
  route_id: string;
  route_code: string;
  pattern_id: string;
  pattern_code: string | null;
  direction_id: number;
  board_stop_id: string;
  board_stop_name: string;
  board_sequence: number;
  alight_stop_id: string;
  alight_stop_name: string;
  alight_sequence: number;
  /** null = the ordered stop sequence is unreliable (honestly withheld). */
  intermediate_stops: number | null;
  estimated_distance_m: number;
  estimated_duration_minutes: { min: number; max: number };
  verification_status: string;
  instruction_code: string;
}

export type PlanLeg = WalkLegPayload | TransitLegPayload;

export interface PlanOptionSummary {
  estimated_duration_minutes: { min: number; max: number };
  walking_distance_m: number;
  transfer_count: number;
  confidence: 'verified' | 'unverified_pattern' | 'unverified_transfer';
}

export interface PlanOption {
  id: string;
  summary: PlanOptionSummary;
  labels: string[];
  warnings: string[];
  legs: PlanLeg[];
  steps: PlanStep[];
}

export interface JourneyPlanResponse {
  status: 'ok' | 'no_route';
  dataset_version: string;
  availability_scope: 'network_feasible_not_live_confirmed';
  options: PlanOption[];
  labels: Record<string, number | null>;
  notes: string[];
  language: string;
  cache?: 'hit' | 'miss';
  journey_id?: string;
  note?: string;
}

/** Plans a journey between two endpoints (stop IDs from search results). */
export async function planJourney(
  origin: PlanEndpoint,
  destination: PlanEndpoint,
  preferences: PlanPreferences,
  language: string,
  fetchImpl: typeof fetch = fetch,
): Promise<JourneyPlanResponse> {
  const response = await fetchImpl(`${apiBaseUrl}/api/v1/journeys/plan`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ origin, destination, preferences, language }),
    signal: AbortSignal.timeout(30_000), // planning may route walking legs
  });
  if (!response.ok) {
    throw new Error(`journey planning failed with status ${response.status}`);
  }
  return (await response.json()) as JourneyPlanResponse;
}
