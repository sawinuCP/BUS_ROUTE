# Support and data correction process (Phase 9, plan item 9)

How travellers get help and how data corrections flow from report to
published correction. The process is deliberately honest about what is and
is not automated: **reports are reviewed by a human moderator before any
data change**, and nothing in the app can modify canonical data by itself.

## 1. Roles (owner assigns names before the pilot)

| Role | Responsibility |
|---|---|
| Support contact | Answers traveller questions; triages non-data issues. |
| Moderator | Reviews traveller reports (`/admin/reports`), decides accept/reject/needs-info; applies AI category suggestions only as suggestions. |
| Data operator | Runs ingestion/validation/publication; folds accepted corrections into candidate dataset versions and publishes them through the normal validation flow. |

## 2. Traveller support channels

- In-app: "Report a problem" on the journey steps screen (consent-gated,
  offline-queueable, idempotent) — the primary intake for data issues.
- A published support contact (email/contact form) for everything else —
  owner provides the address for the store listing.
- Privacy requests (report/session data deletion or export): sessions and
  reports are anonymous and stored server-side without personal data; the
  data operator can delete a specific journey/report by id on request.
  Preferences, caches and queues are device-only — clearing app data or
  uninstalling removes them completely.

## 3. Data correction flow (grounded in the Phase 7/8 implementation)

1. **Intake**: traveller submits a report with a category (wrong stop,
   route/variant, direction, transfer path, landmark/name, fare, access
   attribute, outdated data, other), tied to canonical entities and the
   dataset version — never coordinates. Explicit consent is required and
   recorded; retries are idempotent per `client_key`.
2. **Triage**: the moderator opens the admin queue
   (`GET /admin/reports?status=`). An AI category suggestion is available
   (`GET /admin/reports/{id}/classification-suggestion`) — it is a
   suggestion only and never modifies the report.
3. **Decision** (`POST /admin/reports/{id}/review`): `accept`, `reject`,
   or `needs_info` (back to the traveller). Every decision is audit-logged
   (`admin_audit` JSON log with request id).
4. **Correction**: acceptance creates a **candidate** dataset version
   (`field-reports-<report id>`), never published automatically. The data
   operator folds the verified correction into the candidate via the
   normal ingestion flow, validates it, and publishes explicitly
   (`POST /admin/dataset-versions/{id}/publish`) — both audited.
5. **Verification**: post-publish, the operator re-runs the affected
   curated routing checks and confirms the fix appears in a new plan
   (dataset-version change invalidates cached plans immediately).

## 4. Escalation and safety rules

- A published correction that breaks routing: **rollback**
  (`POST /admin/dataset-versions/{id}/rollback`, audited) restores the
  previous active version; the candidate is fixed and re-published.
- Never auto-publish: automated approval applies only to sources and
  change classes with proven quality (architecture doc 09 §4 step 11);
  field reports always require a human decision.
- Anything touching safety claims (accessibility attributes, "safe" stops)
  requires verified evidence (field-checked), never traveller opinion
  alone.

## 5. Records

- Every report (with consent + status trail), every moderation decision
  and every publish/rollback is recorded server-side and in the audit log.
- The status report's issue log (`docs/status/development-status-report.md`
  §7) remains the engineering-side record of systemic data problems.
