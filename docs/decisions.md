# Design decisions

Rationale for the architectural choices made before any code was written. Update this file when a decision is reversed; do not silently change direction.

## D1 — Clean repo, not a fork of OpenLingo
OpenLingo is the closest existing project but its stack (TypeScript / Next.js / Drizzle / Postgres / R2 / Better Auth) is the wrong shape for a **local-first, hackable, Python** library. Borrowing patterns (agent + tools, SM-2, markdown-unit DSL, memory-tool trio) is high-value; vendoring its code is not. New repo, MIT license, attribution in `docs/references.md`.

## D2 — Project name: `lingua-agent`
Short, descriptive, neutral about which language pairs are supported. Avoids locking in "polyglot" / "trilingual" framings that age badly.

## D3 — Python 3.11+, Pydantic v2, JSON-on-disk for MVP (SQLite via Protocol later)
The bootstrap brief allows "SQLite or local JSON" for MVP. Reasons to start with JSON:
- Inspectable by hand and by `git diff`. Matches the local-first / hackable goal.
- Avoids Pydantic-v2 / SQLModel version friction during the scaffolding sprint.
- Storage is hidden behind a `Repository` Protocol per entity, so SQLite/SQLModel can be swapped in without touching call sites.

We will introduce SQLite once we hit one of the natural triggers: an HTTP API, multi-process review queues, or learner datasets that exceed comfortable JSON size (~10 MB).

## D4 — "Any A → any B" is the core abstraction; English is not privileged
Every entity that has a language carries `source_language` and `target_language`. A separate `support_language` field exists for explanations (typically English, but optional). The CLI requires `--source` and `--target`; defaults are taken from learner profile, never hard-coded to English.

## D5 — Persian/Farsi gets first-class RTL handling
- `Language` carries `direction: "ltr" | "rtl"` and `script` fields.
- Lesson markdown export wraps RTL blocks in `<div dir="rtl">…</div>` so they render correctly in any markdown viewer.
- Transliteration is an **optional scaffold field** on vocabulary items, never a replacement for the original script. The Persian, Russian, and Arabic-script languages all have `transliteration_supported: true`; transliteration is generated only when explicitly requested.

## D6 — SM-2 first, FSRS later, Scheduler Protocol from day one
SM-2 is implemented in pure Python (~80 LOC) and matches the upstream `open-spaced-repetition/sm-2` semantics including the `q==3` same-day re-review branch. The `Scheduler` Protocol exposes one method: `update(card, rating, reviewed_at) -> Card`. py-fsrs will be a drop-in implementation.

We add an explicit `lapses` counter on `Flashcard` (not present in upstream SM-2) so the future FSRS migration has the data it needs.

## D7 — Tutor is an agent with typed tools, not a chat loop
Even before a real LLM is wired up, the tutor module defines its **tool surface as Pydantic-typed call objects** in `tutor/tools.py`. Every tool execution is logged to `TutorSession.tool_calls` with arguments, return value, and timestamp. This makes traces inspectable, gradeable, and replayable. Phase 6 wires an actual provider to the tool surface; the tools themselves are usable now via the mock provider.

## D8 — AI provider is a Protocol; mock is the default
`AIProvider` Protocol exposes `generate_structured(prompt, schema) -> dict` and `chat(messages, tools=None) -> ChatResponse`. The mock provider returns deterministic, schema-valid synthetic content (looked up by language pair + input length) so the entire pipeline runs in tests without a network call. Real providers (`openai_compatible`, `anthropic`) are optional install extras.

This is not a fall-through: the mock provider is the **primary** provider for tests and local development. Real providers are an orthogonal concern.

## D9 — Lesson units are Markdown + YAML frontmatter, written under `content/units/`
Lessons are inspectable, diff-friendly, and human-editable. We don't invent a binary format. The frontmatter schema is the canonical lesson schema; the rendered markdown body is for humans.

## D10 — Voice mode uses Discute's 3-function seam, but only as Protocols for MVP
`voice/stt.py` and `voice/tts.py` define `STTProvider` and `TTSProvider` Protocols. No implementations ship in MVP. Phase N will pick faster-whisper (STT) and Piper (TTS, better Persian/Russian coverage than Kokoro) behind those Protocols.

## D11 — No frontend in MVP
The CLI is the proving ground. A FastAPI + minimal UI is scaffolded under `api/` but commented as Phase 8.

## D12 — Conservative content policy (hallucination control)
- The original source text is never overwritten. Translations live in adjacent fields with a `generated: true` and `provenance` marker.
- Vocabulary items always cite the sentence they were extracted from.
- Etymology and morphology fields default to empty; the model must mark `confidence: "uncertain"` when filling them in or omit them.
- Transliteration is labelled `approximate: true`.

## D13 — Reversed: ~~SQLModel for MVP~~
The bootstrap brief listed SQLModel as a suggested option. Reversed by D3 above. May be reversed back when we add the HTTP API.
