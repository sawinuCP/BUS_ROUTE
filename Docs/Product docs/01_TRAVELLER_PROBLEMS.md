# What Sri Lankan Travellers Are Actually Struggling With

**Purpose:** Understand the real-world problem space before designing features.  
**Evidence status:** Research-backed themes + hypotheses to validate.  
**Important:** Examples below are realistic illustrative scenarios, not verbatim interviews or claims that a specific event occurred.

## 1. The travel task is more than choosing a vehicle

A traveller must solve several linked tasks: locate the correct access point; identify a usable service; understand direction and route variant; board; recognize when to alight; transfer safely and efficiently; and reach the final entrance. A route may be technically valid but still fail a user if one of these actions is ambiguous.

## 2. Problem themes

### P1 — Fragmented and hard-to-discover transport information

**What people face:** Route information is spread across route maps, operator/agency information, fare notices, stop signs, informal advice, web pages, social posts, apps and personal knowledge. A traveller may not know which source is current or where to begin.

**Why this is a problem:** A person needs to assemble a coherent journey from pieces of information, compare conflicting names, and decide whether the source is trustworthy. The burden is high for unfamiliar trips.

**Illustrative example:** Someone in a suburb needs to attend an appointment in a different town. They know a nearby bus route number but not whether it reaches the destination, whether they must change buses, or where to find the next service. They search several sources and still ask a friend or conductor.

**Evidence:** Sri Lankan research and policy literature describe poor information sharing as a public transport service weakness. A 2019 University of Moratuwa GTFS study notes the difficulty of assembling route, stop-time and transfer data; bus stop times were not generally available and had to be estimated for its study. This is evidence of fragmented transit data, not proof that every traveller lacks information.

### P2 — Uncertainty about which stop to use and where it is located

**What people face:** Stop names may be colloquial, shared, inconsistent, abbreviated, or represented by nearby landmarks. A map pin can be on the wrong side of a road, at a junction, or far from the actual boarding point. Some services may board at a stand, terminal, roadside stop or different location depending on direction.

**Why this matters:** The user can arrive at a visually plausible place but still be at the wrong stop. In busy areas, crossing a road, finding a stand, or walking to the correct platform is itself a task.

**Illustrative example:** The plan says “Town bus stop.” The traveller sees two stops near a junction and boards at the one opposite the required direction. A generic pin does not explain which side or landmark confirms the boarding location.

**Evidence:** Accessibility research in Sri Lanka identifies access to public transport as a distinct challenge, with walking commonly used to reach services. Location accuracy and stop-side detail are product hypotheses requiring local field validation.

### P3 — Route number is not enough: direction, destination board and service pattern

**What people face:** Knowing a route number alone may not resolve which direction to board, whether a bus is short-working, whether the route has variants, or whether a service terminates before the desired stop. Route labels, destination boards, service type and local names can differ.

**Why this matters:** Two services with similar route numbers or route names may have different stopping patterns. A user may board a service that follows part of the route but does not reach the intended alighting point.

**Illustrative example:** A traveller is told to take “Route 100” but sees a bus with a familiar route number and a destination board that indicates a short-run or different endpoint. The user is not confident whether it is correct and either misses it or boards incorrectly.

**Validation needed:** Catalogue real route variants, partial services, destination-board wording and direction conventions corridor by corridor.

### P4 — Transfer uncertainty and interchange friction

**What people face:** A transfer is not simply a line change. The user must alight at the right place, find the next stop/stand/platform, understand the walking connection, cross safely if necessary, and know which service/direction to board.

**Why this matters:** Transfer instructions can be the most cognitively demanding part of a journey. A route planner may suggest a transfer that is geographically close but operationally confusing or inconvenient.

**Illustrative example:** The app says “Change at Junction X.” The user alights but the next bus stop is across a busy road or around a block. Without a landmark or pedestrian path, they may follow the road edge, cross at an unsafe point, or abandon the transfer.

**Evidence:** Sri Lankan GTFS research explicitly discusses transfer files for bus–rail connections and notes that bus stops and railway stations may be dispersed, making transfer-location collection a challenge.

