# Data Sources, Acquisition, Licensing and Quality Strategy

**Critical product dependency:** A high-quality instruction experience cannot compensate for incorrect or missing route, stop, direction, transfer and pedestrian data. Data acquisition and verification are core product work.

## 1. Minimum data needed for static-network MVP

- Route identifiers and aliases.
- Route variants, direction, origin/destination and ordered stop sequence.
- Bus stop/station/platform coordinates and names/aliases.
- Route shape/geometry where available.
- Walking network and paths between stops.
- Transfer links and pedestrian connector geometry.
- POIs, landmarks, destination entrances.
- Mode and service type.
- Source, licence, extraction date, verification date, confidence.
- Fare data only if reliable and valid.

Schedules, departure times, live GPS, predictions, booking and payments are deferred. Without schedules, the app cannot verify when a service operates or whether it is available at a selected time; this limitation must be displayed.

## 2. Source inventory and recommended role

### 2.1 OpenStreetMap (OSM) — primary mapped-network candidate

- Main: https://www.openstreetmap.org/
- Sri Lanka Geofabrik extract: https://download.geofabrik.de/asia/sri-lanka.html
- Public transport route relation viewer/export tool: https://openstreetmap.tools/public_transport_geojson/
- OSM copyright/licence: https://www.openstreetmap.org/copyright

Potential content: roads, paths, footways, bus stops, platforms, railway stations/halts, railway lines, POIs, route relations and route geometry. Coverage and tagging quality vary by region and corridor; this is a hypothesis to audit, not a verified national count.

**Use:** pedestrian graph, initial stop/POI candidates, mapped route relations and geometry. Extract `route=bus`, `route_master=bus`, stop/platform roles, `public_transport=*`, `highway=bus_stop`, railway station/halt and route members. Inspect relation order, direction, `ref`, `name`, `operator`, network and completeness.

**Licence:** ODbL. Attribution and database-share-alike implications may apply to derived databases. Commercial use is not automatically prohibited, but obligations must be reviewed. Do not mix OSM-derived database with other sources without understanding licensing consequences.

**Limitations:** OSM does not guarantee current operational status, full stop sequence, service variants, timetable or exact boarding position.

### 2.2 Sri Lanka NSDI — official GIS reference candidate

- Geoportal: https://geoportal.nsdi.gov.lk/
- Transport REST service: https://gisapps.nsdi.gov.lk/server/rest/services/SLNSDI/Transport/MapServer
- Transportation metadata: https://nsdi.gov.lk/transportation
- Spatial data services: https://nsdi.gov.lk/spatial-data-services
- Data access FAQ: https://nsdi.gov.lk/faq

The Transport service lists railway infrastructure, railway lines, road classes including footpath, road rights-of-way, interchanges and road transportation points. It supports JSON and GeoJSON query formats in its service description.

**Use:** government reference geometry for roads/footpaths, rail infrastructure/lines, transport points, cross-checks and POI layers where access permits.

**Limitations:** infrastructure lines are not necessarily bus-route stop sequences, operational service patterns or current passenger service. Rights/access conditions vary; confirm each dataset's licence and permission before redistribution or commercial use. Some NSDI data may be free, commercial, authorized or restricted.

### 2.3 National Transport Commission (NTC) — route/permit/fare source candidate

- NTC: https://www.ntc.gov.lk/
- Route maps: https://www.ntc.gov.lk/Bus_info/route_map.php
- Permit summary: https://www.ntc.gov.lk/Bus_info/permit_Summary.php
- Time table/permit details: https://www.ntc.gov.lk/Bus_info/time_table.php
- Permit publications: https://www.ntc.gov.lk/corporate/media_and_news/permit-details.php
- National Transport Statistics (official reports are linked from NTC site)

Potential records include route number, origin/destination, operator/service, permit information and fare publications. Route maps/PDFs may require manual extraction and validation. A publicly accessible page or PDF is not an automatic redistribution licence.

**Use:** route master, route-number reconciliation, fare and service-type evidence, official source cross-check. Do not assume it provides a complete machine-readable ordered stop sequence or geometry.

