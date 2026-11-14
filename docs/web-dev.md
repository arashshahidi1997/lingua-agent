# Web app — dev workflow

Phase 8 ships the React PWA in two pieces:
- **FastAPI** backend in `src/lingua_agent/api/` (`lingua-agent serve`).
- **React + Vite + TypeScript + Tailwind** frontend in `web/`.

This page is the dev cheatsheet. The architectural rationale lives in [`clients.md`](clients.md).

## Prerequisites

- Python 3.11+ with the package installed: `pip install -e ".[api,dev]"`.
- Node.js 22+ and npm 10+ (whatever ships with current Node LTS works).

## First-time setup

```bash
# Install Python side (if you haven't already)
python3.11 -m venv .venv
.venv/bin/pip install -e ".[api,dev]"

# Install React side
npm --prefix web install
```

## Two-server dev loop

Run both servers in separate terminals; Vite proxies `/api` to FastAPI so you write `fetch('/api/...')` exactly as in production.

```bash
# Terminal 1 — FastAPI
.venv/bin/lingua-agent serve            # → http://127.0.0.1:8000

# Terminal 2 — React + Vite (HMR)
npm --prefix web run dev                # → http://127.0.0.1:5173
```

Open http://127.0.0.1:5173 in your browser. Edit anything under `web/src/` and it hot-reloads. Edit anything under `src/lingua_agent/`, restart `lingua-agent serve` (or pass `--reload` for uvicorn auto-reload).

## Single-server (production-like)

When you want to test the production shape — one process, FastAPI serving both the API and the built static UI:

```bash
npm --prefix web run build              # writes web/dist/
.venv/bin/lingua-agent serve            # FastAPI mounts web/dist at /
# Open http://127.0.0.1:8000
```

`api/main.py` mounts `web/dist/` at `/` only if it exists, so the dev loop above doesn't conflict.

## Folder layout

```
web/
├── index.html              # Vite entry HTML (<title>, theme-color, viewport-fit=cover)
├── package.json            # React, Vite, Tailwind v4, lucide-react, @fontsource (Inter, Vazirmatn, Literata)
├── vite.config.ts          # Vite config + PWA manifest + /api proxy to :8000
├── public/                 # Static assets served as-is (favicon, icons)
└── src/
    ├── main.tsx            # React entry; imports only the font subsets we use
    ├── App.tsx             # Shell: header (pair chip, settings), tab bar / rail, overlay stack
    ├── index.css           # Design tokens (CSS variables, dark mode) exposed to Tailwind via @theme
    ├── state/              # settings + language pair (localStorage), navigation (tabs + overlays + history)
    ├── lib/                # api.ts, course-api.ts (Product v2 contract), speech, recorder, dictation, grading, rtl
    ├── components/         # ui primitives, Text (target text + transliteration + gloss), PlayButton, Exercises
    └── views/              # Today, Path, Library, Talk, Settings, and the full-screen Player, Review, readers, chat
```

Navigation has no router: `state/nav.ts` holds the active tab plus a stack of overlays (player, readers,
chat, settings). Opening an overlay pushes a history entry, so the Android back button closes it.

## Stack choices and why

- **React 19 + TypeScript** — most AI tools (Claude, Copilot, Cursor) generate React better than any other framework due to training-data volume; that matters more for solo + AI-assisted dev than the small Svelte advantages. See `decisions.md` D-frontend.
- **Vite 8** — instant HMR, no Webpack, default for new React projects in 2026.
- **Tailwind v4** — single `@import "tailwindcss";` with the `@tailwindcss/vite` plugin, no PostCSS config, no `tailwind.config.js` required for basic use. Major simplification over v3.
- **No shadcn/ui yet** — bringing it in adds initial-component scaffolding noise without a clear payoff at this scaffold stage; Phase 8.2 will pull in the components we actually use (Button, Dialog, Tabs, Select).
- **No router yet** — tabs and overlays are state in `state/NavProvider.tsx`, with `history.pushState` for the back button. A router comes in when we want shareable URLs.

## What ships in each phase

| Phase | What's added |
|---|---|
| **8.0** ✓ | FastAPI backend with all CLI commands as endpoints. |
| **8.1** ✓ | React + Vite + Tailwind scaffold; Dashboard / Languages / Lessons / Review views ping the API. |
| **8.2** | Ingest form, full lesson view (bilingual reader), reveal/grade SRS UI, tutor chat, **PWA manifest + service worker** so it installs to home screen on Android/iOS. |
| **8b** (optional) | Tauri or Electron desktop wrapper around the same React build. |
