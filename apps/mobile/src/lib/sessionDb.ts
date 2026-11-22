/**
 * Active-session persistence (Phase 6 exit criterion: state survives a
 * process restart). Stores only the session id and the last known state
 * snapshot — **never location data** (data model doc §6). SQLite is the
 * ratified local store (ADR-0002); full offline caching arrives in Phase 7.
 */

import * as SQLite from 'expo-sqlite';

const DB_NAME = 'sljp.db';

export interface PersistedSession {
  session_id: string;
  saved_at: string;
  /** JSON of the last known JourneySessionState (for display when offline). */
  snapshot: string | null;
}

function openDb(): SQLite.SQLiteDatabase {
  return SQLite.openDatabaseSync(DB_NAME);
}

function ensureSchema(db: SQLite.SQLiteDatabase): void {
  db.execSync(
    'CREATE TABLE IF NOT EXISTS active_session ('
    + ' id INTEGER PRIMARY KEY CHECK (id = 1),'
    + ' session_id TEXT NOT NULL,'
    + ' snapshot TEXT,'
    + ' saved_at TEXT NOT NULL)',
  );
}

export function saveActiveSession(sessionId: string, snapshot: string | null): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('INSERT OR REPLACE INTO active_session (id, session_id, snapshot, saved_at) VALUES (1, ?, ?, ?)', [
    sessionId,
    snapshot,
    new Date().toISOString(),
  ]);
}

export function readActiveSession(): PersistedSession | null {
  const db = openDb();
  ensureSchema(db);
  const rows = db.getAllSync<{ session_id: string; snapshot: string | null; saved_at: string }>(
    'SELECT session_id, snapshot, saved_at FROM active_session WHERE id = 1',
  );
  const row = rows[0];
  return row ? { session_id: row.session_id, snapshot: row.snapshot, saved_at: row.saved_at } : null;
}

export function clearActiveSession(): void {
  const db = openDb();
  ensureSchema(db);
  db.runSync('DELETE FROM active_session WHERE id = 1');
}
