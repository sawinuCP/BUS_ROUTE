import { Link } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { searchPlaces, type SearchHit } from '@/lib/api';

/**
 * Home / plan entry (Phase 2).
 * Origin/destination search over the pilot index with multilingual aliases.
 * Ambiguous candidates are listed — the user selects; nothing auto-selects.
 * Manual coordinate entry is the no-location / no-result fallback (US-002/005).
 * Map selection (MapLibre) is a separate screen pending the dev-client spike.
 */

type Selection =
  | { kind: 'hit'; label: string; detail: string; coords?: { lat: number; lon: number } }
  | { kind: 'coordinates'; label: string; detail: string; coords: { lat: number; lon: number } };

const TYPE_LABELS: Record<SearchHit['entity_type'], string> = {
  stop: 'Bus stop',
  place: 'Place',
  locality: 'Area',
  route: 'Route',
};

export default function HomeScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchHit[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [manualLat, setManualLat] = useState('');
  const [manualLon, setManualLon] = useState('');

  async function runSearch() {
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await searchPlaces(trimmed);
      setResults(response.results);
      setSearched(true);
    } catch {
      setError('Search failed — check the backend connection and try again.');
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  }

  function useManualCoordinates() {
    const lat = Number.parseFloat(manualLat);
    const lon = Number.parseFloat(manualLon);
    if (Number.isNaN(lat) || Number.isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setError('Enter valid latitude (-90…90) and longitude (-180…180).');
      return;
    }
    setError(null);
    setSelection({
      kind: 'coordinates',
      label: 'Manual coordinate',
      detail: `lat ${lat.toFixed(5)}, lon ${lon.toFixed(5)} (approximate)`,
      coords: { lat, lon },
    });
  }

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="subtitle">Where to?</ThemedText>
      <TextInput
        style={styles.input}
        placeholder="Search a stop, place, area or route…"
        placeholderTextColor="#888"
        value={query}
        onChangeText={setQuery}
        onSubmitEditing={() => {
          void runSearch();
        }}
        testID="search-input"
      />
      <Pressable style={styles.button} onPress={() => void runSearch()} testID="search-button">
        <ThemedText type="smallBold">{loading ? 'Searching…' : 'Search'}</ThemedText>
      </Pressable>

      {error ? <ThemedText type="small">{error}</ThemedText> : null}

      {selection ? (
        <View style={styles.selectionCard}>
          <ThemedText type="smallBold">{selection.label}</ThemedText>
          <ThemedText type="small">{selection.detail}</ThemedText>
          {selection.coords ? (
            <Link
              href={{
                pathname: '/map',
                params: {
                  lat: selection.coords.lat.toString(),
                  lon: selection.coords.lon.toString(),
                  name: selection.label,
                },
              }}
              testID="view-on-map"
            >
              <ThemedText type="linkPrimary">View on map</ThemedText>
            </Link>
          ) : null}
        </View>
      ) : null}

      {searched && results.length === 0 && !error ? (
        <ThemedText type="small">
          No matches in the pilot data. Try a nearby landmark, or enter coordinates below.
        </ThemedText>
      ) : null}

      <FlatList
        data={results}
        keyExtractor={(item) => `${item.entity_type}-${item.entity_id}`}
        renderItem={({ item }) => (
          <Pressable
            style={styles.resultRow}
            onPress={() =>
              setSelection({
                kind: 'hit',
                label: `${TYPE_LABELS[item.entity_type]}: ${item.name}`,
                detail: `${
                  item.matched_language === 'canonical'
                    ? 'matched by name'
                    : `matched via ${item.matched_language} name`
                }${item.verification_status === 'unverified' ? ' · not field-checked yet' : ''}`,
                ...(item.coordinates ? { coords: item.coordinates } : {}),
              })
            }
            testID={`result-${item.entity_id}`}
          >
            <ThemedText type="small">{TYPE_LABELS[item.entity_type]}</ThemedText>
            <ThemedText>{item.name}</ThemedText>
            {item.matched_language !== 'canonical' ? (
              <ThemedText type="small" themeColor="textSecondary">
                matched via {item.matched_language}: {item.matched_text}
              </ThemedText>
            ) : null}
          </Pressable>
        )}
        ListEmptyComponent={undefined}
      />

      <View style={styles.manualRow}>
        <ThemedText type="small">No result? Enter coordinates manually:</ThemedText>
        <View style={styles.manualInputs}>
          <TextInput
            style={[styles.input, styles.manualInput]}
            placeholder="lat (e.g. 6.9107)"
            placeholderTextColor="#888"
            keyboardType="numbers-and-punctuation"
            value={manualLat}
            onChangeText={setManualLat}
          />
          <TextInput
            style={[styles.input, styles.manualInput]}
            placeholder="lon (e.g. 79.8483)"
            placeholderTextColor="#888"
            keyboardType="numbers-and-punctuation"
            value={manualLon}
            onChangeText={setManualLon}
          />
          <Pressable style={styles.button} onPress={useManualCoordinates} testID="manual-button">
            <ThemedText type="smallBold">Use</ThemedText>
          </Pressable>
        </View>
      </View>

      <Link href="/journey">
        <ThemedText type="linkPrimary">Journey placeholder</ThemedText>
      </Link>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  input: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(128,128,128,0.15)',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  resultRow: {
    paddingVertical: Spacing.one,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#777',
    gap: 2,
  },
  selectionCard: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    padding: Spacing.two,
    gap: 2,
  },
  manualRow: {
    gap: Spacing.one,
  },
  manualInputs: {
    flexDirection: 'row',
    gap: Spacing.one,
    alignItems: 'center',
  },
  manualInput: {
    flex: 1,
  },
});
