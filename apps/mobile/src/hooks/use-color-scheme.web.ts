import { useSyncExternalStore } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

/**
 * To support static rendering, this value needs to be re-calculated on the client side for web.
 *
 * Uses `useSyncExternalStore` with server/client snapshots instead of a
 * `setState` call inside an effect (react-hooks/set-state-in-effect): during
 * SSR the server snapshot (`false`) renders the default theme; after client
 * hydration the client snapshot (`true`) activates the real color scheme.
 */

const subscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

export function useColorScheme() {
  const hasHydrated = useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);

  const colorScheme = useRNColorScheme();

  if (hasHydrated) {
    return colorScheme;
  }

  return 'light';
}
