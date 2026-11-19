# 15 — Testing, Deployment and Operations

## 1. Testing strategy
### Unit tests
- Alias matching and place resolution.
- Route-pattern and stop-sequence validation.
- Transfer eligibility.
- Routing cost and dominance.
- Instruction generation.
- Dataset version selection.
- State-machine transitions.
- Permission and privacy rules.

### Integration tests
- PostgreSQL/PostGIS queries.
- External adapter parsing.
- GTFS import and validation.
- Walking engine integration.
- API request/response contracts.
- Sync pipeline staging and publication.
- Rollback behaviour.

### End-to-end tests
- Search origin/destination.
- Plan a journey.
- Select alternative.
- Inspect boarding and transfer instructions.
- Start journey and confirm progress.
- Offline selected-journey flow.
- Report an issue.
- Admin review and publish.

### Data tests
- Known corridor fixtures.
- Field-verified stop sequence.
- Route variant distinction.
- Transfer walk validation.
- Regression comparison between dataset versions.
- No-path and incomplete-data behaviour.

## 2. Environments
- Local: Docker Compose, seeded synthetic/test data.
- CI: ephemeral database and automated tests.
- Staging: production-like integrations with test credentials and limited pilot data.
- Production: managed database, object storage, secrets, monitoring and backups.

## 3. CI/CD gates
1. Formatting/lint/type checks.
2. Unit tests.
3. Integration tests.
4. Migration checks.
5. Dependency/security scan.
6. Mobile build checks.
7. Staging smoke tests.
8. Human approval for production release.

## 4. Observability
Track:
- API latency and error rate.
- Route-planning latency and no-path rate.
- Provider timeout/rate-limit/error counts.
- Source freshness and sync failures.
- Candidate validation failures.
- Dataset version and rollback events.
- App crash-free sessions.
- GPS battery impact.
- Report volume and resolution time.

Do not log raw precise location or personal journey details unnecessarily.

## 5. Backup and recovery
- Automated database backups and point-in-time recovery where supported.
- Immutable raw source snapshots.
- Versioned dataset releases.
- Periodic restore test.
- Document recovery time and recovery point objectives after pilot requirements are known.

## 6. Operational runbooks
Prepare procedures for:
- source outage;
- failed/partial import;
- suspicious mass deletion;
- invalid geometry;
- bad dataset release;
- rollback;
- provider quota exhaustion;
- database restore;
- credential rotation.
