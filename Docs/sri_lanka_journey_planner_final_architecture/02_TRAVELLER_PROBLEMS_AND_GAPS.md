# 02 — Traveller Problems and Product Gaps

The following are product hypotheses to validate with interviews, field observation and usability tests.

| ID | Traveller problem | Why it matters | Proposed response |
|---|---|---|---|
| P01 | A journey may require several transport modes | Separate mode searches leave the traveller to combine them | One multimodal itinerary |
| P02 | A stop pin does not identify the correct side/stand | Traveller may board across the road or at a different bay | Boarding access point and verified side/stand |
| P03 | Same route number may have different variants | Wrong bus can follow a different path | Route pattern, direction and destination context |
| P04 | Traveller does not know where to get off | Risk of missing destination stop | Explicit alighting instruction and cues |
| P05 | Transfer is shown as a line but not explained | Traveller cannot find the next boarding point | Pedestrian transfer leg with distance and directions |
| P06 | Destination pin may not be the public entrance | Final approach can be confusing | Verified destination access point |
| P07 | Stop names have multiple spellings/languages | Search misses the intended place | Alias and transliteration index |
| P08 | Transport data changes | Old route information can mislead | Scheduled sync, source freshness and versioning |
| P09 | Estimated duration looks exact | User may interpret an estimate as a promise | Ranges, assumptions and caveats |
| P10 | Route options are hard to compare | More choices do not necessarily help | Non-dominated alternatives and preference ranking |
| P11 | Mobile connectivity may fail | User loses directions mid-trip | Offline cache of selected itinerary |
| P12 | User may board wrong service or miss a stop | Need a recovery path | Re-plan and manual confirmation |
| P13 | Fare data may be outdated | Incorrect cost expectations | Source/effective-date fare data or no fare shown |
| P14 | Accessibility details are missing | Route may be unusable for some travellers | Verified access attributes and unknown state |
| P15 | User reports may not correct the system | Repeated errors remain | Moderated issue workflow and audit trail |
| P16 | Map-heavy interfaces can be difficult to follow | Traveller needs a clear immediate action | Current-step mode and readable text |
| P17 | Local terminology differs from formal data | Search and instructions feel unfamiliar | Local names, aliases and terminology |
| P18 | Service availability may be unknown | A route pattern is not proof a service is running | Separate network feasibility from live availability |

## Competitor validation
Benchmark actual journeys in Beep Sri Lanka, LMT-GO and other relevant services. Compare:
- route coverage and data provenance;
- route variants and destination-board information;
- stop/stand/side accuracy;
- transfer walking detail;
- language and alias handling;
- freshness and update cadence;
- offline behaviour;
- uncertainty disclosure;
- correction/report workflow.

Do not claim a competitor lacks a feature without testing a current version and recording evidence.
