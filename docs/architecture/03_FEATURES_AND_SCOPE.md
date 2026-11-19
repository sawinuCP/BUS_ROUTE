# 03 — Feature Catalogue and Scope

Priority: **P0** first useful release; **P1** important follow-on; **P2** later or conditional.

## A. Search and place resolution
- **F01 Origin/destination search (P0):** search towns, localities, landmarks, addresses and map points. Present disambiguation when multiple candidates are plausible.
- **F02 Stop/station search (P0):** find stops, stands, bays, platforms, terminals and station entrances.
- **F03 Multilingual aliases (P0):** canonical entity with Sinhala, Tamil, English, transliteration and colloquial aliases.
- **F04 Nearby stops (P1):** opt-in location; rank using walkable distance, not straight-line distance alone.
- **F05 Manual map selection (P0):** allow origin/destination selection if search fails.

## B. Journey planning
- **F06 Multimodal planner (P0):** combine supported walking, bus and rail legs.
- **F07 Route variants/directions (P0):** preserve route pattern, direction and service type.
- **F08 Alternatives (P0):** return a small set of non-dominated options.
- **F09 Preference ranking (P0):** fastest estimated, least walking, fewest transfers, simplest.
- **F10 Duration estimates (P0):** component-level estimates/ranges; no implied real-time guarantee.
- **F11 Fare information (P1):** show only when source, fare type and effective date are known.
- **F12 Coverage explanation (P0):** explain if a mode or area is unsupported.

## C. Step-by-step guidance
- **F13 Walk to boarding point (P0):** path geometry, distance and simple landmarks where verified.
- **F14 Board correct service (P0):** route, direction, destination wording and boarding point.
- **F15 Alight at correct point (P0):** named stop/station and verified recognition cues.
- **F16 Walk transfer (P0):** explicit pedestrian route between access points.
- **F17 Final approach (P0):** walk to destination coordinate; verified entrance when available.
- **F18 Map/text synchronisation (P0):** selected leg and instructions remain aligned.

## D. Active journey
- **F19 Start journey (P1):** save itinerary snapshot and show first action.
- **F20 GPS progress assistance (P1):** location-based progress suggestions with accuracy checks.
- **F21 Manual confirmations (P1):** reached stop, boarded, alighted, transfer completed.
- **F22 Deviation detection (P1):** prompt only when confidence and persistence thresholds are met.
- **F23 Re-plan (P1):** generate a new route from current/manual location.
- **F24 Pause/resume (P1):** persist active step and last confirmed event.

## E. Trust and data quality
- **F25 Provenance/freshness (P0):** source, fetched time, effective time, verification state.
- **F26 Data sync pipeline (P0 backend):** staged ingestion, validation, diff, publish and rollback.
- **F27 User report (P1):** report wrong stop, route, direction, transfer, name or access detail.
- **F28 Moderation console (P1):** review and approve/reject reports with audit history.
- **F29 Sync dashboard (P0 internal):** source health, run status, changed records and errors.

## F. Personalisation and offline
- **F30 Recent searches (P1):** local by default.
- **F31 Saved journeys (P1):** save route intent and refresh before reuse.
- **F32 Offline active journey (P1):** cache itinerary, steps, stop names, geometry and warnings.
- **F33 Language selection (P0):** English, Sinhala and Tamil UI foundations.
- **F34 Voice readout (P2):** optional text-to-speech; never audio-only.
- **F35 Share journey (P2):** opt-in, expiring link or summary.

## G. AI assistance
- **F36 Conversational planning request (P1):** parse intent and preferences, then call deterministic planner.
- **F37 Grounded explanation (P1):** explain returned itinerary only.
- **F38 FAQ/help (P2):** curated knowledge base; RAG optional for explanatory content only.

## H. Explicitly out of first release
- Guaranteed live vehicle locations.
- Guaranteed arrival/departure predictions.
- Ticket purchase/payment.
- Seat reservations.
- Crowd/occupancy estimates.
- Automated emergency response.
- National coverage claims without validated data.
- Fully accessible routing without reliable accessibility attributes.
- AI-generated route or fare facts.
