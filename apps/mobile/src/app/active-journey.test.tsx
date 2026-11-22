import {
  act,
  fireEvent,
  render,
  screen as rtlScreen,
  userEvent,
  waitFor,
} from '@testing-library/react-native';

import ActiveJourneyScreen from '@/app/active-journey';
import { clearActiveSession } from '@/lib/sessionDb';

// Native modules do not exist under jest — mock them while keeping the
// screen's rendering/interaction contract testable. Manual progress and the
// GPS-suggestion safeguards are the assertions under test here.

jest.mock('expo-sqlite', () => {
  const rows: { session_id: string; snapshot: string | null; saved_at: string }[] = [];
  const runSync = (sql: string, params?: unknown[]) => {
    if (sql.startsWith('INSERT OR REPLACE') && params) {
      rows.length = 0;
      rows[0] = {
        session_id: params[0] as string,
        snapshot: params[1] as string | null,
        saved_at: '',
      };
    }
    if (sql.startsWith('DELETE')) {
      rows.length = 0;
    }
  };
  const db = {
    execSync: jest.fn(),
    runSync,
    getAllSync: () => rows,
  };
  return { openDatabaseSync: () => db };
});

jest.mock('expo-location', () => {
  const state: { callbacks: ((position: unknown) => void)[] } = { callbacks: [] };
  return {
    __gpsState: state,
    Accuracy: { Balanced: 3 },
    requestForegroundPermissionsAsync: jest.fn(async () => ({ status: 'granted' })),
    watchPositionAsync: jest.fn(
      async (_options: unknown, callback: (position: unknown) => void) => {
        state.callbacks.push(callback);
        return { remove: () => undefined };
      },
    ),
  };
});

const locationMock = jest.requireMock('expo-location') as {
  __gpsState: { callbacks: ((position: unknown) => void)[] };
};

jest.mock('expo-keep-awake', () => ({
  useKeepAwake: jest.fn(),
  activateKeepAwakeAsync: jest.fn(async () => undefined),
  deactivateKeepAwake: jest.fn(async () => undefined),
}));

jest.mock('expo-router', () => ({
  ...jest.requireActual('expo-router'),
  useLocalSearchParams: () => ({ session: 'sess-1' }),
}));

const sessionState = {
  session_id: 'sess-1',
  journey_id: 'j-1',
  option_id: 'option-1',
  status: 'active_ride',
  dataset_version: 'osm-overpass-1679d061',
  language: 'en',
  availability_scope: 'network_feasible_not_live_confirmed',
  progress: { current_step: 0, step_count: 2 },
  current_step: {
    action: 'WALK_TO_STOP',
    text: 'Walk 240 m to the boarding point.',
    facts: { target_lat: 6.9107, target_lon: 79.8483 },
    confidence: 'unverified',
  },
  next_step: {
    action: 'BOARD_TRANSIT',
    text: 'Board route 101 at A.',
    facts: {},
    confidence: 'unverified',
  },
};

const sessionAfterAdvance = {
  ...sessionState,
  progress: { current_step: 1, step_count: 2 },
  status: 'active_ride',
  current_step: sessionState.next_step,
  next_step: null,
};

function urlFetch(handler: (url: string, init?: RequestInit) => unknown) {
  return jest.fn((url: string, init?: RequestInit) =>
    Promise.resolve(handler(url, init) as unknown as Response),
  );
}

