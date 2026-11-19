# 04 — User Stories and Acceptance Criteria

Stories are grouped by capability. Each story is independently testable. “Given/When/Then” criteria are minimum acceptance conditions, not an exhaustive test suite.

## Epic A — Search and place resolution

### US-001 — Search for an origin
**As a** traveller, **I want** to search for my starting place, **so that** I can plan from a meaningful location.

Acceptance criteria:
- Given a valid query, when I search, then ranked place candidates are returned with name, type and locality.
- Given several similar candidates, when results are shown, then I can distinguish them by locality/type.
- Given no result, when search completes, then I can select a point on the map or refine the query.
- Results must not silently select an ambiguous candidate.

### US-002 — Search for a destination
**As a** traveller, **I want** to search for my destination, **so that** I can plan a journey to it.

Acceptance criteria:
- Search supports place names and supported aliases.
- Candidate details include locality and entity type.
- Selecting a candidate resolves to a stable internal place identifier and coordinate.
- If a destination has multiple entrances, the app uses a verified public access point or labels the coordinate approximate.

### US-003 — Search in Sinhala, Tamil or English
**As a** traveller, **I want** to search using the language or spelling I know, **so that** I can find the intended place.

Acceptance criteria:
- Search indexes stored language aliases and transliterations.
- Search result displays a canonical name and available localized name.
- Alias matches retain the same canonical entity ID.
- Low-confidence fuzzy matches require user selection.

### US-004 — Find a stop or station
**As a** traveller, **I want** to search for a stop/station, **so that** I can use it as an origin, destination or transfer point.

Acceptance criteria:
- Results distinguish a station from its entrances/platforms and distinguish nearby but separate bus stops.
- Stop result includes available mode and locality.
- The system does not merge two access points solely because they are geographically close.

### US-005 — Choose an origin on the map
**As a** traveller, **I want** to set an origin by tapping the map, **so that** I can plan when search does not identify my location.

Acceptance criteria:
- Map tap creates a coordinate candidate.
- The app reverse-geocodes if a provider is available, but preserves the selected coordinate if not.
- The user can move or clear the marker.
- The UI indicates that a coordinate is approximate if no known entrance/place is resolved.

## Epic B — Journey planning

### US-006 — Plan a public transport journey
**As a** traveller, **I want** to enter an origin and destination, **so that** I can see feasible public transport options.

Acceptance criteria:
- Planner validates both endpoints and coverage.
- Returned itinerary contains ordered legs with mode, endpoints and geometry/instructions where available.
- No path result explains the coverage/data limitation.
- The response includes the active network dataset version and freshness metadata.
- A network-feasible route is not described as a currently operating service unless live operational evidence exists.

### US-007 — Combine walking, bus and rail
**As a** traveller, **I want** a journey that combines supported modes, **so that** I do not have to plan each mode separately.

Acceptance criteria:
- Planner may connect walking access, bus, rail and final walking legs.
- Each transfer is represented as its own leg or explicit transfer instruction.
- Unsupported mode connections are not fabricated.
- A journey with missing transfer geometry is flagged or excluded according to configured quality rules.

### US-008 — Understand bus route direction and variant
**As a** traveller, **I want** to see the correct route pattern and direction, **so that** I do not board a bus with the same route number going somewhere else.

Acceptance criteria:
- Transit leg identifies route, direction and variant/pattern.
- Destination/headsign text is shown only when source data or verification supports it.
- Distinct patterns are not collapsed into one route solely by route number.
- If direction cannot be established, the instruction is marked incomplete and the itinerary is not presented as fully verified.

### US-009 — Compare journey alternatives
**As a** traveller, **I want** a small set of different route options, **so that** I can choose what suits me.

Acceptance criteria:
- Results are non-dominated or meaningfully distinct.
- Each option shows estimated duration, walking amount, transfer count and confidence/quality.
- Near-identical options are deduplicated.
- The app explains when values are estimates.

### US-010 — Prefer less walking
**As a** traveller, **I want** to prioritise less walking, **so that** I can choose a route that better suits my needs.

Acceptance criteria:
- Selecting the preference changes ranking or filtering.
- It does not invent accessibility or step-free status.
- If no lower-walking route exists, the app says so and presents the closest alternative.

### US-011 — Prefer fewer transfers
**As a** traveller, **I want** to minimise transfers, **so that** the journey is easier to follow.

Acceptance criteria:
- Planner ranks fewer-transfer options higher when feasible.
- It still respects route feasibility and quality constraints.
- A direct route is not ranked first if its data quality is below configured minimum.

### US-012 — Understand duration estimates
**As a** traveller, **I want** to understand how long the journey may take, **so that** I can make a reasonable plan.

Acceptance criteria:
- Walking, in-vehicle and transfer components are separately represented where possible.
- Unknown waiting time is not disguised as a precise value.
- Estimates include assumptions or uncertainty labels.
- Without schedules/live data, the app does not claim an exact departure or arrival time.

