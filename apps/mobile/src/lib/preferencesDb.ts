/**
 * Local-first user preferences (Phase 7, plan item 9).
 *
 * Stored in SQLite on the device only — basic planning must not require an
 * account (product rule), and account sync remains optional/deferred (plan
 * item 10). Nothing here leaves the device. Values are applied to journey
 * planning (language, priority, walking cap, transfers, allowed modes) and to
 * presentation (text scale; voice guidance is stored ahead of the read-aloud
 * work, which is P1 and blocked on D-7 native review).
 *
 * Defaults are returned for a missing or corrupted row — a broken preference
 * store must never break planning.
 */

import * as SQLite from 'expo-sqlite';

const DB_NAME = 'sljp.db';

export type PrefLanguage = 'en' | 'si' | 'ta';
export type PlanPriority = 'fastest' | 'least_walking' | 'fewest_transfers' | 'simplest';
export type PrefMode = 'bus' | 'rail';

export interface UserPreferences {
  language: PrefLanguage;
  priority: PlanPriority;
  max_walking_m: number;
  max_transfers: number;
  allowed_modes: PrefMode[];
  /** Typography multiplier applied by ThemedText (1 = normal). */
  text_scale: number;
  /** Read-aloud preference (the reader itself arrives in Phase 8 / P1). */
  voice_guidance: boolean;
}

export const DEFAULT_PREFERENCES: UserPreferences = {
  language: 'en',
  priority: 'fastest',
  max_walking_m: 1500,
  max_transfers: 1,
  allowed_modes: ['bus'],
  text_scale: 1,
  voice_guidance: false,
};

const WALKING_CAPS = [500, 1000, 1500, 2000, 3000, 5000];

export function isWalkingCap(value: number): boolean {
  return WALKING_CAPS.includes(value);
}

function openDb(): SQLite.SQLiteDatabase {
  return SQLite.openDatabaseSync(DB_NAME);
}

function ensureSchema(db: SQLite.SQLiteDatabase): void {
  db.execSync(
    'CREATE TABLE IF NOT EXISTS user_preferences ('
    + ' id INTEGER PRIMARY KEY CHECK (id = 1),'
    + ' prefs_json TEXT NOT NULL,'
    + ' saved_at TEXT NOT NULL)',
  );
}

export function readPreferences(): UserPreferences {
  try {
    const db = openDb();
    ensureSchema(db);
    const rows = db.getAllSync<{ prefs_json: string }>(
      'SELECT prefs_json FROM user_preferences WHERE id = 1',
    );
    const row = rows[0];
    if (!row) {
      return { ...DEFAULT_PREFERENCES };
    }
    return parsePreferences(row.prefs_json);
  } catch {
    // Native store unavailable (e.g. unit tests without the sqlite mock):
    // fall back to defaults — a broken preference store must never break
    // planning or rendering.
    return { ...DEFAULT_PREFERENCES };
  }
}

function parsePreferences(raw: string): UserPreferences {
  try {
    const parsed = JSON.parse(raw) as Partial<UserPreferences>;
    const language = parsed.language;
    return {
      language:
        language === 'en' || language === 'si' || language === 'ta'
          ? language
          : DEFAULT_PREFERENCES.language,
      priority: parsed.priority ?? DEFAULT_PREFERENCES.priority,
      max_walking_m:
        parsed.max_walking_m !== undefined && isWalkingCap(parsed.max_walking_m)
          ? parsed.max_walking_m
          : DEFAULT_PREFERENCES.max_walking_m,
      max_transfers:
        parsed.max_transfers !== undefined && parsed.max_transfers >= 0 && parsed.max_transfers <= 3
          ? parsed.max_transfers
          : DEFAULT_PREFERENCES.max_transfers,
      allowed_modes:
        Array.isArray(parsed.allowed_modes) && parsed.allowed_modes.includes('bus')
          ? (parsed.allowed_modes.filter((mode) => mode === 'bus' || mode === 'rail') as PrefMode[])
          : DEFAULT_PREFERENCES.allowed_modes,
      text_scale:
        typeof parsed.text_scale === 'number' && parsed.text_scale >= 1 && parsed.text_scale <= 2
          ? parsed.text_scale
          : DEFAULT_PREFERENCES.text_scale,
      voice_guidance: parsed.voice_guidance ?? DEFAULT_PREFERENCES.voice_guidance,
    };
  } catch {
    return { ...DEFAULT_PREFERENCES }; // corrupted prefs must never break planning
  }
}

export function savePreferences(patch: Partial<UserPreferences>): UserPreferences {
  const merged = { ...readPreferences(), ...patch };
  try {
    const db = openDb();
    ensureSchema(db);
    db.runSync('INSERT OR REPLACE INTO user_preferences (id, prefs_json, saved_at) VALUES (1, ?, ?)', [
      JSON.stringify(merged),
      new Date().toISOString(),
    ]);
  } catch {
    // Store unavailable: the in-memory value still applies for this session.
  }
  return merged;
}

export function clearPreferencesForTests(): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('DELETE FROM user_preferences');
}
