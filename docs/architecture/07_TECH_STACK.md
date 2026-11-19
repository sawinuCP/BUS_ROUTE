# 07 — Recommended Technology Stack

## Mobile application
| Technology | Purpose | Reason |
|---|---|---|
| React Native + TypeScript | Android/iOS app | Shared codebase and strong ecosystem |
| Expo development builds | Native app workflow | Faster iteration while retaining native modules |
| Expo Router | Navigation | File-based routing |
| TanStack Query | Server state/cache | Request lifecycle and cache invalidation |
| Zustand | Small client state | Active journey/UI state without heavy boilerplate |
| React Hook Form + Zod | Forms/validation | Typed validation |
| MapLibre React Native | Map display | Flexible map rendering; verify current package compatibility |
| Expo Location | Location permission/GPS | Native location integration |
| SQLite | Offline selected journeys | Local structured cache |
| SecureStore | Tokens/secrets | Protected local storage |
| i18next or equivalent | UI localisation | English/Sinhala/Tamil |
| Jest + React Native Testing Library | Unit/component tests | Component behaviour |
| Maestro | End-to-end tests | Mobile flow automation |

Use Expo development builds rather than assuming Expo Go supports every native map/location requirement. Confirm MapLibre compatibility, build tooling and target OS versions in a short technical spike.

## Backend
| Technology | Purpose |
|---|---|
| Python 3.12+ (pin supported version) | Main language |
| FastAPI | HTTP API |
| Pydantic | Request/response schemas |
| SQLAlchemy 2.x | ORM/data access |
| Alembic | Database migrations |
| PostgreSQL + PostGIS | Relational and spatial source of truth |
| Redis | Optional cache/job broker |
| Celery or Dramatiq | Background tasks; select one, do not use both initially |
| httpx | Async external HTTP |
| Shapely / GeoAlchemy | Geometry handling |
| Pytest | Backend tests |
| Ruff + mypy/pyright | Linting/type checks |
| OpenTelemetry | Traces/metrics |
| Structured JSON logging | Operations |

## Routing and maps
- **Transit graph:** implement deterministic graph search over validated route patterns and transfer edges.
- **Walking engine:** prototype Valhalla; compare GraphHopper for Sri Lankan OSM coverage, pedestrian restrictions, deployment and licence.
- **Map rendering:** MapLibre client.
- **Tiles:** use a provider with production terms or operate an appropriately licensed tile stack. Do not rely on public community tile servers for production traffic.
- **Geocoding:** evaluate a licensed provider or self-hosted OSM-based service. Respect provider caching and attribution restrictions.

## Infrastructure
- Docker and Docker Compose for local development.
- GitHub Actions or equivalent CI.
- Managed PostgreSQL/PostGIS where feasible.
- Object storage for immutable raw source payloads and evidence.
- Secret manager for credentials.
- Sentry or equivalent crash/error monitoring.
- OpenTelemetry-compatible tracing/metrics backend.
- Terraform later if infrastructure complexity warrants it.

## Technology selection rules
- Pin versions and commit lockfiles.
- Avoid adding a library without a concrete requirement.
- Run proof-of-concept tests for map, walking engine, geocoder and GTFS ingestion before locking provider choices.
- Do not introduce Kubernetes, Kafka, vector databases or microservices in the MVP without measured need.
