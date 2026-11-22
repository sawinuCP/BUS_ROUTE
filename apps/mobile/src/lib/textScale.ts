/**
 * Text-size preference as a tiny subscribable store (Phase 7, plan item 9).
 *
 * ThemedText reads the scale through `useSyncExternalStore`, so every text in
 * the app re-renders when the traveller changes the setting. The scale value
 * itself is persisted in the local preferences store (never leaves the
 * device).
 */

import { readPreferences, savePreferences } from '@/lib/preferencesDb';

// Lazy initialisation: the native store may be unavailable (unit tests
// without a sqlite mock) — the scale then falls back to normal.
let current: number | null = null;
const listeners = new Set<() => void>();

function currentScale(): number {
  if (current === null) {
    try {
      current = readPreferences().text_scale;
    } catch {
      current = 1;
    }
  }
  return current;
}

export function getTextScale(): number {
  return currentScale();
}

export function setTextScale(value: number): void {
  current = value;
  try {
    savePreferences({ text_scale: value });
  } catch {
    // The in-memory value still applies for this session.
  }
  for (const listener of listeners) {
    listener();
  }
}

export function subscribeTextScale(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export const TEXT_SCALE_OPTIONS = [
  { label: 'Normal', value: 1 },
  { label: 'Large', value: 1.2 },
] as const;
