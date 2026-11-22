import {
  render,
  screen as rtlScreen,
  userEvent,
  waitFor,
} from '@testing-library/react-native';

import JourneyStepsScreen from '@/app/journey-steps';
import { clearCachedPlan, readCachedPlan, saveCachedPlan, setCachedPlanOption } from '@/lib/planDb';
import { clearPlan, setPlan } from '@/lib/planStore';

// expo-sqlite backs the offline plan cache (Phase 7) — mocked so cache
// restore after a restart is testable without the native module.
jest.mock('expo-sqlite', () => {
  const rows: { plan_json: string; option_id: string | null; saved_at: string }[] = [];
  const db = {
    execSync: jest.fn(),
    runSync: (sql: string, params?: unknown[]) => {
      if (sql.startsWith('INSERT OR REPLACE INTO cached_plan') && params) {
        rows.length = 0;
        rows.push({ plan_json: params[0] as string, option_id: null, saved_at: params[1] as string });
      }
      if (sql.startsWith('UPDATE cached_plan') && params) {
        if (rows[0]) {
          rows[0].option_id = params[0] as string;
        }
      }
      if (sql.startsWith('DELETE FROM cached_plan')) {
        rows.length = 0;
      }
    },
    getAllSync: () => rows.map((row) => ({ ...row })),
  };
  return { openDatabaseSync: () => db };
});

// Router params are mocked (the screen reads the selected option id); the
// plan itself arrives through the in-memory store, exactly as the plan screen
// hands it over in the app.

