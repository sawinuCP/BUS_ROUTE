import { render, screen as rtlScreen, userEvent } from '@testing-library/react-native';

import JourneyScreen from '@/app/journey';
import { clearPlan, getPlan } from '@/lib/planStore';
import { clearPreferencesForTests, savePreferences } from '@/lib/preferencesDb';

// The offline plan cache (Phase 7) is backed by expo-sqlite — mocked here so
// the cache write on a successful plan is testable without the native module.
// Routes by SQL so the plan cache and the preference store share one fake DB.
jest.mock('expo-sqlite', () => {
  const planRows: { plan_json: string; option_id: string | null; saved_at: string }[] = [];
  const prefRows: { prefs_json: string; saved_at: string }[] = [];
  const runSync = (sql: string, params?: unknown[]) => {
    if (sql.startsWith('INSERT OR REPLACE INTO cached_plan') && params) {
      planRows.length = 0;
      planRows.push({ plan_json: params[0] as string, option_id: null, saved_at: params[1] as string });
    }
    if (sql.startsWith('UPDATE cached_plan') && params) {
      if (planRows[0]) {
        planRows[0].option_id = params[0] as string;
      }
    }
    if (sql.startsWith('INSERT OR REPLACE INTO user_preferences') && params) {
      prefRows.length = 0;
      prefRows.push({ prefs_json: params[0] as string, saved_at: params[1] as string });
    }
    if (sql.startsWith('DELETE FROM cached_plan')) {
      planRows.length = 0;
    }
    if (sql.startsWith('DELETE FROM user_preferences')) {
      prefRows.length = 0;
    }
  };
  const getAllSync = (sql: string) => {
    if (sql.includes('FROM cached_plan')) {
      return planRows.map((row) => ({ ...row }));
    }
    if (sql.includes('FROM user_preferences')) {
      return prefRows.map((row) => ({ ...row }));
    }
    return [];
  };
  const db = { execSync: jest.fn(), runSync, getAllSync };
  return { openDatabaseSync: () => db, __rows: planRows };
});

// userEvent is required: search and planning update state asynchronously
// after the press resolves.

const searchHit = (id: string, name: string) => ({
  entity_type: 'stop',
  entity_id: id,
  name,
  matched_text: name,
  matched_language: 'canonical',
  score: 0.9,
  coordinates: { lon: 79.85, lat: 6.91 },
  verification_status: 'unverified',
  locality: null,
  mode: 'bus',
});

const searchResponse = (stops: ReturnType<typeof searchHit>[]) => ({
  query: 'q',
  count: stops.length,
  results: stops,
  note: '',
});

const planResponse = {
  status: 'ok',
  dataset_version: 'osm-overpass-1679d061',
  availability_scope: 'network_feasible_not_live_confirmed',
  journey_id: 'j-1',
  options: [
    {
      id: 'option-1',
      summary: {
        estimated_duration_minutes: { min: 12.5, max: 18.7 },
        walking_distance_m: 0,
        transfer_count: 0,
        confidence: 'unverified_pattern',
      },
      labels: ['fastest', 'least_walking', 'fewest_transfers', 'simplest'],
      warnings: ['Static network data: service operation, frequencies and live availability are not checked.'],
      legs: [],
      steps: [
        { action: 'BOARD_TRANSIT', text: 'Board route 101 at Kollupitiya Junction halt.', facts: {}, confidence: 'unverified' },
      ],
    },
  ],
  labels: { fastest: 0 },
  notes: [],
  language: 'en',
};

const noRouteResponse = {
  status: 'no_route',
  dataset_version: 'osm-overpass-1679d061',
  availability_scope: 'network_feasible_not_live_confirmed',
  options: [],
  labels: { fastest: null },
  notes: ['Walking-only distance (4219 m) exceeds the walking cap (1500 m).'],
  language: 'en',
};

const noRouteWithSuggestions = {
  ...noRouteResponse,
  suggestions: [
    {
      kind: 'nearby_stop',
      role: 'origin',
      text: 'Alternative mapped stop for the origin: Willium Junction halt — 220 m away (straight-line as mapped; walking distance not checked).',
      stop_id: 's1b',
      stop_name: 'Willium Junction halt',
      distance_m: 220,
    },
  ],
};

