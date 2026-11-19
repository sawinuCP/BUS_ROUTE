# User Stories and End-to-End User Flows

Stories are written from user intent and must be verified through usability tests. Priority: P0 MVP, P1 pilot enhancement, P2 later capability.

## 1. Personas (working hypotheses)

- **Nimali — occasional traveller:** knows destination, not the route; wants simple instructions.
- **Kasun — commuter:** wants repeatable routes and alternatives when a route is inconvenient.
- **Alex — visitor:** uses unfamiliar names and prefers English; wants landmark context.
- **Ravi — access-conscious traveller:** wants limited walking and access details, but accepts “unknown” if data is missing.
- **Planner/family member:** plans a journey for someone else and shares instructions.

These are design personas, not research participants.

## 2. Story inventory

### Planning/search
- US-01 As a traveller, I want to enter an origin and destination so I can discover possible journeys. (P0)
- US-02 I want to use my current location or select a point on a map so I can plan from where I am. (P0)
- US-03 I want to search using Sinhala, Tamil, English, transliteration or a familiar landmark. (P0)
- US-04 I want ambiguous search results clarified by locality/type. (P0)
- US-05 I want to choose a destination entrance/building when the place has multiple access points. (P1)
- US-06 I want to reverse origin and destination. (P0)
- US-07 I want to select modes and a maximum walking distance. (P0)

### Comparing routes
- US-08 I want several practical options rather than one route. (P0)
- US-09 I want to compare duration estimate, walking, transfers, fare confidence and route complexity. (P0)
- US-10 I want a “least walking” and “fewest transfers” option. (P0)
- US-11 I want to know when a result is network-based and service time is unverified. (P0)
- US-12 I want to see route confidence and critical data limitations. (P0)

### Executing journey
- US-13 I want exact boarding-stop guidance. (P0)
- US-14 I want route number plus direction/destination and the required segment. (P0)
- US-15 I want to know where to alight and what landmark/stop name to watch for. (P0)
- US-16 I want transfer walking instructions and the next boarding location. (P0)
- US-17 I want a clear final walk to my destination entrance. (P0)
- US-18 I want voice/read-aloud instructions. (P1)
- US-19 I want to confirm steps manually when GPS is unreliable. (P0)
- US-20 I want progress and the next action without reading the entire itinerary. (P0)

### Recovery and resilience
- US-21 I missed my stop; I want to re-plan from my current location. (P1)
- US-22 I boarded the wrong service; I want recovery options. (P1)
- US-23 I missed a transfer; I want alternatives and clear availability caveats. (P1)
- US-24 My internet is unavailable; I want to continue with cached instructions. (P1)
- US-25 Location permission is denied; I want to plan manually. (P0)
- US-26 GPS is inaccurate; I want to avoid automatic step changes. (P0)

### Trust and contribution
- US-27 I want to see whether route/stop information is verified and when it was checked. (P0)
- US-28 I want to report a wrong route, stop, transfer or landmark. (P1)
- US-29 I want to suggest a local alias or destination entrance. (P1)
- US-30 I want privacy controls and no compulsory account for basic planning. (P0)
- US-31 I want to share my planned itinerary or active trip with someone I choose. (P1, opt-in)

### Accessibility and preferences
- US-32 I want to limit walking. (P0)
- US-33 I want to avoid stairs/choose step-free routes where verified. (P1)
- US-34 I want readable text, screen-reader support and my preferred language. (P0)
- US-35 I want to filter modes or prefer fewer transfers. (P0)

## 3. Flow A — Plan a new journey

1. Open app → plan screen.
2. Origin defaults to “Use current location” only after permission; otherwise manual entry.
3. User searches destination.
4. Search returns typed candidates (POI, stop, station, landmark, address) with locality and language alias.
5. User selects destination/entrance if relevant.
6. Select travel preferences (optional: modes, walk cap, transfers, accessibility).
7. Planner validates origin/destination and network coverage.
8. If coverage is insufficient, show explanation and possible nearby network points; do not silently produce an unsupported route.
9. Results display several options with trade-offs and confidence.
10. User opens an option → journey overview with leg sequence/map.
11. User taps Start → active trip, or saves/shares itinerary.

**Error/edge states:** no results, ambiguous result, no route, low network coverage, missing route sequence, invalid coordinates, location permission denied, network unavailable.

## 4. Flow B — Follow the journey

