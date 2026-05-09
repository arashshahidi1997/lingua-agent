# Client platforms

`lingua-agent` is built as a **headless Python core** plus thin clients. This separation means we can ship desktop and mobile without rewriting the language-learning logic.

```
┌────────────────────────────────────────────────────────────────────┐
│                         Clients (thin)                             │
├──────────────┬───────────────────┬───────────────────┬─────────────┤
│ CLI (Typer)  │ Streamlit         │ Web SPA (React/   │ (optional)  │
│ shell        │ playground        │ Svelte) + PWA     │ Tauri /     │
│              │ (dev/iteration)   │ — desktop browser │ Electron    │
│              │                   │ + Android/iOS     │ wrapper     │
│              │                   │ home-screen       │             │
└──────┬───────┴────────┬──────────┴──────────┬────────┴──────┬──────┘
       │  in-process    │  in-process         │  HTTP         │  HTTP
       ▼                ▼                     ▼               ▼
┌────────────────────────────────────────────────────────────────────┐
│        Python core (this repo)                                     │
│  models · ingest · srs · tutor · ai                                │
│  CLI (✓) · Streamlit playground (Phase 5b) · FastAPI (Phase 8)     │
└────────────────────────────────────────────────────────────────────┘
```

## Why this shape

The honest answer about what professional AI/dev-tool teams ship today:

- **Python AI core + FastAPI server + React/Svelte SPA + PWA** is the dominant pattern. Open WebUI, LibreChat, AnythingLLM, Jan.ai — all ship a web app. Mobile coverage comes from PWA "install to home screen", which on Android (Chrome) and iOS (Safari) is genuinely a real-app experience for non-camera, non-push-heavy tools.
- **Streamlit / Gradio** is what every AI/ML team uses internally for prototyping and demos (Hugging Face Spaces is Gradio; OpenAI, Anthropic, Cohere ship internal tools on Streamlit). Not a production UI; the right "let me actually play with it this afternoon" tool.
- **Tauri** is rising and is a fine choice for shipping a desktop binary, but it's not yet the default any pro team picks for cross-platform mobile in production. Treat it as an optional desktop wrapper.
- **Native React Native / Flutter** is correct only when the app needs camera, push notifications, true offline-first, or app-store discoverability that PWA can't deliver — a real product decision, not a default.

## Today (in the repo)

- **CLI (Typer)** — works now. `lingua-agent ingest text`, `review due`, `tutor chat`, etc.
- **Streamlit playground** — `lingua-agent playground` opens a local browser UI for clicking through ingest → lesson → review → tutor against the same core. Single-file Streamlit app; for iteration, not production.

## Phase 8 — FastAPI + React PWA (the default product UI)

- **FastAPI** server mounted on the same package; every CLI command is reachable over HTTP.
- **React (or Svelte) SPA** as the frontend. Ships as static files served by FastAPI. RTL-aware (Persian, future Arabic / Hebrew). Built-in dark mode.
- **PWA**: `manifest.json` + service worker, so "Install to Home Screen" on Chrome (Android) and Safari (iOS) gets you an app icon, full-screen launch, and offline shell. Covers mobile for free without an app store, code-signing, or store fees.
- Distribution: `pip install lingua-agent && lingua-agent serve` for self-hosters; Docker image for one-line install.

This is the boring, professional, ships-today choice.

## Phase 8b — Optional desktop binary wrapper

For users who prefer a `.dmg` / `.exe` / AppImage over "open the browser":
- **Electron** (mature, large bundles ~80–150 MB) — boring default. VS Code, Slack, Linear, Discord, Figma desktop.
- **Tauri** (Rust, small bundles ~5–15 MB, growing) — picked when bundle size or memory matters. Spacedrive, Pot, Cap.

Both wrap the same React SPA built in Phase 8. Pick one when there's demand; either is straightforward.

## Phase 11 — Native mobile (only if PWA isn't enough)

A real native app is correct when one of these matters and PWA can't do it:
- Push notifications for review streaks (PWA push works on Android Chrome but is unreliable on iOS Safari).
- Deep on-device offline review (PWA offline works but storage limits are tight).
- App-store discoverability (App Store and Play Store distribution).
- Background sync for `ReviewEvent`s.

Framework picks at that point:
- **React Native + Expo** — what consumer-mobile-first AI startups use in 2025/2026. Best ecosystem, easiest hot-reload dev loop, ships to iOS + Android + web from one codebase.
- **Flutter** — what cross-platform indie shops with desktop ambitions pick. Best text-rendering for Persian / Cyrillic; one codebase across iOS / Android / desktop / web.

Either talks to the same FastAPI backend.

## Distribution paths when we get there

- **GitHub Releases** with APK from CI: zero-friction, free, Obtainium auto-updates.
- **F-Droid**: free OSS distribution, no developer fee, requires reproducible builds + open license (we have MIT). Best fit for our open-source posture.
- **Google Play**: $25 one-time + 2024 closed-test rule (12+ testers for 14+ days for new accounts). Wait for actual demand.
- **Apple App Store**: $99/year + review process. Same — wait for demand.

## Backend hosting model for mobile / multi-device

The same FastAPI server supports three modes:
1. **Local desktop pairing** — phone talks to your desktop on LAN or via Tailscale / Wireguard. Local-first, private.
2. **Self-hosted cloud** — run the FastAPI image on a small VPS / Fly.io / Coolify. Single-tenant.
3. **Slim offline review** — phone keeps a local SQLite of due flashcards; review works fully offline; ingest + tutor + lesson generation require online. The replication layer pushes `ReviewEvent`s back when online. This is the only mode that requires a small TypeScript / Dart port of the SM-2 scheduler (~80 LOC) on the client.

Mode 1 is the local-first default; Mode 2 is the "share across my devices" upgrade; Mode 3 is the "review on the train" optimisation.

## Open decisions (still tracked in `docs/decisions.md` when made)

- D14 (open): SPA framework for Phase 8 — React vs Svelte. Default React for ecosystem; Svelte if we want smaller bundles + simpler state.
- D15 (open, deferred): desktop wrapper — Electron vs Tauri vs none. Decide in Phase 8b based on user requests.
- D16 (open, deferred): native mobile — React Native vs Flutter. Decide in Phase 11 only if PWA falls short.
