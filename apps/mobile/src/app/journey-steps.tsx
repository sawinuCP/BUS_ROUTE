import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, TextInput, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import {
  ApiStatusError,
  startJourneySession,
  submitReport,
  type JourneyPlanResponse,
  type PlanOption,
  type PlanStep,
  type ReportCategory,
  type ReportSubjectType,
} from '@/lib/api';
import { getOptionById, getPlan, setPlan } from '@/lib/planStore';
import { readCachedPlan } from '@/lib/planDb';
import { enqueueReport, flushQueuedReports, newReportClientKey, readQueuedReports } from '@/lib/reportQueue';

/**
 * Step-by-step instructions (Phase 5, plan item 10; Phase 7 items 1–2).
 *
 * Renders the option's ordered `steps` exactly as the backend's deterministic
 * templates produced them — the app never rewrites or reorders instruction
 * text. The honesty footer repeats the dataset version and the
 * "network feasible, not live confirmed" scope so a traveller can never mistake
 * a plan for a live departure board.
 *
 * Offline support (Phase 7): when the in-memory hand-off is empty (app
 * restart), the last cached plan is restored from SQLite and shown with an
 * explicit "saved on this device" banner (cache age + capabilities note) —
 * the app never presents cached content as fresh.
 */

const ACTION_LABELS: Record<PlanStep['action'], string> = {
  WALK_TO_STOP: 'Walk',
  BOARD_TRANSIT: 'Board',
  RIDE_TRANSIT: 'Ride',
  ALIGHT_TRANSIT: 'Alight',
  WALK_TRANSFER: 'Change',
  WALK_TO_DESTINATION: 'Arrive',
};