### US-013 — See fare only when reliable
**As a** traveller, **I want** fare information when available, **so that** I can estimate cost without being misled.

Acceptance criteria:
- Fare shows source, fare category and effective date.
- If route/fare applicability is uncertain, show “not verified” or omit it.
- Fare updates are versioned and can be rolled back.
- A fare estimate is not represented as an official guaranteed quote.

## Epic C — Step-by-step journey instructions

### US-014 — Walk to the correct boarding point
**As a** traveller, **I want** directions to the correct physical boarding point, **so that** I do not wait at the wrong side or stand.

Acceptance criteria:
- Walking leg ends at a specific access point where data exists.
- Distance and route geometry are provided when walking engine supports them.
- Stand, bay, road side or entrance appears only when verified.
- If access-point certainty is low, the app warns the user.

### US-015 — Know which bus/train to board
**As a** traveller, **I want** a clear boarding instruction, **so that** I can identify the correct service.

Acceptance criteria:
- Instruction includes mode, route/service pattern, direction and boarding location.
- Local route/destination wording is displayed when verified.
- The app never invents a bus destination board or platform.
- If timetable/live service data is unavailable, no “arriving now” claim appears.

### US-016 — Know where to get off
**As a** traveller, **I want** an explicit alighting point, **so that** I can leave the service at the correct location.

Acceptance criteria:
- Alighting stop/station is named and uniquely identified.
- The app can display distance/sequence context if supported.
- Recognition cues are shown only if verified.
- User can manually confirm alighting during active journey.

### US-017 — Follow a transfer
**As a** traveller, **I want** a clear walking instruction between services, **so that** I can reach the next boarding point.

Acceptance criteria:
- Transfer has origin and destination access-point IDs.
- Walking distance/geometry is returned when available.
- Transfer is not inferred solely from straight-line proximity.
- If transfer access is unverified, it is flagged or excluded.

### US-018 — Reach the destination entrance
**As a** traveller, **I want** the final walk to a useful destination access point, **so that** I can finish at the right place.

Acceptance criteria:
- The app uses a verified entrance when available.
- Otherwise it labels the map point as approximate.
- Final walking path is generated by the walking provider or clearly marked unavailable.
- The user can adjust the final destination point.

## Epic D — Active journey

### US-019 — Start a planned journey
**As a** traveller, **I want** to start an itinerary, **so that** I can follow one step at a time.

Acceptance criteria:
- Starting creates a journey session with a plan snapshot and network dataset version.
- The first actionable step is prominent.
- User can pause or end the session.
- The plan remains available if the network changes during the trip.

### US-020 — Confirm boarding and alighting
**As a** traveller, **I want** to confirm when I board and alight, **so that** the app can advance reliably.

Acceptance criteria:
- Manual confirmation is always available.
- GPS suggestions do not automatically assert boarding/alighting without adequate evidence.
- State transitions are recorded with timestamps.
- User can correct an accidental confirmation.

### US-021 — Detect likely deviation
**As a** traveller, **I want** to be notified if I may have deviated, **so that** I can recover.

Acceptance criteria:
- Detection uses accuracy, map matching, distance and persistence thresholds.
- One noisy GPS sample does not trigger a disruptive warning.
- User can dismiss or request re-planning.
- Uncertain location is expressed as uncertainty, not fact.

### US-022 — Re-plan after a missed stop
**As a** traveller, **I want** a revised journey from my current or selected location, **so that** I can continue safely.

Acceptance criteria:
- User can use current location or manually choose a point.
- Planner returns only supported paths.
- Existing journey remains accessible for context.
- The app explains if no supported alternative is available.

### US-023 — Resume an interrupted journey
**As a** traveller, **I want** to resume after closing the app or losing connectivity, **so that** I do not lose my instructions.

Acceptance criteria:
- Last confirmed journey state is persisted locally.
- Cached itinerary steps are accessible offline.
- Stale network information is labelled.
- Resume does not silently assume the user remains at the previous GPS coordinate.

## Epic E — Data quality and feedback

### US-024 — View data freshness
**As a** traveller, **I want** to know how recently route information was checked, **so that** I can judge its reliability.

Acceptance criteria:
- Journey/leg exposes freshness and verification metadata where useful.
- “Last fetched” and “last verified” are not conflated.
- Unknown source update cadence is labelled unknown.
- Stale data can trigger warning or route suppression rules.

### US-025 — Report incorrect information
**As a** traveller, **I want** to report a wrong stop, route or transfer, **so that** it can be reviewed.

Acceptance criteria:
- Report is linked to a specific entity/leg and dataset version.
- User selects a report category and may add a note.
- Location/photo attachment is optional and consent-based.
- Submission receives a reference/status; it does not immediately alter production routing.

