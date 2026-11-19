# 00 — Executive Summary and Design Decisions

## 1. Product definition
Build a Sri Lankan multimodal journey planner that helps a person understand and execute a journey, not merely see a route line. It should explain:
- how to walk from the origin to the correct stop, stand, bay or station entrance;
- which bus route or train service pattern to use, including direction and destination wording where verified;
- where to get off;
- how to walk between transfer points;
- which next service to board;
- how to reach the correct destination entrance.

## 2. Product promise
**“Know exactly what to do next during your public transport journey.”**

The word “exactly” refers to clarity of instructions when the underlying data is verified. It is not a promise of real-time service availability or guaranteed arrival times.

## 3. Baseline architecture decisions

| Area | Decision |
|---|---|
| Initial platform | Android and iOS mobile application |
| Admin | Protected web-based operations console |
| Later platform | Public web journey planner, if validated |
| Mobile stack | React Native, TypeScript, Expo development builds |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Architecture | Modular monolith with clear domain boundaries |
| Primary database | PostgreSQL + PostGIS |
| Cache | Redis when measured need exists |
| Mobile local store | SQLite for selected journeys and offline instructions |
| Maps | MapLibre React Native; provider/tiles selected after licensing and compatibility review |
| Walking routing | Evaluate Valhalla first; compare GraphHopper |
| Transit routing | Deterministic graph search over validated route/stop data |
| AI | Optional tool-calling assistant; never the routing authority |
| RAG | Not required for core journey planning |
| Data strategy | API-first hybrid: live/request APIs where suitable, canonical local data for relationships and validation |
| Data refresh | Versioned source ingestion, staging, validation, controlled publication and rollback |
| Initial live data | No assumption of live vehicle positions or complete live timetable feeds |
| Deployment | Docker-based environments; managed PostgreSQL where feasible |

## 4. Initial product scope (P0)
- Place, stop and station search.
- English/Sinhala/Tamil-ready naming and aliases.
- Bus and rail route patterns where validated data exists.
- Walking connections to/from stops and between transfer points.
- Multimodal route alternatives.
- Route variant and direction clarity.
- Step-by-step boarding, alighting and transfer instructions.
- Map and text instructions kept in sync.
- Route/data freshness and uncertainty labels.
- Internal data ingestion and source monitoring.
- Basic operational/admin capability to inspect syncs and data quality.

## 5. Follow-on scope (P1/P2)
- Active journey GPS assistance and deviation recovery.
- Offline selected-journey support.
- User issue reporting and moderated corrections.
- Saved journeys and accounts.
- Conversational AI and voice instructions.
- Live disruption and vehicle data, only if reliable feeds and rights become available.
- Fare estimates, only when current rules and effective dates are available.
- Accessibility-specific routing, only when the required infrastructure data is verified.

## 6. Critical product rules
1. Never invent a route, stop sequence, platform, boarding side, fare, timetable or transfer.
2. A geographic proximity match is not sufficient to declare a valid transfer.
3. Keep route variants and direction as separate, identifiable patterns.
4. Distinguish “mapped route exists” from “service is operating now”.
5. Show source, freshness and confidence where they materially affect a decision.
6. User reports are evidence for review, not direct edits to the production network.
7. AI may explain planner output but cannot create transport facts.
8. Preserve a known-good data version and support rollback.

## 7. Definition of a successful first release
A user can select an origin and destination inside the declared pilot coverage area, receive at least one validated bus/rail/walking itinerary where a path exists, understand each leg and transfer, and identify what is known versus unknown. The team can update the underlying transport data without manually rebuilding the application.

## 8. Assumptions to approve
- The first release is mobile-first.
- A limited pilot geography is preferable to weak national coverage.
- Guest planning is allowed; accounts are optional for saved/synchronised features.
- Exact service times are not required for the first useful release.
- The app will display only supported modes and coverage.
- Data-source licensing is checked before production reuse.