const planFixture = {
  status: 'ok',
  dataset_version: 'osm-overpass-1679d061',
  availability_scope: 'network_feasible_not_live_confirmed',
  journey_id: 'j-1',
  options: [
    {
      id: 'option-1',
      summary: {
        estimated_duration_minutes: { min: 20.7, max: 30.2 },
        walking_distance_m: 142,
        transfer_count: 1,
        confidence: 'unverified_transfer',
      },
      labels: ['fastest'],
      warnings: [
        'Static network data: service operation, frequencies and live availability are not checked.',
        'A transfer path in this option is not field-verified yet.',
      ],
      legs: [],
      steps: [
        {
          action: 'BOARD_TRANSIT',
          text: 'Board route 101 at Willium Junction heading towards Colombo Fort.',
          facts: {},
          confidence: 'unverified',
        },
        {
          action: 'RIDE_TRANSIT',
          text: 'Stay on route 101 and alight at Wellawatte Market.',
          facts: { intermediate_stops: 'not confirmed' },
          confidence: 'unverified',
        },
        {
          action: 'ALIGHT_TRANSIT',
          text: 'Alight at Wellawatte Market.',
          facts: {},
          confidence: 'unverified',
        },
        {
          action: 'WALK_TRANSFER',
          text: 'Walk 142 m to Manning Place halt to change buses.',
          facts: {},
          confidence: 'unverified',
        },
        {
          action: 'BOARD_TRANSIT',
          text: 'Board route 141 at Manning Place halt.',
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

jest.mock('expo-router', () => ({
  ...jest.requireActual('expo-router'),
  useLocalSearchParams: jest.fn(() => ({ option: 'option-1' })),
  useRouter: jest.fn(() => ({ push: jest.fn() })),
}));

describe('JourneyStepsScreen (Phase 5 item 10)', () => {
  beforeEach(() => {
    clearPlan();
    clearCachedPlan();
  });
  afterEach(() => {
    clearPlan();
    jest.restoreAllMocks();
  });

  it('renders the ordered steps verbatim with the honesty footer', async () => {
    setPlan(planFixture as never);

    const screen = await render(<JourneyStepsScreen />);

    expect(await screen.findByText('Your journey')).toBeTruthy();
    expect(
      screen.getByText('20.7–30.2 min (network estimate) · 1 transfer · walk 142 m'),
    ).toBeTruthy();
    expect(
      screen.getByText('Board route 101 at Willium Junction heading towards Colombo Fort.'),
    ).toBeTruthy();
    expect(screen.getByText('Stay on route 101 and alight at Wellawatte Market.')).toBeTruthy();
    expect(screen.getByText('Walk 142 m to Manning Place halt to change buses.')).toBeTruthy();
    expect(screen.getByText('Board route 141 at Manning Place halt.')).toBeTruthy();
    // Warnings surface on the detail screen too.
    expect(screen.getByText(/not field-verified yet/)).toBeTruthy();
    // Honesty footer: dataset version + not-live scope.
    expect(screen.getByText(/dataset osm-overpass-1679d061/)).toBeTruthy();
    expect(screen.getByText(/network feasible, not live confirmed/)).toBeTruthy();
    expect(rtlScreen.getByTestId('step-3')).toBeTruthy();
    // Guided mode entry (Phase 6): a saved plan can start a session.
    expect(screen.getByTestId('start-guided-button')).toBeTruthy();
  });

  it('starts a guided session from the saved plan', async () => {
    setPlan(planFixture as never);
    const push = jest.fn();
    const { useRouter } = jest.requireMock('expo-router') as {
      useRouter: jest.Mock;
    };
    useRouter.mockReturnValue({ push });

    const fetchMock = jest.fn((url: string) => {
      if (url.includes('/journey-sessions')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ session_id: 'sess-9' }),
        } as unknown as Response);
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyStepsScreen />);
    const user = userEvent.setup();
    await user.press(await screen.findByTestId('start-guided-button'));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/journey-sessions'),
        expect.objectContaining({ body: expect.stringContaining('"option_id":"option-1"') }),
      );
      expect(push).toHaveBeenCalledWith({
        pathname: '/active-journey',
        params: { session: 'sess-9' },
      });
    });
  });

  it('explains itself when opened without a plan', async () => {
    const { useLocalSearchParams } = jest.requireMock('expo-router') as {
      useLocalSearchParams: jest.Mock;
    };
    useLocalSearchParams.mockReturnValue({});

    const screen = await render(<JourneyStepsScreen />);

    expect(await screen.findByTestId('no-plan')).toBeTruthy();
    expect(screen.getByText('No plan in progress')).toBeTruthy();
    expect(screen.getByText(/Start from the plan screen/)).toBeTruthy();
  });

  it('restores the journey from the offline cache after a restart (Phase 7 item 1)', async () => {
    // Nothing in the in-memory store (fresh process) — the cache has the plan.
    saveCachedPlan(planFixture as never);
    setCachedPlanOption('option-1');

    const screen = await render(<JourneyStepsScreen />);

    // Steps render verbatim from the cache...
    expect(await screen.findByText('Board route 101 at Willium Junction heading towards Colombo Fort.')).toBeTruthy();
    expect(screen.getByText('Board route 141 at Manning Place halt.')).toBeTruthy();
    // ...with the honest saved-on-device banner (Phase 7 item 2).
    expect(screen.getByTestId('cached-banner')).toBeTruthy();
    expect(screen.getByText(/Saved on this device · /)).toBeTruthy();
    expect(
      screen.getByText(/planning, search and live checks are unavailable/),
    ).toBeTruthy();
    // Cache restore also revives the guided-mode entry point.
    expect(screen.getByTestId('start-guided-button')).toBeTruthy();
    // And the in-memory hand-off is restored for the next screen.
    expect(readCachedPlan()?.option_id).toBe('option-1');
  });

  it('shows the honest no-plan state when the requested option is not cached', async () => {
    saveCachedPlan(planFixture as never); // cache holds option-1 only
    const { useLocalSearchParams } = jest.requireMock('expo-router') as {
      useLocalSearchParams: jest.Mock;
    };
    useLocalSearchParams.mockReturnValue({ option: 'option-99' });

    const screen = await render(<JourneyStepsScreen />);

    expect(await screen.findByTestId('no-plan')).toBeTruthy();
    expect(screen.queryByTestId('cached-banner')).toBeNull();
  });

  it('shows no cached banner when the plan came from the live flow', async () => {
    setPlan(planFixture as never);
    const { useLocalSearchParams } = jest.requireMock('expo-router') as {
      useLocalSearchParams: jest.Mock;
    };
    useLocalSearchParams.mockReturnValue({ option: 'option-1' });

    const screen = await render(<JourneyStepsScreen />);

    expect(await screen.findByText('Your journey')).toBeTruthy();
    expect(screen.queryByTestId('cached-banner')).toBeNull();
  });
});

