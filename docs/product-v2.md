# Product v2 — proposal

> **Status: first pass implemented (2026-11-14)** — the four tabs, the Path with a hand-written Farsi A1
> course, the exercise engine, practice and checkpoint quizzes, stories with shadowing, recordings, imported
> audio with transcripts, Talk with corrections and summaries, and Piper speech. Still open for review:
> nothing here is fixed, and neither is the spec it revises. It reframes the
> app from "paste text, get a lesson" into a daily learning companion. The existing core (ingest pipeline,
> SRS, providers, materials adapter, PWA) stays; this adds structure and surfaces on top of it.

## Why

Today the app is ingest-driven: you bring a text, it builds a lesson. That works for a B1+ learner with
material in hand, but not for someone starting from zero (e.g. English speaker → Farsi A1), who needs a
sequence, audio, and somewhere to practise speaking. The UI also shows the plumbing (ingest, languages,
pair pickers) instead of the next thing to do.

## Information architecture

Four tabs plus Settings. Bottom tab bar on mobile, slim rail on desktop.

| Tab | Purpose | Replaces |
|---|---|---|
| **Today** | One primary "Continue" action, then: reviews due, story of the day, a short conversation. Daily goal in minutes. | Dashboard, Review |
| **Path** | The structured course (units → steps), progress through CEFR levels. | — (new) |
| **Library** | Stories, dialogues, your own texts and audio. "+ Add" is where ingest lives now. | Lessons, Ingest |
| **Talk** | AI conversation partner, text or voice, role-play scenes. | Tutor |
| *Settings* | Languages and pairs, AI provider, voices and microphone, material sources, script display, daily goal, scheduler, export, data. | Languages, sidebar pair pickers |

The active pair shrinks to a chip in the header (`EN → فا`); tapping it switches between pairs you've set up.

### Visual direction

- Minimal: one accent colour, generous whitespace, no text-heavy dashboards; one primary button per screen.
- Reading text in a serif; a proper Persian face (Vazirmatn) and Cyrillic coverage; RTL everywhere it matters.
- Dark mode first-class. Calm, not gamified-loud: progress is visible, streaks are optional (off by default).

## Features

### 1. Path — a structured, Duolingo-style track

- **Syllabus as data**: one YAML file per target language and level, e.g. `syllabi/fa/a1.yaml`, listing units
  and steps with their goals (vocab themes, grammar points, script items, can-do statements). Hand-curated,
  reviewable, versioned. Farsi A1 sketch: script in small batches (ا ب پ ت …) → greetings → `است` / `هستم`
  → numbers → ezafe → present tense `می‌` → café / taxi / family → past tense intro.
- **Generated once, then stable**: the AI fills each step (lesson, story, exercises) the first time it's
  reached and the result is cached in the store, so revisiting gives the same content; a "regenerate" action
  exists for bad output.
- **Unit shape**: 3–5 lessons → a story → a role-play → a checkpoint quiz.
- **Placement test** to skip ahead; checkpoint quizzes can test out of a unit.
- Path progress feeds Today's "Continue" and the tutor's `recommend_next_activity` (Phase 6).

### 2. Quiz — one practice engine

Review and Quiz merge into a single practice engine with interchangeable exercise types, drawing items from
SRS due cards and the current unit:

multiple choice · typed answer · listen and pick · match pairs · word-order tiles · gap fill · speak the
sentence · script recognition (Farsi letters, Cyrillic).

Adaptive within a session (missed items come back), and every answer still logs a `ReviewEvent`, so FSRS
(Phase 10) slots in unchanged.

### 3. Audio

**From sources**
- Import your own audio (podcasts, Pimsleur/Assimil from the SSD or Drive via the materials adapter) →
  faster-whisper transcript with word timestamps → **synced transcript**: highlight follows playback, tap a
  word to save it, loop a sentence, 0.75× speed.
- **Hands-free mode**: a generated Pimsleur-style audio lesson (prompt, pause, answer) for walking or driving.

**Your own voice**
- **Shadowing**: play a native/TTS line, record yours, play both back to back (waveform overlay later).
- **Your voice on cards**: record your pronunciation as card audio.
- **Spoken diary**: one minute a day; transcribed, corrected, saved as a mini lesson.

**Generated speech** (TTS) for every lesson, story and card — Piper locally; a cloud voice as an option where
local Persian quality falls short.

Copyright posture as in Phase 6c: personal copies only, never shared through the app.

### 4. Stories and conversations — read and listen

- **Graded stories** generated from your known vocabulary (≈95% known words, i+1), with recurring characters
  across a unit (Assimil-style).
- **Dialogues** with two distinct voices.
- **Reader**: parallel text (support language hidden, tap to reveal), read-along highlight with audio, tap a
  word for gloss + "add to SRS".
- **Script toggle for Farsi**: Persian script / transliteration / both — essential at A1.
- The diglot-weave reader (Phase 6e) becomes a reading mode here.

### 5. Talk — AI conversation partner

- **Role-play scenes** tied to the current unit (order tea in a Tehran café, take a taxi, meet a neighbour);
  a persistent persona per scene.
- **Text or voice**: push-to-talk → STT → LLM → TTS.
- **Gentle correction**: recasts in the reply instead of interrupting; a "hint" button and a "say it in
  English" escape hatch; difficulty slider.
- **Session summary**: mistakes and new words become cards; a line in the learner memory (Phase 6).

## Data model additions (sketch)

| Model | Holds |
|---|---|
| `Syllabus`, `PathUnit`, `PathStep` | Course structure from the YAML; per-learner step state (locked / current / done / tested out). |
| `Story` | Generated or imported text, level, characters, segments with audio timing. |
| `AudioAsset` | File ref, source (TTS / import / recording), transcript with word timestamps. |
| `Recording` | Learner's own recording, linked to a card, a story line, or a diary entry. |
| `Scenario`, `Conversation` | Role-play setup and transcript, with the end-of-session summary. |

## Proposed build order

Supersedes the phase order in the roadmap where they conflict; the phases themselves stay as references.

1. **UI shell** — four tabs + Settings + pair chip, on the existing API. Cheap, and everything after lands in it.
2. **Syllabus + Path** — Farsi A1 syllabus first (the motivating case), generate-and-cache per step.
3. **Quiz engine** — exercise types above; Review folds in.
4. **TTS** (from Phase 9) — audio for lessons, stories, cards.
5. **Stories + reader** — graded stories, read-along, script toggle.
6. **Talk** — role-play on the tutor (Phase 6), text first, then voice (STT from Phase 9).
7. **Own-voice + imported audio** — shadowing, recordings, synced transcripts of your audio.

Dictionary grounding (6b), FSRS (10), the diglot reader (6e) and the FME layer (6d) slot in where the above
need them.

## Open questions

- **AI quality locally**: the XPS has no GPU; `qwen2.5:7b` on CPU takes minutes per lesson. Generate-once
  caching helps; is a cloud model (Claude Max / API) acceptable for content generation, with Ollama for
  cheap tasks?
- **TTS for Persian**: is local Piper good enough, or is a cloud voice acceptable?
- **Gamification**: streaks and XP — off, optional, or on?
- **Transliteration scheme** for Farsi (e.g. UniPers vs a simple ASCII scheme).
- **Who uses it**: just you, or also the friend from the Drive share (affects Phase 12 timing)?
