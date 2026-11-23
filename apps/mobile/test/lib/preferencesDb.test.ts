/**
 * Local-first user preferences (Phase 7, plan item 9) — SQLite-backed store.
 *
 * Under test: defaults, round-trip, validation of out-of-range values, and
 * corrupted-row honesty (a broken preference store must never break
 * planning). Nothing here ever leaves the device.
 */

import {
  clearPreferencesForTests,
  DEFAULT_PREFERENCES,
  readPreferences,
  savePreferences,
} from '@/lib/preferencesDb';

jest.mock('expo-sqlite', () => {
  const rows: { prefs_json: string; saved_at: string }[] = [];
  const db = {
    execSync: jest.fn(),
    runSync: (sql: string, params?: unknown[]) => {
      if (sql.startsWith('INSERT OR REPLACE INTO user_preferences') && params) {
        rows.length = 0;
        rows.push({ prefs_json: params[0] as string, saved_at: params[1] as string });
      }
      if (sql.startsWith('DELETE FROM user_preferences')) {
        rows.length = 0;
      }
    },
    getAllSync: () => rows.map((row) => ({ ...row })),
    __rows: rows,
  };
  return { openDatabaseSync: () => db, __rows: rows };
});

describe('preferencesDb (Phase 7 item 9)', () => {
  beforeEach(() => {
    clearPreferencesForTests();
  });

  it('returns local-first defaults when nothing is stored', () => {
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
    expect(DEFAULT_PREFERENCES.allowed_modes).toEqual(['bus']);
  });

  it('round-trips a partial patch and keeps unspecified values', () => {
    savePreferences({ max_walking_m: 2000, max_transfers: 2 });
    savePreferences({ language: 'si' });

    const prefs = readPreferences();
    expect(prefs.language).toBe('si');
    expect(prefs.max_walking_m).toBe(2000);
    expect(prefs.max_transfers).toBe(2);
    expect(prefs.allowed_modes).toEqual(['bus']); // untouched by the patch
  });

  it('stores rail in allowed modes next to bus', () => {
    savePreferences({ allowed_modes: ['bus', 'rail'] });
    expect(readPreferences().allowed_modes).toEqual(['bus', 'rail']);
  });

  it('rejects out-of-range values back to defaults on read', () => {
    const mock = jest.requireMock('expo-sqlite') as {
      __rows: { prefs_json: string; saved_at: string }[];
    };
    mock.__rows.push({
      prefs_json: JSON.stringify({
        language: 'de', // not supported
        max_walking_m: 99999, // not an offered cap
        max_transfers: 9, // beyond the backend bound (0–3)
        text_scale: 5, // beyond the 1–2 scale
        allowed_modes: ['rail'], // bus must always be present
      }),
      saved_at: '',
    });

    const prefs = readPreferences();
    expect(prefs.language).toBe('en');
    expect(prefs.max_walking_m).toBe(1500);
    expect(prefs.max_transfers).toBe(1);
    expect(prefs.text_scale).toBe(1);
    expect(prefs.allowed_modes).toEqual(['bus']);
  });

  it('never breaks planning on a corrupted row', () => {
    savePreferences({ language: 'ta' });
    const mock = jest.requireMock('expo-sqlite') as {
      __rows: { prefs_json: string; saved_at: string }[];
    };
    mock.__rows[0].prefs_json = '{corrupted';
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
  });
});
