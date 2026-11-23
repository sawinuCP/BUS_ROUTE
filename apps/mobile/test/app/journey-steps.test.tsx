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

  it('explains a step with the grounded AI explanation (Phase 8)', async () => {
    setPlan(planFixture as never);
    const fetchMock = jest.fn((url: string, init?: RequestInit) => {
      if (url.includes('/ai/explain-step')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            mode: 'explain_step',
            source: 'ai',
            provider: 'fake',
            model: 'fake-model',
            explanation:
              'Board at the halt marked for route 101. The direction label comes from the mapped dataset and is not field-verified.',
            cites: ['f_step', 'f_summary'],
            dataset_version: 'osm-overpass-1679d061',
            notes: ['AI-generated explanation — always follow the step wording.'],
            language: 'en',
          }),
        } as unknown as Response);
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyStepsScreen />);
    await screen.findByText('Your journey');
    await userEvent.setup().press(rtlScreen.getByTestId('explain-button-0'));

    expect(await screen.findByTestId('explanation-panel')).toBeTruthy();
    expect(rtlScreen.getByText(/AI explanation · grounded in your plan data/)).toBeTruthy();
    expect(rtlScreen.getByText(/Board at the halt marked for route 101/)).toBeTruthy();
    expect(
      rtlScreen.getByText(/always follow the step wording above/),
    ).toBeTruthy();

    // Grounded call: the saved journey id + the step index, nothing else.
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) =>
        String(url).includes('/ai/explain-step'),
      ) as unknown[] | undefined;
      const body = JSON.parse(String((call?.[1] as RequestInit)?.body)) as {
        mode: string;
        journey_id: string;
        step_index: number;
        option_index: number;
      };
      expect(body.mode).toBe('explain_step');
      expect(body.journey_id).toBe('j-1');
      expect(body.step_index).toBe(0);
      expect(body.option_index).toBe(0);
    });
  });

  it('labels the built-in explanation honestly when the AI is unavailable (Phase 8 item 7)', async () => {
    setPlan(planFixture as never);
    const fetchMock = jest.fn((url: string) => {
      if (url.includes('/ai/explain-step')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            mode: 'explain_step',
            source: 'deterministic_fallback',
            provider: null,
            model: null,
            explanation:
              'This step: Board route 101 at Willium Junction heading towards Colombo Fort.',
            cites: [],
            dataset_version: 'osm-overpass-1679d061',
            notes: ['AI unavailable: provider down.', 'Built-in deterministic explanation (no AI was used).'],
            language: 'en',
          }),
        } as unknown as Response);
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyStepsScreen />);
    await screen.findByText('Your journey');
    await userEvent.setup().press(rtlScreen.getByTestId('explain-button-1'));

    expect(await screen.findByTestId('explanation-panel')).toBeTruthy();
    expect(rtlScreen.getByText('Built-in explanation')).toBeTruthy();
    expect(rtlScreen.queryByText(/AI explanation ·/)).toBeNull();
    expect(rtlScreen.getByText('Produced by the app itself, no AI involved.')).toBeTruthy();
  });

  it('stays usable when the explanation request fails offline (Phase 8)', async () => {
    setPlan(planFixture as never);
    const fetchMock = jest.fn((url: string) => {
      if (url.includes('/ai/explain-step')) {
        return Promise.reject(new TypeError('network unreachable'));
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyStepsScreen />);
    await screen.findByText('Your journey');
    await userEvent.setup().press(rtlScreen.getByTestId('explain-button-0'));

    // Honest failure: no invented content, the step wording stays in charge.
    expect(
      await screen.findByText(/Could not load an explanation — the step wording above is all you need./),
    ).toBeTruthy();
    expect(rtlScreen.queryByTestId('explanation-panel')).toBeNull();
    expect(rtlScreen.getByText('Board route 101 at Willium Junction heading towards Colombo Fort.')).toBeTruthy();
  });

  it('reads all steps aloud on an explicit tap when the preference is on (Phase 6 item 7)', async () => {
    prefsMock.__prefsState.voice_guidance = true;
    speechMock.__speechState.speakCalls.length = 0;
    speechMock.__speechState.stopCount = 0;
    setPlan(planFixture as never);

    const screen = await render(<JourneyStepsScreen />);
    await screen.findByText('Your journey');

    await userEvent.setup().press(rtlScreen.getByTestId('read-steps-aloud-button'));

    // One speak call per deterministic step, in order, verbatim.
    expect(speechMock.__speechState.speakCalls.map((call) => call.text)).toEqual([
      'Board route 101 at Willium Junction heading towards Colombo Fort.',
      'Stay on route 101 and alight at Wellawatte Market.',
      'Alight at Wellawatte Market.',
      'Walk 142 m to Manning Place halt to change buses.',
      'Board route 141 at Manning Place halt.',
    ]);
    expect(rtlScreen.getByText('Stop reading')).toBeTruthy();

    await userEvent.setup().press(rtlScreen.getByTestId('read-steps-aloud-button'));
    expect(speechMock.__speechState.stopCount).toBeGreaterThan(0);
    expect(rtlScreen.getByText('Read all steps aloud')).toBeTruthy();
  });

  it('hides the read-aloud control when the preference is off', async () => {
    prefsMock.__prefsState.voice_guidance = false;
    setPlan(planFixture as never);

    const screen = await render(<JourneyStepsScreen />);
    await screen.findByText('Your journey');
    expect(rtlScreen.queryByTestId('read-steps-aloud-button')).toBeNull();
  });

  it('deletes the saved journey with a two-tap confirm (privacy)', async () => {
    setPlan(planFixture as never);
    const deleteCalls: string[] = [];
    const fetchMock = jest.fn((url: string, init?: RequestInit) => {
      if (url.includes('/journeys/j-1') && init?.method === 'DELETE') {
        deleteCalls.push(String(url));
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ deleted: true, journey_id: 'j-1' }),
        } as unknown as Response);
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<JourneyStepsScreen />);
    await screen.findByText('Your journey');

    // First press arms the confirm (nothing sent yet).
    await userEvent.setup().press(rtlScreen.getByTestId('delete-journey-button'));
    expect(rtlScreen.getByText('Tap again to confirm deletion')).toBeTruthy();
    expect(deleteCalls).toHaveLength(0);

    // Second press deletes, honestly noting what remains on-device.
    await userEvent.setup().press(rtlScreen.getByTestId('delete-journey-button'));
    expect(await screen.findByText(/Deleted from the server/)).toBeTruthy();
    expect(deleteCalls).toHaveLength(1);
    expect(screen.getByText(/Local copies on this device/)).toBeTruthy();
  });
});

