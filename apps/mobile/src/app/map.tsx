import { useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Camera, Map, Marker } from '@maplibre/maplibre-react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { fetchStopsInBbox, type StopMarker } from '@/lib/api';
import { mapStyle } from '@/lib/config';

/**
 * Pilot map (Phase 2.1 / D-9).
 * Shows the pilot stop markers from the backend's bbox endpoint, centred on a
 * selected search hit when one was passed. Runtime verification on a device
 * is pending the owner's Expo dev-client spike (see status report D-9) —
 * this screen ships with jest coverage over its logic and rendering contract.
 */

/** Overview fallback centre: the pilot bbox (Western Province, D-8) midpoint. */
const PILOT_CENTRE = { lat: 6.95, lon: 80.0 };

function parseCoord(raw: string | undefined): number | null {
  if (!raw) {
    return null;
  }
  const value = Number.parseFloat(raw);
  return Number.isFinite(value) ? value : null;
}

export default function MapScreen() {
  const params = useLocalSearchParams<{ lat?: string; lon?: string; name?: string }>();

  const centre = useMemo(() => {
    const lat = parseCoord(params.lat);
    const lon = parseCoord(params.lon);
    if (lat === null || lon === null) {
      return PILOT_CENTRE;
    }
    return { lat, lon };
  }, [params.lat, params.lon]);

  const selectedName = params.name ?? null;

  const [stops, setStops] = useState<StopMarker[]>([]);
  const [count, setCount] = useState(0);
  // The first load starts pending, so no synchronous setState is needed here.
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Bbox around the centre (±0.05° ≈ 5–6 km) in south,west,north,east order.
    const bbox = [
      (centre.lat - 0.05).toFixed(4),
      (centre.lon - 0.05).toFixed(4),
      (centre.lat + 0.05).toFixed(4),
      (centre.lon + 0.05).toFixed(4),
    ].join(',');
    let cancelled = false;
    fetchStopsInBbox(bbox)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setStops(response.stops);
        setCount(response.count);
        setError(null);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setError('Could not load pilot stops — check the backend connection.');
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [centre.lat, centre.lon]);

  return (
    <ThemedView style={styles.container}>
      <Map style={styles.map} mapStyle={mapStyle} compass testID="map-view">
        <Camera center={[centre.lon, centre.lat]} zoom={selectedName ? 14 : 9.5} />
        {stops.map((stop) => (
          <Marker
            key={stop.entity_id}
            id={stop.entity_id}
            lngLat={[stop.coordinates.lon, stop.coordinates.lat]}
            testID={`marker-${stop.entity_id}`}
          >
            <View
              style={[
                styles.dot,
                selectedName !== null && stop.name === selectedName ? styles.dotSelected : null,
              ]}
            />
          </Marker>
        ))}
      </Map>

      <View style={styles.overlay}>
        {selectedName ? <ThemedText type="smallBold">{selectedName}</ThemedText> : null}
        <ThemedText type="small">
          {loading ? 'Loading pilot stops…' : `${count} pilot stop${count === 1 ? '' : 's'} in view`}
        </ThemedText>
        {error ? <ThemedText type="small">{error}</ThemedText> : null}
        <ThemedText type="small" themeColor="textSecondary">
          Pilot data — all stops not field-checked yet.
        </ThemedText>
        {/* ODbL attribution: required for any public display of OpenStreetMap data. */}
        <ThemedText type="small" themeColor="textSecondary" testID="osm-attribution">
          Map and stop data © OpenStreetMap contributors (ODbL).
        </ThemedText>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  overlay: {
    position: 'absolute',
    top: Spacing.four,
    left: Spacing.three,
    right: Spacing.three,
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderRadius: 8,
    padding: Spacing.two,
    gap: Spacing.one,
  },
  dot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#208AEF',
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  dotSelected: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: '#D93025',
  },
});
