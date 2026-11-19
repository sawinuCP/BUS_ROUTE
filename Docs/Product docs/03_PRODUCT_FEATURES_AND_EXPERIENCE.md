# Product Features & Traveller Experience

**UX objective:** The traveller should always understand (1) where they are in the journey, (2) what they should do now, (3) how to recognize the next place/service, and (4) what to do if the plan is uncertain or changes.

## 1. Main experience architecture

1. **Home / Plan** — origin and destination search, current location, recent/favourite journeys, destination shortcuts.
2. **Route results** — practical alternatives and transparent trade-offs.
3. **Journey overview** — ordered legs and map; user chooses start.
4. **Journey mode / Travel companion** — step-by-step execution with one current action.
5. **Recovery** — missed stop, wrong bus, unexpected stop, transfer failure, connectivity loss.
6. **Saved / Recent** — repeat trips, editable destinations, saved places.
7. **Report / Contribute** — correct errors or add field observations.
8. **Settings / Accessibility / Language / Privacy**.

## 2. Feature inventory (comprehensive candidate set)

### A. Search and trip planning — P0

- Origin and destination fields with autocomplete.
- Use current location (permission on demand) and manual map pin.
- Search by address, POI, stop, station, route alias, landmark and local name.
- Sinhala, Tamil, English and transliteration/alias search.
- Recent searches and favourites.
- Reverse origin/destination.
- “Choose on map” for ambiguous places.
- Search results disambiguation (town vs stop vs building vs entrance).
- Destination sub-location selection for hospitals, campuses, terminals, large sites.
- Avoid forcing login for core planning.

**Experience gain:** Users can start with what they know, including a familiar landmark or local name, rather than needing an exact official name.

### B. Route options and comparison — P0

- Generate multiple practical route alternatives.
- Alternative labels: fastest estimated, least walking, fewest transfers, lower fare (only when verified), simplest/easiest (criteria visible).
- Total estimated duration and uncertainty/range.
- Total walking distance/time.
- Number of transit legs/transfers.
- Fare estimate and fare-data date, or “not verified.”
- Service modes (bus, rail; future additional modes).
- Route/stop data confidence and key caveat.
- Compare trade-offs without claiming the one route is universally best.
- Filter by maximum walking distance, transfers, modes and verified accessibility attributes.
- Map preview and itinerary summary.

**Experience gain:** Users choose based on their needs rather than being forced into fastest-only optimization.

### C. Leg-by-leg instruction detail — P0

Every itinerary is structured into legs and actions.

**Walking leg:**
- Start/end labels, distance and estimated duration.
- Pedestrian path geometry, turn/landmark instructions where supported.
- Crossing notes only if verified; avoid suggesting unsafe crossing.
- Stop entrance/platform/stand identification.
- Unknown or low-confidence path warning.

**Transit leg:**
- Mode and route number/name.
- Operator/service type if known.
- Board at stop, stop-side/stand/platform if verified.
- Direction/headsign/destination wording.
- Ride segment and number of stops where sequence is reliable.
- Alight stop name/aliases, landmark and “watch for” guidance.
- Fare and source if verified.
- Route variant warning if applicable.

**Transfer leg:**
- Where to alight.
- Transfer walk distance/time.
- Connector map and path.
- Next boarding location and identification cues.
- Next route/direction.
- Buffer/uncertainty.

**Experience gain:** The plan is executable, not just visual.

### D. Journey mode / active guidance — P0

- Prominent “Do this now” action card.
- Current step and journey progress.
- Next step preview.
- Map with current leg highlighted.
- Stop/route details accessible on tap.
- Large readable text and high contrast.
- Voice readout of current and next step.
- Optional step alerts when approaching alighting (initially may be manual; GPS alerts only when validated and permission granted).
- “I am at this step,” “I got off,” or “skip/confirm” actions where user confirmation is safer than automatic detection.
- Pause/end journey.
- Share journey link/details with explicit privacy choice.
- Keep screen awake option, user-controlled.

**Experience gain:** Reduce memory burden and the need to repeatedly inspect the entire route while travelling.

### E. Stop identification and local context — P0/P1

- Stop pin, name and aliases.
- Route direction and served route variants.
- Landmark context.
- Photo/reference image only with permission and clear provenance.
- Stand/bay/platform information when available.
- Stop-side/road-side description when verified.
- Nearby stops and alternative boarding locations.
- “This stop is unverified” status.

### F. First/last-mile walking — P0

- Walkable network routing, not straight-line routing.
- Distance/time and path.
- Landmark/turn guidance when map data supports it.
- Maximum walking filter.
- Final destination entrance selection.
- Avoid stairs/step-free preference only when route attributes are verified.
- Report missing footpath/path obstruction.

### G. Destination and POI support — P1

- Major destinations curated by category: hospitals, universities, government offices, tourist attractions, terminals, shopping areas, places of worship, etc.
- Destination entrances, internal access notes where validated.
- “Popular destination” cards.
- Saved places.
- Share destination pin.

### H. Recovery and exception handling — P1

