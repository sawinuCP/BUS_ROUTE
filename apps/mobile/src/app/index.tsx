import { Link } from 'expo-router';
import { StyleSheet } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { apiBaseUrl } from '@/lib/config';

/**
 * Home / plan entry (Phase 0.4 skeleton).
 * Origin/destination search, current location and map selection arrive in
 * Phase 2 (search, geocoding and map foundation).
 */
export default function HomeScreen() {
  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Sri Lanka Journey Planner</ThemedText>
      <ThemedText type="subtitle">Know exactly what to do next.</ThemedText>
      <ThemedText>
        Step-by-step bus, rail and walking instructions — grounded in validated transport data.
        Search, map and planning arrive in Phase 2.
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        API: {apiBaseUrl}
      </ThemedText>
      <Link href="/journey" style={styles.link}>
        <ThemedText type="linkPrimary">Open journey placeholder</ThemedText>
      </Link>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: Spacing.four,
    gap: Spacing.two,
    justifyContent: 'center',
  },
  link: {
    marginTop: Spacing.two,
  },
});
