# 06 — System Architecture

## 1. Architecture style
Use a **modular monolith** for the first production version. It keeps deployment and operations manageable while maintaining boundaries so high-load components can later be extracted.

Do not begin with microservices or Kubernetes. They add operational cost before independent scaling needs are proven.

## 2. Logical architecture

```text
React Native Mobile App
  ├── Search / Map / Results / Active Journey
  ├── Local SQLite cache
  └── API client + location permission layer
             |
             | HTTPS / JSON
             v
FastAPI Application
  ├── Identity & Preferences
  ├── Place Search & Resolution
  ├── Journey Planning
  ├── Journey Session / Progress
  ├── Data Quality & Reports
  ├── Admin & Source Registry
  ├── AI Assistant Gateway (optional)
  └── Provider Adapters
       ├── Geocoding provider
       ├── Walking router
       ├── Map/tile provider
       └── Transport source adapters
             |
       ┌─────┴──────────┐
       v                v
PostgreSQL/PostGIS    Redis (optional cache/queue)
  ├── Canonical data     └── Cache / job broker
  ├── Source snapshots
  ├── Dataset versions
  ├── Reports
  └── User data
       |
       v
Background Worker / Scheduler
  ├── Fetch
  ├── Parse & normalise
  ├── Validate & diff
  ├── Publish / rollback
  └── Health checks
```

## 3. Backend modules
- **places:** place records, geospatial lookup, aliases and search.
- **transport_network:** agencies, routes, patterns, stops, stations, ordered stop calls and shapes.
- **transfers:** pedestrian links and transfer constraints.
- **routing:** graph construction, candidate search, scoring and itinerary generation.
- **journeys:** saved plans, sessions and progress events.
- **data_sources:** source registry, adapters, raw snapshots and sync runs.
- **data_quality:** validation rules, confidence, reports and review.
- **fares:** optional, effective-dated fare records.
- **identity:** users, sessions, preferences and consent.
- **assistant:** intent parsing and grounded explanations.
- **notifications:** optional later module.

## 4. Request path
1. Authenticate/validate request and apply rate limits.
2. Resolve origin/destination to canonical entities or coordinates.
3. Determine supported coverage and active dataset version.
4. Fetch walking paths from configured engine.
5. Search transport graph for candidate paths.
6. Build complete itinerary legs and instructions.
7. Score/deduplicate alternatives.
8. Attach freshness, confidence and warnings.
9. Return structured response.
10. Log anonymised performance/quality metrics.

## 5. Data refresh path
A background worker updates source snapshots and candidate network versions. User requests never wait for a full external dataset extraction. Publishing a validated version is atomic. Each journey response references the version used.

## 6. External service boundaries
Every external dependency must be behind an adapter interface. Application domain logic must not depend on a provider-specific response schema. Adapters normalise external results and enforce timeouts, retry budgets, circuit breakers and licence rules.

## 7. Scaling path
Start with one API deployment, one worker deployment and managed Postgres. Add read replicas, separate routing workers or dedicated services only after metrics show a need. Keep routing interfaces stable to permit later extraction.
