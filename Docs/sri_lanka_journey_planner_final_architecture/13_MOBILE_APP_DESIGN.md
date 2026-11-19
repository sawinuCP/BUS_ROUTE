# 13 — Mobile Application Design

## 1. Main screens
- Home/search
- Search results and map picker
- Journey alternatives
- Journey detail
- Active journey
- Saved journeys
- Reports
- Settings/language/privacy
- Admin console (separate protected web client)

## 2. State management
- TanStack Query: API/server state and cache.
- Zustand: transient UI and active-session state.
- SQLite: durable offline itinerary and essential entity snapshots.
- SecureStore: authentication tokens and sensitive local secrets.

Do not duplicate the full transport network on the phone in the first release.

## 3. Offline model
Cache the selected journey:
- plan and dataset version;
- ordered legs and instructions;
- stop/station names and aliases used;
- access point notes;
- geometry required to render the trip;
- warnings and freshness timestamps.

Offline behaviour:
- show cached instructions;
- clearly indicate no live refresh;
- do not claim current service operation;
- allow manual progress confirmations;
- sync reports/events when connectivity returns, subject to privacy policy.

## 4. Location
- Ask permission only when the user chooses current location or starts location-assisted progress.
- Manual origin/destination selection remains available.
- Show a persistent indication when active location tracking is enabled.
- Stop tracking when journey ends or user pauses/stops it.
- Avoid storing a detailed location trail unless a clear feature and consent justify it.

## 5. Active journey state machine
Suggested states:
`PLANNED → STARTED → WALKING_TO_STOP → READY_TO_BOARD → ON_TRANSPORT → APPROACHING_ALIGHT → ALIGHTED → WALKING_TO_TRANSFER → READY_TO_BOARD_NEXT → FINAL_WALK → COMPLETED`

Additional states: `PAUSED`, `DEVIATED`, `REPLANNING`, `MANUAL_ASSISTANCE`.

Transitions should be event-driven and auditable. GPS may suggest a transition; explicit user confirmation is available for boarding and alighting.

## 6. Accessibility
- Screen-reader labels and semantic controls.
- Dynamic text sizing.
- High contrast and non-colour status cues.
- Text alternatives for map instructions.
- Voice readout as an optional enhancement.
- Do not label a path wheelchair accessible unless verified.
