# Mobile — Sri Lanka Journey Planner

React Native + TypeScript + Expo (SDK 58) skeleton with Expo Router (Phase 0.4).
Stack decisions are recorded in `docs/adr/ADR-0002` and `docs/adr/ADR-0005`.

## Layout

```text
apps/mobile/
├── src/
│   ├── app/           # Expo Router routes: _layout (Stack), index (Home), journey (placeholder)
│   ├── components/    # ThemedText / ThemedView foundations
│   ├── constants/     # theme tokens (light/dark colors, fonts, spacing)
│   ├── hooks/         # use-color-scheme, use-theme
│   └── lib/           # config (EXPO_PUBLIC_* env) and typed API client
├── app.json           # Expo config (slug sljp-mobile, scheme sljp, Android package lk.sljp.mobile)
├── .env.example       # environment template (EXPO_PUBLIC_API_BASE_URL)
└── eslint.config.js   # eslint-config-expo (flat config)
```

## Commands (run inside `apps/mobile/`)

```powershell
npm install          # install deps (package-lock.json is committed)
npm run lint         # expo lint (eslint-config-expo)
npm run typecheck    # tsc --noEmit (strict)
npm test             # jest via jest-expo preset
npm run android      # launch on Android (requires Android SDK/emulator)
npm run ios          # launch on iOS (requires macOS/Xcode)
npm start            # dev server (Expo Go / dev client)
```

## Environment configuration

Copy `.env.example` to `.env` (gitignored). Only `EXPO_PUBLIC_*` variables are
inlined into the bundle; **never place secrets in this file**. On Android
emulators use `http://10.0.2.2:8000` to reach a backend running on the host.

## Verification status (Phase 0.4)

Verified locally: `npm run lint`, `npm run typecheck`, `npm test`, and the CI
workflow definition. Launching on Android/iOS simulators requires local mobile
tooling (Android Studio / Xcode) and is a manual step for the team; the Phase 0
exit criterion "app launches on at least one device path" is therefore recorded
as pending until a device/simulator run is performed.
