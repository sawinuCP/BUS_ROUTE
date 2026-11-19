# Sri Lanka Journey Planner — Documentation Index & Product Vision

**Status:** Product discovery / pre-development foundation  
**Version:** 0.1 — research draft  
**Scope:** Sri Lanka, multimodal public transport + pedestrian access  
**Primary product promise:** Turn a destination into a practical, understandable, step-by-step journey that a traveller can follow confidently.

## 1. Product vision

Build a Sri Lankan journey-planning companion that helps people understand not only *which combination of transport might get them there*, but **exactly how to execute the journey**: where to walk, which side/stop to use, which service or route to board, what destination sign or direction to look for, where to get off, how to make a transfer, and how to complete the final walk.

The product should make unfamiliar public transport feel navigable for first-time travellers, occasional travellers, tourists, students, workers, older users, and people travelling to appointments or unfamiliar destinations. It should also be useful for regular commuters who want to compare practical alternatives.

### Core principle

> A route suggestion is not a successful journey plan unless the traveller can understand and carry out every leg, including access, boarding, alighting, transfers, and the final approach to the destination.

## 2. Product positioning

This is not merely a map, timetable browser, route-number directory, or AI chatbot. It is a **journey execution guide** built on a validated multimodal network and a human-readable instruction layer.

The initial experience is based on static route structure, stop order, route geometry, walking connections, transfer possibilities, and destination landmarks. Exact timetables, vehicle tracking, live service status, booking and payments are deliberately not prerequisites for the first version.

## 3. Product goals

1. Help users discover practical public-transport combinations from origin to destination.
2. Explain each segment in actionable language rather than only drawing a route line.
3. Present a small, meaningful set of alternatives (fastest estimated, least walking, fewest transfers, lower-cost when fares are reliable, and easiest/most confidence-inspiring).
4. Reduce uncertainty around stop choice, route direction, boarding, alighting, transfer location and final walking.
5. Use Sri Lankan place names, transliterations, route naming conventions, landmarks and transport context.
6. Make data confidence and freshness visible; avoid inventing service facts.
7. Improve through field verification and structured traveller feedback.
8. Build a scalable, auditable data pipeline with source attribution and legal reuse checks.

## 4. Non-goals for initial release

- Guaranteed arrival times or schedule-based trip optimization when no validated timetable exists.
- Live bus/train GPS tracking or predictions.
- Ticket purchasing, QR payments, seat reservation, or operator dispatch.
- Claiming that every bus in the country is covered.
- Exhaustively enumerating every combinatorial route. Return practical, non-dominated options.
- Using generative AI to invent routes, stops, route numbers, fares, operating hours or transfer facts.
- Replacing official operators or government transport services.

## 5. Intended user groups

- **First-time/occasional public transport traveller:** needs reassurance and simple instructions.
- **Daily commuter:** needs alternatives, walking/transfer trade-offs and repeatable saved journeys.
- **Student / new worker:** budget-sensitive, learns unfamiliar corridors and interchange locations.
- **Tourist / visiting relative:** needs multilingual names, landmark context, low jargon, confidence and practical instructions.
- **Traveller with mobility, visual, hearing or other access needs:** needs filters and honest access attributes; this cannot be guaranteed without verified infrastructure data.
- **Caregiver / accompanying traveller:** may plan a route for someone else and share instructions.

## 6. Product principles

### Actionable over abstract
Say “Walk approximately 350 m along [verified street/landmark] to the stop on the [verified side]” rather than “walk to stop A” when the extra detail is supported.

### Explain uncertainty
Separate confirmed data, estimated walking/time, user reports and unknown information. Never use confidence styling to hide poor coverage.

### Local language first-class
Support Sinhala, Tamil and English UI and instructions, including place aliases, route names, transliteration search, and graceful mixed-language results.

### Low cognitive load
Show one current action prominently, with a progress view and the full itinerary available. Avoid dumping a long list of stops on the user.

### Privacy by default
Location is sensitive. Request it only when needed, offer manual search, explain permissions, minimize retention, and avoid exposing a user's journey or live location by default.

### Resilient and usable on weak connectivity
Cache active itinerary, route details, map tiles where legally and technically permitted, and critical instructions. Show what is offline and what may be stale.

## 7. Product success measures

- Successful journey completion (self-reported, optional and privacy-conscious).
- Percentage of journeys where user can identify correct boarding stop, route/direction and alighting stop.
- Route/stop instruction error rate from field audits.
- Search-to-route-result success rate.
- Route-result usefulness rating; alternative selected rate.
- Transfer instruction comprehension.
- Data coverage by pilot corridor: mapped route variants, ordered stops, stop coordinates, route shape, transfer links, source and verification status.
- Rate of reports resolved; age of stale records.
- Crash-free sessions, response time, offline itinerary availability.
- Accessibility and language task success.

Metrics must not encourage false precision or collect unnecessary user movement histories.

## 8. What differentiates the product

Potential differentiators—subject to user validation and data feasibility—are the quality of the **journey instructions and execution support**, not the existence of route planning itself:
- Explicit “board here / ride this direction / get off here” actions.
- Transfer guidance that explains where to walk and how to identify the next boarding point.
- Sri Lankan local landmark and stop-name aliases.
- Route variants and partial services represented correctly.
- Confidence, freshness and source transparency.
- Multilingual instructions and voice-friendly short phrases.
- Field-verified access paths and contributor workflow.
- Recovery guidance if the traveller misses a stop or transfer.

Existing local products already advertise multimodal planning, fares, stop lists, walking directions, tracking and notifications. We should not assume those are absent in the market. Our opportunity must be demonstrated by a comparative hands-on test and traveller research.

## 9. How this documentation is organized

- [01 Problems and traveller research](01_TRAVELLER_PROBLEMS.md)
- [02 Gap analysis](02_PROBLEM_GAP_ANALYSIS.md)
- [03 Product features and experience](03_PRODUCT_FEATURES_AND_EXPERIENCE.md)
- [04 Sri Lanka-specific differentiation](04_SRI_LANKA_SPECIFIC_FEATURES.md)
- [05 User stories and flows](05_USER_STORIES_AND_FLOWS.md)
- [06 Technical architecture](06_TECHNICAL_ARCHITECTURE.md)
- [07 Data strategy and sources](07_DATA_SOURCES_AND_ACQUISITION.md)
- [08 Scope, roadmap, decisions and risks](08_SCOPE_ROADMAP_AND_RISKS.md)
- [09 Research evidence and validation](09_RESEARCH_REFERENCES_AND_VALIDATION.md)

## 10. Important evidence qualification

This document set combines published research, official data-source descriptions, competitor feature claims and **illustrative journey scenarios**. Illustrative scenarios are not presented as direct quotations or observed individual experiences. Several issues are supported by Sri Lankan research, but product-specific pain points—especially route-direction confusion, transfer uncertainty, stop-side ambiguity, and the usefulness of detailed instructions—must be validated through interviews, field observations and usability tests before treating them as proven universal problems.
