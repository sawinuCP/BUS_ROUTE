/**
 * Offline report queue (Phase 7, plan item 4).
 *
 * Under test: the queue stores the payload with its idempotency key, network
 * failures keep reports queued for a later flush, a 4xx is a permanent
 * refusal (dropped, not retried forever), and a corrupted queued payload is
 * dropped rather than sent. Idempotency on the backend means a retried
 * submission can never create a duplicate.
 */

import { ApiStatusError, type ReportRequest } from '@/lib/api';
import {
  clearQueuedReportsForTests,
  enqueueReport,
  flushQueuedReports,
  newReportClientKey,
  readQueuedReports,
} from '@/lib/reportQueue';

jest.mock('expo-sqlite', () => {
  const rows: { id: number; payload_json: string; queued_at: string }[] = [];
  let nextId = 1;
  const db = {
    execSync: jest.fn(),
    runSync: (sql: string, params?: unknown[]) => {
      if (sql.startsWith('INSERT INTO pending_reports') && params) {
        rows.push({
          id: nextId++,
          payload_json: params[0] as string,
          queued_at: params[1] as string,
        });
      }
      if (sql.startsWith('DELETE FROM pending_reports WHERE id =') && params) {
        const index = rows.findIndex((row) => row.id === params[0]);
        if (index >= 0) {
          rows.splice(index, 1);
        }
      }
      if (sql.startsWith('DELETE FROM pending_reports') && !sql.includes('WHERE')) {
        rows.length = 0;
      }
    },
    getAllSync: () => rows.map((row) => ({ ...row })),
    __rows: rows,
  };
  return { openDatabaseSync: () => db, __rows: rows };
});

function reportPayload(clientKey: string): ReportRequest {
  return {
    category: 'wrong_stop',
    description: 'The 138 boards at the opposite side of the road here.',
    consent: true,
    client_key: clientKey,
    subject_type: 'journey',
    subject_id: 'j-1',
    dataset_version_label: 'osm-overpass-1679d061',
  };
}

describe('report queue (Phase 7 item 4)', () => {
  beforeEach(() => {
    clearQueuedReportsForTests();
  });

  it('queues reports with their idempotency key, in order', () => {
    enqueueReport(reportPayload('client-key-a'));
    enqueueReport(reportPayload('client-key-b'));

    const queued = readQueuedReports();
    expect(queued).toHaveLength(2);
    expect(queued[0].payload.client_key).toBe('client-key-a');
    expect(queued[1].payload.client_key).toBe('client-key-b');
    expect(queued[0].queued_at).toBeTruthy();
  });

  it('flushes queued reports in order and clears them on success', async () => {
    enqueueReport(reportPayload('client-key-a'));
    enqueueReport(reportPayload('client-key-b'));

    const posted: string[] = [];
    const outcome = await flushQueuedReports(async (request) => {
      posted.push(request.client_key);
      return { id: 'r-1', category: request.category, status: 'submitted' };
    });

    expect(posted).toEqual(['client-key-a', 'client-key-b']); // ordering kept
    expect(outcome).toEqual({ synced: 2, remaining: 0, dropped: 0 });
    expect(readQueuedReports()).toEqual([]);
  });

  it('keeps reports queued when the network is still down', async () => {
    enqueueReport(reportPayload('client-key-a'));
    enqueueReport(reportPayload('client-key-b'));

    let call = 0;
    const outcome = await flushQueuedReports(async () => {
      call += 1;
      if (call === 2) {
        throw new TypeError('network unreachable');
      }
      return { id: 'r-1', category: 'wrong_stop', status: 'submitted' };
    });

    expect(outcome.synced).toBe(1);
    expect(outcome.remaining).toBe(1); // retried later, never dropped silently
    expect(outcome.dropped).toBe(0);
  });

  it('drops permanently-refused (4xx) reports instead of retrying forever', async () => {
    enqueueReport(reportPayload('client-key-a'));
    const outcome = await flushQueuedReports(async () => {
      throw new ApiStatusError(422, 'report submission failed with status 422');
    });
    expect(outcome).toEqual({ synced: 0, remaining: 0, dropped: 1 });
    expect(readQueuedReports()).toEqual([]);
  });

  it('generates unique client keys for idempotent retries', () => {
    const keys = new Set([newReportClientKey(), newReportClientKey(), newReportClientKey()]);
    expect(keys.size).toBe(3);
    for (const key of keys) {
      expect(key.length).toBeLessThanOrEqual(64);
      expect(key.length).toBeGreaterThanOrEqual(8);
    }
  });

  it('drops a corrupted queued payload instead of sending it', () => {
    enqueueReport(reportPayload('client-key-a'));
    const mock = jest.requireMock('expo-sqlite') as {
      __rows: { payload_json: string }[];
    };
    mock.__rows[0].payload_json = '{corrupted';

    expect(readQueuedReports()).toEqual([]);
  });
});
