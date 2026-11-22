import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { startJourneySession } from '@/lib/api';
import type { PlanOption, PlanStep } from '@/lib/api';
import { getOptionById, getPlan } from '@/lib/planStore';

/**
 * Step-by-step instructions (Phase 5, plan item 10).
 *
 * Renders the option's ordered `steps` exactly as the backend's deterministic
 * templates produced them — the app never rewrites or reorders instruction
 * text. The honesty footer repeats the dataset version and the
 * "network feasible, not live confirmed" scope so a traveller can never mistake
 * a plan for a live departure board.
 */

const ACTION_LABELS: Record<PlanStep['action'], string> = {
  WALK_TO_STOP: 'Walk',
  BOARD_TRANSIT: 'Board',
  RIDE_TRANSIT: 'Ride',
  ALIGHT_TRANSIT: 'Alight',
  WALK_TRANSFER: 'Change',
  WALK_TO_DESTINATION: 'Arrive',
};

export default function JourneyStepsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ option?: string }>();
  const option: PlanOption | null = getOptionById(params.option);
  const plan = getPlan();
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  async function startGuided() {
    if (!plan?.journey_id || !option) {
      return;
    }
    setStarting(true);
    setStartError(null);
    try {
      const session = await startJourneySession(plan.journey_id, option.id);
      router.push({ pathname: '/active-journey', params: { session: session.session_id } });
    } catch {
      setStartError('Could not start the guided journey — check the connection and try again.');
    } finally {
      setStarting(false);
    }
  }

  if (!option) {
    return (
      <ThemedView style={styles.container} testID="no-plan">
        <ThemedText type="subtitle">No plan in progress</ThemedText>
        <ThemedText type="small">
          Start from the plan screen: pick a start and destination stop, then choose one of the
          journey options.
        </ThemedText>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="subtitle">Your journey</ThemedText>
        <ThemedText type="smallBold">
          {option.summary.estimated_duration_minutes.min}–
          {option.summary.estimated_duration_minutes.max} min (network estimate) ·{' '}
          {option.summary.transfer_count} transfer
          {option.summary.transfer_count === 1 ? '' : 's'} · walk{' '}
          {Math.round(option.summary.walking_distance_m)} m
        </ThemedText>

        {option.warnings.map((warning) => (
          <ThemedText key={warning} type="small" themeColor="textSecondary">
            • {warning}
          </ThemedText>
        ))}

        <View style={styles.steps}>
          {option.steps.map((step, index) => (
            <View key={`${step.action}-${index}`} style={styles.step} testID={`step-${index}`}>
              <View style={styles.stepBadge}>
                <ThemedText type="smallBold">{ACTION_LABELS[step.action]}</ThemedText>
              </View>
              <ThemedText style={styles.stepText}>{step.text}</ThemedText>
            </View>
          ))}
        </View>

        {plan?.journey_id ? (
          <View style={styles.startBlock}>
            <Pressable
              style={styles.startButton}
              onPress={() => void startGuided()}
              disabled={starting}
              testID="start-guided-button"
            >
              <ThemedText type="smallBold">
                {starting ? 'Starting…' : 'Start guided journey'}
              </ThemedText>
            </Pressable>
            <ThemedText type="small" themeColor="textSecondary">
              Follows this option step by step with manual confirmations — you stay in control.
            </ThemedText>
            {startError ? <ThemedText type="small">{startError}</ThemedText> : null}
          </View>
        ) : null}

        <ThemedText type="small" themeColor="textSecondary">
          Grounded in dataset {getPlan()?.dataset_version ?? 'unknown'} · network feasible, not
          live confirmed — service frequency is not checked. Waiting times are unknown; board the
          next bus on the shown route.
        </ThemedText>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: Spacing.three,
    gap: Spacing.two,
  },
  steps: {
    gap: Spacing.one,
    marginTop: Spacing.one,
  },
  step: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.two,
  },
  stepBadge: {
    minWidth: 64,
    borderRadius: 8,
    backgroundColor: 'rgba(32,138,239,0.15)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    alignItems: 'center',
  },
  stepText: {
    flex: 1,
  },
  startBlock: {
    gap: Spacing.one,
  },
  startButton: {
    borderRadius: 8,
    backgroundColor: 'rgba(32,138,239,0.15)',
    paddingVertical: 12,
    alignItems: 'center',
  },
});