### P5 — Walking access and last-mile/first-mile difficulties

**What people face:** Public transport rarely provides door-to-door access. The journey includes walking to a stop and from the final stop to the destination. Pedestrian infrastructure can be discontinuous, uneven, obstructed, poorly marked, or difficult to interpret. Distance alone does not communicate effort or safety.

**Why this matters:** A route with fewer bus minutes may require a long, difficult or confusing walk. A user may need to choose an alternative with a shorter walk or a better pedestrian connection.

**Illustrative example:** A route is ranked first because it has one bus and a 900 m final walk. The destination entrance is on a different street and the walk involves a difficult crossing. The user would have preferred a route with a second bus and a shorter final walk.

**Evidence:** Sri Lankan accessibility research specifically examines access to public transport and walking access. Physical accessibility attributes are incomplete and must not be guessed.

### P6 — Long, uncertain waiting and lack of certainty about service availability

**What people face:** A static route map tells the user that a route exists but not whether it is running at the time, how frequently it operates, or whether the wait is reasonable. Service frequency can differ by time, day and corridor.

**Why this matters:** Without schedule or real-time data, a plan can be network-valid but operationally unavailable. The user may make a costly or time-consuming trip based on an assumption.

**Illustrative example:** The app recommends a bus connection based on route geometry. The traveller arrives and discovers that the route operates infrequently or is not operating at that moment.

**MVP response:** Do not claim a departure time or “running now” status. Label plans as network-based, show estimated travel time with caveats, and where available show the source's service pattern or verification date. Timetables/live data are future scope.

### P7 — Delays, congestion and travel-time unpredictability

**What people face:** Road traffic, weather, incidents, stop dwell time, boarding conditions and service variation make travel times uncertain. Static estimates may be inaccurate.

**Why this matters:** A user may be late for work, an appointment or a connection. The route planner should avoid presenting estimates as guarantees and should eventually account for real-world variability.

**Evidence:** CoMTrans Colombo urban transport report lists bus problems including crowding, waiting, lower night frequency, insufficient frequency and traffic delays. These are historical study findings, not current measured levels for every corridor.

### P8 — Crowding, boarding difficulty and service comfort

**What people face:** Crowding may prevent boarding, create discomfort, make it hard to move toward the door, or make it difficult to alight at the intended stop. Users may prefer a less crowded or easier option even if it is slower.

**Why this matters:** Route choice is multi-criteria. “Fastest” alone may not be the best route for a person with luggage, children, mobility constraints or a preference for comfort.

**Evidence:** A Sri Lankan bus-service perception study reported overcrowding as the leading issue among surveyed bus users (73% of 86 bus-user respondents), followed by lack of information (56%), longer travel time (49%) and harassment (48%). The sample/context must be read from the paper; do not generalize these percentages to the whole country.

### P9 — Personal safety and harassment concerns

**What people face:** Users may be concerned about harassment, theft, unsafe waiting locations, walking in poorly lit areas, crowding or unfamiliar locations, particularly at night or when travelling alone.

**Why this matters:** Safety affects route choice, willingness to walk, wait or transfer, and whether the person uses public transport at all.

**Product boundary:** The app cannot certify a route as safe. It may allow cautious route preferences, verified lighting/footpath information where available, trusted sharing, emergency resources and reports—but must avoid stigmatizing places or falsely assuring safety.

**Evidence:** User-perception research includes harassment and security as reported service issues. Safety-feature effectiveness needs user research and ethical design.

### P10 — Unfamiliar destinations and confusing final approaches

**What people face:** The final stop may be close to a destination by distance but not by entrance. Large hospitals, universities, offices, malls, temples, government buildings, campuses and event venues can have multiple entrances or confusing internal access.

**Why this matters:** “Get off near X” may not complete the journey. The traveller needs a practical last approach, ideally to the correct entrance or public access point.

**Illustrative example:** A user is going to a hospital appointment. The bus stop is near the hospital boundary, but the appointment entrance is on the opposite side. The user needs a final walking path and entrance label, not just a destination pin.

