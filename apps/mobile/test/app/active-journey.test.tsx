import {
  act,
  fireEvent,
  render,
  screen as rtlScreen,
  userEvent,
  waitFor,
} from '@testing-library/react-native';

import ActiveJourneyScreen from '@/app/active-journey';
import { saveCachedPlan } from '@/lib/planDb';
import {
  clearQueuedEventsForTests,
  enqueueProgressEvent,
  readQueuedEvents,
} from '@/lib/progressQueue';
import { clearActiveSession } from '@/lib/sessionDb';

// Native modules do not exist under jest — mock them while keeping the
// screen's rendering/interaction contract testable. Manual progress and the
// GPS-suggestion safeguards are the assertions under test here. The sqlite
// mock routes by SQL so all three local stores (active session, offline plan
// cache, pending offline progress events) share one fake database.

jest.mock('expo-sqlite', () => {
  const sessionRows: { session_id: string; snapshot: string | null; saved_at: string }[] = [];
  const planRows: { plan_json: string; option_id: string | null; saved_at: string }[] = [];
  const eventRows: {
    id: number;
    session_id: string;
    event_type: string;
    step_index: number | null;
    note: string | null;
    queued_at: string;
  }[] = [];
  let nextEventId = 1;
  const runSync = (sql: string, params?: unknown[]) => {
    if (sql.startsWith('INSERT OR REPLACE INTO active_session') && params) {
      sessionRows.length = 0;
      sessionRows.push({
        session_id: params[0] as string,
        snapshot: params[1] as string | null,
        saved_at: params[2] as string,
      });
    }
    if (sql.startsWith('INSERT INTO pending_session_events') && params) {
      eventRows.push({
        id: nextEventId++,
        session_id: params[0] as string,
        event_type: params[1] as string,
        step_index: (params[2] as number | null) ?? null,
        note: (params[3] as string | null) ?? null,
        queued_at: params[4] as string,
      });
    }
    if (sql.startsWith('INSERT OR REPLACE INTO cached_plan') && params) {
      planRows.length = 0;
      planRows.push({
        plan_json: params[0] as string,
        option_id: null,
        saved_at: params[1] as string,
      });
    }
    if (sql.startsWith('UPDATE cached_plan') && params) {
      if (planRows[0]) {
        planRows[0].option_id = params[0] as string;
      }
    }
    if (sql.startsWith('DELETE FROM pending_session_events WHERE id =') && params) {
      const index = eventRows.findIndex((row) => row.id === params[0]);
      if (index >= 0) {
        eventRows.splice(index, 1);
      }
    }
    if (sql.startsWith('DELETE FROM pending_session_events WHERE session_id') && params) {
      const sessionId = params[0] as string;
      for (let i = eventRows.length - 1; i >= 0; i -= 1) {
        if (eventRows[i].session_id === sessionId) {
          eventRows.splice(i, 1);
        }
      }
    }
    if (sql.startsWith('DELETE FROM pending_session_events') && !sql.includes('WHERE')) {
      eventRows.length = 0;
    }
    if (sql.startsWith('DELETE FROM active_session')) {
      sessionRows.length = 0;
    }
    if (sql.startsWith('DELETE FROM cached_plan')) {
      planRows.length = 0;
    }
  };
  const getAllSync = (sql: string, params?: unknown[]) => {
    if (sql.includes('FROM active_session')) {
      return sessionRows.map((row) => ({ ...row }));
    }
    if (sql.includes('FROM cached_plan')) {
      return planRows.map((row) => ({ ...row }));
    }
    if (sql.includes('FROM pending_session_events')) {
      const sessionId = (params?.[0] as string) ?? '';
      return eventRows.filter((row) => row.session_id === sessionId).map((row) => ({ ...row }));
    }
    return [];
  };
  const db = { execSync: jest.fn(), runSync, getAllSync };
  return { openDatabaseSync: () => db };
});