describe('ActiveJourneyScreen (Phase 6 items 2–6)', () => {
  beforeEach(() => {
    locationMock.__gpsState.callbacks.length = 0;
    clearActiveSession();
  });
  afterEach(() => {
    // Clear call history but KEEP mock implementations: restoreAllMocks
    // would strip the expo-location/expo-router factory implementations
    // needed by the later tests in this file.
    jest.clearAllMocks();
  });

  it('renders the do-this-now card and confirms manual progress', async () => {
    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      if (url.endsWith('/journey-sessions/sess-1/events')) {
        return { ok: true, status: 200, json: async () => sessionAfterAdvance };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    expect(await screen.findByTestId('do-this-now')).toBeTruthy();
    expect(screen.getByText('Walk 240 m to the boarding point.')).toBeTruthy();
    expect(screen.getByText(/Step 1 of 2/)).toBeTruthy();
    expect(screen.getByText(/Next: Board — Board route 101 at A\./)).toBeTruthy();

    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('confirm-button'));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/events'),
        expect.objectContaining({
          body: expect.stringContaining('"event_type":"step_advanced"'),
        }),
      );
    });
    expect(await screen.findByText('Board route 101 at A.')).toBeTruthy();
  });

  it('pauses and resumes via manual buttons', async () => {
    const paused = { ...sessionState, status: 'paused' };
    const fetchMock = urlFetch((url, init) => {
      if (url.endsWith('/events')) {
        const eventType = JSON.parse(String(init?.body)).event_type;
        return {
          ok: true,
          status: 200,
          json: async () => (eventType === 'paused' ? paused : sessionState),
        };
      }
      return { ok: true, status: 200, json: async () => sessionState };
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    const user = userEvent.setup();
    await user.press(await screen.findByTestId('pause-button'));
    expect(await screen.findByTestId('resume-button')).toBeTruthy();
    await user.press(rtlScreen.getByTestId('resume-button'));
    expect(await screen.findByTestId('pause-button')).toBeTruthy();
  });

  it('GPS can only suggest arrival after dwell — it never advances a step', async () => {
    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    await screen.findByTestId('do-this-now');

    fireEvent(rtlScreen.getByTestId('gps-switch'), 'valueChange', true);

    await waitFor(() => {
      expect(locationMock.__gpsState.callbacks.length).toBeGreaterThan(0);
    });
    // The last registered callback belongs to the live watcher (a StrictMode
    // remount can leave an earlier, cancelled registration in the mock).
    const onPosition =
      locationMock.__gpsState.callbacks[locationMock.__gpsState.callbacks.length - 1];
    const near = { coords: { latitude: 6.9107, longitude: 79.8483, accuracy: 8 } };
    // RNTL's act() always returns a thenable that must be awaited — a
    // non-awaited act leaves the act scope open and swallows every later
    // update in the file.
    await act(async () => {
      onPosition(near);
      onPosition(near);
      onPosition(near);
    });
    await screen.findByTestId('gps-suggestion'); // dwell satisfied → suggestion

    // No automatic step advance may have been fired by GPS.
    const eventCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes('/events'));
    expect(eventCalls).toHaveLength(0);

    // A weak-signal sample clears the suggestion immediately.
    await act(async () => {
      onPosition({ coords: { latitude: 6.9107, longitude: 79.8483, accuracy: 95 } });
    });
    await waitFor(() => {
      expect(screen.queryByTestId('gps-suggestion')).toBeNull();
    });
  });

  it('shows the terminal state after completing', async () => {
    const completedState = {
      ...sessionState,
      status: 'completed',
      progress: { current_step: 2, step_count: 2 },
      current_step: null,
      next_step: null,
    };
    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => completedState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    expect(await screen.findByTestId('terminal-note')).toBeTruthy();
    expect(screen.getByText('Journey completed.')).toBeTruthy();
    expect(screen.queryByTestId('confirm-button')).toBeNull();
  });

  it('shows the no-session state when nothing is active', async () => {
    const fetchMock = urlFetch(() => {
      throw new Error('no fetch expected');
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);
    // No persisted session (beforeEach cleared the local DB) and the backend
    // is unreachable → the screen must show the honest no-session state.

    const screen = await render(<ActiveJourneyScreen />);
    expect(await screen.findByTestId('no-session')).toBeTruthy();
    expect(screen.getByText('No active journey')).toBeTruthy();
  });
});

