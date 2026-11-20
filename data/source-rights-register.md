# Source Rights Register

Living register of transport data sources. **Public availability is not
permission to redistribute** — each source is recorded here with its licence
position before any ingestion. Sources are kept private in development until
rights/attribution are recorded (implementation plan §1.3).

## 1. OpenStreetMap via Overpass API — REGISTERED (Phase 1.3, first adapter)

| Field | Value |
|---|---|
| Registry name | `osm-overpass` (seeded by `backend/scripts/seed_osm_source.py`) |
| Owner | OpenStreetMap contributors (via Overpass API) |
| Access method | Read-only POST to `https://overpass-api.de/api/interpreter` |
| Format | Overpass JSON |
| Licence | **ODbL 1.0** (OpenStreetMap) |
| Attribution | "(c) OpenStreetMap contributors" required on any published product using this data |
| Share-alike | **ODbL share-alike may apply to derived databases — legal review required before any public publishing of derived data** |
| Update cadence | Manual during pilot; per-source policy to be defined |
| Evidence | Source URLs recorded in `docs/product/07_DATA_SOURCES_AND_ACQUISITION.md` §2.1 |
| Imported content | Named bus-stop/platform nodes (with `name:si`/`name:ta` aliases), `route=bus` relations grouped by `ref` into routes + per-relation variants (patterns) + ordered member stop calls with role-derived boarding/alighting eligibility |
| Known limitations | OSM does not guarantee operational status, complete stop sequences or boarding positions; `direction_id` is not derivable from OSM alone; unnamed stop nodes are excluded, not invented |
| Privacy | Contains no personal data |

### Compliance notes

- Raw snapshots are archived (checksummed) but kept **out of version control**
  (`.gitignore: backend/data/raw/`) — private in development.
- All facts imported from this source carry `verification_status = 'unverified'`
  until field-verified; they are never presented as confirmed.
- Data-quality reports (aggregate counts only) are committed under
  `backend/data/validation_reports/`.
- Before any public release: confirm ODbL attribution placement and
  share-alike implications with qualified counsel (open question from
  `docs/architecture/17`, §C14).

## 2. Other candidate sources — NOT REGISTERED (no evidence of rights yet)

Per the Phase 0.1 audit and `docs/product/07_DATA_SOURCES_AND_ACQUISITION.md`,
the following remain **unknown** — no dataset, key, or licence evidence exists
in this repository. Do not ingest until each has its own register entry:

- Sri Lanka NSDI transport layers (per-layer reuse terms unknown)
- National Transport Commission (NTC) route/permit/fare publications (reuse rights unknown)
- GTFS feeds for Sri Lanka (no feed version, producer or licence verified)
- Sri Lanka Railways station/line information (no confirmed public API)
