import { render, screen as rtlScreen, userEvent } from '@testing-library/react-native';

import HomeScreen from '@/app/index';

jest.mock('expo-location', () => ({
  Accuracy: { Balanced: 3 },
  getCurrentPositionAsync: jest.fn(async () => ({
    coords: { latitude: 6.9107, longitude: 79.8483 },
  })),
}));

// userEvent is used because runSearch updates state asynchronously after the
// press resolves — fireEvent's synchronous act() scope does not cover it.

const sampleResults = {
  query: 'homagama',
  count: 2,
  results: [
    {
      entity_type: 'stop',
      entity_id: 's1',
      name: 'Homagama Junction',
      matched_text: 'Homagama Junction',
      matched_language: 'canonical',
      score: 0.9,
      coordinates: { lon: 79.9777, lat: 6.844 },
      verification_status: 'unverified',
      locality: null,
      mode: 'bus',
    },
    {
      entity_type: 'stop',
      entity_id: 's2',
      name: 'Homagama Bus Stand',
      matched_text: 'Homagama Bus Stand',
      matched_language: 'canonical',
      score: 0.85,
      coordinates: { lon: 79.977, lat: 6.8445 },
      verification_status: 'unverified',
      locality: null,
      mode: 'bus',
    },
  ],
  note: 'candidates listed',
};

describe('HomeScreen search (Phase 2)', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('lists ambiguous candidates and selects only on user tap', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => sampleResults,
    } as unknown as Response);

    const screen = await render(<HomeScreen />);
    const user = userEvent.setup();
    await user.type(rtlScreen.getByTestId('search-input'), 'homagama');
    await user.press(rtlScreen.getByTestId('search-button'));

    expect(await screen.findByText('Homagama Junction')).toBeTruthy();
    expect(screen.getByText('Homagama Bus Stand')).toBeTruthy();

    // User explicitly selects one — ambiguous results are never auto-selected.
    await user.press(screen.getByTestId('result-s1'));
    expect(screen.getByText('Bus stop: Homagama Junction')).toBeTruthy();
    expect(screen.getByText(/not field-checked yet/)).toBeTruthy();
  });

  it('shows the no-match hint when the backend returns nothing', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ query: 'zzz', count: 0, results: [], note: '' }),
    } as unknown as Response);

    const screen = await render(<HomeScreen />);
    const user = userEvent.setup();
    await user.type(rtlScreen.getByTestId('search-input'), 'zzz');
    await user.press(rtlScreen.getByTestId('search-button'));

    expect(await screen.findByText(/No matches in the pilot data/)).toBeTruthy();
  });

  it('lists nearby mapped stops on an explicit tap — assistive, never stored (Phase 2 item 9)', async () => {
    const fetchMock = jest.fn((url: string) => {
      if (url.includes('/stops?bbox=')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            bbox: '6.89070,79.82830,6.93070,79.86830',
            count: 1,
            stops: [
              {
                entity_type: 'stop',
                entity_id: 'near-1',
                name: 'Nearby Junction halt',
                coordinates: { lon: 79.8483, lat: 6.9107 },
                stop_type: 'bus_stop',
                mode: 'bus',
                verification_status: 'unverified',
              },
            ],
          }),
        } as unknown as Response);
      }
      throw new Error(`unexpected url ${url}`);
    });
    jest.spyOn(global, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch);

    const screen = await render(<HomeScreen />);
    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('nearby-button'));

    // One-shot fix → bbox query → candidates listed; nothing auto-selected.
    expect(await screen.findByText('Nearby Junction halt')).toBeTruthy();
    await user.press(screen.getByTestId('result-near-1'));
    expect(screen.getByText('Bus stop: Nearby Junction halt')).toBeTruthy();
    expect(screen.getByText(/nearest to you \(straight-line, as mapped\)/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/stops?bbox=6.89070%2C79.82830%2C6.93070%2C79.86830'),
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('falls back honestly when the location fix fails (permission denied / no fix)', async () => {
    const { getCurrentPositionAsync } = jest.requireMock('expo-location') as {
      getCurrentPositionAsync: jest.Mock;
    };
    getCurrentPositionAsync.mockRejectedValueOnce(new Error('permission denied'));

    const screen = await render(<HomeScreen />);
    const user = userEvent.setup();
    await user.press(rtlScreen.getByTestId('nearby-button'));

    // The manual-coordinate fallback always works (product rule).
    expect(
      await screen.findByText(/Could not get your location — search by name or enter coordinates/),
    ).toBeTruthy();
    expect(rtlScreen.getByTestId('manual-button')).toBeTruthy();
  });
});
