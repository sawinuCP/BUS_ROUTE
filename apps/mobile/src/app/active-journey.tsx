import { useLocalSearchParams } from 'expo-router';
import * as KeepAwake from 'expo-keep-awake';
import * as Location from 'expo-location';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import {
  ApiStatusError,
  getJourneySession,
  postSessionEvent,
  replanJourneySession,
  type JourneySessionState,
  type SessionEventType,
  type SessionStep,
} from '@/lib/api';
import { evaluateProximity, type LocationSample, type SuggestionResult } from '@/lib/geoSuggestions';
import { readCachedPlan, readCachedOptionSteps } from '@/lib/planDb';
import {
  enqueueProgressEvent,
  projectOfflineState,
  readQueuedEvents,
  replayQueuedEvents,
} from '@/lib/progressQueue';
import { clearActiveSession, readActiveSession, saveActiveSession } from '@/lib/sessionDb';

/**
 * "Do this now" — active journey mode (Phase 6, plan items 2–6, 8).
 *
 * Manual progress is authoritative: every state change is an explicit button
 * (confirm/pause/resume/end). GPS is **assistive only** and off by default:
 * when enabled it can surface an arrival *suggestion* (after accuracy and
 * dwell safeguards), which the traveller still confirms manually — a GPS
 * sample can never advance or complete a step. State is persisted locally
 * (session id + last snapshot, no location) and restored after restart.
 */

const ACTION_LABELS: Record<SessionStep['action'], string> = {
  WALK_TO_STOP: 'Walk',
  BOARD_TRANSIT: 'Board',
  RIDE_TRANSIT: 'Ride',
  ALIGHT_TRANSIT: 'Alight',
  WALK_TRANSFER: 'Change',
  WALK_TO_DESTINATION: 'Arrive',
};

/** Stop-proximity radius for arrival suggestions (metres). */
const ARRIVAL_RADIUS_M = 40;

