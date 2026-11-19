# Sri Lanka-Specific Features and Differentiation

The application must be locally grounded. Localisation is not simply translating labels: the network data, route conventions, stop identity, landmarks, search, transfer context and instructions must reflect how people actually navigate Sri Lanka.

## 1. Multilingual place identity

- Search and display Sinhala, Tamil and English names where available.
- Store transliterations and colloquial/alternate names as aliases with language/script and source.
- Normalize common spelling variants, punctuation and spacing.
- Allow the user to search with a landmark, neighbourhood, town, junction or institution name.
- When names are ambiguous, show multiple candidates with locality and type; never silently choose.
- Native reviewers validate critical translated instructions.

**Example:** A stop may be stored under a formal English spelling but searched using a Sinhala colloquial name. The search result should map to the same stop while showing which name matched.

## 2. Route variants and local service patterns

- Treat route numbers as identifiers, not complete service definitions.
- Model variant paths, direction, origin/destination, partial services, limited-stop services and route-specific stop patterns when confirmed.
- Distinguish route number aliases from unrelated routes with similar labels.
- Store route board/headsign wording as verified text or alias.
- Display route and direction together.

**Example:** If a route number has full-route and short-run services, do not imply that every bus with the number reaches the final destination. The data must represent the specific pattern.

## 3. Stop, stand, terminal and side-of-road context

- Distinguish roadside stop, bus stand, terminal, bay, platform, railway station and informal/verified boarding location.
- Include stop side or access point only when mapped/verified.
- Record nearby landmarks, junctions and recognizable buildings.
- Provide stop photos only when rights/consent and safety/privacy considerations are met.
- Support alternative stops for the same route where users may board.

**Example:** “Board at the stand inside the terminal” is materially different from “board at the roadside stop opposite the terminal.” The app should capture that distinction only when verified.

## 4. Local landmark-based instructions

Landmarks can make a stop recognizable, but the app must not invent them. Use curated verified landmarks, map POIs and contributor observations with provenance.

Instruction template: “Walk approximately [distance] toward [landmark/road], then use [verified access point] to reach [stop name].”

## 5. Transfer guidance designed for local interchanges

- Connect bus stands, roadside stops, railway stations and nearby stops with pedestrian network paths.
- Explain transfer walking distance and direction.
- Identify whether transfer is within a station/terminal or outside it.
- Record crossings, stairs, platform/stand changes and access barriers only when verified.
- Provide a clear next service identifier and destination/direction.

## 6. Tourist and unfamiliar-place support

- Curated destination categories: heritage, beaches, wildlife, religious sites, museums, hospitals, campuses, government services, terminals.
- Search with destination names and local aliases.
- Explain the final walk to the correct public entrance, not merely a centroid.
- Offer language switching independent of device language.
- Low-jargon instruction and voice-readout.
- Optional trip sharing for trusted contacts.
- Clearly distinguish route-network knowledge from departure-time knowledge.

## 7. Local service-type and fare context

- Where verified, identify ordinary, express, semi-luxury, air-conditioned, long-distance, limited-stop or other relevant service classes.
- Store fare source, effective date, route/variant and fare class.
- Do not infer fare from a route number or display stale prices as current.
- Do not make ticket/payment feature promises without operator partnership and technical/legal confirmation.

## 8. Sri Lankan transport mode scope

**Initial:** Bus and pedestrian access. Railway included corridor-by-corridor only where station, line and sequence data are verified.  
**Potential later:** Metro bus/digital bus services where reliable data exists, intercity/express services, other public modes where data is available and routing rules are understood.

The app must avoid treating every mapped road or route as a currently operating public service.

## 9. Local data validation strategy

- Pilot selected corridors and transfer nodes.
- Collect stop photos/field observations with privacy safeguards.
- Verify route board/direction and stop sequence with multiple evidence types.
- Compare official records, OSM, community reports and field observation.
- Document discrepancies rather than silently merge.
- Prioritize high-use destinations and corridors, not an unrealistic “island-wide complete” claim.

## 10. Accessibility and safety context

Sri Lankan-specific physical conditions may include uneven footpaths, missing footpaths, roadside boarding, crowded terminals, crossings and varied station access. The product should record factual attributes where verified and provide filters/preferences. It must not label locations or routes “safe,” “unsafe,” “accessible” or “inaccessible” based on assumptions or anecdotal reports alone.

## 11. Local terminology and instruction style

Maintain a reviewed vocabulary for common terms (bus stand, stop, junction, station, platform, terminal, destination board, route variant, etc.) in Sinhala, Tamil and English. Avoid overly formal translations that travellers do not use. Test short instructions with native speakers and users in the pilot corridor.

## 12. Competitive differentiation caution

Beep publicly advertises bus/train/metro multimodal planning, walking directions, fares, tracking, timetables, crowd-related/community features and multilingual support; LMT-GO advertises journey planning, stops, transfers, walking directions, estimated time, fares and QR payment in its supported network. These are strong local examples, so our differentiation cannot honestly be “we have journey planning” or “we combine bus and train.” The measurable opportunity is superior coverage/accuracy for the selected pilot, actionable execution instructions, clear route-variant/transfer context, transparent confidence, and field validation—if testing proves those are better.
