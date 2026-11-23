import { render } from '@testing-library/react-native';
import type { TextStyle } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { setTextScale } from '@/lib/textScale';

describe('ThemedText', () => {
  it('renders the given text content', async () => {
    const { getByText } = await render(<ThemedText>Board route 138 toward Kollupitiya</ThemedText>);
    expect(getByText('Board route 138 toward Kollupitiya')).toBeTruthy();
  });

  it('renders title type without crashing', async () => {
    const { getByText } = await render(<ThemedText type="title">Sri Lanka Journey Planner</ThemedText>);
    expect(getByText('Sri Lanka Journey Planner')).toBeTruthy();
  });

  it('applies the text-size preference scale (Phase 7 item 9)', async () => {
    setTextScale(1.2);
    try {
      const screen = await render(<ThemedText type="default">Larger text</ThemedText>);
      const node = screen.getByText('Larger text');
      // default: fontSize 16 → 16 × 1.2 = 19.2 (float-safe comparison)
      const style = (node.props.style as TextStyle[])[1];
      expect(style.fontSize).toBeCloseTo(19.2);
      expect(style.lineHeight).toBeCloseTo(28.8);
    } finally {
      setTextScale(1); // restore for other tests
    }
  });
});