### 2.4 Community extraction project — NTC fare route data

- Repository: https://github.com/nave3nP/sri-lanka-transit-data

The project describes itself as unofficial/community-maintained, extracting current inter-provincial route/fare data from official sources, and provides reproducible tooling and datasets. It reports a v0.2 stage focused on NTC source discovery and route/fare extraction.

**Use:** accelerate route master discovery, inspect extraction methodology and source lineage; independently validate before production. Code/data licence and original-source rights must be reviewed separately.

### 2.5 GTFS feed — ingestion/testing source

- Mobility Database LMT feed listing: https://mobilitydatabase.org/feeds/gtfs/mdb-3490
- Producer download URL listed by the feed: https://api.transit.seyone.dev/api/v1/gtfs/download?agency=LMT
- BusMaps corrected feed summary: https://busmaps.com/en/sri-lanka/Lanka-Metro/lanka-metro

The LMT feed is limited network coverage, not a nationwide feed. A third-party corrected summary reports 6 routes, 185 stops and 56 scheduled trips for one feed version, updated October 2026, with validation warnings; another listing may show a different route count. Feed versions and validation results can differ, so inspect and validate the exact ZIP before importing.

**Use:** test GTFS ingestion, shapes, route/stop/trip relationships and schema. Do not treat the feed as complete Sri Lankan coverage. Confirm CC BY 4.0 or other licence at the exact feed version and attribute accordingly.

### 2.6 Sri Lanka Railways — official rail service source

- Official website: https://www.railway.gov.lk/
- Official schedule search: https://eservices.railway.gov.lk/schedule/searchTrain.action?lang=en

**Use:** official station/service information, line/route validation and later schedule integration. A public documented full machine-readable network API has not been confirmed in this research. For MVP, reconcile station names, line order, station coordinates and railway geometry using official material, NSDI and OSM. Timetables are deferred.

### 2.7 Third-party rail station lists

- https://trains.sri.lanka.com/stations
- RailReportCard OSM analysis: https://www.railreportcard.org/search?country=LKA

Useful for cross-checking station names, line membership and coordinates. Reported station counts vary (lists and OSM-derived inventories count halts, mapped stations and stations differently). These are not authoritative or licence-cleared for bulk reuse merely because publicly accessible.

### 2.8 University research / GTFS methodology

- University of Moratuwa, 2019 GTFS development research: https://dl.lib.uom.lk/items/9e8da31f-79c7-47a6-b96f-aa0ffbd51f36
- Stop-times development in Western Province bus transit: https://dl.lib.uom.lk/items/7c2877c7-a34a-4b84-af98-c7ea50674a17

Research describes GTFS components and Sri Lankan data challenges, including lack of stop-level bus time data in the studied context and derivation of stop times from average speed for study feeds. Useful methodological reference, not a production data source.

### 2.9 Geocoding and POIs

Candidate: OSM-derived geocoder (self-hosted where appropriate), a commercial geocoding provider with Sri Lanka coverage and clear licence, or curated POI/alias index. Use OSM and NSDI POI/building data where licence and availability allow.

Requirements: Sinhala/Tamil/English aliases, transliteration, local place names, locality disambiguation, POI categories, entrances/access points, cache/use limits and licence review. Do not rely on public Nominatim as an unrestricted production geocoding service; evaluate usage policy or self-host/provider.

### 2.10 Field surveys and community reports

Field data is necessary for route variants, stop side, destination board, terminal/bay, transfer path, landmark recognition and final entrance. Use structured collection, contributor consent, report moderation, source date and confidence. Photos may contain people/plates; minimize and review privacy.

## 3. Recommended data acquisition sequence

