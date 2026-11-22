/**
 * Offline plan cache (Phase 7, plan item 1).
 *
 * Persists the most recent successful plan response — the itinerary, its
 * ordered instruction steps and the dataset version they are grounded in —
 * so the traveller can still read and manually follow the journey after an
 * app restart or while offline (Phase 7 exit criterion). SQLite is the
 * ratified local store (ADR-0002). Only one plan is kept: the cache mirrors
 * the in-memory hand-off store and is overwritten on every new plan. No
 * location data is stored — a plan is derived from explicit stop choices.
 */

import * as SQLite from 'expo-sqlite';

import type { JourneyPlanResponse, PlanStep } from '@/lib/api';

const DB_NAME = 'sljp.db';

export interface CachedPlan {
  plan: JourneyPlanResponse;
  /** Option the traveller opened (null = plan not opened yet). */
  option_id: string | null;
  saved_at: string;
}

function openDb(): SQLite.SQLiteDatabase {
  return SQLite.openDatabaseSync(DB_NAME);
}

function ensureSchema(db: SQLite.SQLiteDatabase): void {
  db.execSync(
    'CREATE TABLE IF NOT EXISTS cached_plan ('
    + ' id INTEGER PRIMARY KEY CHECK (id = 1),'
    + ' plan_json TEXT NOT NULL,'
    + ' option_id TEXT,'
    + ' saved_at TEXT NOT NULL)',
  );
}

export function saveCachedPlan(plan: JourneyPlanResponse): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('INSERT OR REPLACE INTO cached_plan (id, plan_json, option_id, saved_at) VALUES (1, ?, NULL, ?)', [
    JSON.stringify(plan),
    new Date().toISOString(),
  ]);
}

/** Points the cache at the option the traveller opened (idempotent). */
export function setCachedPlanOption(optionId: string): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('UPDATE cached_plan SET option_id = ? WHERE id = 1', [optionId]);
}

export function readCachedPlan(): CachedPlan | null {
  const db = openDb();
  ensureSchema(db);
  const rows = db.getAllSync<{ plan_json: string; option_id: string | null; saved_at: string }>(
    'SELECT plan_json, option_id, saved_at FROM cached_plan WHERE id = 1',
  );
  const row = rows[0];
  if (!row) {
    return null;
  }
  try {
    return { plan: JSON.parse(row.plan_json) as JourneyPlanResponse, option_id: row.option_id, saved_at: row.saved_at };
  } catch {
    return null; // corrupted cache must never fabricate a plan
  }
}

/** The ordered steps of a cached option, for offline progress projection. */
export function readCachedOptionSteps(journeyId: string, optionId: string): PlanStep[] | null {
  const cached = readCachedPlan();
  if (!cached || cached.plan.journey_id !== journeyId) {
    return null;
  }
  const option = cached.plan.options.find((candidate) => candidate.id === optionId);
  return option ? option.steps : null;
}

export function clearCachedPlan(): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('DELETE FROM cached_plan WHERE id = 1');
}
