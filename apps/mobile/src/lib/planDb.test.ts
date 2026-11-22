/**
 * Offline plan cache (Phase 7, plan item 1) — SQLite-backed persistence.
 *
 * The cache must round-trip the plan exactly (steps verbatim), point at the
 * opened option, and never fabricate content from a corrupted row.
 */

import { clearCachedPlan, readCachedOptionSteps, readCachedPlan, saveCachedPlan, setCachedPlanOption } from '@/lib/planDb';
import type { JourneyPlanResponse } from '@/lib/api';

jest.mock('expo-sqlite', () => {
  const rows: { plan_json: string; option_id: string | null; saved_at: string }[] = [];
  const db = {
    execSync: jest.fn(),
    runSync: (sql: string, params?: unknown[]) => {
      if (sql.startsWith('INSERT OR REPLACE INTO cached_plan') && params) {
        rows.length = 0;
        rows.push({ plan_json: params[0] as string, option_id: null, saved_at: params[1] as string });
      }
      if (sql.startsWith('UPDATE cached_plan') && params) {
        if (rows[0]) {
          rows[0].option_id = params[0] as string;
        }
      }
      if (sql.startsWith('DELETE FROM cached_plan')) {
        rows.length = 0;
      }
    },
    getAllSync: () => rows.map((row) => ({ ...row })),
    __rows: rows,
  };
  return { openDatabaseSync: () => db, __rows: rows };
});

const planFixture = {
  status: 'ok',
  dataset_version: 'osm-overpass-1679d061',
  availability_scope: 'network_feasible_not_live_confirmed',
  journey_id: 'j-1',
  options: [
    {
      id: 'option-1',
      summary: {
        estimated_duration_minutes: { min: 20, max: 30 },
        walking_distance_m: 142,
        transfer_count: 1,
        confidence: 'unverified_transfer',
      },
      labels: ['fastest'],
      warnings: [],
      legs: [],
      steps: [
        { action: 'WALK_TO_STOP', text: 'Walk 240 m to the boarding point.', facts: {}, confidence: 'unverified' },
        { action: 'BOARD_TRANSIT', text: 'Board route 101 at A.', facts: {}, confidence: 'unverified' },
      ],
    },
  ],
  labels: {},
  notes: [],
  language: 'en',
} as unknown as JourneyPlanResponse;

describe('planDb (Phase 7 item 1)', () => {
  beforeEach(() => {
    clearCachedPlan();
  });

  it('round-trips the plan with steps verbatim', () => {
    expect(readCachedPlan()).toBeNull(); // nothing fabricated when empty

    saveCachedPlan(planFixture);
    const cached = readCachedPlan();
    expect(cached).not.toBeNull();
    expect(cached?.plan.dataset_version).toBe('osm-overpass-1679d061');
    expect(cached?.plan.journey_id).toBe('j-1');
    expect(cached?.plan.options[0].steps[1].text).toBe('Board route 101 at A.');
    expect(cached?.option_id).toBeNull();
    expect(cached?.saved_at).toBeTruthy();
  });

  it('records the opened option and overwrites on a new plan', () => {
    saveCachedPlan(planFixture);
    setCachedPlanOption('option-1');
    expect(readCachedPlan()?.option_id).toBe('option-1');

    const nextPlan = { ...planFixture, journey_id: 'j-2' } as JourneyPlanResponse;
    saveCachedPlan(nextPlan);
    const cached = readCachedPlan();
    expect(cached?.plan.journey_id).toBe('j-2');
    expect(cached?.option_id).toBeNull(); // a new plan resets the selection
  });

  it('returns the ordered steps of the cached option for progress projection', () => {
    saveCachedPlan(planFixture);
    const steps = readCachedOptionSteps('j-1', 'option-1');
    expect(steps?.map((step) => step.action)).toEqual(['WALK_TO_STOP', 'BOARD_TRANSIT']);
    // A different journey/option must not leak steps (honesty: no invention).
    expect(readCachedOptionSteps('j-other', 'option-1')).toBeNull();
    expect(readCachedOptionSteps('j-1', 'option-other')).toBeNull();
  });

  it('never fabricates a plan from a corrupted cache row', () => {
    saveCachedPlan(planFixture);
    const mock = jest.requireMock('expo-sqlite') as {
      __rows: { plan_json: string }[];
    };
    mock.__rows[0].plan_json = '{corrupted';
    expect(readCachedPlan()).toBeNull();
    expect(readCachedOptionSteps('j-1', 'option-1')).toBeNull();
  });

  it('clears the cache', () => {
    saveCachedPlan(planFixture);
    clearCachedPlan();
    expect(readCachedPlan()).toBeNull();
  });
});
