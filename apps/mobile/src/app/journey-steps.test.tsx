import {
  render,
  screen as rtlScreen,
  userEvent,
  waitFor,
} from '@testing-library/react-native';

import JourneyStepsScreen from '@/app/journey-steps';
import { clearPlan, setPlan } from '@/lib/planStore';

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
});