### P11 — Language, transliteration and naming friction

**What people face:** Place names may be used in Sinhala, Tamil, English, transliterated spellings, shortened local names, or names of nearby landmarks. Search may fail when the user does not know the official spelling.

**Why this matters:** The user may not find the stop or destination, misread instructions, or be forced to use a language they are less comfortable with.

**Illustrative example:** The traveller searches using a familiar Sinhala name while the dataset contains only an English transliteration. The location is not found even though it exists.

### P12 — Fare and service-type uncertainty

**What people face:** Fare information may vary by route, distance, service type, fare revision, and source date. Users may need to compare ordinary, express, semi-luxury, air-conditioned, or other service types where such categories apply.

**Why this matters:** Price affects route choice and confidence. A stale fare can mislead users or cause disputes.

**MVP:** Show fare only if a source and effective date are recorded and the fare calculation is supported. Otherwise show “fare not verified” rather than an invented estimate.

### P13 — Accessibility and inclusive travel information is insufficient

**What people face:** People with reduced mobility, older travellers, parents with strollers, travellers with luggage, or those with sensory needs may need information about stairs, ramps, surface quality, crossings, seating, platform access and walking distance.

**Why this matters:** A route may be technically possible but not usable for an individual. Accessibility cannot be represented by a generic “accessible” badge without evidence.

**MVP:** Allow user preferences and filter out known barriers only when verified data exists. Provide a clear unknown/not-confirmed status.

### P14 — Poor fallback when a journey goes wrong

**What people face:** Missing a stop, boarding the wrong service, a route not appearing, losing connectivity, or an unexpected transfer can leave a traveller unsure what to do next.

**Why this matters:** A journey planner that only describes the ideal path is brittle. A real travel companion needs recovery actions.

**Illustrative example:** The user misses the planned alighting stop. They need to know whether to exit at the next stop and re-plan, rather than panicking or blindly retracing.

### P15 — Trust, freshness and data-quality ambiguity

**What people face:** Route data can be outdated, incomplete, inconsistent or crowdsourced. A user often cannot tell whether a route or stop was recently checked or how the information was obtained.

**Why this matters:** Trust is a product feature. If one incorrect instruction causes a failed trip, the user may stop relying on the application.

**MVP:** Every core route/stop/transfer record should retain provenance, retrieval/verification date, confidence, and an issue-report path. Display freshness selectively without overwhelming the UI.

### P16 — Information overload and lack of actionable guidance

**What people face:** Maps, long stop lists, route codes and dense schedules may be difficult to translate into an action while standing in a busy environment.

**Why this matters:** A user needs a simple next step at the moment of travel, with detail available on demand.

**Illustrative example:** The user sees a route map with two lines and many stop names but cannot identify the immediate boarding instruction. A “Next action” card should say what to do now.

## 3. Problems are not all solved by an app

The application can reduce information uncertainty, help plan, and support decisions. It cannot directly fix overcrowding, driver behaviour, infrastructure, service frequency, road congestion, harassment or the physical condition of stops. We must avoid positioning software as a solution to systemic transport problems.

## 4. Initial prioritization

**High product relevance / likely MVP:** information discovery, stop identification, direction and route variants, transfer guidance, first/last mile, destination entrance, route comparison, uncertainty and data freshness, multilingual search, recovery and offline itinerary.

**Potential later value / data-dependent:** live availability, crowding, delay predictions, safety context, accessibility details, fare comparison, community reports, service alerts.

**Outside app control:** fleet supply, road congestion, physical infrastructure, enforcement, service quality and operator policy.

## 5. Research to validate

Conduct interviews with daily commuters, occasional travellers, students, tourists, people travelling to hospitals/appointments, older travellers, people with access needs and bus/train operators. Ask for a recent real journey, not only opinions: where they searched, what confused them, what they did, what failed, time/cost impact, and how they knew they were at the correct stop. Observe real journeys with consent. Record the corridor, mode, situation and evidence without retaining unnecessary personal information.
