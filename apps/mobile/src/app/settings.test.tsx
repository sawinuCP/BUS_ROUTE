/**
 * Settings screen (Phase 7, plan item 9) — local-first preferences.
 *
 * Under test: every plan-relevant preference is selectable and persisted
 * immediately; the honesty notes are shown (si/ta D-7 fallback, rail's
 * verified-station-order rule, read-aloud deferral, local-first storage).
 */

import { act, fireEvent, render, userEvent } from '@testing-library/react-native';

import SettingsScreen from '@/app/settings';
import { clearPreferencesForTests, readPreferences } from '@/lib/preferencesDb';
import { getTextScale } from '@/lib/textScale';

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
  };
  return { openDatabaseSync: () => db };
});

describe('SettingsScreen (Phase 7 item 9)', () => {
  beforeEach(() => {
    clearPreferencesForTests();
  });

  it('renders every preference group with the local-first honesty note', async () => {
    const screen = await render(<SettingsScreen />);

    expect(await screen.findByTestId('local-first-note')).toBeTruthy();
    expect(screen.getByText(/no account, nothing synced or uploaded/)).toBeTruthy();
    expect(screen.getByText(/native review is complete \(D-7\)/)).toBeTruthy();
    expect(screen.getByText(/verified station order/)).toBeTruthy();
    expect(screen.getByText(/read-aloud arrives with the grounded AI assistance phase/)).toBeTruthy();
  });

  it('persists journey planning preferences immediately', async () => {
    const screen = await render(<SettingsScreen />);
    const user = userEvent.setup();

    await user.press(screen.getByTestId('pref-language-si'));
    await user.press(screen.getByTestId('pref-priority-fewest_transfers'));
    await user.press(screen.getByTestId('pref-walk-2000'));
    await user.press(screen.getByTestId('pref-transfers-2'));

    const prefs = readPreferences();
    expect(prefs.language).toBe('si');
    expect(prefs.priority).toBe('fewest_transfers');
    expect(prefs.max_walking_m).toBe(2000);
    expect(prefs.max_transfers).toBe(2);
  });

  it('toggles rail with the grounding caveat visible (Phase 7 item 9)', async () => {
    const screen = await render(<SettingsScreen />);

    expect(readPreferences().allowed_modes).toEqual(['bus']);
    // Switch events need the host 'valueChange' event (userEvent.press does
    // not drive onValueChange — I-25 lesson); the awaited act() closes the
    // scope so it cannot poison the next test.
    await act(async () => {
      fireEvent(screen.getByTestId('pref-mode-rail'), 'valueChange', true);
    });
    expect(readPreferences().allowed_modes).toEqual(['bus', 'rail']);
    await act(async () => {
      fireEvent(screen.getByTestId('pref-mode-rail'), 'valueChange', false);
    });
    expect(readPreferences().allowed_modes).toEqual(['bus']);
  });

  it('applies the text-size preference to the shared text scale', async () => {
    expect(getTextScale()).toBe(1);

    const screen = await render(<SettingsScreen />);
    const user = userEvent.setup();
    await user.press(screen.getByTestId('pref-text-large'));

    expect(getTextScale()).toBe(1.2);
    expect(readPreferences().text_scale).toBe(1.2);
  });
});