1. Active trip shows first action (walk to boarding point).
2. Map highlights pedestrian leg; instruction includes distance/time and verified landmark.
3. User arrives; confirm manually or by GPS with accuracy guard.
4. Boarding card shows route identifier, direction/headsign and boarding point.
5. User boards; active state becomes ride leg.
6. Progress shows destination stop/number of stops only if ordered stops are reliable.
7. Alighting cue shows stop name, aliases and landmark; GPS alerts are optional and require permission.
8. User confirms alighting.
9. If transfer: show connector walk and next boarding point/service.
10. Repeat until final walk.
11. Destination arrival shows completion and optional feedback.

## 5. Flow C — Compare and choose route

- Route cards show estimated time, walk distance, transfers, modes, fare only if verified, and confidence.
- Sort/filter: fastest estimate, least walking, fewest transfers, lower verified fare, modes allowed.
- Explain “why this option” in simple text (e.g., one fewer transfer but longer walk).
- Ensure route alternatives are not duplicates with tiny variations.

## 6. Flow D — Ambiguous stop or route variant

1. Search/route planner identifies ambiguity (same name, similar route number, variants).
2. Present choices with area, direction, endpoint, served segment and evidence.
3. User chooses/opens map.
4. If unresolved, mark uncertainty and avoid generating confident boarding instructions.
5. Optionally report missing/ambiguous data.

## 7. Flow E — Missed stop

1. User selects “I missed my stop” or app detects possible overshoot but does not assume.
2. Confirm approximate current location or choose on map.
3. Re-plan to destination from current position.
4. Present safe, actionable next steps and static-service availability caveat.
5. Keep original trip history only as local session context unless user opts to save.

## 8. Flow F — Wrong bus/route

1. User taps “I boarded a different route.”
2. Ask route/stop/current location only as needed.
3. Re-plan from confirmed location.
4. Show a clear explanation of the new route; avoid unsupported “get off now” instruction.

## 9. Flow G — Transfer missed or unavailable

1. User indicates transfer missed or next service unavailable.
2. Use current location, destination and permitted modes.
3. If schedules are not available, say that service availability cannot be verified and offer network alternatives only.
4. Show extra walk/transfer/time trade-offs.

## 10. Flow H — Offline mode

1. User starts/downloads trip while online.
2. Cache itinerary, stop names, route segment details, instruction text and permitted map data.
3. Connection drops; show offline banner with cache age.
4. Manual step confirmations continue.
5. GPS-dependent actions disabled or marked unavailable if needed.
6. Reports queue locally only with user consent; sync later.

## 11. Flow I — Report data issue

1. User taps report on route/stop/step.
2. Choose category: wrong stop, route pattern, direction, transfer, walking path, landmark/name, fare, access attribute, other.
3. Add optional explanation/photo/location; show privacy note and strip unnecessary metadata from image where possible.
4. Submit or queue offline.
5. Server creates report linked to canonical entity and source/version.
6. Duplicate detection/moderation.
7. Data reviewer validates against sources/field evidence.
8. Change is versioned; route graph rebuilds; reporter receives status if opted in.

## 12. Flow J — Saved commute

1. User saves a route with a chosen origin/destination and preferences.
2. Home shows quick plan.
3. User selects it; planner refreshes route data and indicates material changes.
4. Do not reuse stale route instructions without freshness check.

## 13. Flow K — Share planned/active journey

1. User selects Share.
2. Choose planned itinerary or active trip/location sharing.
3. Planned share includes only route details and approximate times if user chooses.
4. Active location sharing requires explicit start, duration/expiry, recipient/link access controls and visible stop-sharing control.
5. End/expiry removes access; avoid public-by-default links.

## 14. Flow L — Accessibility preference

1. User chooses maximum walking distance and optional avoid-stairs/step-free preference.
2. Routing applies only verified attributes.
3. Results label unknown access attributes.
4. If no route can be confidently filtered, explain data limitation rather than claim accessibility.

## 15. Flow M — No route found

1. Explain why: no mapped route connection, low coverage, modes restricted, destination outside data coverage.
2. Offer nearby search/adjustment: broader walking radius, additional modes, nearby stop/destination pin.
3. Provide report data gap action.
4. Never fabricate a bus route to fill empty results.

## 16. Flow N — Permission and privacy

- Location permission requested at the moment it materially helps.
- Explain benefit and alternatives.
- If denied, manual origin/map selection works.
- Background location is not required for basic planning.
- Active trip sharing only by explicit action; user controls duration and recipients.
- Account is optional for basic trip planning.

## 17. User-flow acceptance principles

Every flow should have: normal path, no-data path, low-confidence path, permission-denied path, network-failure path, and recovery path where relevant. Critical route instructions should not depend on a single fragile signal.
