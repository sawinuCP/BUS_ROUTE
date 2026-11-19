# 17 — Open Questions and Pre-Implementation Checklist

The architecture is sufficiently defined to begin a discovery/prototype phase, but the following decisions should be confirmed before committing to full implementation.

## A. Product decisions
1. **Pilot geography:** Which area should be supported first (e.g. Colombo metropolitan area, a selected corridor, or another district)?
2. **Primary user:** Daily commuters, occasional travellers, students, tourists, or a balanced group?
3. **Platforms:** Confirm Android and iOS first. Is a web planner required in the first release?
4. **Accounts:** Should core planning be guest-accessible, with accounts only for saved journeys and sync?
5. **Languages:** Confirm English, Sinhala and Tamil for first release, and who will review transport terminology.
6. **Brand/product name:** Is there an existing name, identity or design system?

## B. Transport scope
7. **Modes:** Confirm bus + rail + walking as initial modes. Should three-wheelers, taxis or park-and-ride be excluded?
8. **Bus coverage:** Is the first release focused on SLTB, private buses, interprovincial buses, or all validated sources?
9. **Rail:** Should rail be included in the first pilot, or added after bus/walking data is validated?
10. **Timetables:** Confirm that exact timetable and live arrival predictions are not MVP requirements.
11. **Fares:** Should fares be excluded initially unless source and effective date are reliable?
12. **Active journey:** Is GPS-assisted progress required in the first public release, or can it follow the core planner?

## C. Data and legal
13. **Source access:** Can the project obtain permission or suitable licences for any official/private feeds that require it?
14. **OSM use:** Confirm attribution and ODbL obligations for any derived database/distribution.
15. **NSDI layers:** Confirm each layer's specific reuse/redistribution terms.
16. **NTC and railway data:** Confirm whether structured feeds or written access can be obtained; public pages are not proof of a complete API.
17. **Field validation:** Who can verify stop sides, stands, route variants and transfers on the ground?
18. **Update cadence:** Who owns each source and what freshness threshold is acceptable?
19. **Data hosting:** Which cloud/hosting region and data residency constraints apply?

## D. Technical and operational
20. **Map provider:** Is a paid tile/geocoding provider acceptable, or is self-hosting preferred?
21. **Budget:** Monthly infrastructure and provider budget?
22. **Team:** Number of developers and their experience with React Native, Python, GIS and data engineering?
23. **Admin access:** Who can review and publish transport data?
24. **Availability target:** What uptime and support expectations are required for the pilot?
25. **Analytics:** Which privacy-preserving product metrics are acceptable?

## E. Suggested defaults if no preference
- Pilot: a small set of high-demand Colombo-area corridors, subject to data audit.
- Mobile: Android and iOS via React Native.
- Web: admin console only at first.
- Modes: walking + bus first; rail included if station/line/transfer data passes validation.
- Guest planning: yes.
- Timetables/live tracking/ticketing: excluded from MVP.
- Fares: omit unless verified and effective-dated.
- AI: after deterministic planner works.
- Deployment: Docker + managed PostgreSQL/PostGIS; no Kubernetes initially.
- Data: source-aware versioned sync with manual review for high-risk changes.

## Approval checklist
- [ ] Pilot geography and initial corridors approved.
- [ ] Primary user group and MVP scope approved.
- [ ] Platforms and languages confirmed.
- [ ] Data-source rights and ingestion methods documented.
- [ ] Walking/map provider evaluation completed.
- [ ] Field verification owner identified.
- [ ] Hosting and budget agreed.
- [ ] Admin/data publishing roles agreed.
- [ ] User stories reviewed and prioritised.
- [ ] Phase 0 exit gate accepted.

## Can implementation begin?
**Yes, Phase 0 discovery and technical spikes can begin now.** Full feature implementation should wait until the pilot area, data rights, source coverage and validation ownership are confirmed. These are the largest risks to the product's core promise.
