import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useColorScheme } from 'react-native';

SplashScreen.preventAutoHideAsync();

/**
 * Root navigation (Phase 0.4 skeleton).
 * Screens grow phase by phase: search/map in Phase 2, results/journey detail in
 * Phase 3+, active journey mode in Phase 5+. Keep navigation typed and record
 * navigation decisions in ADRs (ADR-0002 chose Expo Router).
 */
export default function RootLayout() {
  const colorScheme = useColorScheme();

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="index" options={{ title: 'Sri Lanka Journey Planner' }} />
        <Stack.Screen name="journey" options={{ title: 'Plan a journey' }} />
        <Stack.Screen name="journey-steps" options={{ title: 'Your journey' }} />
        <Stack.Screen name="active-journey" options={{ title: 'Do this now' }} />
      </Stack>
    </ThemeProvider>
  );
}
