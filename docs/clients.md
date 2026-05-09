# Client platforms (desktop + Android)

`lingua-agent` is built as a **headless Python core** plus thin clients. This separation means we can ship desktop and Android (and iOS, web, CLI) without rewriting the language-learning logic.

## Architecture

```
┌──────────────────────────────────────────┐
│            Clients (thin)                │
├──────────────┬───────────────────────────┤
│ CLI (Typer)  │ Desktop UI │ Mobile UI    │
│ shell        │ (Tauri 2)  │ (Tauri 2     │
│              │            │  or Flutter) │
└──────┬───────┴─────┬──────┴──────┬───────┘
       │   HTTP      │   HTTP      │   HTTP / LAN / cloud
       ▼             ▼             ▼
┌──────────────────────────────────────────┐
│       Python core (this repo)            │
│  models · ingest · srs · tutor · ai      │
│  CLI (Phase 4)  ·  FastAPI (Phase 8)     │
└──────────────────────────────────────────┘
```

The CLI and the future FastAPI server are both clients of the same core package. UIs talk to FastAPI over HTTP. **Python does not run on the phone.**

## Desktop (Phase 8)

**Recommendation: Tauri 2.**
- One web-tech UI (React + Tailwind, with `dir="rtl"` per language) packaged as native binaries for macOS / Windows / Linux.
- Bundles the FastAPI Python process as a sidecar; UI talks to `http://127.0.0.1:<port>`.
- Small bundles (~5–15 MB shell), good native integration, MIT-friendly.

**Alternative: Electron.**
- Bigger bundles (~80–150 MB) but a more mature ecosystem. Fall back to this only if Tauri sidecar packaging blocks us.

**Alternative: Native Python + PyWebView.**
- Smallest dev cost, but no shared codebase with mobile. Use only as a stop-gap.

## Mobile (Phase 11)

The core question: **can the mobile UI share code with the desktop UI?**

### Recommendation: Tauri 2 mobile (single web UI for desktop + mobile)
- **Pros**: one React codebase ships to all five OSes. RTL works out of the box. Native plugins for camera/storage/notifications via Tauri plugins.
- **Cons**: Tauri mobile shipped in 2024 — younger than Flutter's mobile story. Some native plugins still maturing.

### Alternative: Flutter (separate from desktop UI)
- **Pros**: most mature cross-platform mobile framework. Strong RTL support. Excellent text rendering for Persian/Arabic/Cyrillic.
- **Cons**: Dart codebase, no sharing with the Tauri desktop UI. Two UI codebases to maintain.

### Alternative: React Native + Expo (or React Native + Capacitor)
- **Pros**: very mature on Android/iOS. JS shared with desktop in principle.
- **Cons**: bridging to a Tauri desktop shell is awkward; usually you end up with two builds anyway.

## Backend hosting model for mobile

Since Python doesn't run on the phone, the mobile app needs to reach a `lingua-agent` server somewhere. Three modes, all supported by the same FastAPI build:

1. **Local desktop pairing.** Phone talks to the user's desktop on LAN (or via Tailscale / Wireguard). Local-first, private, works offline as long as both devices are on the same network.
2. **Self-hosted cloud.** User runs the FastAPI image on a small VPS / Fly.io / Coolify instance. Single-tenant; user owns the data.
3. **Slim offline review.** Mobile keeps a local SQLite of due flashcards and `ReviewEvent`s; review works offline; ingest + tutor + lesson generation require connecting to a server. The replication layer pushes `ReviewEvent`s back to the server when online.

Mode 3 is the only one that requires a small TypeScript / Dart port of the SRS scheduler (~80 LOC) on the client. It's optional and can be added when offline review becomes a hard requirement.

## What this means for the current build

Nothing changes in Phases 1–4. The headless Python core, models, SRS, ingest pipeline, and CLI are the foundation regardless of which client framework wins.

The first concrete commitment to a client framework happens in Phase 8 when we scaffold the FastAPI server + first desktop UI. Until then we can keep this open.

## Open decisions (tracked in `docs/decisions.md` when made)

- D14 (open): pick Tauri 2 vs Flutter vs Electron for desktop.
- D15 (open): pick Tauri 2 mobile vs Flutter for Android.
- D16 (open): commit to one of the three backend hosting modes as the default mobile experience.