function cacheAgeLabel(savedAt: string): string {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(savedAt)) / 60_000));
  if (minutes < 1) {
    return 'just now';
  }
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours} h ago`;
  }
  return `${Math.round(hours / 24)} d ago`;
}

interface StepsBoot {
  option: PlanOption | null;
  plan: JourneyPlanResponse | null;
  /** Cache `saved_at` when the view is restored from the offline cache. */
  fromCache: string | null;
}

function bootstrapSteps(optionParam: string | undefined): StepsBoot {
  const storeOption = getOptionById(optionParam);
  if (storeOption) {
    return { option: storeOption, plan: getPlan(), fromCache: null };
  }
  const cached = readCachedPlan();
  if (!cached) {
    return { option: null, plan: null, fromCache: null };
  }
  setPlan(cached.plan); // restore the hand-off so "Start guided journey" works
  const optionId = optionParam ?? cached.option_id ?? undefined;
  const option = cached.plan.options.find((candidate) => candidate.id === optionId) ?? null;
  return { option, plan: cached.plan, fromCache: cached.saved_at };
}

const REPORT_CATEGORIES: { value: ReportCategory; label: string }[] = [
  { value: 'wrong_stop', label: 'Wrong stop (name/location)' },
  { value: 'route_variant', label: 'Route or variant' },
  { value: 'direction', label: 'Direction' },
  { value: 'transfer_path', label: 'Transfer path' },
  { value: 'landmark_name', label: 'Landmark or name' },
  { value: 'fare', label: 'Fare' },
  { value: 'access_attribute', label: 'Access (step-free, shelter…)' },
  { value: 'outdated_data', label: 'Outdated data' },
  { value: 'other', label: 'Other' },
];

export default function JourneyStepsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ option?: string }>();
  // Read once at mount: the plan comes either from the in-memory hand-off
  // (normal flow) or from the offline cache (restart). SQLite reads are
  // synchronous, so no loading state is needed. Cache restore also updates
  // the in-memory store (module variable, not React state).
  const [boot] = useState<StepsBoot>(() => bootstrapSteps(params.option));
  const option = boot.option;
  const plan = boot.plan;
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  // Report a problem (Phase 7 items 4 + 7): consent-gated, queued offline.
  const [reporting, setReporting] = useState(false);
  const [reportCategory, setReportCategory] = useState<ReportCategory | null>(null);
  const [reportText, setReportText] = useState('');
  const [reportConsent, setReportConsent] = useState(false);
  const [reportNote, setReportNote] = useState<string | null>(null);
  const [pendingReports, setPendingReports] = useState(0);

  // Queued reports sync at the first opportunity (idempotent per client key).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setPendingReports(readQueuedReports().length);
      const outcome = await flushQueuedReports();
      if (!cancelled) {
        setPendingReports(outcome.remaining);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function subjectType(): ReportSubjectType | undefined {
    return plan?.journey_id ? 'journey' : undefined;
  }

  async function submitProblemReport() {
    if (!reportCategory || reportText.trim().length < 5 || !reportConsent) {
      return;
    }
    const request = {
      category: reportCategory,
      description: reportText.trim(),
      consent: true,
      client_key: newReportClientKey(),
      subject_type: subjectType(),
      subject_id: plan?.journey_id,
      dataset_version_label: plan?.dataset_version,
    };
    try {
      await submitReport(request);
      setReportNote(
        'Report submitted — thank you. A moderator reviews it before any data'
        + ' changes; nothing here auto-changes data.',
      );
      setReportCategory(null);
      setReportText('');
      setReportConsent(false);
    } catch (error) {
      if (error instanceof ApiStatusError && error.status >= 400 && error.status < 500) {
        setReportNote('The report was refused by the backend — please check it and try again.');
        return;
      }
      // Offline: queue with its idempotency key; a later flush can never
      // duplicate the submission (plan item 4).
      enqueueReport(request);
      setPendingReports(readQueuedReports().length);
      setReportNote(
        'Offline — the report is saved on this device and will sync automatically.',
      );
      setReportCategory(null);
      setReportText('');
      setReportConsent(false);
    }
  }

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
        {boot.fromCache ? (
          <View style={styles.cachedBanner} testID="cached-banner">
            <ThemedText type="smallBold">Saved on this device · {cacheAgeLabel(boot.fromCache)}</ThemedText>
            <ThemedText type="small">
              If you are offline, planning, search and live checks are unavailable — the steps
              below remain followable as written.
            </ThemedText>
          </View>
        ) : null}
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

        <View style={styles.reportBlock} testID="report-block">
          <Pressable
            style={styles.reportButton}
            onPress={() => {
              setReporting((open) => !open);
              setReportNote(null);
            }}
            testID="report-button"
          >
            <ThemedText type="smallBold">Report a problem with this journey</ThemedText>
          </Pressable>

          {pendingReports > 0 ? (
            <ThemedText type="small" themeColor="textSecondary" testID="reports-pending">
              {pendingReports} report{pendingReports === 1 ? '' : 's'} saved on this device,
              waiting to sync.
            </ThemedText>
          ) : null}

          {reporting ? (
            <View style={styles.reportPanel} testID="report-panel">
              <ThemedText type="smallBold">What is wrong?</ThemedText>
              <View style={styles.reportCategories}>
                {REPORT_CATEGORIES.map((category) => (
                  <Pressable
                    key={category.value}
                    style={[styles.option, reportCategory === category.value ? styles.optionSelected : null]}
                    onPress={() => setReportCategory(category.value)}
                    testID={`report-category-${category.value}`}
                  >
                    <ThemedText type="small">{category.label}</ThemedText>
                  </Pressable>
                ))}
              </View>
              <TextInput
                style={styles.reportInput}
                placeholder="Describe the problem (at least a few words)…"
                placeholderTextColor="#888"
                multiline
                value={reportText}
                onChangeText={setReportText}
                testID="report-description"
              />
              <View style={styles.consentRow}>
                <Switch
                  value={reportConsent}
                  onValueChange={setReportConsent}
                  testID="report-consent"
                />
                <ThemedText type="small" style={styles.consentText}>
                  I agree that this report is stored and reviewed by a moderator before any data
                  changes. It is tied to this journey and dataset version — no location data is
                  stored. Nothing auto-changes the data.
                </ThemedText>
              </View>
              <Pressable
                style={[styles.reportButton, reportCategory && reportText.trim().length >= 5 && reportConsent ? null : styles.disabled]}
                onPress={() => void submitProblemReport()}
                disabled={!(reportCategory && reportText.trim().length >= 5 && reportConsent)}
                testID="report-submit"
              >
                <ThemedText type="smallBold">Submit report</ThemedText>
              </Pressable>
              {reportNote ? (
                <ThemedText type="small" testID="report-note">
                  {reportNote}
                </ThemedText>
              ) : null}
            </View>
          ) : null}
        </View>

        <ThemedText type="small" themeColor="textSecondary">
          Grounded in dataset {boot.plan?.dataset_version ?? 'unknown'} · network feasible, not
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
  cachedBanner: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    padding: Spacing.two,
    gap: Spacing.one,
    backgroundColor: 'rgba(128,128,128,0.12)',
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
  reportBlock: {
    gap: Spacing.one,
  },
  reportButton: {
    alignSelf: 'flex-start',
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  reportPanel: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    padding: Spacing.two,
    gap: Spacing.one,
  },
  reportCategories: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  option: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  optionSelected: {
    backgroundColor: 'rgba(32,138,239,0.15)',
  },
  reportInput: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minHeight: 60,
  },
  consentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one,
  },
  consentText: {
    flex: 1,
  },
  disabled: {
    opacity: 0.5,
  },
});
