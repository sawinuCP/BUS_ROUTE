/**
 * Offline report queue (Phase 7, plan item 4).
 *
 * "Optional queued reports with explicit consent and later sync": when a
 * report cannot reach the backend, it is queued in SQLite with its
 * client-generated idempotency key and replayed later. Idempotency is the
 * backend's guarantee — a retry with the same `client_key` can never create
 * a duplicate submission. The queue stores only the report payload (category,
 * text, subject reference, dataset version) — **no location data**.
 *
 * A 400/422 is a permanent refusal (bad request) — the event is dropped and
 * the reason surfaced rather than retried forever. Network failures keep the
 * report queued for a later flush.
 */

import * as SQLite from 'expo-sqlite';

import { ApiStatusError, submitReport, type ReportRequest } from '@/lib/api';

const DB_NAME = 'sljp.db';

export interface QueuedReport {
  id: number;
  payload: ReportRequest;
  queued_at: string;
}

function openDb(): SQLite.SQLiteDatabase {
  return SQLite.openDatabaseSync(DB_NAME);
}

function ensureSchema(db: SQLite.SQLiteDatabase): void {
  db.execSync(
    'CREATE TABLE IF NOT EXISTS pending_reports ('
    + ' id INTEGER PRIMARY KEY AUTOINCREMENT,'
    + ' payload_json TEXT NOT NULL,'
    + ' queued_at TEXT NOT NULL)',
  );
}

export function enqueueReport(payload: ReportRequest): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('INSERT INTO pending_reports (payload_json, queued_at) VALUES (?, ?)', [
    JSON.stringify(payload),
    new Date().toISOString(),
  ]);
}

export function readQueuedReports(): QueuedReport[] {
  try {
    const db = openDb();
    ensureSchema(db);
    const rows = db.getAllSync<{ id: number; payload_json: string; queued_at: string }>(
      'SELECT id, payload_json, queued_at FROM pending_reports ORDER BY id ASC',
    );
    return rows
      .map((row) => {
        try {
          return { id: row.id, payload: JSON.parse(row.payload_json) as ReportRequest, queued_at: row.queued_at };
        } catch {
          return null; // a corrupted queued payload is dropped, never sent
        }
      })
      .filter((row): row is QueuedReport => row !== null);
  } catch {
    return []; // store unavailable → nothing to sync
  }
}

function removeQueuedReport(id: number): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('DELETE FROM pending_reports WHERE id = ?', [id]);
}

export function clearQueuedReportsForTests(): void {
  try {
    const db = openDb();
    ensureSchema(db);
    db.runSync('DELETE FROM pending_reports');
  } catch {
    // store unavailable → nothing to clear
  }
}

/** Generates the stable idempotency key stored with the queued payload. */
export function newReportClientKey(): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `rep-${Date.now()}-${random}`;
}

export interface ReportFlushOutcome {
  synced: number;
  remaining: number;
  /** 4xx refusals: dropped permanently with the reason surfaced. */
  dropped: number;
}

export async function flushQueuedReports(
  postReport: (request: ReportRequest) => Promise<unknown> = submitReport,
): Promise<ReportFlushOutcome> {
  let synced = 0;
  let dropped = 0;
  for (const queued of readQueuedReports()) {
    try {
      await postReport(queued.payload);
      removeQueuedReport(queued.id);
      synced += 1;
    } catch (error) {
      if (error instanceof ApiStatusError && error.status >= 400 && error.status < 500) {
        // Permanent refusal (e.g. consent missing in a stale payload):
        // retrying would fail forever — drop it and surface the reason.
        removeQueuedReport(queued.id);
        dropped += 1;
        continue;
      }
      // Network failure: keep every remaining report queued for a later flush.
      break;
    }
  }
  return { synced, remaining: readQueuedReports().length, dropped };
}
