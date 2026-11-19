# Problem-to-Gap Analysis: What We Can Cover and How

This file turns the problem themes into actionable product gaps. A **gap** is not automatically an absence in every competitor; it is a capability, quality or usability opportunity that must be benchmarked and validated.

## Gap matrix

| ID | Traveller problem | Gap/opportunity | Proposed solution | Example of benefit | Priority |
|---|---|---|---|---|---|
| G01 | Fragmented information | One coherent itinerary across modes and legs | Unified journey graph and itinerary | No need to manually stitch separate route pages | P0 |
| G02 | Stop-location ambiguity | Stops are not explained as actionable places | Accurate stop coordinates, side/direction where verified, landmark context | Traveller can identify correct boarding point | P0 |
| G03 | Route-number confusion | Route number alone is insufficient; variants/partial runs | Route variants, direction, destination/headsign and stop pattern | Avoid wrong service/short-run | P0 |
| G04 | Transfer uncertainty | Transfer connection lacks practical walk/wayfinding | Transfer connector with walking path, distance, crossing/landmark notes | Traveller knows where next boarding point is | P0 |
| G05 | First/last mile | Route optimization may ignore walking difficulty and entrance | Pedestrian network, access and final-entrance points, walking preference | Better route choice, fewer confusing final walks | P0 |
| G06 | Service availability unknown | Static route existence can be mistaken for current operation | Explicit static-network disclaimer; future schedule/live integration | Prevent false promise “this bus is running now” | P0 |
| G07 | Estimated time uncertainty | Estimates appear precise despite variability | Time ranges/uncertainty, component breakdown, source and confidence | More realistic planning | P0 |
| G08 | Crowding/boarding uncertainty | Fastest route may be unusable or uncomfortable | Future crowdsourced crowd state; preference weighting, not safety guarantee | Compare comfort when evidence available | P2 |
| G09 | Safety concerns | No trustworthy route-context or support affordances | Privacy-safe trip share, night-mode preferences, vetted resources and reports | Better awareness/support; never safety certification | P2 |
| G10 | Destination entrance ambiguity | Nearby stop is not necessarily correct entrance | Destination entrance/POI access point, campus/hospital sub-destination | Finish at correct building/entry | P1 |
| G11 | Language/name mismatch | Search names/aliases limited | Sinhala/Tamil/English aliases, transliteration, fuzzy search | Search using local name/spelling | P0 |
| G12 | Fare uncertainty | Fare is stale or absent | Provenance/effective-date fares; clearly unavailable otherwise | Cost comparison with transparent confidence | P1 |
| G13 | Accessibility uncertainty | Physical access is unknown | Access attributes, filters, unknown status, verified observations | Avoid claiming inaccessible/accessible without evidence | P1/P2 |
| G14 | Journey failure | No clear recovery path | Missed-stop, wrong-bus, transfer-missed, connectivity recovery | Re-plan calmly from current location | P1 |
| G15 | Data freshness | No source or verification visible | Provenance, versioning, freshness, reports and QA | Trust and corrections | P0 |
| G16 | Dense information | Map/list not converted into immediate action | Journey mode, “do this now” step, progress and concise instruction | Lower cognitive load | P0 |
| G17 | Limited alternatives | Route options may be hard to compare | Non-dominated options with trade-off labels | Choose fast/cheap/easy/low-walking | P0 |
| G18 | No offline continuity | Instructions disappear with connectivity | Download/cache active trip and core details | Continue following a trip during weak network | P1 |
| G19 | Local context missing | Landmark/terminology context not normalized | Local stop aliases, landmark confirmation, route-specific wording | Recognize locations in local context | P0/P1 |
| G20 | Data contribution is difficult | Errors are not structured or actionable | “Report stop/route/instruction issue,” moderation and verification queue | Improve network over time | P1 |

## Detailed gap analysis

### G01 — From disconnected route lookup to a complete multimodal journey

**Gap:** Data and interfaces may present transport modes separately. The user has to decide where a mode ends, where another begins, and how the pieces connect. Existing local apps advertise multimodal planners; our comparative gap must be confirmed through actual testing.

**Solution:** Represent a journey as ordered legs: walk → transit ride → transfer walk → transit ride → final walk. Each leg has an origin, destination, instructions, duration estimate, distance, evidence and confidence. A journey object links the legs and provides a coherent execution view.

**Illustrative:** “Walk 5 minutes to Stop A; board route 138 toward verified destination; alight at Stop B; walk 4 minutes to the next stop; board route 177; alight at C; walk to the destination entrance.” All details must be source-backed.

### G02 — Stop pin to usable boarding instruction

**Gap:** A coordinate alone does not tell a traveller which side of a road, stand, terminal bay or platform to use. Stop names may be ambiguous.

**Solution:** Stop entity includes multilingual/alias names, mode, coordinates, platform/stand where known, direction served, road-side or access notes, landmark, photo/reference where permitted, verification date and confidence. The UI shows “Board here” plus map and landmark confirmation. If side or stand is unverified, say so explicitly.

### G03 — Route number to correct service and direction

**Gap:** Route number may not fully identify a service pattern.

**Solution:** Route master separates route identity from variant/trip pattern. Store origin/destination, ordered stops, direction, short-running patterns, operator/service type, route ref aliases and headsign wording when verified. User instruction displays number plus direction/destination and the required stop sequence segment.

### G04 — Transfer pin to real transfer path

**Gap:** Transfer may require walking, crossing, terminal navigation or locating a different stand.

**Solution:** Transfer connections are explicit graph edges. Store pedestrian connector geometry, length, expected walk, accessibility attributes, landmarks, crossing notes and verification. A transfer card shows “Exit/leave vehicle → follow this path → find next stop → board this service.”

