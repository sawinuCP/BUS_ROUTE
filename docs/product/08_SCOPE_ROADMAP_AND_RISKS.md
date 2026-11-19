# Scope, Roadmap, Product Decisions and Risks

## 1. Product scope boundaries

### MVP promise
Plan a feasible network journey on supported and sufficiently validated coverage, compare a few practical options, and guide the user through each leg with clear boarding, alighting, transfer and final-walk instructions. Make uncertainty and static-service limitations explicit.

### MVP modes
- Walking access/egress and transfer paths.
- Bus on pilot corridors with verified route variants and stop sequences.
- Railway only on validated pilot lines/station sequences; not a blanket nationwide inclusion.

### Deferred
- Exact timetables and departure time optimization.
- Real-time GPS/arrival predictions.
- Crowding/live occupancy.
- Ticketing/payment/booking.
- Nationwide complete coverage claims.
- Operator fleet/dispatch integration.

## 2. Recommended staged roadmap

### Phase 0 — Discovery and data feasibility
- Interview/observe travellers.
- Hands-on competitor test for selected journeys.
- Audit OSM/NSDI/NTC/rail/LMT sources.
- Define pilot corridor based on data availability and user need.
- Resolve licence/terms and source lineage.
- Produce coverage scorecard.

**Exit:** Evidence-backed pain points, pilot decision, source/rights register, route coverage baseline.

### Phase 1 — Data foundation
- Raw-source archive and ingestion scripts.
- Canonical PostGIS schema.
- Route/variant/stop/transfer normalization.
- QA dashboard/queue and confidence.
- Import pilot data.
- Field validation of routes, stops and transfers.

**Exit:** Stable versioned pilot network, route sequences and transfer graph with audit trail.

### Phase 2 — Planning engine and basic UX
- Origin/destination search and aliases.
- Pedestrian access/egress.
- Bus/rail route candidates on supported coverage.
- Alternative generation and ranking.
- Result cards and itinerary overview.
- Coverage/no-route/low-confidence states.

**Exit:** Users can find and compare routes on curated pilot test cases.

### Phase 3 — Instruction and journey mode
- Step templates.
- Boarding/direction/alighting/transfer/final walk cards.
- Active progress and manual confirmation.
- Multilingual instruction support.
- Voice/read-aloud if feasible.
- Recovery/re-plan flows.

**Exit:** Usability tests show users can follow real pilot journeys with acceptable error rates.

### Phase 4 — Pilot deployment
- Field testing and corrections.
- Offline itinerary caching.
- Report workflow.
- Saved trips and privacy settings.
- Reliability, performance and accessibility audits.

**Exit:** Measured task success, data quality, user feedback, crash/latency and correction turnaround.

### Phase 5 — Coverage expansion and intelligence
- Additional corridors and modes.
- Timetable integration where reliable/licensed.
- Live tracking/alerts through partnerships or verified sources.
- Community validation scale-up.
- Crowding and comfort reports, carefully aggregated.

## 3. Pilot selection criteria

Score corridors/regions on:
- Traveller demand and important destinations.
- Bus route/stop data completeness.
- Route variants and service complexity.
- OSM/official source agreement.
- Pedestrian and transfer graph quality.
- Ability to field-check with reasonable effort.
- Variety of trip types and transfer points.
- Language/localization needs.
- Potential partner/feedback access.

Do not choose solely because the area is easy to map. Pilot must expose meaningful problems but be verifiable.

## 4. Risks and mitigations

### R1 — Incorrect route/stop instructions (critical)
Mitigation: source provenance, confidence, field validation, QA gates, critical instruction templates, reporting and rollback.

### R2 — Data coverage mistaken for service availability
Mitigation: static-network disclaimer, no schedule/operating guarantees, later schedule integration.

### R3 — OSM completeness/licence risk
Mitigation: coverage audit, source separation, attribution, legal review of ODbL obligations, licence registry.

### R4 — Official source access and reuse uncertain
Mitigation: contact agencies, document access conditions, permission checks, manual/limited use if necessary.

### R5 — Route variants and short services are incorrectly merged
Mitigation: variant entity, separate stop sequences, QA and field validation.

### R6 — Pedestrian path unsafe/inaccurate
Mitigation: pedestrian network, field check, avoid unsupported crossing/safety claims, uncertainty warnings.

### R7 — Geocoder fails local names
Mitigation: alias collection, local-language review, search testing and curated pilot place index.

### R8 — Users expect live data
Mitigation: product messaging and UI distinguish static planning from live operations; avoid deceptive countdowns.

### R9 — Privacy leakage through location/trip sharing
Mitigation: no mandatory account, minimized logs, explicit sharing, expiry, deletion, secure access.

### R10 — AI hallucinates critical instructions
Mitigation: grounded structured inputs, deterministic critical templates, source IDs, validation, fallback “unknown.”

### R11 — Scope becomes too large
Mitigation: corridor-based MVP, mode/data gate, P0/P1/P2 prioritization, deferred live features.

### R12 — Community misinformation/abuse
Mitigation: moderation, duplicate reports, contributor trust, review gates, no automatic critical changes.

### R13 — Accessibility claims are inaccurate
Mitigation: verified attribute schema and unknown status, user research and field audits.

### R14 — Estimates are misleading
Mitigation: uncertainty, assumption documentation, calibration and test against field journeys.

## 5. Product decisions (proposed)

- Core trip planning without login.
- Static route network is the MVP data basis; no timetable/live guarantee.
- Bus and walking first; rail only on verified coverage.
- Route variants must be separate entities.
- Generate a small set of non-dominated alternatives.
- Critical directions use grounded templates; AI only assists language/explanation.
- Confidence/provenance is required internally and visible when important.
- Selected trip can be cached for offline use.
- User contribution is opt-in and moderated.
- No “safe route” certification.
- Fare is displayed only with valid source and effective date.

## 6. Open decisions

- Pilot region/corridor.
- Client framework.
- Routing engine or hybrid.
- Geocoding and map provider/licence.
- Data licensing and agency agreements.
- Fare handling in MVP.
- Accessibility attribute model.
- Account/saved trip synchronization.
- Community moderation model.
- Voice and automatic alighting notification approach.
- Hosting, data residency, cost and retention.

## 7. Definition of MVP done

- Pilot coverage is explicitly described.
- Supported route variants and ordered stop sequences pass QA.
- Every generated route is grounded in the data graph.
- Walking and transfer paths are feasible and field-checked for pilot journeys.
- Boarding/direction/alighting/transfer instructions are comprehensible.
- No timetable or service availability claims unsupported by source.
- Multilingual search works on tested names/aliases.
- Low-confidence/no-route cases are handled honestly.
- Selected itinerary works offline at least for instructions.
- Privacy/security/accessibility checks completed.
- Usability test demonstrates journey task completion with agreed thresholds.
- Data sources/licences and attribution are documented.