/** Fetch double: URL decides between search and plan endpoints. */
function mockFetch(planJson: unknown) {
  return jest.fn((url: string) => {
    if (url.includes('/journeys/plan')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => planJson,
      } as unknown as Response);
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => searchResponse([searchHit('s1', 'Kollupitiya Junction halt'), searchHit('s2', 'Colombo Fort')]),
    } as unknown as Response);
  });
}

async function pickStopsAndPlan(screen: Awaited<ReturnType<typeof render>>, fetchMock: jest.Mock) {
  const user = userEvent.setup();
  await user.type(rtlScreen.getByTestId('origin-input'), 'kollupitiya');
  await user.press(rtlScreen.getByTestId('origin-search'));
  await user.press(await screen.findByTestId('origin-result-s1'));
  await user.type(rtlScreen.getByTestId('destination-input'), 'fort');
  await user.press(rtlScreen.getByTestId('destination-search'));
  await user.press(await screen.findByTestId('destination-result-s2'));
  await user.press(rtlScreen.getByTestId('plan-button'));
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/journeys/plan'),
    expect.objectContaining({ method: 'POST' }),
  );
}

describe('JourneyScreen results (Phase 5 items 9–10)', () => {
  beforeEach(() => {
    clearPlan();
    clearPreferencesForTests();
    (jest.requireMock('expo-sqlite').__rows as unknown[]).length = 0;
  });
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders option cards with explicit trade-offs and honest confidence', async () => {
    const fetchMock = mockFetch(planResponse);
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyScreen />);
    await pickStopsAndPlan(screen, fetchMock);

    expect(await screen.findByText('12.5–18.7 min (network estimate)')).toBeTruthy();
    expect(screen.getByText('Walk 0 m · 0 transfers')).toBeTruthy();
    expect(screen.getByText('Includes route data not yet field-checked')).toBeTruthy();
    expect(screen.getByTestId('label-option-1-fastest')).toBeTruthy();
    expect(screen.getByText(/dataset osm-overpass-1679d061/)).toBeTruthy();
    expect(
      screen.getByText(/service operation, frequencies and live availability are not checked/),
    ).toBeTruthy();
    // The plan is handed to the steps screen via the store.
    expect(getPlan()?.options[0]?.id).toBe('option-1');
    // ...and cached for offline use (Phase 7 item 1), with verbatim steps.
    const sqliteMock = jest.requireMock('expo-sqlite') as {
      __rows: { plan_json: string }[];
    };
    expect(sqliteMock.__rows).toHaveLength(1);
    expect(sqliteMock.__rows[0].plan_json).toContain('Board route 101 at Kollupitiya Junction halt.');
  });

  it('renders no_route honestly with the backend reasons', async () => {
    const fetchMock = mockFetch(noRouteResponse);
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyScreen />);
    await pickStopsAndPlan(screen, fetchMock);

    expect(await screen.findByTestId('no-route')).toBeTruthy();
    expect(
      screen.getByText('• Walking-only distance (4219 m) exceeds the walking cap (1500 m).'),
    ).toBeTruthy();
    expect(screen.queryByText(/min \(network estimate\)/)).toBeNull();
  });

  it('shows a connection error when planning fails', async () => {
    // Only the plan POST fails; the stop searches must still work.
    const fetchMock = jest.fn((url: string) => {
      if (url.includes('/journeys/plan')) {
        return Promise.reject(new Error('network down'));
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          searchResponse([searchHit('s1', 'Kollupitiya Junction halt'), searchHit('s2', 'Colombo Fort')]),
      } as unknown as Response);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyScreen />);
    await pickStopsAndPlan(screen, fetchMock);

    expect(await screen.findByText(/Planning failed/)).toBeTruthy();
  });

  it('plans with the saved local-first preferences (Phase 7 item 9)', async () => {
    savePreferences({
      language: 'si',
      priority: 'least_walking',
      max_walking_m: 2000,
      max_transfers: 2,
      allowed_modes: ['bus', 'rail'],
    });
    const planBodies: string[] = [];
    const fetchMock = jest.fn((url: string, init?: RequestInit) => {
      if (url.includes('/journeys/plan')) {
        planBodies.push(String(init?.body));
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => planResponse,
        } as unknown as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          searchResponse([searchHit('s1', 'Kollupitiya Junction halt'), searchHit('s2', 'Colombo Fort')]),
      } as unknown as Response);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyScreen />);
    await pickStopsAndPlan(screen, fetchMock);

    expect(await screen.findByText('12.5–18.7 min (network estimate)')).toBeTruthy();
    expect(planBodies).toHaveLength(1);
    const body = JSON.parse(planBodies[0]) as {
      language: string;
      preferences: {
        priority: string;
        max_walking_m: number;
        max_transfers: number;
        allowed_modes: string[];
      };
    };
    // Language and constraints come from the local-first preference store.
    expect(body.language).toBe('si');
    expect(body.preferences).toEqual({
      priority: 'least_walking',
      max_walking_m: 2000,
      max_transfers: 2,
      allowed_modes: ['bus', 'rail'],
    });
  });

  it('acts on an allow_mode suggestion by re-planning with rail included', async () => {
    savePreferences({ allowed_modes: ['bus'] });
    const noRouteWithModeSuggestion = {
      ...noRouteResponse,
      suggestions: [
        {
          kind: 'allow_mode',
          role: 'request',
          text:
            '2 rail pattern(s) exist in this dataset but rail is excluded by the current mode'
            + ' preference; rail rides additionally require a verified station order.',
          suggested_mode: 'rail',
        },
      ],
    };
    let planCalls = 0;
    const planBodies: string[] = [];
    const fetchMock = jest.fn((url: string, init?: RequestInit) => {
      if (url.includes('/journeys/plan')) {
        planCalls += 1;
        planBodies.push(String(init?.body));
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => (planCalls === 1 ? noRouteWithModeSuggestion : planResponse),
        } as unknown as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          searchResponse([searchHit('s1', 'Kollupitiya Junction halt'), searchHit('s2', 'Colombo Fort')]),
      } as unknown as Response);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyScreen />);
    await pickStopsAndPlan(screen, fetchMock);

    expect(await screen.findByTestId('suggestions')).toBeTruthy();
    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('suggestion-action-0'));

    expect(await screen.findByText('12.5–18.7 min (network estimate)')).toBeTruthy();
    expect(planBodies).toHaveLength(2);
    const second = JSON.parse(planBodies[1]) as { preferences: { allowed_modes: string[] } };
    // The mode preference is user-controlled; the backend still enforces the
    // verified-station-order rule for actual rail rides.
    expect(second.preferences.allowed_modes).toEqual(['bus', 'rail']);
  });

  it('offers grounded no-route suggestions and re-plans through them (Phase 7 item 6)', async () => {    // First plan answers no_route with a suggestion; the re-planned request
    // (through the same honest planner) then succeeds.
    let planCalls = 0;
    const planBodies: string[] = [];
    const fetchMock = jest.fn((url: string, init?: RequestInit) => {
      if (url.includes('/journeys/plan')) {
        planCalls += 1;
        planBodies.push(String(init?.body));
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => (planCalls === 1 ? noRouteWithSuggestions : planResponse),
        } as unknown as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          searchResponse([searchHit('s1', 'Kollupitiya Junction halt'), searchHit('s2', 'Colombo Fort')]),
      } as unknown as Response);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyScreen />);
    await pickStopsAndPlan(screen, fetchMock);

    // The suggestion card shows the backend's grounded text verbatim…
    expect(await screen.findByTestId('suggestions')).toBeTruthy();
    expect(screen.getByTestId('suggestion-0')).toBeTruthy();
    expect(screen.getByText(/straight-line as mapped; walking distance not checked/)).toBeTruthy();
    // …and acting on it re-plans through the planner with the suggested stop.
    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('suggestion-action-0'));

    expect(await screen.findByText('12.5–18.7 min (network estimate)')).toBeTruthy();
    expect(planBodies).toHaveLength(2);
    const secondPlan = JSON.parse(planBodies[1]) as {
      origin: { type: string; stop_id: string };
      destination: { type: string; stop_id: string };
    };
    // The suggested mapped stop becomes the origin; the destination is kept.
    expect(secondPlan.origin).toEqual({ type: 'stop', stop_id: 's1b' });
    expect(secondPlan.destination).toEqual({ type: 'stop', stop_id: 's2' });
  });
});
