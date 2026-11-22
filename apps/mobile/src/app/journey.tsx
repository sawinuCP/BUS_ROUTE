import { useRouter } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import {
  planJourney,
  searchPlaces,
  type JourneyPlanResponse,
  type PlanOption,
  type SearchHit,
} from '@/lib/api';
import { setPlan } from '@/lib/planStore';

/**
 * Journey planning + results comparison (Phase 5, plan items 9–10).
 *
 * The traveller picks an origin and a destination **stop** from search
 * results — candidates are listed and selected by explicit taps, never
 * auto-selected (product rule from Phase 2). Results are rendered as cards
 * with their explicit trade-offs (duration band, walking, transfers) and
 * honest confidence/warnings; a `no_route` answer is shown with the
 * backend's own reasons — the app never invents a journey.
 */

interface PickerState {
  query: string;
  results: SearchHit[];
  searched: boolean;
  selected: SearchHit | null;
}

const EMPTY_PICKER: PickerState = { query: '', results: [], searched: false, selected: null };

const CONFIDENCE_TEXT: Record<PlanOption['summary']['confidence'], string> = {
  verified: 'All facts verified',
  unverified_pattern: 'Includes route data not yet field-checked',
  unverified_transfer: 'Includes a transfer path not yet field-checked',
};

function EndpointPicker({
  role,
  state,
  onChangeQuery,
  onSearch,
  onSelect,
}: {
  role: 'origin' | 'destination';
  state: PickerState;
  onChangeQuery: (text: string) => void;
  onSearch: () => void;
  onSelect: (hit: SearchHit) => void;
}) {
  const title = role === 'origin' ? 'From' : 'To';
  return (
    <View style={styles.picker}>
      <ThemedText type="smallBold">{title}</ThemedText>
      <TextInput
        style={styles.input}
        placeholder={role === 'origin' ? 'Start stop…' : 'Destination stop…'}
        placeholderTextColor="#888"
        value={state.query}
        onChangeText={onChangeQuery}
        testID={`${role}-input`}
      />
      <Pressable style={styles.button} onPress={onSearch} testID={`${role}-search`}>
        <ThemedText type="smallBold">Search stops</ThemedText>
      </Pressable>
      {state.selected ? (
        <ThemedText type="small" themeColor="textSecondary">
          Selected: {state.selected.name}
        </ThemedText>
      ) : null}
      {state.searched && state.results.length === 0 ? (
        <ThemedText type="small">No stop matches — try another name.</ThemedText>
      ) : null}
      <FlatList
        data={state.results}
        keyExtractor={(item) => item.entity_id}
        renderItem={({ item }) => (
          <Pressable
            style={styles.resultRow}
            onPress={() => onSelect(item)}
            testID={`${role}-result-${item.entity_id}`}
          >
            <ThemedText type="small">{item.name}</ThemedText>
          </Pressable>
        )}
      />
    </View>
  );
}