export default function ActiveJourneyScreen() {
  const params = useLocalSearchParams<{ session?: string }>();
  const [state, setState] = useState<JourneySessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [gpsEnabled, setGpsEnabled] = useState(false);
  const [suggestion, setSuggestion] = useState<SuggestionResult | null>(null);
  const [keepAwakeOn, setKeepAwakeOn] = useState(false);
  const [pendingSync, setPendingSync] = useState(0);
  const [syncNote, setSyncNote] = useState<string | null>(null);
  const [staleVersion, setStaleVersion] = useState<string | null>(null);
  const samplesRef = useRef<LocationSample[]>([]);
  const locationWatchRef = useRef<Location.LocationSubscription | null>(null);
  const aliveRef = useRef(true);

  // Keep-awake is opt-in (plan §Phase 6): activated only while the toggle is
  // on, deactivated on toggle-off and unmount.
  useEffect(() => {
    if (!keepAwakeOn) {
      return;
    }
    let active = true;
    void KeepAwake.activateKeepAwakeAsync().catch(() => {
      if (active) {
        setError('Could not keep the screen awake on this device.');
        setKeepAwakeOn(false);
      }
    });
    return () => {
      active = false;
      void KeepAwake.deactivateKeepAwake();
    };
  }, [keepAwakeOn]);

  const applyState = useCallback((next: JourneySessionState) => {
    setState(next);
    saveActiveSession(next.session_id, JSON.stringify(next));
    samplesRef.current = []; // new step → fresh dwell window
    setSuggestion(null);
  }, []);

  // GPS watcher lifecycle (Phase 6 item 5): the switch handler stays purely
  // synchronous; the async permission/watch setup lives in this effect and is
  // fully cleaned up on toggle-off, unmount and re-toggles.
  useEffect(() => {
    if (!gpsEnabled) {
      return;
    }
    let cancelled = false;
    samplesRef.current = [];
    (async () => {
      try {
        const permission = await Location.requestForegroundPermissionsAsync();
        if (cancelled) {
          return;
        }
        if (!permission || permission.status !== 'granted') {
          setError('Location permission declined — manual progress still works fully.');
          setGpsEnabled(false);
          return;
        }
        const watch = await Location.watchPositionAsync(
          { accuracy: Location.Accuracy.Balanced, timeInterval: 5000, distanceInterval: 10 },
          (position) => {
            if (cancelled) {
              return; // stale watcher (re-toggle/unmount) must never evaluate samples
            }
            const step = state?.current_step;
            const lat = step?.facts.target_lat;
            const lon = step?.facts.target_lon;
            if (typeof lat !== 'number' || typeof lon !== 'number') {
              return; // no mapped target for this step → assistant stays silent
            }
            samplesRef.current.push({
              lat: position.coords.latitude,
              lon: position.coords.longitude,
              accuracy_m: position.coords.accuracy ?? 999,
            });
            if (samplesRef.current.length > 10) {
              samplesRef.current = samplesRef.current.slice(-10);
            }
            const result = evaluateProximity(samplesRef.current, {
              lat,
              lon,
              radius_m: ARRIVAL_RADIUS_M,
              label: step?.text ?? '',
            });
            setSuggestion(result.suggest ? result : null);
          },
        );
        if (cancelled) {
          watch.remove();
          return;
        }
        locationWatchRef.current = watch;
      } catch {
        // GPS must never break manual progress (plan §Phase 6).
        if (!cancelled) {
          setError('Location tracking unavailable — manual progress still works fully.');
          setGpsEnabled(false);
        }
      }
    })();
    return () => {
      cancelled = true;
      if (locationWatchRef.current) {
        locationWatchRef.current.remove();
        locationWatchRef.current = null;
      }
      samplesRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gpsEnabled]);

  /**
   * Phase 7 (items 1–3): after a successful server GET, replay any events
   * queued while offline (in order — the backend's transition table stays
   * valid) and adopt the server state. Also warn honestly when the session's
   * dataset version differs from the cached plan the traveller is following.
   */
  async function reconcileAfterRestore(fetched: JourneySessionState) {
    if (!aliveRef.current) {
      return;
    }
    const outcome = await replayQueuedEvents(fetched.session_id);
    if (!aliveRef.current) {
      return;
    }
    setPendingSync(outcome.remaining);
    if (outcome.conflict) {
      if (outcome.final_state) {
        applyState(outcome.final_state);
      }
      setSyncNote(null);
      setError(`Offline progress could not all be applied — ${outcome.conflict}`);
      return;
    }
    if (outcome.synced > 0 && outcome.final_state) {
      applyState(outcome.final_state);
      if (
        outcome.final_state.status === 'completed'
        || outcome.final_state.status === 'cancelled'
      ) {
        clearActiveSession();
      }
      setSyncNote(
        `Synced ${outcome.synced} offline progress change${outcome.synced === 1 ? '' : 's'}.`,
      );
    }
    const cached = readCachedPlan();
    if (
      cached
      && cached.plan.journey_id === fetched.journey_id
      && cached.plan.dataset_version !== fetched.dataset_version
    ) {
      setStaleVersion(
        `This saved journey was planned on dataset ${cached.plan.dataset_version}; the network`
        + ` now serves ${fetched.dataset_version}. Steps may no longer match the current data.`,
      );
    }
  }

  /**
   * Network failure (not a 409): queue the event, project it locally so the
   * itinerary stays followable offline, and surface the sync note. The
   * backend confirms everything on replay — the projection is display-only.
   */
  function handleOfflineEvent(
    currentState: JourneySessionState,
    event: { event_type: SessionEventType; step_index?: number; note?: string },
  ) {
    enqueueProgressEvent(currentState.session_id, event);
    const steps = readCachedOptionSteps(currentState.journey_id, currentState.option_id);
    const projected = projectOfflineState(currentState, event, steps);
    if (projected) {
      // Keep the session cached even for projected terminal states: the
      // backend must confirm completion before local cleanup.
      saveActiveSession(projected.session_id, JSON.stringify(projected));
      setState(projected);
      samplesRef.current = []; // new step → fresh dwell window
    }
    setPendingSync(readQueuedEvents(currentState.session_id).length);
    setSyncNote(
      projected
        ? 'Offline — progress saved on this device and will sync when the connection returns.'
        : 'Offline — progress saved on this device; the next step will appear after sync.',
    );
    setError(null);
  }

  /**
   * Replays queued offline events before any new online action so the
   * backend receives them in order. Returns false when the caller should
   * stop (conflict adopted from the server state, or still offline).
   */
  async function flushPendingSync(sessionId: string): Promise<boolean> {
    if (readQueuedEvents(sessionId).length === 0) {
      return true;
    }
    const outcome = await replayQueuedEvents(sessionId);
    setPendingSync(outcome.remaining);
    if (outcome.conflict) {
      if (outcome.final_state) {
        applyState(outcome.final_state);
      }
      setSyncNote(null);
      setError(`Offline progress could not all be applied — ${outcome.conflict}`);
      return false;
    }
    if (outcome.synced > 0 && outcome.final_state) {
      applyState(outcome.final_state);
      if (
        outcome.final_state.status === 'completed'
        || outcome.final_state.status === 'cancelled'
      ) {
        clearActiveSession();
      }
      setSyncNote(
        `Synced ${outcome.synced} offline progress change${outcome.synced === 1 ? '' : 's'}.`,
      );
    }
    return outcome.remaining === 0;
  }

  useEffect(() => {
    aliveRef.current = true;
    let cancelled = false;
    async function restore() {
      const persisted = readActiveSession();
      const sessionId = params.session ?? persisted?.session_id;
      if (!sessionId) {
        setLoading(false);
        return;
      }
      try {
        const fetched = await getJourneySession(sessionId);
        if (!cancelled) {
          applyState(fetched);
          setError(null);
          await reconcileAfterRestore(fetched);
        }
      } catch {
        // Offline / backend down: show the last known snapshot honestly.
        if (!cancelled && persisted?.snapshot) {
          try {
            const parsed = JSON.parse(persisted.snapshot) as JourneySessionState;
            setState(parsed);
            setError('Could not refresh — showing the last known state.');
            setPendingSync(readQueuedEvents(parsed.session_id).length);
          } catch {
            setError('Could not load the active journey. Check the backend connection.');
          }
        } else if (!cancelled) {
          setError('Could not load the active journey. Check the backend connection.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void restore();
    return () => {
      cancelled = true;
      aliveRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runEvent(eventType: 'paused' | 'resumed' | 'completed' | 'cancelled') {
    if (!state) {
      return;
    }
    setBusy(true);
    try {
      const flushed = await flushPendingSync(state.session_id);
      if (!flushed) {
        return; // conflict adopted from the server state, or still offline
      }
      const next = await postSessionEvent(state.session_id, eventType);
      applyState(next);
      setError(null);
      setSyncNote(null);
      if (eventType === 'completed' || eventType === 'cancelled') {
        clearActiveSession();
      }
    } catch (err) {
      if (err instanceof ApiStatusError && err.status === 409) {
        setError(`The backend refused that — ${err.message}`);
      } else {
        handleOfflineEvent(state, { event_type: eventType });
      }
    } finally {
      setBusy(false);
    }
  }

  async function confirmStep() {
    if (!state || !state.current_step) {
      return;
    }
    const isLast = state.progress.current_step >= state.progress.step_count - 1;
    setBusy(true);
    try {
      const flushed = await flushPendingSync(state.session_id);
      if (!flushed) {
        return; // conflict adopted from the server state, or still offline
      }
      const next = isLast
        ? await postSessionEvent(state.session_id, 'completed', undefined, 'confirmed last step')
        : await postSessionEvent(state.session_id, 'step_advanced', state.progress.current_step + 1);
      applyState(next);
      setError(null);
      setSyncNote(null);
      if (isLast) {
        clearActiveSession();
      }
    } catch (err) {
      if (err instanceof ApiStatusError && err.status === 409) {
        setError(`The backend refused that — ${err.message}`);
      } else if (isLast) {
        handleOfflineEvent(state, { event_type: 'completed', note: 'confirmed last step' });
      } else {
        handleOfflineEvent(state, {
          event_type: 'step_advanced',
          step_index: state.progress.current_step + 1,
        });
      }
    } finally {
      setBusy(false);
    }
  }

  async function replan() {
    if (!state) {
      return;
    }
    setBusy(true);
    try {
      const next = await replanJourneySession(state.session_id);
      if (next.replanned) {
        applyState(next);
      } else {
        // Honest no-replacement: keep following the current plan.
        setError(
          `No replacement journey found — continuing with the current plan (${(next.notes ?? []).join(' ')}).`,
        );
      }
    } catch (err) {
      if (err instanceof ApiStatusError && err.status === 409) {
        setError(`The backend refused that — ${err.message}`);
      } else {
        setError(
          'Re-planning needs a connection — try again when back online.'
          + ' Your progress stays saved on this device.',
        );
      }
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <ThemedView style={styles.container} testID="loading">
        <ThemedText type="small">Loading your journey…</ThemedText>
      </ThemedView>
    );
  }

  if (!state) {
    return (
      <ThemedView style={styles.container} testID="no-session">
        <ThemedText type="subtitle">No active journey</ThemedText>
        <ThemedText type="small">
          Plan a journey, pick an option, then tap &quot;Start guided journey&quot;.
        </ThemedText>
      </ThemedView>
    );
  }

  const isTerminal = state.status === 'completed' || state.status === 'cancelled';
  const isLast = state.progress.current_step >= state.progress.step_count - 1;

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <ThemedText type="subtitle">Do this now</ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          Step {state.progress.current_step + 1} of {state.progress.step_count} · status:{' '}
          {state.status}
        </ThemedText>

        {state.current_step ? (
          <View style={styles.nowCard} testID="do-this-now">
            <View style={styles.badge}>
              <ThemedText type="smallBold">{ACTION_LABELS[state.current_step.action]}</ThemedText>
            </View>
            <ThemedText>{state.current_step.text}</ThemedText>
          </View>
        ) : (
          <ThemedText type="small">All steps done — confirm below to finish.</ThemedText>
        )}

        {state.next_step ? (
          <ThemedText type="small" themeColor="textSecondary">
            Next: {ACTION_LABELS[state.next_step.action]} — {state.next_step.text}
          </ThemedText>
        ) : null}

        {suggestion ? (
          <ThemedText type="small" themeColor="textSecondary" testID="gps-suggestion">
            GPS suggests you may have arrived — confirm above when you are sure.
          </ThemedText>
        ) : null}

        {syncNote || pendingSync > 0 ? (
          <View style={styles.syncBanner} testID="sync-banner">
            <ThemedText type="smallBold" testID="sync-note">
              {syncNote
                ?? `Offline progress: ${pendingSync} change${pendingSync === 1 ? '' : 's'} waiting to sync`}
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              Manual progress is saved on this device — nothing is lost. Planning, search and
              re-planning need a connection.
            </ThemedText>
          </View>
        ) : null}

        {staleVersion ? (
          <ThemedText type="small" testID="stale-version-note">
            {staleVersion}
          </ThemedText>
        ) : null}

        {error ? <ThemedText type="small">{error}</ThemedText> : null}

        {isTerminal ? (
          <ThemedText type="smallBold" testID="terminal-note">
            {state.status === 'completed' ? 'Journey completed.' : 'Journey ended.'}
          </ThemedText>
        ) : (
          <View style={styles.actions}>
            <Pressable
              style={[styles.button, styles.primary]}
              onPress={() => void confirmStep()}
              disabled={busy}
              testID="confirm-button"
            >
              <ThemedText type="smallBold">
                {isLast ? 'Finish journey' : 'Done — next step'}
              </ThemedText>
            </Pressable>
            {state.status === 'paused' ? (
              <Pressable
                style={styles.button}
                onPress={() => void runEvent('resumed')}
                disabled={busy}
                testID="resume-button"
              >
                <ThemedText type="smallBold">Resume</ThemedText>
              </Pressable>
            ) : (
              <Pressable
                style={styles.button}
                onPress={() => void runEvent('paused')}
                disabled={busy}
                testID="pause-button"
              >
                <ThemedText type="smallBold">Pause</ThemedText>
              </Pressable>
            )}
            <Pressable
              style={styles.button}
              onPress={() => void replan()}
              disabled={busy}
              testID="replan-button"
            >
              <ThemedText type="smallBold">Missed it? Re-plan</ThemedText>
            </Pressable>
            <Pressable
              style={styles.button}
              onPress={() => void runEvent('cancelled')}
              disabled={busy}
              testID="end-button"
            >
              <ThemedText type="smallBold">End journey</ThemedText>
            </Pressable>
          </View>
        )}

        <View style={styles.toggleRow} testID="gps-row">
          <ThemedText type="small">GPS arrival hints (optional, suggestions only)</ThemedText>
          <Switch
            value={gpsEnabled}
            onValueChange={(value) => {
              samplesRef.current = []; // fresh dwell window on every toggle
              setSuggestion(null);
              setGpsEnabled(value);
            }}
            testID="gps-switch"
          />
        </View>
        <View style={styles.toggleRow} testID="awake-row">
          <ThemedText type="small">Keep screen awake</ThemedText>
          <Switch value={keepAwakeOn} onValueChange={setKeepAwakeOn} testID="awake-switch" />
        </View>

        <ThemedText type="small" themeColor="textSecondary">
          Grounded in dataset {state.dataset_version} · network feasible, not live confirmed. No
          location data is stored or sent with your progress.
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
  nowCard: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    padding: Spacing.two,
    gap: Spacing.one,
  },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 8,
    backgroundColor: 'rgba(32,138,239,0.15)',
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  actions: {
    gap: Spacing.one,
  },
  button: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    paddingVertical: 12,
    alignItems: 'center',
  },
  primary: {
    backgroundColor: 'rgba(32,138,239,0.15)',
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  syncBanner: {
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#999',
    padding: Spacing.two,
    gap: Spacing.one,
    backgroundColor: 'rgba(128,128,128,0.12)',
  },
});

