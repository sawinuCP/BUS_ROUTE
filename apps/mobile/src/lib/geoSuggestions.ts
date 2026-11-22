/**
 * GPS proximity **suggestions** (Phase 6 work item 5) — pure logic, heavily
 * safeguarded, and never authoritative.
 *
 * Rules (implementation plan §Phase 6: "Optional GPS proximity suggestions
 * with accuracy and dwell safeguards; never auto-advance a critical step on a
 * weak signal"):
 * - **Accuracy gate**: samples whose reported accuracy is worse than the cap
 *   (default 50 m) are discarded — a weak signal can never fire a suggestion.
 * - **Jump rejection**: a sample that jumps implausibly far from the previous
 *   valid sample (default > 200 m) breaks the dwell run — a single fix or a
 *   location glitch cannot trigger anything.
 * - **Dwell requirement**: only after `dwell_samples` consecutive valid
 *   samples inside the target radius does a suggestion fire.
 * - The output is a *suggestion* only: the caller must still obtain an
 *   explicit manual confirmation (the backend's `step_advanced` event) — this
 *   module has no side effects and no access to session state.
 */

export interface LocationSample {
  lat: number;
  lon: number;
  /** GPS-reported accuracy in metres (higher = worse). */
  accuracy_m: number;
}

export interface SuggestionTarget {
  lat: number;
  lon: number;
  radius_m: number;
  /** Human label for the confirmation card (from the step's facts). */
  label: string;
}

export interface SuggestionResult {
  suggest: boolean;
  /** Why the current verdict holds: 'dwell' | 'accuracy' | 'jump' | 'outside'. */
  reason: string;
}

export interface SuggestionOptions {
  max_accuracy_m?: number;
  dwell_samples?: number;
  max_jump_m?: number;
}

const DEFAULTS = {
  max_accuracy_m: 50,
  dwell_samples: 3,
  max_jump_m: 200,
};

/** Great-circle distance in metres (WGS84 approximation, same as backend). */
export function distanceMeters(
  latFrom: number,
  lonFrom: number,
  latTo: number,
  lonTo: number,
): number {
  const R = 6_371_000;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(latTo - latFrom);
  const dLon = toRad(lonTo - lonFrom);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(latFrom)) * Math.cos(toRad(latTo)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

export function evaluateProximity(
  samples: LocationSample[],
  target: SuggestionTarget,
  options?: SuggestionOptions,
): SuggestionResult {
  const opts = { ...DEFAULTS, ...options };
  // Keep only the trailing run of valid samples (accuracy + no jump).
  const valid: LocationSample[] = [];
  for (const sample of samples) {
    if (sample.accuracy_m > opts.max_accuracy_m) {
      valid.length = 0; // weak signal resets the dwell run
      continue;
    }
    if (valid.length > 0) {
      const previous = valid[valid.length - 1];
      const jump = distanceMeters(previous.lat, previous.lon, sample.lat, sample.lon);
      if (jump > opts.max_jump_m) {
        valid.length = 0; // implausible move resets the dwell run
        continue;
      }
    }
    valid.push(sample);
  }

  const dwell = valid.slice(-opts.dwell_samples);
  if (dwell.length < opts.dwell_samples) {
    return { suggest: false, reason: 'dwell' };
  }
  const allInside = dwell.every(
    (sample) => distanceMeters(sample.lat, sample.lon, target.lat, target.lon) <= target.radius_m,
  );
  return allInside
    ? { suggest: true, reason: 'dwell' }
    : { suggest: false, reason: 'outside' };
}
