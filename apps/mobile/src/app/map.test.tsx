import { render, screen as rtlScreen } from '@testing-library/react-native';

import MapScreen from '@/app/map';

// The native MapLibre module does not exist under jest — mock the exported
// components with plain Views that render their children so the screen's
// rendering contract (overlay text, markers) stays testable. Runtime
// verification on a device is pending the owner's dev-client spike (D-9).
jest.mock('@maplibre/maplibre-react-native', () => {
  const { View } = jest.requireActual('react-native');
  const Map = ({ children }: { children?: React.ReactNode }) => (
    <View testID="map-view">{children}</View>
  );
  const Camera = ({ children }: { children?: React.ReactNode }) => (
    <View testID="camera">{children}</View>
  );
  const Marker = ({ children, testID }: { children?: React.ReactNode; testID?: string }) => (
    <View testID={testID}>{children}</View>
  );
  return { Map, Camera, Marker };
});

const sampleStops = {
  bbox: '6.9000,79.9500,7.0000,80.0500',
  count: 2,
  stops: [
    {
      entity_type: 'stop',
      entity_id: 'st-1',
      name: 'Pasyala Bus Stop',
      coordinates: { lon: 80.0369, lat: 7.0917 },
      stop_type: null,
      mode: 'bus',
      verification_status: 'unverified',
    },
    {
      entity_type: 'stop',
      entity_id: 'st-2',
      name: 'Ayurwedha Bus stop',
      coordinates: { lon: 79.9777, lat: 6.844 },
      stop_type: null,
      mode: 'bus',
      verification_status: 'unverified',
    },
  ],
};

describe('MapScreen (Phase 2.1 / D-9)', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders the pilot stop markers and honesty note', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => sampleStops,
    } as unknown as Response);

    const screen = await render(<MapScreen />);

    expect(await screen.findByText('2 pilot stops in view')).toBeTruthy();
    // Markers are plain dots (no labels) — assert via testID.
    expect(screen.getByTestId('marker-st-1')).toBeTruthy();
    expect(screen.getByTestId('marker-st-2')).toBeTruthy();
    expect(screen.getByText(/not field-checked yet/)).toBeTruthy();
  });

  it('shows an error message when the stops fetch fails', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as unknown as Response);

    const screen = await render(<MapScreen />);

    expect(await screen.findByText(/Could not load pilot stops/)).toBeTruthy();
    expect(rtlScreen.getByTestId('map-view')).toBeTruthy();
  });
});
