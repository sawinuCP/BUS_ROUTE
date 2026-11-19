# 10 — Multimodal Routing Engine

## 1. Core approach
Use a deterministic, explainable routing engine. AI does not decide which route exists.

Represent the network as a graph with:
- pedestrian nodes/edges;
- boarding/alighting access points;
- route-pattern stop sequences;
- rail station/line sequences;
- explicit transfer connections;
- place access points.

A transit edge is tied to a specific route pattern and direction. Do not connect every geographically close stop.

## 2. Graph model
- **Walk edge:** from/to coordinate or access point, pedestrian distance/time, geometry, restrictions and source.
- **Transit ride edge:** board stop/access point, alight stop/access point, pattern ID, ordered sequence span, mode and known attributes.
- **Transfer edge:** verified walk connection between two access points.
- **Access edge:** origin/destination to nearest usable network access point through pedestrian routing.

## 3. Algorithms
- Start with Dijkstra for a transparent baseline.
- Add A* for point-to-point search if heuristic and graph representation are validated.
- Use multi-criteria label-setting or bounded candidate generation for alternatives.
- Remove dominated itineraries: another route is no worse in all selected dimensions and better in at least one.
- Consider RAPTOR or timetable-aware algorithms only when reliable stop times and service calendars are available.

## 4. Cost model
A candidate score can combine:
- estimated walking time;
- estimated in-vehicle time;
- transfer count/penalty;
- route simplicity;
- data quality/confidence penalty;
- user preference weights.

Do not present the internal score as an objective truth. Show user-understandable components instead.

## 5. Time estimates without timetables
The first version can produce network-feasible paths and approximate durations from:
- walking engine estimates;
- conservative configured in-vehicle estimates, if supported by measured/validated corridor data;
- explicit transfer walk estimates.
If no defensible in-vehicle estimate exists, show unknown or a broad range. Do not fabricate waiting times or arrival predictions.

## 6. Route alternatives
Return a small number of distinct options such as:
- fastest estimated;
- least walking;
- fewest transfers;
- simplest.
Do not return four options that are the same route with trivial stop differences.

## 7. Instructions generation
Generate structured steps from route legs:
- `WALK_TO_STOP`
- `BOARD_TRANSIT`
- `RIDE_TRANSIT`
- `ALIGHT_TRANSIT`
- `WALK_TRANSFER`
- `WALK_TO_DESTINATION`
Every instruction references canonical entities and evidence. Text rendering is localised separately.

## 8. Confidence and suppression
A route can be excluded or downgraded if:
- ordered stop sequence is missing;
- direction/variant is unresolved;
- transfer access is unverified;
- required walking link is unavailable;
- source freshness is outside configured policy.
Confidence should be rule-based and explainable, not a made-up LLM score.

## 9. Walking engine evaluation
Prototype Valhalla and compare GraphHopper for:
- Sri Lankan pedestrian graph coverage;
- footpaths, crossings and access restrictions;
- route quality around terminals/stations;
- deployment cost and update process;
- licence and data terms;
- latency and operational reliability.

## 10. Map matching and progress
Use GPS accuracy, temporal smoothing and map matching. Apply hysteresis so one noisy location does not move the user between steps. Boarding/alighting remains user-confirmed unless a later evidence-backed workflow is introduced.
