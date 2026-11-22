import {
  act,
  fireEvent,
  render,
  screen as rtlScreen,
  userEvent,
  waitFor,
} from '@testing-library/react-native';

import JourneyStepsScreen from '@/app/journey-steps';
import { clearCachedPlan, readCachedPlan, saveCachedPlan, setCachedPlanOption } from '@/lib/planDb';
import { clearQueuedReportsForTests, readQueuedReports } from '@/lib/reportQueue';
import { clearPlan, setPlan } from '@/lib/planStore';

// expo-sqlite backs the offline plan cache (Phase 7) and the offline report
// queue (Phase 7 item 4) — mocked so both are testable without the native
// module. Routes by SQL so the two stores share one fake database.
jest.mock('expo-sqlite', () => {
  const planRows: { plan_json: string; option_id: string | null; saved_at: string }[] = [];
  const reportRows: { id: number; payload_json: string; queued_at: string }[] = [];
  let nextReportId = 1;
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
    if (sql.startsWith('INSERT INTO pending_reports') && params) {
      reportRows.push({
        id: nextReportId++,
        payload_json: params[0] as string,
        queued_at: params[1] as string,
      });
    }
    if (sql.startsWith('DELETE FROM pending_reports WHERE id =') && params) {
      const index = reportRows.findIndex((row) => row.id === params[0]);
      if (index >= 0) {
        reportRows.splice(index, 1);
      }
    }
    if (sql.startsWith('DELETE FROM pending_reports') && !sql.includes('WHERE')) {
      reportRows.length = 0;
    }
    if (sql.startsWith('DELETE FROM cached_plan')) {
      planRows.length = 0;
    }
  };
  const getAllSync = (sql: string) => {
    if (sql.includes('FROM cached_plan')) {
      return planRows.map((row) => ({ ...row }));
    }
    if (sql.includes('FROM pending_reports')) {
      return reportRows.map((row) => ({ ...row }));
    }
    return [];
  };
  const db = { execSync: jest.fn(), runSync, getAllSync };
  return { openDatabaseSync: () => db, __reportRows: reportRows };
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
    clearQueuedReportsForTests();
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

  it('reports a problem with explicit consent (Phase 7 items 4 + 7)', async () => {
    const reportBodies: string[] = [];
    const fetchMock = jest.fn((url: string, init?: RequestInit) => {
      if (url.includes('/reports')) {
        reportBodies.push(String(init?.body));
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 'r-1',
            category: 'wrong_stop',
            status: 'submitted',
            duplicate: false,
          }),
        } as unknown as Response);
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    setPlan(planFixture as never);
    const screen = await render(<JourneyStepsScreen />);
    await screen.findByText('Your journey');

    await userEvent.setup().press(rtlScreen.getByTestId('report-button'));
    expect(await screen.findByTestId('report-panel')).toBeTruthy();
    // All plan item 7 categories are offered.
    for (const category of [
      'wrong_stop',
      'route_variant',
      'direction',
      'transfer_path',
      'landmark_name',
      'fare',
      'access_attribute',
      'outdated_data',
      'other',
    ]) {
      expect(rtlScreen.getByTestId(`report-category-${category}`)).toBeTruthy();
    }

    await userEvent.setup().press(rtlScreen.getByTestId('report-category-wrong_stop'));
    await userEvent.setup().type(
      rtlScreen.getByTestId('report-description'),
      'The 138 boards at the opposite side of the road here.',
    );

    // Submit is disabled without consent — nothing is stored without it.
    expect(rtlScreen.getByTestId('report-submit').props.accessibilityState.disabled).toBe(true);
    await act(async () => {
      fireEvent(rtlScreen.getByTestId('report-consent'), 'valueChange', true);
    });
    expect(rtlScreen.getByTestId('report-submit').props.accessibilityState.disabled).toBe(false);

    await userEvent.setup().press(rtlScreen.getByTestId('report-submit'));

    expect(await screen.findByText(/A moderator reviews it before any data changes/)).toBeTruthy();
    expect(reportBodies).toHaveLength(1);
    const body = JSON.parse(reportBodies[0]) as {
      consent: boolean;
      category: string;
      subject_type: string;
      subject_id: string;
      dataset_version_label: string;
    };
    expect(body.consent).toBe(true);
    expect(body.category).toBe('wrong_stop');
    // Grounded: the report is tied to the journey and the dataset version.
    expect(body.subject_type).toBe('journey');
    expect(body.subject_id).toBe('j-1');
    expect(body.dataset_version_label).toBe('osm-overpass-1679d061');
    expect(readQueuedReports()).toEqual([]);
  });

  it('queues the report offline and syncs it on the next mount (Phase 7 item 4)', async () => {
    let reportCalls = 0;
    const fetchMock = jest.fn((url: string) => {
      if (url.includes('/reports')) {
        reportCalls += 1;
        if (reportCalls === 1) {
          return Promise.reject(new TypeError('network unreachable'));
        }
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({ id: 'r-2', category: 'wrong_stop', status: 'submitted' }),
        } as unknown as Response);
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    setPlan(planFixture as never);
    const first = await render(<JourneyStepsScreen />);
    await first.findByText('Your journey');

    await userEvent.setup().press(rtlScreen.getByTestId('report-button'));
    await userEvent.setup().press(rtlScreen.getByTestId('report-category-wrong_stop'));
    await userEvent.setup().type(
      rtlScreen.getByTestId('report-description'),
      'The 138 boards at the opposite side of the road here.',
    );
    await act(async () => {
      fireEvent(rtlScreen.getByTestId('report-consent'), 'valueChange', true);
    });
    await userEvent.setup().press(rtlScreen.getByTestId('report-submit'));

    // Honest offline handling: queued on the device, never dropped.
    expect(await first.findByText(/saved on this device and will sync automatically/)).toBeTruthy();
    expect(readQueuedReports()).toHaveLength(1);

    // Next mount (or next screen visit) flushes the queued report.
    const second = await render(<JourneyStepsScreen />);
    await second.findByText('Your journey');
    await waitFor(() => {
      expect(readQueuedReports()).toEqual([]);
      expect(reportCalls).toBe(2); // retry with the SAME client key
    });
    expect(second.queryByText(/waiting to sync/)).toBeNull();
  });
});

