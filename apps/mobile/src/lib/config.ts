/**
 * Environment configuration.
 *
 * Expo inlines variables prefixed with `EXPO_PUBLIC_` from `.env` files at
 * build time (see `apps/mobile/.env.example`). Only non-sensitive values may
 * be exposed this way — secrets must never be placed in the mobile bundle
 * (implementation plan §4.2).
 */

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

export function resolveApiBaseUrl(rawUrl: string | undefined): string {
  const candidate = rawUrl?.trim();
  if (!candidate) {
    return 'http://localhost:8000';
  }
  return trimTrailingSlash(candidate);
}

export const apiBaseUrl = resolveApiBaseUrl(process.env.EXPO_PUBLIC_API_BASE_URL);

const DEFAULT_MAP_STYLE = 'https://demotiles.maplibre.org/style.json';

export function resolveMapStyle(rawUrl: string | undefined): string {
  const candidate = rawUrl?.trim();
  return candidate ? trimTrailingSlash(candidate) : DEFAULT_MAP_STYLE;
}

/**
 * Vector style for the MapLibre map. The default is the MapLibre demo style
 * (development only, no account/token needed). A production basemap/tile
 * provider is a separate owner decision (data licensing + hosting) recorded
 * in the status report — the app never hard-codes a vendor here.
 */
export const mapStyle = resolveMapStyle(process.env.EXPO_PUBLIC_MAP_STYLE);

