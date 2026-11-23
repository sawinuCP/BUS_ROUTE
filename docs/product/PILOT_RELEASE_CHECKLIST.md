# Pilot release checklist (Phase 9, plan items 3, 7, 8)

Working checklist for the pilot release. Items marked **owner** need the
product owner's decision/sign-off; everything else can be verified from the
repository and the running stack. The status report
(`docs/status/development-status-report.md`) remains the authoritative
progress record.

## 1. Engineering gates (all green, re-run before release)

- [ ] Backend: `pytest` (all tests), `ruff format --check`, `ruff check`, `mypy`.
- [ ] Mobile: `jest`, `tsc --noEmit`, `eslint`.
- [ ] Concurrency gate green (`test_concurrency.py`); load baseline re-run
      and diffed against `docs/evidence/load-baseline-2026-11-23.md` and
      `load-stress-2026-11-23-25u.md` (zero 5xx required).
- [ ] Migration state: `alembic upgrade head` applies cleanly to a fresh DB.
- [ ] Docker stack healthy (postgres/redis/backend/valhalla).

## 2. Device readiness (owner)

- [ ] **D-5/D-9 device spike**: Android Studio + dev client, app runs on a
      real device; full journey flow verified.
- [ ] Airplane-mode test: cached plan readable, offline progress queues and
      syncs idempotently, offline report queue works.
- [ ] Voice read-aloud heard on-device (English), interruption controls work
      (pause/leave/step-change).
- [ ] Location permission flow and the manual fallback verified.

## 3. Data (owner)

- [ ] Owner field walks completed (tier-A stops; `data/field-verification/`
      submissions imported into `verification_records`).
- [ ] Fare evidence decision (Phase 4 item 11) recorded.
- [ ] Curated POI entrances decision (Phase 2 item 10) recorded.

## 4. Privacy and disclosures (plan item 7; doc 14)

- [ ] Privacy review confirms: no accounts required, no location stored
      server-side, local-first preferences/caches/queues, report consent
      gate, AI facts bundle coordinate-free (§11 honesty section of the
      status report is the current-code record).
- [ ] Store privacy disclosures drafted from that record (data collected:
      none beyond user-entered search terms and consent-gated reports;
      location: on-device only, never transmitted/stored).
- [ ] Permissions explanations for store listing: location (assistive
      nearby-stop search + optional GPS suggestions, off by default),
      speech (read-aloud, explicit tap only).
- [ ] Sri Lankan data-protection review with counsel (doc 14) — **owner/counsel**.
- [ ] Retention periods documented for reports, sessions, logs
      (data model doc §6) — confirm with the owner.

## 5. Accessibility (plan item 3)

- [ ] Dynamic type (text scale) verified across screens on-device.
- [ ] Screen-reader pass: labels on controls, step cards, report panel,
      settings (VoiceOver/TalkBack on-device — **owner device spike**).
- [ ] Contrast check against the theme on-device.
- [ ] Large touch targets verified on-device.

## 6. Localization (D-7 owner)

- [ ] si/ta native review of instruction templates completed → then enable
      si/ta rendering (Phase 5 item 11) and si/ta read-aloud phrasing.
- [ ] Until then: English-only disclosure in the store listing.

## 7. Attribution and licences (plan item 8)

- [ ] OpenStreetMap attribution visible in the app (map screen footer /
      about) — required by ODbL: "© OpenStreetMap contributors".
- [ ] Source register (`docs/product/07_DATA_SOURCES_AND_ACQUISITION.md`)
      matches the ingested sources and licences.
- [ ] Valhalla/graph attribution acknowledged where applicable.
- [ ] Third-party licences of shipped packages reviewed (Expo/React Native
      stack; no copyleft conflicts identified for distribution).

## 8. Support and data correction (plan item 9)

- [ ] `docs/product/SUPPORT_AND_DATA_CORRECTION.md` reviewed and owner
      roles assigned (moderator, data operator, support contact).
- [ ] In-app report-a-problem flow verified end-to-end (consent → queue →
      moderation → candidate version).

## 9. Release mechanics (plan item 10 — owner)

- [ ] Pilot group defined; staged rollout plan agreed.
- [ ] Monitoring in place: `/api/v1/metrics`, `/api/v1/ops/dashboard`,
      error webhook (`ERROR_WEBHOOK_URL`) configured.
- [ ] Rollback rehearsed (dataset rollback + app rollback).
- [ ] Support contact reachable; data-correction intake tested.
