/**
 * Offline manual progress (Phase 7, plan item 3) — queue storage, the local
 * projection (mirroring the backend state machine) and ordered replay.
 *
 * Key honesty properties under test:
 * - the queue preserves insertion order (the backend's transition rules stay
 *   valid on replay);
 * - the projection refuses events the backend would refuse (terminal states,
 *   advance while paused, unknown steps) — nothing is invented;
 * - replay is ordered, keeps events on network failure, and on a 409 the
 *   server state wins (remaining events dropped, conflict surfaced).
 */

import { ApiStatusError, type JourneySessionState, type PlanStep, type SessionStep } from '@/lib/api';
import {
  clearQueuedEventsForTests,
  enqueueProgressEvent,
  projectOfflineState,
  readQueuedEvents,
  replayQueuedEvents,
} from '@/lib/progressQueue';

jest.mock('expo-sqlite', () => {
  const rows: {
    id: number;
    session_id: string;
    event_type: string;
    step_index: number | null;
    note: string | null;
    queued_at: string;
  }[] = [];
  let nextId = 1;
  const db = {
    execSync: jest.fn(),
    runSync: (sql: string, params?: unknown[]) => {
      if (sql.startsWith('INSERT INTO pending_session_events') && params) {
        rows.push({
          id: nextId++,
          session_id: params[0] as string,
          event_type: params[1] as string,
          step_index: (params[2] as number | null) ?? null,
          note: (params[3] as string | null) ?? null,
          queued_at: params[4] as string,
        });
      }
      if (sql.startsWith('DELETE FROM pending_session_events WHERE id =') && params) {
        const index = rows.findIndex((row) => row.id === params[0]);
        if (index >= 0) {
          rows.splice(index, 1);
        }
      }
      if (sql.startsWith('DELETE FROM pending_session_events WHERE session_id') && params) {
        const sessionId = params[0] as string;
        for (let i = rows.length - 1; i >= 0; i -= 1) {
          if (rows[i].session_id === sessionId) {
            rows.splice(i, 1);
          }
        }
      }
      if (sql.startsWith('DELETE FROM pending_session_events') && !sql.includes('WHERE')) {
        rows.length = 0; // test-only full clear
      }
    },
    getAllSync: (sql: string, params?: unknown[]) => {
      const sessionId = (params?.[0] as string) ?? '';
      return rows.filter((row) => row.session_id === sessionId).map((row) => ({ ...row }));
    },
  };
  return { openDatabaseSync: () => db };
});

const STEPS: PlanStep[] = [
  { action: 'WALK_TO_STOP', text: 'Walk 240 m to the boarding point.', facts: {}, confidence: 'unverified' },
  { action: 'BOARD_TRANSIT', text: 'Board route 101 at A.', facts: {}, confidence: 'unverified' },
  { action: 'WALK_TO_DESTINATION', text: 'Arrive at your destination.', facts: {}, confidence: 'unverified' },
];

function sessionState(overrides?: Partial<JourneySessionState>): JourneySessionState {
  return {
    session_id: 'sess-1',
    journey_id: 'j-1',
    option_id: 'option-1',
    status: 'active_walk',
    dataset_version: 'osm-overpass-1679d061',
    language: 'en',
    availability_scope: 'network_feasible_not_live_confirmed',
    progress: { current_step: 0, step_count: 3 },
    current_step: STEPS[0] as SessionStep,
    next_step: STEPS[1] as SessionStep,
    ...overrides,
  };
}

describe('progress queue storage', () => {
  beforeEach(() => {
    clearQueuedEventsForTests();
  });

  it('queues events in insertion order with their payloads', () => {
    enqueueProgressEvent('sess-1', { event_type: 'paused' });
    enqueueProgressEvent('sess-1', { event_type: 'step_advanced', step_index: 1 });
    enqueueProgressEvent('sess-1', { event_type: 'completed', note: 'confirmed last step' });

    const queued = readQueuedEvents('sess-1');
    expect(queued.map((event) => event.event_type)).toEqual(['paused', 'step_advanced', 'completed']);
    expect(queued[1].step_index).toBe(1);
    expect(queued[2].note).toBe('confirmed last step');
    expect(queued[0].queued_at).toBeTruthy();
    expect(readQueuedEvents('sess-other')).toEqual([]); // per-session isolation
  });
});