- Missed alighting stop: re-plan from current location; give safe, simple next action.
- Wrong route/vehicle: re-plan and explain not to assume return route.
- Missed transfer: search feasible next options; if timetable absent, clearly indicate service availability is not verified.
- Route/stop unavailable: alternate plan, or explain data gap.
- Network loss: continue cached itinerary and mark live features unavailable.
- Location permission denied: manual location and map-pin options.
- GPS uncertain: ask user to confirm area, avoid automatic step change.
- “I need help understanding this step” contextual explanation.

### I. Language and accessibility — P0/P1

- English, Sinhala and Tamil UI and instruction templates.
- Search across language aliases and transliteration.
- Native-reviewed translations, not machine-only for critical directions.
- Voice/read-aloud instructions and adjustable speech.
- Text size, high contrast, accessible controls, screen-reader labels.
- Low-complexity instruction style.
- Walking distance limit and avoid stairs preferences.
- Honest unknown access status.

### J. Data quality and trust — P0

- Source and verification timestamp for critical route facts.
- Confidence status (Verified, High, Medium, Low, Unverified) defined in data policy.
- User report button per route/stop/transfer/step.
- Route coverage limitations.
- Fare validity date.
- “Service times not checked” static-network notice.
- Feedback acknowledgement and report status if feasible.

### K. Community validation — P1

- Report route missing/incorrect.
- Confirm stop name/location.
- Report transfer connector.
- Suggest landmark/alias.
- Report accessibility attribute.
- Optional photo upload with consent, privacy reminders and moderation.
- Contributor trust levels; avoid rewarding quantity over quality.
- Field verification tasks.
- Moderation and audit history.

### L. Offline and low-connectivity — P1

- Cache selected itinerary and instruction text.
- Cache route/stops needed for active trip.
- Map asset caching only within tile-provider licence.
- Offline status and cached-data timestamp.
- Manual progress tracking when GPS/network unavailable.
- Re-sync feedback/report when connectivity returns.

### M. Personalization — P1/P2

- Default walking speed preference (not medical inference).
- Max walk distance.
- Transfers preference.
- Modes allowed.
- Fare sensitivity.
- Avoid stairs/step-free only based on known attributes.
- Language and voice settings.
- Saved commuter routes and quick plan.
- Favourite stop/landmark.

### N. Future service intelligence — P2, dependent on verified feeds

- Timetable and departure selection.
- Live bus/train positions.
- Estimated arrivals.
- Delay and disruption notices.
- Missed connection prediction.
- Crowd estimates/reports.
- Fare comparison and ticket/booking integration where partnership and rights permit.
- Trip share with live location only during user-started session.

## 3. Recommended journey result design

Each card should contain:
- Estimated total duration (range or uncertainty-aware label).
- Total walk.
- Transfers.
- Transit leg count.
- Verified fare only when applicable.
- Mode icons.
- Trade-off label and short explanation.
- Confidence/coverage note if materially low.

Avoid: false precision, too many alternatives, badges unsupported by data, or ranking a route as “safe.”

## 4. Recommended active trip screen

**Current action:** “Walk to [boarding stop]. Approx. 280 m / 4 min.”  
**Recognition:** “Look for the stop beside [verified landmark].”  
**Next:** “Board route [number] toward [verified headsign].”  
**Progress:** Step 1 of 6; Leg 1 of 4.  
**Controls:** Map; full itinerary; voice; report issue; re-plan; share trip; end.

The active step must be derived from itinerary state and confirmed user/GPS signals. GPS alone should not silently advance through critical steps when accuracy is low.

## 5. Feature prioritization

### P0 — MVP

- Search origin/destination, aliases, map selection.
- Bus and walking route planning, railway where validated.
- Route variants and ordered stops.
- Transfer connector paths.
- Multiple practical alternatives.
- Detailed leg instructions.
- Active journey mode with manual progress.
- Estimate caveats and data confidence.
- Sinhala/Tamil/English foundational support.
- User feedback/report.
- Basic offline selected trip.
- Privacy controls and no-account planning.

### P1 — Pilot improvements

- Destination entrances and curated POIs.
- Voice guidance.
- Recovery/re-plan flows.
- Accessibility filters based on verified attributes.
- Saved journeys, quick plans, contributor/field verification.
- Offline maps if provider licence permits.
- More route corridors and coverage dashboard.

### P2 — Network maturity

- Timetables, live tracking, arrival prediction.
- Crowding reports, service alerts.
- Fare integration and partnerships.
- Advanced safety-context features, carefully validated.
- Additional modes and intercity/long-distance support.

## 6. Experience principles

- **One action at a time:** current instruction is visually primary.
- **No surprises:** show transfers, walking and unknowns before starting.
- **Confidence visible:** uncertain instructions are not written as facts.
- **Progress:** indicate where the traveller is in the plan.
- **Recovery is normal:** re-planning is easy and non-judgmental.
- **Language is local:** allow the user to choose instruction language.
- **Privacy is explicit:** location and sharing are opt-in and understandable.
