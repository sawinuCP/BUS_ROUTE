# 01 — Product Vision, Users and Principles

## Vision
Make public transport in Sri Lanka easier to understand, especially for people travelling to unfamiliar places or making transfers between buses, trains and walking routes.

## Primary user groups
1. **Occasional traveller:** does not know local route numbers, stands or transfer points.
2. **Daily commuter:** wants to compare practical alternatives and reduce uncertainty.
3. **Student/new employee:** regularly travels to a new campus or workplace.
4. **Visitor/tourist:** may not understand local stop names, language variants or route conventions.
5. **Older or less confident traveller:** benefits from simple, sequential instructions.
6. **Traveller with access needs:** needs reliable information about walking surfaces, steps, lifts and accessible entrances.
7. **Journey planner/caregiver:** plans a route for another person.

## User needs
- Find a destination even if its name is typed differently.
- Know which physical boarding point to use.
- Distinguish services that share a route number but follow different patterns.
- Know when and where to transfer.
- Compare alternatives using meaningful criteria.
- Understand uncertainty instead of receiving false precision.
- Continue following a saved itinerary during temporary connectivity loss.
- Report incorrect information and see that reports are reviewed.

## Product principles
- **Action over abstraction:** show the next practical action, not only a line on a map.
- **Evidence over confidence theatre:** preserve source and verification status.
- **No fabricated transport facts:** unknown is an acceptable result.
- **Local-first naming:** support Sinhala, Tamil, English, transliteration and colloquial aliases.
- **Explicit transfer logic:** transfer edges must be verified or conservatively derived.
- **Human confirmation:** GPS assists; it does not automatically prove boarding or alighting.
- **Useful alternatives:** return meaningfully different, non-dominated routes.
- **Offline continuity:** cache the selected journey before the traveller needs it.
- **Privacy by default:** collect the minimum location and identity data required.
- **Accessibility honesty:** do not claim a route is accessible without evidence.

## Differentiation hypothesis
The market may already contain apps advertising route planning, maps, fares, tracking or local-language features. The product must prove differentiation through:
- clearer boarding-point and route-direction guidance;
- more reliable stop sequence and route-variant data;
- explicit, understandable transfer walking instructions;
- visible freshness and confidence;
- better handling of local aliases;
- practical correction and verification processes.

## Success measures
- Planning success rate within declared coverage.
- Share of returned journeys with complete stop/transfer instructions.
- Field-verified accuracy of boarding and alighting points.
- User-reported “I knew what to do next” score.
- Journey start and completion rates.
- Re-plan success after deviation.
- Data freshness by source and entity.
- Sync failure rate and time to recover.
- Incorrect-route report rate.
- API latency, crash-free sessions and battery impact.
