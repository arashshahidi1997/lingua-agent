# Roadmap

## ✅ MVP (this release)
- Pure Python core, JSON-on-disk persistence.
- `Language`, `LanguagePair`, `Document`, `TextSegment`, `VocabularyItem`, `GrammarPoint`, `LessonUnit`, `Exercise`, `ExerciseAttempt`, `Flashcard`, `ReviewEvent`, `LearnerProfile`, `TutorSession` models.
- SM-2 scheduler with `Scheduler` Protocol.
- Mock AI provider returning deterministic, schema-valid output (tests do not need network).
- Ingest pipeline: text/markdown → `LessonUnit` + vocabulary + grammar + exercises + flashcards.
- Lesson markdown export with YAML frontmatter under `content/units/`.
- Anki-compatible CSV export.
- Typer CLI: `init`, `languages list`, `ingest text`, `ingest file`, `unit list`, `review due`, `review answer`, `export anki`, `tutor chat` (mock).
- Tests for language registry, SM-2, ingest pipeline, lesson schema, exercise schema, mock pipeline, RTL preservation.

## ✅ Phase 5 — Real AI providers
- `OpenAICompatibleProvider` (httpx, no SDK dependency) targets OpenAI, **Google AI Studio (Gemma)**, **Ollama (Gemma / Qwen)**, **DashScope (Qwen)**, OpenRouter, vLLM, llama.cpp, LM Studio.
- JSON-mode by default with transparent fallback when the backend rejects it.
- Schema-validation repair loop (default 2 attempts) so small open-weights models still produce pipeline-valid output.
- Anthropic native API deferred — stub raises with a hint to use OpenRouter for Claude in the meantime.
- 10 tests using `httpx.MockTransport` cover happy path, JSON-fence stripping, validation repair, give-up, json-mode fallback, prose salvage, and auth header handling.

## Phase 5b — Per-language-pair prompt tuning (open)
- Specialise the prompt templates in `ai/prompts.py` for each pair (Italian needs gender, Russian needs case, Persian needs ezafe + register).
- Promote `LearnerProfile.correction_style` and weakness list into the tutor system prompt.

## Phase 6 — Tutor agent
- Wire real provider to the existing tool surface.
- Memory trio (read/add/rewrite) using `LearnerProfile.memory`.
- Bayesian Knowledge Tracing module (clean-room port of OATutor's BKT).
- `recommend_next_activity` with mastery-aware item selection.

## Phase 6b — Dictionary-grounded lookup tool
- `lingua-agent download dictionaries --lang fa` — pulls kaikki.org Wiktionary extract + OpenSubtitles frequency list, indexes into SQLite at `~/.lingua-agent/dict/`.
- Optional download of Tatoeba (~700 MB) for example sentences.
- `lookup_word` tool exposed to the tutor agent: returns translations, POS, IPA, frequency rank, CEFR estimate, example sentences. Grounded answers, no LLM hallucination of translations.
- Wiktionary REST API as online fallback for words missing locally.
- Same lexical data regardless of which AI provider drives the tutor.

## Phase 7 — Richer ingestion
- PDF (via `pypdf`) and EPUB (via `ebooklib`) ingestion.
- URL fetcher for articles (text-only, no JS execution).
- Subtitle (`.srt`, `.vtt`) ingestion with sentence-mining preset.
- AnkiConnect upload as an alternative to CSV export.

## Phase 5b — Streamlit playground (✓ shipped)
- `lingua-agent playground` opens a local browser UI for clicking through ingest → lesson → review → tutor against the existing core.
- Single-file Streamlit app; for iteration, not production.
- Industry-standard "let me play with it" tool for AI / Python projects (Hugging Face Spaces, internal tools at OpenAI / Anthropic / Cohere).

## Phase 8 — FastAPI + React PWA (default product UI)
- FastAPI server mounted on the same package; every CLI command reachable over HTTP.
- React (or Svelte) SPA, RTL-aware, dark-mode, served as static files by FastAPI.
- **PWA** — `manifest.json` + service worker. "Install to Home Screen" on Chrome (Android) / Safari (iOS) gets you an app icon and full-screen launch. Covers mobile for free without an app store, code-signing, or store fees.
- Distribution: `pip install lingua-agent && lingua-agent serve`; Docker image for one-line install.
- See [`docs/clients.md`](clients.md). This is the boring, professional, ships-today choice — the same shape Open WebUI / LibreChat / AnythingLLM / Jan.ai use.

## Phase 8b — Optional desktop binary wrapper
- Wrap the same React SPA in **Electron** (mature, large bundles) or **Tauri** (Rust, small bundles). Ship on demand; both are straightforward.

## Phase 9 — Voice mode
- `STTProvider` and `TTSProvider` implementations.
- faster-whisper for STT (handles all four target languages).
- Piper for TTS (better Persian/Russian coverage than Kokoro).
- Speaking-prompt and listening-dictation exercises become functional.

## Phase 10 — FSRS
- Drop in `py-fsrs` behind the existing `Scheduler` Protocol.
- Migration script to replay `ReviewEvent` log into FSRS card state.

## Phase 11 — Native mobile (only if PWA isn't enough)
- Trigger: PWA falls short on push notifications, deep offline review, app-store discoverability, or background sync.
- Pick at that point: **React Native + Expo** (consumer-mobile-first AI startup default) or **Flutter** (cross-platform indie default with stronger desktop story and best Persian/Cyrillic text rendering). Both talk to the same FastAPI backend.
- Distribution: GitHub Releases first (zero-friction), F-Droid for OSS reach, Google Play / App Store only when demand justifies the friction.
- See [`docs/clients.md`](clients.md).

## Out of scope (for now)
- Audio synthesis caching to a CDN. Local files only.
- Multi-user accounts / SaaS hosting.
- Gamification (streaks, XP, leaderboards). Optional later.
- Pronunciation scoring (would require an alignment + phoneme model).
