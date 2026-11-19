import { StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';

/**
 * Journey screen placeholder (Phase 0.4 skeleton).
 * Results comparison and step-by-step instructions are implemented in Phases 3–5
 * (planner, instruction templates, active journey mode).
 */
export default function JourneyScreen() {
  return (
    <ThemedView style={styles.container}>
      <ThemedText type="subtitle">Journey</ThemedText>
      <ThemedText>
        Route alternatives, leg-by-leg instructions and active journey mode are built in later
        phases. This screen is a navigation placeholder only.
      </ThemedText>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: Spacing.four,
    gap: Spacing.two,
  },
});
