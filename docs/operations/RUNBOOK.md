# Operations runbook (Phase 9, plan item 6)

Day-to-day operator procedures for the backend. Every admin command below
requires the operator token:

```bash
TOKEN="<ADMIN_API_TOKEN>"   # from the environment/.env — never committed
BASE="http://localhost:8000/api/v1"
curl -H "Authorization: Bearer $TOKEN" "$BASE/admin/..."
```

If `ADMIN_API_TOKEN` is unset, admin endpoints answer **403** in
staging/production (fail closed); only local/test run in dev mode.

## 1. Admin authentication

- Set `ADMIN_API_TOKEN` in the environment (or `.env` for compose). Rotate
  by changing the value and restarting the backend; the token is compared
  constant-time and audit-logged attempts never include the credential.
- Wrong/missing token → 401 `UNAUTHORIZED` (stable error envelope). Audit
  attempts appear in the JSON log stream with `logger: app.platform.security`.
- OAuth2/OIDC + RBAC (architecture doc 14) replace this token when identity
  exists; the seam is `app.platform.security.require_admin`.

## 2. Data-version lifecycle (ingest → validate → publish → rollback)

1. **Ingest**: `POST /admin/sources` (register), `POST
   /admin/sources/{id}/sync` (`{"adapter": "overpass"}` or a file path).
   Every sync is audited with the run id.
2. **Inspect**: `GET /admin/sync-runs/{id}` (records in/added/updated/
   failed), `GET /admin/dataset-versions` (all versions + status).
3. **Validate**: `GET /admin/dataset-versions/{id}/quality-report` and
   `POST .../quality-report/write` (writes the committed evidence report).
4. **Publish**: `POST /admin/dataset-versions/{id}/publish` — makes the
   version active; audit-logged (`dataset.publish`). A plan-cache version
   change invalidates cached plans immediately (ADR-0003).
5. **Rollback**: `POST /admin/dataset-versions/{id}/rollback` — restores the
   previous active version; audit-logged (`dataset.rollback`). Plan against
   the restored version afterwards to confirm.

## 3. QA queue and verification records

- `GET /admin/qa-queue` — entities failing quality gates.
- `POST /admin/verifications` — record a field/official-source verification
  (audit-logged). Method `report_review` must reference a moderated report.
- Coverage posture: `GET /admin/coverage-scorecard`.

## 4. Report moderation

1. `GET /admin/reports?status=submitted` (oldest first).
2. Optional AI category suggestion: `GET
   /admin/reports/{id}/classification-suggestion` — **suggestion only**; the
   report row is never modified.
3. Decide: `POST /admin/reports/{id}/review` with `accept | reject |
   needs_info` (audit-logged). **Accept creates a candidate dataset version
   (`field-reports-<id>`, never published)** — fold the verified correction
   in through the normal ingestion flow and publish explicitly.
4. Accepted/rejected are terminal; `needs_info` can be reviewed again.

## 5. Grounded AI assistance configuration

- Provider adapter and model come from the environment:
  `AI_PROVIDER` (`none` | `openai_compatible`), `AI_BASE_URL`, `AI_MODEL`,
  `AI_API_KEY` (secret). Switching models is a config change.
- Cost/abuse controls: `AI_REQUESTS_PER_MINUTE`, `AI_EXPLANATIONS_ENABLED`.
  Provider outage never breaks the app: explanations answer with the
  deterministic fallback (`source: deterministic_fallback`).
- Grounding evidence: run `python backend/scripts/eval_ai_grounding.py`
  (from `backend/`) — writes `backend/data/validation_reports/
  ai-grounding-<stamp>.md`; the fixed offline set runs on every gate.

## 6. Log stream and audit

- Single-line JSON logs on stdout (request id, level, logger, message +
  extras). Filter audit actions with `"message": "admin_audit"`.
- Request bodies, query strings and precise locations are never logged.
- Deployment-level: HTTPS/HSTS at the reverse proxy; request rate limits
  for public endpoints are enforced there or via Redis-backed limiting when
  scaling beyond one node.

## 7. Known operational caveats

- The rate limiter is in-process (single node) — Redis backing is a release
  checklist item (Phase 9).
- Admin OAuth2/OIDC + RBAC replaces the operator token when accounts exist.
- Valhalla tiles must be rebuilt after large OSM re-syncs
  (`backend/scripts/build_valhalla_tiles.py`).
