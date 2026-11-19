# Research References, Evidence and Validation Plan

**Purpose:** Record sources behind problem statements, competitor facts, data-source discovery and research questions. Web pages can change; retrieval date and exact source should be recorded when used for implementation.

## 1. Sri Lankan transport problem evidence

### CoMTrans Urban Transport Master Plan — Colombo Metropolitan Region and Suburbs
- Official Ministry of Transport PDF: https://www.transport.gov.lk/web/images/downloads/F-CoMTrans_Main_S.pdf
- The report describes public-transport problem categories for buses, including overcrowding, waiting when few passengers, reduced night frequency, insufficient frequency/long waiting, traffic delay, air-conditioned fare expense, staff behaviour and security concerns.
- Evidence is a home-visit survey and report from an earlier period; use as historical evidence and context, not current national statistics.

### Bus Transport Service in Sri Lanka: A Perception of Users
- University of Moratuwa repository: https://dl.lib.uom.lk/items/c14dbdc5-b39d-4bb8-80ad-f7e4cd94ab1b
- Research collects perceptions from passengers, operators and private-vehicle users in a Colombo suburban context. The abstract identifies safety, comfort, driver behaviour, noise, speed and cost-efficiency as factors affecting bus desirability.
- Related ResearchGate summary: https://www.researchgate.net/publication/378697835_Bus_Transport_Service_in_Sri_Lanka_A_Perception_of_Users
- Reported survey summary: overcrowding (73% of 86 bus users), lack of information (56%), longer travel time (49%), harassment (48%) and loud noise (47%). Treat as sample-specific percentages, not national prevalence. Obtain the full paper and inspect sampling and question wording before quoting in public materials.

### Accessibility issues to public transport in Sri Lanka
- University of Moratuwa repository: https://dl.lib.uom.lk/items/b8acca71-7f03-4f5d-8f69-e959ea396659
- 2023 research description focuses on access to public transport, walking as a common access mode and survey analysis of access-related issues.
- Use as evidence that first-mile access is a distinct problem. Full findings need review before more specific claims.

### Stressors for Bus Passengers in the City of Colombo
- University of Moratuwa abstract collection: https://uom.lk/sites/default/files/tcp/files/ISRP%20Abstracts_2020_2024%20Batch_2.pdf
- Describes a quantitative study with 350 commuter questionnaires and seven major bus routes, assessing overcrowding, delays, infrastructure, comfort and safety/stress factors across land-use contexts.
- The abstract establishes study scope, not necessarily published final results. Do not quote result values without full report.

### Public transport service quality / broader policy context
- Institute of Policy Studies occasional paper: https://www.ips.lk/wp-content/uploads/2022/06/Towards-a-Developed-Urban-Transportation-System-Lessons-for-Sri-Lanka_E_Book.pdf
- Discusses weaknesses including insufficient service turns, poor information sharing, complaint management, facilities/stop maintenance, crowding, cost/ticketing, cleanliness, road infrastructure, limited intermodal connectivity and service quality.
- This is broad policy literature and may reference historical statistics; avoid presenting dated statistics as current.

### Accessibility and missed-transport conference findings
- R4TLI conference proceedings: https://slstl.lk/wp-content/uploads/2024/06/R4TLI-2023-Conference-Proceedings.pdf
- A paper reports survey findings including access/connectivity issues, missed transport, congestion and inaccessible stops. Full paper/sample context must be reviewed before using numerical findings.

## 2. Transit data and integration research

### Development of GTFS data for Sri Lanka
- University of Moratuwa repository: https://dl.lib.uom.lk/items/9e8da31f-79c7-47a6-b96f-aa0ffbd51f36
- 2019 research describes GTFS agency, route, trip, calendar, stop, stop-time, shape, frequency and transfer files. It notes bus stop-time data limitations in the study context, with stop times derived from average speed for selected agencies. Transfer files support bus–rail transfers; dispersed stop/station locations create collection challenges.

### Stop-times development for Western Province bus transit
- University of Moratuwa repository: https://dl.lib.uom.lk/items/7c2877c7-a34a-4b84-af98-c7ea50674a17
- Explains stop sequence and stop-time generation methodology and absence of stop-by-stop scheduled times in the studied bus context.

## 3. Competitor/product evidence (feature claims, not independent quality evaluation)

### Beep Sri Lanka
- Official site: https://beep.lk/
- Google Play: https://play.google.com/store/apps/details?id=com.beeplk.beep
- App Store: https://apps.apple.com/lk/app/beep-sri-lanka/id6753198449
- Public claims include multimodal bus/train/metro planning, route alternatives, walking directions, fares, timetables, live tracking, nearby stops, popular destinations, notifications, community contributions, multilingual support and offline favourites (claims vary by page/version).
- **Competitive implication:** These capabilities are already advertised locally. Our product cannot claim novelty solely for planning bus/train routes, walking directions, fares, tracking or multilingual support. Hands-on journey testing should compare actual instruction clarity, stop/direction/transfer detail, data coverage and confidence.

### Lanka Metro Transit / LMT-GO
- Google Play: https://play.google.com/store/apps/details?id=com.lankametrotransit.lmtgo
- App Store: https://apps.apple.com/sg/app/lmt-go/id6761980523
- Public claims include live tracking, journey planning, stops, transfers, walking directions, estimated duration, fares, nearby stops, occupancy and QR payments on supported/pilot routes.
- **Competitive implication:** A network-specific digital service already has journey-planning and payment functionality. We should not overstate the gap; focus on supported-network coverage and our validated execution experience.