1. **OSM country extract:** download PBF; create audit of bus route relations, route masters, stops, railway stations/halts/lines, footways, POIs, route geometry and ordered stop membership.
2. **OSM coverage audit:** count records and completeness by region/corridor; identify missing refs, sequence roles, geometry and variants. Do not state national completeness without this audit.
3. **NSDI audit:** list layer schema, query sample/count, download/export limits, data update dates and licence/access requirements; cross-check road/footpath/rail/transport point data.
4. **NTC route master:** capture route map/fare/permit records, source URL, publication/effective date, route ref, endpoints, service type and operator only as necessary. Parse PDFs with extraction logs and manual verification.
5. **GTFS import test:** download exact LMT feed version; run validator; inspect `agency`, `routes`, `stops`, `trips`, `stop_times`, `shapes`, `transfers`, calendars and fare fields; record limitations and licence.
6. **Rail network:** reconcile official station list, NSDI, OSM, third-party station list; create station aliases, station order, line geometry and transfer nodes. Validate pilot segment.
7. **Walking/transfer graph:** build pedestrian links; inspect transfer distances and path feasibility; field-check key interchanges.
8. **POIs/entrances:** select pilot destinations and map correct public access points.
9. **Field validation:** route rides/walks with structured checklist and evidence.
10. **Publish versioned dataset:** QA, source registry, confidence, coverage map and known gaps.

## 4. Canonical schema (suggested tables)

- `source_registry`: source name/type, URL, licence, rights note, update cadence, capture timestamp, checksum.
- `source_artifacts`: raw file, source ID, parser version, archived location, status.
- `agencies`: internal ID, names/aliases, mode, source.
- `routes`: internal route ID, public ref, name, mode, agency, aliases.
- `route_variants`: route ID, variant, direction, origin/destination, service type, validity, confidence.
- `stops`: stop/station/platform ID, names, aliases, coordinates, type, locality, access notes, confidence.
- `route_stop_sequence`: variant ID, stop ID, sequence, boarding/alighting flags if verified.
- `route_shapes`: route variant geometry and source.
- `pedestrian_nodes/edges`: walk network, attributes and source.
- `transfer_connections`: from/to stop/platform, walk geometry, distance, crossing/access attributes, source.
- `poi/destination/entrance`: names, categories, coordinates, aliases, entrance points.
- `fare_records`: route/variant, fare type, value, currency, effective date, source.
- `verification_events`: entity, method, reviewer/contributor, date, evidence and result.
- `data_reports`: user correction, category, evidence, status, moderation history.
- `dataset_versions`: published graph/data version and QA summary.

## 5. Confidence model

- **Verified:** field check or authoritative confirmation of the specific fact, with date.
- **High:** multiple consistent credible sources, no material contradiction.
- **Medium:** one credible source or partly verified record.
- **Low:** inferred, weakly supported or incomplete.
- **Unverified:** imported/candidate data not checked.

Confidence is fact-level where possible. A route can have verified stop coordinates but unverified operating pattern; do not assign one confidence label that hides this.

## 6. Data QA checklist

- Duplicate stops and aliases.
- Coordinate sanity, projection and geometry validity.
- Route variant has consistent endpoint and ordered sequence.
- Stops lie reasonably near route geometry; exceptions reviewed.
- Direction/headsign is not confused with route number.
- Partial route/short run represented.
- Boarding/alighting eligibility not assumed.
- Transfer link walk path exists; distance/time plausible.
- Stop and station names multilingual and aliases source-backed.
- POI entrance not simply centroid where inappropriate.
- Fare date/route variant/service class valid.
- Source licence and attribution tracked.
- Stale data and update cadence flagged.
- Confidence assigned and critical uncertainty surfaced.

## 7. Data rights and compliance

- Public accessibility does not equal permission to redistribute or commercially reuse.
- Track licence per dataset and derived record.
- OSM ODbL attribution and database obligations need legal review.
- NSDI rights vary by dataset and access class.
- NTC PDFs/publications need reuse confirmation.
- GTFS feed licence must be verified for exact version and producer.
- Third-party websites are cross-checks, not automatically reusable datasets.
- Map tiles/geocoder use and caching follow provider terms.
- Contributors need terms, attribution, privacy notice, consent and moderation process.

## 8. Static-network MVP data limitation

Because the first version does not have verified timetables or live availability, it should not present exact departure times, guarantee route operation, claim a transfer will be available, or provide schedule-aware “arrive by” planning. It can propose a network route and estimates with a clear caveat. Route availability by time/day should be added only when reliable schedule/service metadata exists.