export default function JourneyScreen() {
  const router = useRouter();
  const [origin, setOrigin] = useState<PickerState>(EMPTY_PICKER);
  const [destination, setDestination] = useState<PickerState>(EMPTY_PICKER);
  const [plan, setPlanState] = useState<JourneyPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runStopSearch(role: 'origin' | 'destination') {
    const state = role === 'origin' ? origin : destination;
    const trimmed = state.query.trim();
    if (!trimmed) {
      return;
    }
    try {
      const response = await searchPlaces(trimmed);
      const stops = response.results.filter((hit) => hit.entity_type === 'stop');
      const next = { ...state, results: stops, searched: true };
      if (role === 'origin') {
        setOrigin(next);
      } else {
        setDestination(next);
      }
    } catch {
      setError('Search failed — check the backend connection and try again.');
    }
  }

  function selectStop(role: 'origin' | 'destination', hit: SearchHit) {
    if (role === 'origin') {
      setOrigin({ ...origin, selected: hit });
    } else {
      setDestination({ ...destination, selected: hit });
    }
  }

  async function findJourneys() {
    if (!origin.selected || !destination.selected) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await planJourney(
        { type: 'stop', stop_id: origin.selected.entity_id },
        { type: 'stop', stop_id: destination.selected.entity_id },
        { priority: 'fastest', max_walking_m: 1500, max_transfers: 1 },
        'en',
      );
      setPlanState(response);
      setPlan(response); // hand-off for the steps screen
    } catch {
      setError('Planning failed — check the backend connection and try again.');
    } finally {
      setLoading(false);
    }
  }

  function openOption(option: PlanOption) {
    router.push({
      pathname: '/journey-steps',
      params: { option: option.id },
    });
  }

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="subtitle">Plan a journey</ThemedText>
      <EndpointPicker
        role="origin"
        state={origin}
        onChangeQuery={(text) => setOrigin({ ...origin, query: text })}
        onSearch={() => void runStopSearch('origin')}
        onSelect={(hit) => selectStop('origin', hit)}
      />
      <EndpointPicker
        role="destination"
        state={destination}
        onChangeQuery={(text) => setDestination({ ...destination, query: text })}
        onSearch={() => void runStopSearch('destination')}
        onSelect={(hit) => selectStop('destination', hit)}
      />
      <Pressable
        style={[styles.button, styles.planButton]}
        onPress={() => void findJourneys()}
        testID="plan-button"
      >
        <ThemedText type="smallBold">{loading ? 'Planning…' : 'Find journeys'}</ThemedText>
      </Pressable>
      {error ? <ThemedText type="small">{error}</ThemedText> : null}

      {plan && plan.status === 'no_route' ? (
        <View style={styles.noRoute} testID="no-route">
          <ThemedText type="smallBold">No journey found in the pilot data</ThemedText>
          {plan.notes.map((note) => (
            <ThemedText key={note} type="small">
              • {note}
            </ThemedText>
          ))}
        </View>
      ) : null}

      {plan && plan.status === 'ok'
        ? plan.options.map((option) => (
            <Pressable
              key={option.id}
              style={styles.card}
              onPress={() => openOption(option)}
              testID={`option-${option.id}`}
            >
              <View style={styles.cardHeader}>
                <ThemedText type="smallBold">
                  {option.summary.estimated_duration_minutes.min}–
                  {option.summary.estimated_duration_minutes.max} min (network estimate)
                </ThemedText>
                {option.labels.map((label) => (
                  <View key={label} style={styles.chip} testID={`label-${option.id}-${label}`}>
                    <ThemedText type="small">{label}</ThemedText>
                  </View>
                ))}
              </View>
              <ThemedText type="small">
                Walk {Math.round(option.summary.walking_distance_m)} m ·{' '}
                {option.summary.transfer_count} transfer
                {option.summary.transfer_count === 1 ? '' : 's'}
              </ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                {CONFIDENCE_TEXT[option.summary.confidence]}
              </ThemedText>
              {option.warnings.map((warning) => (
                <ThemedText key={warning} type="small" themeColor="textSecondary">
                  • {warning}
                </ThemedText>
              ))}
            </Pressable>
          ))
        : null}

      {plan && plan.status === 'ok' ? (
        <ThemedText type="small" themeColor="textSecondary">
          Plans are grounded in pilot data (dataset {plan.dataset_version}) and are network
          estimates — service frequency is not confirmed. Tap a card for step-by-step directions.
        </ThemedText>
      ) : null}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  picker: {
    gap: Spacing.one,
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
  planButton: {
    alignSelf: 'stretch',
    alignItems: 'center',
  },
  resultRow: {
    paddingVertical: Spacing.one,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#777',
  },
  card: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    padding: Spacing.two,
    gap: Spacing.one,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one,
    flexWrap: 'wrap',
  },
  chip: {
    borderRadius: 10,
    backgroundColor: 'rgba(32,138,239,0.15)',
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  noRoute: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    padding: Spacing.two,
    gap: Spacing.one,
  },
});