describe('projectOfflineState mirrors the backend state machine', () => {
  it('advances to the explicit step index and derives the status', () => {
    const projected = projectOfflineState(
      sessionState(),
      { event_type: 'step_advanced', step_index: 1 },
      STEPS,
    );
    expect(projected?.status).toBe('active_ride'); // BOARD_TRANSIT
    expect(projected?.progress).toEqual({ current_step: 1, step_count: 3 });
    expect(projected?.current_step?.text).toBe('Board route 101 at A.');
    expect(projected?.next_step?.text).toBe('Arrive at your destination.');
  });

  it('pauses and resumes without changing progress', () => {
    const paused = projectOfflineState(sessionState(), { event_type: 'paused' }, STEPS);
    expect(paused?.status).toBe('paused');
    expect(paused?.progress.current_step).toBe(0);

    const resumed = projectOfflineState(
      sessionState({ status: 'paused' }),
      { event_type: 'resumed' },
      STEPS,
    );
    expect(resumed?.status).toBe('active_walk'); // derived from WALK_TO_STOP
    expect(resumed?.progress.current_step).toBe(0);
  });

  it('projects explicit completion and cancellation as terminal states', () => {
    const completed = projectOfflineState(
      sessionState({ progress: { current_step: 2, step_count: 3 } }),
      { event_type: 'completed', note: 'confirmed last step' },
      STEPS,
    );
    expect(completed?.status).toBe('completed');
    expect(completed?.progress).toEqual({ current_step: 3, step_count: 3 });
    expect(completed?.current_step).toBeNull();

    const cancelled = projectOfflineState(sessionState(), { event_type: 'cancelled' }, STEPS);
    expect(cancelled?.status).toBe('cancelled');
    expect(cancelled?.current_step).toBeNull();
  });

  it('refuses exactly what the backend refuses — nothing is invented', () => {
    // Terminal states accept nothing.
    expect(
      projectOfflineState(sessionState({ status: 'completed' }), { event_type: 'step_advanced' }, STEPS),
    ).toBeNull();
    expect(
      projectOfflineState(sessionState({ status: 'cancelled' }), { event_type: 'paused' }, STEPS),
    ).toBeNull();
    // Progress cannot advance while paused.
    expect(
      projectOfflineState(sessionState({ status: 'paused' }), { event_type: 'step_advanced' }, STEPS),
    ).toBeNull();
    // Steps unknown locally → the caller must show the server truth instead.
    expect(
      projectOfflineState(sessionState(), { event_type: 'step_advanced', step_index: 1 }, null),
    ).toBeNull();
    // Beyond the last step: completion is explicit, never implicit.
    expect(
      projectOfflineState(sessionState(), { event_type: 'step_advanced', step_index: 5 }, STEPS),
    ).toBeNull();
  });
});

describe('replayQueuedEvents', () => {
  beforeEach(() => {
    clearQueuedEventsForTests();
  });

  it('posts queued events in order and clears them on success', async () => {
    enqueueProgressEvent('sess-1', { event_type: 'paused' });
    enqueueProgressEvent('sess-1', { event_type: 'resumed' });

    const posted: string[] = [];
    const states = [sessionState({ status: 'paused' }), sessionState()];
    let call = 0;
    const outcome = await replayQueuedEvents('sess-1', async (_id, eventType) => {
      posted.push(eventType);
      return states[call++];
    });

    expect(posted).toEqual(['paused', 'resumed']); // ordering preserved
    expect(outcome.synced).toBe(2);
    expect(outcome.remaining).toBe(0);
    expect(outcome.conflict).toBeNull();
    expect(outcome.final_state?.status).toBe('active_walk');
    expect(readQueuedEvents('sess-1')).toEqual([]);
  });

  it('keeps the remaining events queued when the network fails', async () => {
    enqueueProgressEvent('sess-1', { event_type: 'paused' });
    enqueueProgressEvent('sess-1', { event_type: 'resumed' });

    let call = 0;
    const outcome = await replayQueuedEvents('sess-1', async (_id, eventType) => {
      call += 1;
      if (call === 2) {
        throw new TypeError('network unreachable'); // not an ApiStatusError
      }
      return sessionState({ status: 'paused' });
    });

    expect(outcome.synced).toBe(1);
    expect(outcome.remaining).toBe(1); // retried later, never dropped silently
    expect(outcome.conflict).toBeNull();
    expect(readQueuedEvents('sess-1')).toHaveLength(1);
  });

  it('lets the server win on a 409 and drops the impossible events', async () => {
    enqueueProgressEvent('sess-1', { event_type: 'paused' });
    enqueueProgressEvent('sess-1', { event_type: 'resumed' });

    const serverState = sessionState({ status: 'completed', current_step: null, next_step: null });
    const outcome = await replayQueuedEvents(
      'sess-1',
      async () => {
        throw new ApiStatusError(409, "event 'paused' is not allowed from 'completed'");
      },
      async () => serverState,
    );

    expect(outcome.synced).toBe(0);
    expect(outcome.remaining).toBe(0);
    expect(outcome.conflict).toBe("event 'paused' is not allowed from 'completed'");
    expect(outcome.final_state?.status).toBe('completed'); // server state adopted
    expect(readQueuedEvents('sess-1')).toEqual([]);
  });

  it('surfaces the conflict text even when the refresh is unreachable', async () => {
    enqueueProgressEvent('sess-1', { event_type: 'paused' });
    const outcome = await replayQueuedEvents(
      'sess-1',
      async () => {
        throw new ApiStatusError(409, 'event not allowed');
      },
      async () => {
        throw new TypeError('still offline');
      },
    );
    expect(outcome.conflict).toBe('event not allowed');
    expect(outcome.final_state).toBeNull();
  });

  it('does nothing when the queue is empty', async () => {
    const outcome = await replayQueuedEvents('sess-1');
    expect(outcome).toEqual({ synced: 0, remaining: 0, conflict: null, final_state: null });
  });
});
