/**
 * Offline manual progress (Phase 7, plan item 3).
 *
 * The backend session state machine stays authoritative: nothing is synced
 * silently and no server state can change while offline. This module
 *
 * 1. queues manual progress events in SQLite when the network is unreachable
 *    (never location data — events are the same typed, stateless payloads the
 *    backend API accepts),
 * 2. projects their effect **locally** so the downloaded itinerary remains
 *    readable and manually followable offline (Phase 7 exit criterion), and
 * 3. replays queued events in order once the connection returns, then adopts
 *    the server state.
 *
 * Replay rules (honesty first):
 * - Events replay in the order they were queued — the backend's transition
 *   table stays valid.
 * - A network failure keeps the remaining events queued (retry later).
 * - A 409 means the backend refused a transition (e.g. the session reached a
 *   terminal state or advanced elsewhere). The server state wins: remaining
 *   queued events are dropped and the conflict text is surfaced — the app
 *   never works around the state machine.
 *
 * The local projection mirrors `backend/app/modules/journey_sessions/
 * state_machine.py` exactly (action → status table, pause/terminal rules);
 * it is a *device-local display* of pending progress, always shown with the
 * offline banner until the server confirms it.
 */

import * as SQLite from 'expo-sqlite';

import {
  ApiStatusError,
  getJourneySession,
  postSessionEvent,
  type JourneySessionState,
  type PlanStep,
  type SessionEventType,
  type SessionStatus,
} from '@/lib/api';

const DB_NAME = 'sljp.db';

export interface QueuedEvent {
  id: number;
  event_type: SessionEventType;
  step_index: number | null;
  note: string | null;
  queued_at: string;
}

export interface NewQueuedEvent {
  event_type: SessionEventType;
  step_index?: number;
  note?: string;
}

function openDb(): SQLite.SQLiteDatabase {
  return SQLite.openDatabaseSync(DB_NAME);
}

function ensureSchema(db: SQLite.SQLiteDatabase): void {
  db.execSync(
    'CREATE TABLE IF NOT EXISTS pending_session_events ('
    + ' id INTEGER PRIMARY KEY AUTOINCREMENT,'
    + ' session_id TEXT NOT NULL,'
    + ' event_type TEXT NOT NULL,'
    + ' step_index INTEGER,'
    + ' note TEXT,'
    + ' queued_at TEXT NOT NULL)',
  );
}

export function enqueueProgressEvent(sessionId: string, event: NewQueuedEvent): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync(
    'INSERT INTO pending_session_events (session_id, event_type, step_index, note, queued_at) VALUES (?, ?, ?, ?, ?)',
    [
      sessionId,
      event.event_type,
      event.step_index ?? null,
      event.note ?? null,
      new Date().toISOString(),
    ],
  );
}

export function readQueuedEvents(sessionId: string): QueuedEvent[] {
  const db = openDb();
  ensureSchema(db);
  return db.getAllSync<{
    id: number;
    event_type: SessionEventType;
    step_index: number | null;
    note: string | null;
    queued_at: string;
  }>(
    'SELECT id, event_type, step_index, note, queued_at FROM pending_session_events'
    + ' WHERE session_id = ? ORDER BY id ASC',
    [sessionId],
  );
}

function removeQueuedEvent(id: number): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('DELETE FROM pending_session_events WHERE id = ?', [id]);
}

function clearQueuedEvents(sessionId: string): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('DELETE FROM pending_session_events WHERE session_id = ?', [sessionId]);
}

/** Test-only helper: empties the queue (all sessions). */
export function clearQueuedEventsForTests(): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('DELETE FROM pending_session_events');
}

/* ------------------------------------------------------------------ */
/* Local projection of a queued event (device display only).           */
/* ------------------------------------------------------------------ */

/** Mirrors state_machine.py's `_ACTION_STATE` table. */
const ACTION_STATE: Record<PlanStep['action'], SessionStatus> = {
  WALK_TO_STOP: 'active_walk',
  BOARD_TRANSIT: 'active_ride',
  RIDE_TRANSIT: 'active_ride',
  ALIGHT_TRANSIT: 'active_ride',
  WALK_TRANSFER: 'transfer_walk',
  WALK_TO_DESTINATION: 'final_walk',
};

