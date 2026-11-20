import { render, screen as rtlScreen, userEvent } from '@testing-library/react-native';

import HomeScreen from '@/app/index';

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
});
