import { render, screen as rtlScreen, userEvent } from '@testing-library/react-native';

import JourneyScreen from '@/app/journey';
import { clearPlan, getPlan } from '@/lib/planStore';

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
});
