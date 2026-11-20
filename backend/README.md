# Backend — Sri Lanka Journey Planner

FastAPI backend skeleton (Phase 0.3). Canonical module boundaries are fixed by
`docs/adr/ADR-0001-documentation-layout-and-canonical-registers.md` (ADR-0001):
`places`, `transport`, `pedestrian`, `transfers`, `routing`, `itineraries`,
`journey_sessions`, `data_ingestion`, `data_quality`, `reports`, `ai_assistance`,
plus shared `platform` code.

## Layout

```text
backend/
├── app/
│   ├── main.py               # app factory + entrypoint
│   ├── api/routes/health.py  # /api/v1/health (liveness), /api/v1/ready (readiness)
│   ├── platform/             # config, structured logging, error envelope, db (Base), model registry
│   └── modules/              # canonical boundaries; models.py holds that module's tables
│       ├── data_ingestion/   # provenance, snapshots, sync runs, dataset versioning
│       ├── transport/        # agencies, routes, patterns, stops, access points, shapes, transfers, fares
│       ├── places/           # localities, places, access points, entity aliases
│       └── data_quality/     # verification records, change audit
├── alembic/                  # migrations (env.py loads model metadata; DATABASE_URL from settings)
├── tests/                    # unit/ + integration/ (live PostGIS via DATABASE_URL)
├── Dockerfile                # python:3.12-slim (Python version is pinned here — ADR-0002/0005)
├── requirements.txt          # pinned runtime deps
└── requirements-dev.txt      # pinned dev/test deps
```

## Canonical schema (Phase 1.1)

`alembic upgrade head` creates 22 canonical tables (ADR-0006) plus the
canonical-link bookkeeping of `0003_source_record_link` (ADR-0007):
provenance and versioning (`data_sources`, `source_snapshots`,
`source_records`, `sync_runs`, `dataset_versions`, `dataset_version_entities`,
`active_dataset`), the transport network (`transport_agencies`,
`transport_routes`, `route_patterns`, `stops`, `stop_access_points`,
`route_pattern_stops`, `route_shapes`, `transfer_connections`, `fare_rules`),
places/aliases (`localities`, `places`, `place_access_points`,
`entity_aliases`), and data quality (`verification_records`,
`data_change_audit`). Core invariant: ordered stop calls are
`UNIQUE (pattern_id, sequence)`.

## Ingestion framework (Phase 1.2)

`app/modules/data_ingestion/` implements the §5.2 lifecycle (ADR-0007):

- `adapters/base.py` — `SourceAdapter` contract (`fetch` + `parse` → `RawRecord`);
  `adapters/file.py` — generic local-JSON source for dev/fixtures.
- `archive.py` — `SnapshotArchive` (sha256 content-addressed, local FS in dev).
- `quality.py` — builtin rules; any failure **quarantines the whole run**.
- `service.py` — `SourceRegistry`, `IngestionService.run_sync`
  (fetch → checksum dedupe → archive → parse → validate → idempotent upsert →
  diffs → candidate version), `DatasetVersionService` (publish/rollback),
  entity upsert handlers for `stop`, `route`, `place`, `route_pattern`,
  `route_pattern_stop` (cross-record matching via `source_records` links).

Admin endpoints (`/api/v1/admin/sources`, `/admin/sources/{id}/sync`,
`/admin/sync-runs/{id}`, `/admin/dataset-versions[...]`, QA reports) are
mounted only outside production (auth arrives in Phase 9).

## First source adapter + quality report (Phase 1.3)

- `adapters/overpass.py` — **OpenStreetMap via Overpass API** (ODbL 1.0; see
  `data/source-rights-register.md`). Fetches named bus stops and
  `route=bus` relations for `PILOT_BBOX` (default central Colombo; configurable,
  never hard-coded). Relations sharing a `ref` are grouped into one route with
  per-relation variants; ordered member calls carry role-derived
  boarding/alighting eligibility; `name:si`/`name:ta` tags become aliases.
  Unnamed stop nodes are excluded, never invented; unresolvable member
  references fail that record and surface in the QA report.
- `report.py` — `QualityReportService`: per-version data-quality report
  (diffs, coverage, checks with honest caveats) as JSON + Markdown under
  `data/validation_reports/` (committed as evidence; raw snapshots are not).
- `scripts/seed_osm_source.py` — idempotent source-registry seed (licence and
  attribution recorded before ingestion).

Typical flow (inside the backend container):

```sh
python scripts/seed_osm_source.py
# then POST /api/v1/admin/sources/<id>/sync {"adapter": "overpass"}
# then POST /api/v1/admin/dataset-versions/<id>/quality-report/write
```

## Development (Docker-first — recommended)

Prerequisites: Docker Desktop running; a local `.env` copied from the repo-root `.env.example`.

All commands run from the **repository root**:

```powershell
# First time / whenever requirements change (builds the backend image):
docker compose --env-file .env -f infra/docker/compose.yaml up -d --build

# Tail backend logs:
docker compose --env-file .env -f infra/docker/compose.yaml logs -f backend

# Run the test suite:
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend pytest

# Lint and type-check:
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend ruff check .
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend mypy

# Apply migrations (currently only the empty baseline):
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend alembic upgrade head

# Stop everything:
docker compose --env-file .env -f infra/docker/compose.yaml down
# ...add -v to also remove the database volume (destroys local data).
```

Endpoints once running (http://localhost:8000):

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Liveness — always 200 while the process is up |
| `GET /api/v1/ready` | Readiness — 200 when PostGIS DB and Redis respond; 503 `degraded` otherwise |
| `GET /api/v1/docs` | OpenAPI UI (generated by FastAPI) |
| `GET /api/v1/openapi.json` | OpenAPI schema |

## Development (host venv — alternative)

Host Python must be **3.12** (ADR-0002/ADR-0005). If your machine only ships
3.11/3.14, use the Docker path above.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r backend\requirements-dev.txt
.venv\Scripts\pytest backend
```

## Conventions (binding)

- No business rules in route handlers; domain logic lives in `app/modules/*`.
- `platform` code must stay generic (config, logging, errors, db, redis).
- Errors use the stable envelope in `app/platform/errors.py` — never ad-hoc dicts.
- Unknown facts are represented as explicit nulls with reasons (implementation plan §6.5).
- No secrets in code; configuration comes from environment/`.env` only.
