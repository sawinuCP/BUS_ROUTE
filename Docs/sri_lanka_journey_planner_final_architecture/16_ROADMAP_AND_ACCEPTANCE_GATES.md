# 16 — Roadmap and Phase Acceptance Gates

## Phase 0 — Product and data validation
Deliverables:
- Choose pilot geography and target user segment.
- Interview and observe representative travellers.
- Benchmark existing apps using defined test journeys.
- Audit source coverage, access, licensing, update cadence and machine-readable structure.
- Field-check sample routes, stops and transfers.
- Prototype map, geocoder and walking engine.

Exit gate:
- A bounded pilot area and initial supported corridors are selected.
- Data rights and access method are documented.
- At least a small set of end-to-end journeys can be validated manually.
- Major unknowns have owners and resolution plans.

## Phase 1 — Platform foundation
Deliverables:
- Repository, CI, Docker development environment.
- FastAPI modular structure.
- PostgreSQL/PostGIS migrations.
- Mobile shell and navigation.
- Authentication decision and basic preferences.
- Logging, error handling and API contract conventions.

Exit gate:
- App calls backend in dev/staging.
- Database migrations and automated tests pass.
- Secrets and environment configuration are separated.

## Phase 2 — Data ingestion and canonical network
Deliverables:
- Source registry and adapters.
- Raw snapshot storage.
- Normalisation and staging.
- Data validation and diff reports.
- Dataset versioning and atomic publication.
- Initial stop/route/pattern/alias dataset.

Exit gate:
- Re-running an unchanged source does not create noisy duplicate data.
- Invalid candidate does not replace active version.
- Rollback restores a prior version.
- Provenance is traceable for core network entities.

## Phase 3 — Core journey planner
Deliverables:
- Place/stop search.
- Walking engine adapter.
- Transit graph and routing.
- Route alternatives and scoring.
- Structured instructions.
- Results and itinerary UI.

Exit gate:
- Field-tested pilot journeys work end to end.
- Route direction and transfer relationships are validated.
- No fabricated timetable/live claims.
- Performance target is agreed and met on representative queries.

## Phase 4 — Journey execution
Deliverables:
- Start/pause/resume journey.
- Manual progress confirmation.
- GPS assistance and deviation prompts.
- Re-planning.
- Selected journey offline cache.

Exit gate:
- No single GPS sample causes a disruptive state transition.
- Offline instructions remain available.
- Re-plan behaviour is tested in real field scenarios.

## Phase 5 — Data quality operations and user feedback
Deliverables:
- Report workflow.
- Admin moderation.
- Sync dashboard.
- Alerts and operational runbooks.

Exit gate:
- Reports cannot directly mutate production data.
- Approved changes go through validation and versioned release.
- Operators can diagnose and roll back a failed update.

## Phase 6 — AI and expansion
Deliverables:
- Conversational intent extraction.
- Grounded itinerary explanations.
- FAQ/help if required.
- More corridors, data sources and optional real-time integrations.

Exit gate:
- AI tool calls are constrained and validated.
- Evaluation confirms no unsupported route claims.
- New data source passes licensing, quality and operational review.

## Suggested build order
Do not start with AI, nationwide coverage, live tracking or complex microservices. Prove the data lifecycle and a small number of complete journeys first.