jest.mock('expo-location', () => {
  const state: { callbacks: ((position: unknown) => void)[] } = { callbacks: [] };
  return {
    __gpsState: state,
    Accuracy: { Balanced: 3 },
    requestForegroundPermissionsAsync: jest.fn(async () => ({ status: 'granted' })),
    getCurrentPositionAsync: jest.fn(async () => ({
      coords: { latitude: 6.9107, longitude: 79.8483 },
    })),
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

// Voice guidance (Phase 6 item 7, P1): the saved preference controls whether
// the read-aloud control exists; the device TTS is faked and asserted.
jest.mock('expo-speech', () => {
  const state = { speakCalls: [] as { text: string; options: unknown }[], stopCount: 0 };
  return {
    __speechState: state,
    speak: jest.fn((text: string, options: unknown) => {
      state.speakCalls.push({ text, options });
    }),
    stop: jest.fn(() => {
      state.stopCount += 1;
    }),
  };
});

const speechMock = jest.requireMock('expo-speech') as {
  __speechState: { speakCalls: { text: string }[]; stopCount: number };
};

jest.mock('@/lib/preferencesDb', () => {
  const state = { voice_guidance: true };
  return {
    __prefsState: state,
    readPreferences: () => ({ voice_guidance: state.voice_guidance }),
    updatePreferences: jest.fn(),
  };
});

const prefsMock = jest.requireMock('@/lib/preferencesDb') as {
  __prefsState: { voice_guidance: boolean };
};

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

/** Cached plan for the offline projection tests (steps match the session). */
const offlinePlanFixture = {
  status: 'ok',
  dataset_version: 'osm-overpass-1679d061',
  availability_scope: 'network_feasible_not_live_confirmed',
  journey_id: 'j-1',
  options: [
    {
      id: 'option-1',
      summary: {
        estimated_duration_minutes: { min: 12, max: 18 },
        walking_distance_m: 240,
        transfer_count: 0,
        confidence: 'unverified_pattern',
      },
      labels: ['fastest'],
      warnings: [],
      legs: [],
      steps: [
        {
          action: 'WALK_TO_STOP',
          text: 'Walk 240 m to the boarding point.',
          facts: {},
          confidence: 'unverified',
        },
        {
          action: 'BOARD_TRANSIT',
          text: 'Board route 101 at A.',
          facts: {},
          confidence: 'unverified',
        },
      ],
    },
  ],
  labels: { fastest: 0 },
  notes: [],
  language: 'en',
};

/** Search fixture for the recovery flow (one confirmed stop). */
const recoverySearchResponse = {
  query: 'new',
  count: 1,
  results: [
    {
      entity_type: 'stop',
      entity_id: 'stop-x',
      name: 'New Junction halt',
      matched_text: 'New Junction halt',
      matched_language: 'canonical',
      score: 0.9,
      coordinates: { lon: 79.85, lat: 6.91 },
      verification_status: 'unverified',
      locality: null,
      mode: 'bus',
    },
  ],
  note: '',
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
    clearQueuedEventsForTests();
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

  it('queues offline progress and keeps the journey followable (Phase 7 item 3)', async () => {
    // The cached plan supplies the option's steps for the offline projection.
    saveCachedPlan(offlinePlanFixture as never);
    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      if (url.endsWith('/events')) {
        // Network failure (not a 409): the event cannot reach the backend.
        return { ok: false, status: 503, json: async () => ({}) };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    await screen.findByTestId('do-this-now');

    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('confirm-button'));

    // The next step appears immediately (local projection from cached steps)…
    expect(await screen.findByText('Board route 101 at A.')).toBeTruthy();
    expect(screen.getByText(/Step 2 of 2/)).toBeTruthy();
    // …with the honest offline banner and the queued event count.
    expect(screen.getByTestId('sync-banner')).toBeTruthy();
    expect(screen.getByText(/progress saved on this device and will sync/)).toBeTruthy();
    expect(readQueuedEvents('sess-1')).toHaveLength(1);
    expect(readQueuedEvents('sess-1')[0].event_type).toBe('step_advanced');
    // The backend state was never faked: the event is pending, not applied.
  });

  it('replays queued offline events when the connection returns', async () => {
    saveCachedPlan(offlinePlanFixture as never);
    enqueueProgressEvent('sess-1', { event_type: 'step_advanced', step_index: 1 });
    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/events')) {
        return { ok: true, status: 200, json: async () => sessionAfterAdvance };
      }
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);

    // After restore, the queued event replays in order and the server state
    // (now step 2) is adopted, with the sync result surfaced honestly.
    expect(await screen.findByText('Board route 101 at A.')).toBeTruthy();
    expect(await screen.findByTestId('sync-note')).toBeTruthy();
    expect(screen.getByText('Synced 1 offline progress change.')).toBeTruthy();
    expect(readQueuedEvents('sess-1')).toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/events'),
      expect.objectContaining({ body: expect.stringContaining('"event_type":"step_advanced"') }),
    );
  });

  it('recovers from a confirmed stop after a missed stop / wrong route (Phase 7 item 5)', async () => {
    const replannedState = {
      ...sessionState,
      replanned: true,
      previous_dataset_version: 'osm-overpass-1679d061',
    };
    const replanBodies: string[] = [];
    const fetchMock = urlFetch((url, init) => {
      if (url.endsWith('/replan')) {
        replanBodies.push(String(init?.body));
        return { ok: true, status: 200, json: async () => replannedState };
      }
      if (url.includes('/places/search')) {
        return { ok: true, status: 200, json: async () => recoverySearchResponse };
      }
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    await screen.findByTestId('do-this-now');

    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('replan-button'));

    // The recovery panel explains the mechanism: confirm, never auto-detect.
    expect(await screen.findByTestId('recovery-panel')).toBeTruthy();
    expect(screen.getByText(/Nothing is detected automatically/)).toBeTruthy();

    await user.type(rtlScreen.getByTestId('recovery-input'), 'new junc');
    await user.press(rtlScreen.getByTestId('recovery-search'));
    await user.press(await screen.findByTestId('recovery-stop-stop-x'));

    // The confirmed stop becomes the re-plan origin override.
    expect(replanBodies).toHaveLength(1);
    expect(JSON.parse(replanBodies[0])).toEqual({
      origin: { type: 'stop', stop_id: 'stop-x' },
    });
    // Success: the panel closes and the re-planned state is adopted.
    expect(await screen.findByText(/Step 1 of 2/)).toBeTruthy();
    expect(screen.queryByTestId('recovery-panel')).toBeNull();
  });

  it('keeps the honest no-replacement answer when recovery finds nothing', async () => {
    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/replan')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            ...sessionState,
            replanned: false,
            notes: ['No route connects from the confirmed stop.'],
          }),
        };
      }
      if (url.includes('/places/search')) {
        return { ok: true, status: 200, json: async () => recoverySearchResponse };
      }
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    await screen.findByTestId('do-this-now');

    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('replan-button'));
    await user.type(rtlScreen.getByTestId('recovery-input'), 'new junc');
    await user.press(rtlScreen.getByTestId('recovery-search'));
    await user.press(await screen.findByTestId('recovery-stop-stop-x'));

    // Honest no-replacement: the plan is kept and the reason is surfaced.
    expect(
      await screen.findByText(
        /No replacement journey found from New Junction halt — continuing with the current plan/,
      ),
    ).toBeTruthy();
    expect(screen.getByText(/No route connects from the confirmed stop/)).toBeTruthy();
    // The manual controls stay available and the panel remains open.
    expect(screen.getByTestId('confirm-button')).toBeTruthy();
    expect(screen.getByTestId('recovery-panel')).toBeTruthy();

    // The traveller can back out to their journey unchanged.
    await user.press(rtlScreen.getByTestId('recovery-cancel'));
    expect(screen.queryByTestId('recovery-panel')).toBeNull();
    expect(await screen.findByTestId('confirm-button')).toBeTruthy();
  });

  it('can list nearby mapped stops to assist confirmation (assistive, never stored)', async () => {
    const replannedState = {
      ...sessionState,
      replanned: true,
      previous_dataset_version: 'osm-overpass-1679d061',
    };
    const replanBodies: string[] = [];
    const fetchMock = urlFetch((url, init) => {
      if (url.endsWith('/replan')) {
        replanBodies.push(String(init?.body));
        return { ok: true, status: 200, json: async () => replannedState };
      }
      if (url.includes('/stops?bbox=')) {
        // bbox around (6.9107, 79.8483), ±0.02° — comes from the one-shot fix.
        return {
          ok: true,
          status: 200,
          json: async () => ({
            bbox: '6.89070,79.82830,6.93070,79.86830',
            count: 1,
            stops: [
              {
                entity_type: 'stop',
                entity_id: 'stop-near',
                name: 'Nearby Junction halt',
                coordinates: { lon: 79.8483, lat: 6.9107 },
                stop_type: 'bus_stop',
                mode: 'bus',
                verification_status: 'unverified',
              },
            ],
          }),
        };
      }
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    await screen.findByTestId('do-this-now');

    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('replan-button'));
    expect(await screen.findByTestId('recovery-panel')).toBeTruthy();

    // Assistive only: the traveller taps to search, the fix is never stored,
    // and the stop must still be confirmed by tapping it.
    await user.press(rtlScreen.getByTestId('recovery-nearby'));
    expect(screen.getByText(/it is never stored/)).toBeTruthy();
    await user.press(await screen.findByTestId('recovery-stop-stop-near'));

    expect(replanBodies).toHaveLength(1);
    expect(JSON.parse(replanBodies[0])).toEqual({
      origin: { type: 'stop', stop_id: 'stop-near' },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/stops?bbox='),
      expect.objectContaining({ method: 'GET' }),
    );
    expect(await screen.findByText(/Step 1 of 2/)).toBeTruthy();
  });

  it('reads the current and next step aloud on an explicit tap (Phase 6 item 7)', async () => {
    prefsMock.__prefsState.voice_guidance = true;
    speechMock.__speechState.speakCalls.length = 0;
    speechMock.__speechState.stopCount = 0;

    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    expect(await screen.findByTestId('read-aloud-button')).toBeTruthy();

    await userEvent.setup().press(rtlScreen.getByTestId('read-aloud-button'));

    // Mirrors the "Do this now" card exactly: current step then next step —
    // the deterministic template wording, never paraphrased.
    expect(speechMock.__speechState.speakCalls.map((call) => call.text)).toEqual([
      'Walk 240 m to the boarding point.',
      'Board route 101 at A.',
    ]);
    expect(rtlScreen.getByText('Stop reading')).toBeTruthy();

    // Interruption control: the same control stops the reading.
    await userEvent.setup().press(rtlScreen.getByTestId('read-aloud-button'));
    expect(speechMock.__speechState.stopCount).toBeGreaterThan(0);
    expect(rtlScreen.getByText('Read this step aloud')).toBeTruthy();
  });

  it('shows no read-aloud control when the preference is off', async () => {
    prefsMock.__prefsState.voice_guidance = false;

    const fetchMock = urlFetch((url) => {
      if (url.endsWith('/journey-sessions/sess-1')) {
        return { ok: true, status: 200, json: async () => sessionState };
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<ActiveJourneyScreen />);
    expect(await screen.findByTestId('do-this-now')).toBeTruthy();
    expect(rtlScreen.queryByTestId('read-aloud-button')).toBeNull();
  });
});

