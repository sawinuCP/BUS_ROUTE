import { render } from '@testing-library/react-native';

import { ThemedText } from '@/components/themed-text';

describe('ThemedText', () => {
  it('renders the given text content', async () => {
    const { getByText } = await render(<ThemedText>Board route 138 toward Kollupitiya</ThemedText>);
    expect(getByText('Board route 138 toward Kollupitiya')).toBeTruthy();
  });

  it('renders title type without crashing', async () => {
    const { getByText } = await render(<ThemedText type="title">Sri Lanka Journey Planner</ThemedText>);
    expect(getByText('Sri Lanka Journey Planner')).toBeTruthy();
  });
});