### US-026 — Review a report
**As an** authorised data reviewer, **I want** to inspect and resolve reports, **so that** verified corrections can be published.

Acceptance criteria:
- Reviewer sees source evidence, report context and affected records.
- Approve/reject requires a reason.
- Changes go through staging and validation.
- Audit history records reviewer, timestamp and before/after values.

### US-027 — Monitor data synchronisation
**As an** operations administrator, **I want** to see source sync status, **so that** I can identify stale or failed data.

Acceptance criteria:
- Dashboard lists source, last successful run, current run, counts and errors.
- Failed sync does not overwrite active good data.
- Alerts are raised for missed schedules or abnormal changes.
- Operator can inspect a candidate diff before publication.

### US-028 — Roll back a bad data release
**As an** authorised administrator, **I want** to restore a previous dataset version, **so that** a faulty import does not corrupt journey planning.

Acceptance criteria:
- Every published release is immutable/versioned.
- Rollback selects a previous validated version.
- Active version changes atomically.
- Rollback is audited and followed by health checks.

## Epic F — Personalisation and offline

### US-029 — Save a journey
**As a** signed-in traveller, **I want** to save a frequent journey, **so that** I can plan it again quickly.

Acceptance criteria:
- Saved item stores origin/destination intent and optional preferred constraints.
- Reuse triggers a fresh plan against the current active dataset.
- Old itinerary is not assumed valid forever.
- User can rename/delete saved journeys.

### US-030 — Use journey instructions offline
**As a** traveller, **I want** my selected itinerary to remain available offline, **so that** I can continue when mobile data is unavailable.

Acceptance criteria:
- App caches selected plan, leg descriptions, stop aliases, geometry and warnings.
- Offline state is visible.
- No live availability is implied while offline.
- Cache can be refreshed or deleted.

### US-031 — Change application language
**As a** traveller, **I want** to choose English, Sinhala or Tamil, **so that** I can read instructions comfortably.

Acceptance criteria:
- UI language can be changed independently of device locale.
- Transport names can show canonical and local forms.
- Missing translation falls back consistently and is not replaced with invented translations.
- Font/layout supports required scripts.

## Epic G — AI assistance

### US-032 — Ask for a journey conversationally
**As a** traveller, **I want** to describe my journey in natural language, **so that** I can plan without filling every field manually.

Acceptance criteria:
- AI extracts origin, destination and preferences into a structured request.
- Ambiguous locations are clarified.
- The deterministic journey planner performs routing.
- AI cannot return a route not present in planner output.

### US-033 — Ask what to do next
**As a** traveller, **I want** a plain-language explanation of the next step, **so that** I understand the itinerary.

Acceptance criteria:
- Explanation is grounded in the selected itinerary leg.
- Missing data is stated as unknown.
- AI does not invent landmarks, route numbers, platforms or times.
- User can view the underlying structured step.

## Epic H — Administration

### US-034 — Manage transport source definitions
**As a** data administrator, **I want** a registry of data sources, **so that** each feed has an owner, licence, endpoint and update policy.

Acceptance criteria:
- Source record contains owner, format, access method, licence/terms, schedule and parser version.
- Disabled or expired sources are not silently ingested.
- Changes to source configuration are audited.

### US-035 — Inspect a candidate dataset
**As a** data reviewer, **I want** to inspect changes before publishing, **so that** suspicious imports do not reach users.

Acceptance criteria:
- Candidate version displays additions, removals and modifications.
- Validation failures and severity are visible.
- Publication requires configured validation gates.
- Reviewer can reject or defer a candidate.

### US-036 — Publish a validated dataset
**As an** authorised operator, **I want** to publish a candidate version, **so that** routing uses approved current data.

Acceptance criteria:
- Candidate passes required checks.
- Publication changes the active-version pointer atomically.
- Existing journey sessions retain their plan snapshot.
- Post-publish health checks can trigger rollback.

## Epic I — Security and account

### US-037 — Use basic planning without an account
**As a** traveller, **I want** to plan a journey without registering, **so that** I can try the service quickly.

Acceptance criteria:
- Core search and planning work for guest users within rate limits.
- Saved cross-device journeys require an account.
- Guest location history is not retained beyond configured operational needs.
- Account prompts do not block core planning.

### US-038 — Control location permission
**As a** traveller, **I want** to grant or deny location access, **so that** I control whether the app uses my location.

Acceptance criteria:
- Manual origin selection works without location permission.
- Permission purpose is explained before system prompt.
- Location is collected only during relevant features.
- User can stop location sharing/tracking.

### US-039 — Delete my account data
**As a** signed-in traveller, **I want** to request deletion of my account and personal data, **so that** I can control my information.

Acceptance criteria:
- Deletion workflow identifies data categories and retention exceptions.
- Personal data is deleted or anonymised according to policy and law.
- Deletion completion is auditable.
- Operational/legal records are retained only where justified and disclosed.
