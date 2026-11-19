# 09 — Data Ingestion, Synchronisation and Quality

## 1. Why persist extracted data?
External APIs are useful, but a journey planner must repeatedly join route patterns, ordered stop calls, access points, walking links and transfer relationships. These relationships are not guaranteed to be exposed by one complete, stable, low-latency API. A canonical local representation enables consistent routing, validation, provenance, offline operation and predictable performance.

This does **not** mean copying every source blindly or treating the database as permanently current. The database is a controlled, versioned operational representation refreshed from sources.

## 2. Data categories

| Data category | Preferred method | Local persistence |
|---|---|---|
| Place search | External geocoder or self-hosted geocoder | Cache only as provider terms permit; canonical curated places persist |
| Walking path | Request to Valhalla/GraphHopper | Cache short-lived results where permitted |
| Map tiles | Tile provider | Provider/client cache under terms |
| Route patterns and stop sequences | Official feed/API or approved extraction | Persist canonical version |
| Railway stations/line geometry | Official source/approved geodata | Persist with provenance |
| Transfers/access points | Source + field verification | Persist and version |
| Fares | Official effective-dated publication/API | Persist versioned rules only if rights and applicability are clear |
| Live vehicle positions | Future real-time feed | Short-lived cache; do not treat as static network |
| User reports | App | Persist internally with moderation |

## 3. Source registry
Each source must have:
- owner and contact;
- endpoint/file location and access method;
- data format;
- licence, terms and attribution requirements;
- permitted storage, caching and redistribution;
- expected update cadence;
- last successful fetch;
- ETag/Last-Modified/version/hash support;
- adapter/parser version;
- operational owner and failure policy.

Never assume an open website means unrestricted commercial reuse.

## 4. Refresh pipeline
1. **Schedule:** trigger source-specific job based on its update cadence and importance.
2. **Check:** use ETag, Last-Modified, feed version or checksum if available.
3. **Fetch:** retrieve through a source adapter with timeout, retry and rate-limit handling.
4. **Archive:** store immutable raw response and metadata in object storage.
5. **Parse:** convert source-specific structure into a common internal model.
6. **Normalise:** map IDs, names, coordinates, route patterns, stop order and geometry.
7. **Diff:** compare candidate records with the last accepted source snapshot.
8. **Validate:** schema, coordinate bounds, geometry validity, route sequence, duplicate IDs, referential integrity, stop displacement, route length change, orphan records and suspicious mass deletions.
9. **Quarantine:** isolate unexpected changes rather than publishing automatically.
10. **Build candidate:** create a new candidate dataset version.
11. **Review:** manual review for high-risk changes; automated approval only for sources and change classes with proven quality.
12. **Publish:** atomically switch active dataset version.
13. **Verify:** run post-publish routing smoke tests and data quality checks.
14. **Rollback:** restore previous known-good version if critical checks fail.
15. **Monitor:** report freshness, failures, anomalies and coverage.

## 5. Refresh frequency policy
Do not invent one universal refresh frequency. Configure per source:
- high-change source with reliable feed: more frequent polling;
- official route/permit publication: check on publication cadence and periodic safety recheck;
- static geography: less frequent;
- manually verified transfer/access details: update when reported or field-checked;
- live vehicle feed: short-lived cache aligned to provider update frequency.

Store `fetched_at`, `source_updated_at` (if supplied), `effective_from`, `effective_to`, `last_verified_at` and `next_check_at` separately.

## 6. Validation examples
- GTFS: required files/columns, unique IDs, stop references, ordered stop_times, route/trip consistency, shape validity and service calendars.
- OSM: relation/route completeness, stop ordering and geometry sanity; coverage is not assumed complete.
- GIS REST: layer schema changes, spatial reference, query limits, pagination and licence.
- PDF/HTML extraction: retain original file, extraction method and human verification; OCR/parser output is not authoritative by itself.
- Manual correction: reviewer identity, evidence, reason and effective date.

## 7. Versioning and rollback
- Published versions are immutable.
- Candidate versions never affect production routing.
- API response includes dataset version.
- A journey session retains the plan snapshot it started with.
- Publishing updates an active-version pointer atomically.
- Keep a configurable number of prior releases and raw snapshots subject to storage/privacy policy.
- Rollback is an audited operation.

## 8. Handling source outages
- Continue serving last known-good version if within policy.
- Display stale-data warnings when freshness threshold is exceeded.
- Do not erase data because a source temporarily returns an empty response or times out.
- Circuit-break repeated failing integrations.
- Alert operators when freshness SLO is breached.

## 9. Human verification
Field-check critical pilot corridors:
- route direction and variant;
- boarding side/stand/platform;
- stop sequence and alighting point;
- pedestrian transfer path;
- final access point.
A report from one user can trigger review, but must not directly rewrite the canonical network.
