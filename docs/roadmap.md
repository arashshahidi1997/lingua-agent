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

## Phase 7 — Richer ingestion
- PDF (via `pypdf`) and EPUB (via `ebooklib`) ingestion.
- URL fetcher for articles (text-only, no JS execution).
- Subtitle (`.srt`, `.vtt`) ingestion with sentence-mining preset.
- AnkiConnect upload as an alternative to CSV export.

## Phase 8 — HTTP server + first desktop client
- FastAPI server mounted on the same package; CLI commands all reachable over HTTP.
- First desktop UI: **Tauri 2** + React (RTL-aware) bundling the FastAPI process as a sidecar. Ships macOS / Windows / Linux from one codebase.
- Views: language-pair selector, ingestion form, lesson view, bilingual reader (RTL-correct), exercise runner, SRS queue, tutor chat, learner dashboard.
- See [`docs/clients.md`](clients.md) for the multi-platform plan.

## Phase 9 — Voice mode
- `STTProvider` and `TTSProvider` implementations.
- faster-whisper for STT (handles all four target languages).
- Piper for TTS (better Persian/Russian coverage than Kokoro).
- Speaking-prompt and listening-dictation exercises become functional.

## Phase 10 — FSRS
- Drop in `py-fsrs` behind the existing `Scheduler` Protocol.
- Migration script to replay `ReviewEvent` log into FSRS card state.

## Phase 11 — Android (and iOS) client
- **Default plan**: Tauri 2 mobile so the desktop React UI ships unchanged on Android/iOS.
- **Fallback**: Flutter if Tauri 2 mobile blocks us on a critical native plugin or text rendering.
- Backend hosting: phone connects to user's desktop server over LAN/Tailscale; self-hosted cloud is a configurable alternative; offline review (slim TS port of SM-2 + local SQLite) is optional and additive.
- See [`docs/clients.md`](clients.md).

## Out of scope (for now)
- Audio synthesis caching to a CDN. Local files only.
- Multi-user accounts / SaaS hosting.
- Gamification (streaks, XP, leaderboards). Optional later.
- Pronunciation scoring (would require an alignment + phoneme model).