### G05 — Straight-line walk to practical walk

**Gap:** Straight-line distance does not equal a walkable path; route ranking may underweight access/egress effort.

**Solution:** Use pedestrian routing over an appropriate network. Estimate walking time from path length and configurable speed; use preferences (short walk, avoid stairs if data exists, minimize crossings only when supported). Show distance, time and uncertainty. Do not infer sidewalk quality.

### G06 — Static route plan to honest service status

**Gap:** Without schedules or live data, the app cannot know that a route is operating now.

**Solution:** MVP label “Network-based route; departure/service availability not verified.” Use route operation metadata only if sourced. Later integrate timetable feeds and real-time data behind separate reliability levels. Do not calculate “next bus” from a static network.

### G07 — Single number to transparent estimate

**Gap:** Estimated time can be mistaken for a guaranteed arrival time.

**Solution:** Break down walking, ride estimates and transfer buffer. Use ranges when uncertainty warrants. Document assumptions (walking speed, route speed assumptions, traffic not included). Rank with estimated time but present it as estimate.

### G08 — Crowding and comfort preferences

**Gap:** Users may prefer comfort, seat availability or easier boarding over fastest.

**Solution:** Future opt-in reports with time window, route/segment and crowd levels; freshness decay; aggregation thresholds to protect privacy; avoid showing individual reporter traces. A preference “avoid reported high crowding” only if sufficient recent reports exist. Reports are not a guarantee.

### G09 — Safety-aware but non-claiming design

**Gap:** Route guidance cannot assure personal safety; however users need choices and help.

**Solution:** Optional trusted trip sharing, user-selected safer-feeling constraints (e.g. avoid long isolated walks only where reliable contextual data exists), night-aware preferences, official emergency/help links localized and periodically checked, report mechanism. Avoid safety heatmaps based on unverified anecdotes and avoid “safe route” certification.

### G10 — Destination approach

**Gap:** Geocoding a building centroid can direct users to a boundary or wrong entrance.

**Solution:** Destinations support sub-place/entrance access points. Search POIs with aliases, let user select building/entrance, and make final walk explicit. Field verify key hospitals, campuses, terminals and large venues in pilot.

### G11 — Multilingual and alias search

**Gap:** Official names may not match colloquial names, transliteration or language.

**Solution:** Alias table with script, language, source, match type and confidence; normalized search; fuzzy matching with a confirmation screen for ambiguous candidates; multilingual instruction templates reviewed by native speakers.

### G12 — Fare transparency with provenance

**Gap:** Fare may be outdated, route-specific, service-type-specific or unavailable.

**Solution:** Fare records store amount, currency, fare type, validity/effective date, route variant, source and extraction confidence. Only display fares when applicable; show “not verified” otherwise. Never invent.

### G13 — Accessibility as evidence, not a badge

**Gap:** Users cannot determine whether walk/stop/station access meets their needs.

**Solution:** Access attributes (step-free, ramp, stairs, surface, width, crossing, elevator, platform access) with “verified / reported / unknown.” Filters only act on reliable data; include user-defined maximum walking distance and avoid stairs where known.

### G14 — Recovery-oriented travel

**Gap:** Itinerary is brittle when the traveller misses a stop, boards incorrectly, or loses connectivity.

**Solution:** Context-aware recovery: “You may have passed the stop—confirm your location, then re-plan from here”; “Wrong route? Re-plan”; “Transfer not available? Find next feasible option.” Never instruct users to remain on an incorrect vehicle without validated facts.

### G15 — Data confidence

**Gap:** Users cannot distinguish official, mapped, crowdsourced, stale and field-verified information.

**Solution:** Internal provenance on every fact; external UI shows a concise status and last checked date for critical details. Route confidence aggregates completeness and source quality but must not conceal uncertainty. Provide feedback and correction workflow.

### G16 — Instruction-first UX

**Gap:** Dense map and stop list make it difficult to know the immediate action.

**Solution:** Journey mode displays one current step, next action, progress (leg/step), map context and optional detail. “Show full trip” and “map view” are secondary. Support audio/voice readout.

### G17 — Alternative selection

**Gap:** A single route or undifferentiated alternatives fail to explain trade-offs.

**Solution:** Return a handful of Pareto-efficient candidates; label fastest estimate, least walking, fewest transfers, lower fare only when fare is verified, and easiest/lowest complexity based on explicit measurable criteria. Explain trade-offs.

### G18 — Offline continuity

**Gap:** Signal may be unreliable; user may need instructions after leaving Wi-Fi.

**Solution:** Cache the selected itinerary, critical stop and route data, instruction text and permitted map assets. Show offline status and cache age. Keep sensitive trip data locally and offer deletion.

### G19 — Local context

**Gap:** Formal route/stop names may not match the way people identify places.

**Solution:** Add verified local names, nearby landmarks, bus stand/bay descriptions, route alias vocabulary and familiar interchange descriptions. Use local context only when sourced/verified.

### G20 — Improvement loop

**Gap:** Data errors are discovered but not structured into a correction process.

**Solution:** Reports categorized as wrong stop, route missing, route variant, transfer path, destination entrance, name/language, fare, accessibility, or outdated. Include optional location/photographic evidence, privacy warning, moderation, duplicate merging and field verification.

## Priority logic

P0 gaps are necessary to deliver a trustworthy basic trip: complete route chain, stop and direction clarity, transfer walking, multilingual search, practical alternatives, provenance, confidence and static-service caveat. P1 improves recovery, destination approach, offline use, verified accessibility and contribution. P2 depends on data partnerships and user adoption: crowding, live tracking, predictions and richer safety context.