function statusForStep(steps: PlanStep[], stepIndex: number): SessionStatus {
  // Backend rule: falls back to `overview` when the list is exhausted —
  // completion is an explicit event, never an implicit one.
  if (stepIndex < 0 || stepIndex >= steps.length) {
    return 'overview';
  }
  return ACTION_STATE[steps[stepIndex].action] ?? 'overview';
}

function asSessionStep(step: PlanStep): JourneySessionState['current_step'] {
  return { action: step.action, text: step.text, facts: step.facts, confidence: step.confidence };
}

/**
 * Projects one queued event onto the local snapshot so the traveller can
 * keep following the itinerary offline. Returns `null` when the backend's
 * rules make the event invalid (terminal state, advance while paused, or
 * steps unknown locally) — the caller must then show the backend's rule
 * text instead of inventing local progress.
 */
export function projectOfflineState(
  current: JourneySessionState,
  event: NewQueuedEvent,
  optionSteps: PlanStep[] | null,
): JourneySessionState | null {
  if (current.status === 'completed' || current.status === 'cancelled') {
    return null; // terminal states accept nothing
  }
  if (current.status === 'paused' && event.event_type === 'step_advanced') {
    return null; // progress cannot advance while paused (resume first)
  }
  const steps = optionSteps;
  switch (event.event_type) {
    case 'paused':
      return { ...current, status: 'paused' };
    case 'resumed': {
      if (!steps) {
        return null;
      }
      return {
        ...current,
        status: statusForStep(steps, current.progress.current_step),
      };
    }
    case 'step_advanced': {
      const index = event.step_index ?? current.progress.current_step + 1;
      if (!steps || index < 0 || index >= steps.length) {
        return null;
      }
      return {
        ...current,
        status: statusForStep(steps, index),
        progress: { current_step: index, step_count: current.progress.step_count },
        current_step: asSessionStep(steps[index]),
        next_step: index + 1 < steps.length ? asSessionStep(steps[index + 1]) : null,
      };
    }
    case 'completed':
      return {
        ...current,
        status: 'completed',
        progress: {
          current_step: current.progress.step_count,
          step_count: current.progress.step_count,
        },
        current_step: null,
        next_step: null,
      };
    case 'cancelled':
      return { ...current, status: 'cancelled', current_step: null, next_step: null };
    default:
      return null; // 'started' and anything unknown are server-only events
  }
}

/* ------------------------------------------------------------------ */
/* Replay of queued events once the connection is back.                */
/* ------------------------------------------------------------------ */

export interface ReplayOutcome {
  /** Events the backend accepted and removed from the queue. */
  synced: number;
  /** Events still queued (network still down) after this attempt. */
  remaining: number;
  /** Backend rule text when a transition was refused (409). */
  conflict: string | null;
  /** Last known server state (post-replay, or the server's on conflict). */
  final_state: JourneySessionState | null;
}

export async function replayQueuedEvents(
  sessionId: string,
  postEvent: (
    sessionId: string,
    eventType: SessionEventType,
    stepIndex?: number,
    note?: string,
  ) => Promise<JourneySessionState> = postSessionEvent,
  getFreshState: (sessionId: string) => Promise<JourneySessionState> = getJourneySession,
): Promise<ReplayOutcome> {
  let synced = 0;
  let finalState: JourneySessionState | null = null;
  let conflict: string | null = null;

  for (const event of readQueuedEvents(sessionId)) {
    try {
      finalState = await postEvent(
        sessionId,
        event.event_type,
        event.step_index ?? undefined,
        event.note ?? undefined,
      );
      removeQueuedEvent(event.id);
      synced += 1;
    } catch (error) {
      if (error instanceof ApiStatusError && error.status === 409) {
        // Server state wins: adopt it, drop the now-impossible events and
        // surface the rule text. A completed/cancelled session makes every
        // remaining queued event invalid by definition.
        conflict = error.message;
        clearQueuedEvents(sessionId);
        try {
          finalState = await getFreshState(sessionId);
        } catch {
          // Cannot refresh right now — the conflict text still tells the
          // traveller the truth; the next successful GET reconciles.
        }
        break;
      }
      // Network failure: keep every remaining event queued for a later retry.
      break;
    }
  }

  return {
    synced,
    remaining: readQueuedEvents(sessionId).length,
    conflict,
    final_state: finalState,
  };
}