### Beep Metro journey planner
- https://metro.beep.lk/journey-planner
- Public page advertises origin/destination planning, fastest bus/metro/train options, fares, stops, walking and next departures for supported network.
- Product claims can change; check current app/web during formal competitor benchmark.

## 4. Data-source reference list

- NTC: https://www.ntc.gov.lk/
- NTC route map: https://www.ntc.gov.lk/Bus_info/route_map.php
- NTC permits: https://www.ntc.gov.lk/corporate/media_and_news/permit-details.php
- NTC route/permit information: https://www.ntc.gov.lk/Bus_info/time_table.php
- Geofabrik Sri Lanka OSM: https://download.geofabrik.de/asia/sri-lanka.html
- OSM public transport route export tool: https://openstreetmap.tools/public_transport_geojson/
- OSM copyright/licence: https://www.openstreetmap.org/copyright
- NSDI transport MapServer: https://gisapps.nsdi.gov.lk/server/rest/services/SLNSDI/Transport/MapServer
- NSDI transportation page: https://nsdi.gov.lk/transportation
- NSDI data services: https://nsdi.gov.lk/spatial-data-services
- NSDI FAQ: https://nsdi.gov.lk/faq
- GTFS Mobility Database LMT: https://mobilitydatabase.org/feeds/gtfs/mdb-3490
- GTFS producer download: https://api.transit.seyone.dev/api/v1/gtfs/download?agency=LMT
- BusMaps feed summary: https://busmaps.com/en/sri-lanka/Lanka-Metro/lanka-metro
- Railway official: https://www.railway.gov.lk/
- Railway schedule search: https://eservices.railway.gov.lk/schedule/searchTrain.action?lang=en
- Third-party stations cross-check: https://trains.sri.lanka.com/stations
- Community route/fare extractor: https://github.com/nave3nP/sri-lanka-transit-data
- Data.gov.lk data sharing: https://data.gov.lk/about-data-sharing

## 5. Evidence levels used in this document set

- **Published research evidence:** source directly reports a study or finding; sample, date and limitations must be stated.
- **Official-source description:** official portal/page describes available service or data; not necessarily proof of completeness or accuracy.
- **Product/competitor claim:** feature described by provider; not independently verified performance.
- **Illustrative scenario:** plausible example created to explain user problem; not observation or quote.
- **Product hypothesis:** proposed gap or feature benefit awaiting validation.

## 6. Research questions for discovery

### Travellers
- Tell me about the last journey to a place you did not know well.
- What did you use to decide where to board?
- How did you confirm the direction and correct service?
- What was the most uncertain part?
- Did you transfer? How did you find the next stop?
- What happened if the route information was wrong?
- How did you navigate the final walk?
- Which language/name did you search?
- How much walking and transfer complexity was acceptable?
- What would make you trust instructions?

### Operators/transport professionals
- How are route variants and short runs represented?
- What official route/stop sequence data exists and how is it updated?
- What can be reused/redistributed?
- How are stop names and destination boards standardized?
- What service changes are frequent and how could we receive updates?

### Field audit
- Validate actual boarding location, route board, direction, stop order, alighting, transfer path, crossing and destination entrance.
- Photograph only with privacy-safe framing and permissions where needed.
- Compare map route to actual route; record deviations and missing stops.
- Ask users to execute tasks with no verbal help and record confusion/error points.

## 7. Competitor benchmark protocol

Select 10–15 representative journeys in pilot area: direct route, one transfer, bus–rail transfer, ambiguous destination, unfamiliar landmark, large hospital/campus, long final walk, route variant, night-time planning (without safety claims), low-connectivity case. Test Beep, LMT-GO where coverage applies, Google Maps, Moovit/other relevant options where supported.

Measure—not assume:
- Did the app return a route?
- Stop location accuracy and direction clarity.
- Route variant/headsign guidance.
- Transfer walk path and next boarding detail.
- Final entrance guidance.
- Alternative comparison.
- Language support.
- Data confidence/freshness transparency.
- Failure/recovery.
- Usability task success and time.

Record date, version, screenshots only as permitted, and distinguish observed feature from marketing claims.

## 8. Suggested pilot evaluation metrics

- 20–30 journeys initially for coverage audit (number adjusted by pilot scale), with a mix of route and transfer patterns.
- 5–8 usability participants per iterative round as a starting heuristic, not a statistically representative sample; repeat with diverse groups.
- Instruction comprehension: participant correctly identifies board stop, service/direction, alight stop and transfer location.
- Completion without researcher intervention.
- Critical wrong-boarding/alighting errors.
- Time to choose route and understand first action.
- Perceived confidence before/after.
- Data defect count and correction time.
- Compare route recommendation to observed feasible route.

## 9. Research gaps / caution

This research is desk research, not a nationwide passenger survey or hands-on evaluation of every app. Published studies vary in date, sample, geography and methods. Competitor features are based on public descriptions. Quantitative coverage counts for OSM, NTC route datasets and railway layers have **not yet been measured in this documentation phase**. A reproducible data audit and field research are required before asserting exact coverage or a unique market gap.
