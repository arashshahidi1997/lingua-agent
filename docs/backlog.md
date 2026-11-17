# Backlog

Concrete, near-term items. The phases themselves live in [roadmap.md](roadmap.md); the direction under review
is [product-v2.md](product-v2.md). Tick items in small hunks, committed by path, in the same commit as the
work. Unit in brackets (see `.projio/manager.yml`).

Principle: **always complete, never finished.** *Complete* = already whole: every part there and working
together. *Finished* = no more work needed, which nothing ever is. Make what exists complete before adding
lessons or features; new ideas wait in "Ideas (parked)".

## Complete what exists (first)

- [x] Completeness audit: [audit/2026-11-17-completeness.md](audit/2026-11-17-completeness.md) — 4 decisions, 14 broken, 15 rough, 3 guest items, leftovers
- [x] Work through the audit's A (broken), B (rough) and C (guest) items; D2–D4 as decided
- [ ] Decision D1: Talk's model (local qwen2.5:7b writes wrong Persian; Claude Max, an OpenAI API key, or the Claude API) — **user**
- [ ] Your voice for the existing course: 4 recordings from `content/recording/fa-en-a1/*.html` → Drive folder → split, match, normalise; the app prefers the native clip over Piper [content, core] — recording: **user**
- [ ] Generated lessons ("Your lessons") are poor with `qwen2.5:7b` (see Phase 5b below); either fix or label them clearly as experimental [core]
- [ ] Sara and Ali share one synthetic voice (only `fa_IR-amir` installed) — moot once your voice is in, except for lines not yet recorded [core]
- [ ] Roadmap order still pre-v2 (architecture, clients, playground, README updated 2026-11-17) [docs]

## Now

- [ ] Review the Product v2 proposal and answer its open questions (cloud vs local generation, Persian TTS, gamification, transliteration scheme, audience) [docs] — **user**
- [ ] Phase 5b for en → fa: language-aware prompts. Observed with `qwen2.5:7b` on an A1 lesson: grammar explained English tenses instead of Persian; summary and exercise instructions in Farsi though support was `en`; ungrammatical exercise sentences; gender tag on a Persian noun; vocab lemma instead of the text's form [core]

## Next

- [ ] Native-speaker review of the Farsi A1 course (`src/lingua_agent/course/data/fa-en-a1.yaml`): transliteration of ع, time phrases, the u6 café bill, words used before they're taught (list in the 2026-11-14 handoff) [content] — **user**
- [ ] Try Talk with Ollama `qwen2.5:7b`: turn latency and whether it follows the `TalkTurn` schema; tune `course/talk.py` prompts [core]
- [ ] UI for importing audio from a materials source (`POST /api/audio/from-materials` exists) [web]
- [ ] Daily goal and streak setting stored server-side (today per browser) [core, web]
- [ ] Generated courses: "generate the next unit" with an LLM, cached once, for pairs without a hand-written course [core]
- [ ] A2 course for Farsi; courses for other pairs [content]
- [ ] Install faster-whisper (`.[voice]`) and try transcribing imported audio [config] — **user**

## Ideas (parked)

Not started on purpose: they wait until what exists is complete.

- Persian look: Isfahan tile palette, a girih band, Solar Hijri date, word of the day in Nastaliq, a line of Hafez or Rumi, Persian digits option (mockup 2026-11-17)
- Handwriting: trace letters in their four forms, then short words, with stroke checking
- Clips from films and TV you own, and YouTube embeds with start/end times; synced, corrected subtitles; owner-only for licensed material
- Book excerpts from your own copies (e.g. the بار هستی audiobook), text and audio in sync
- Telegram bot for recording your voice item by item

## Housekeeping

- [ ] mkdocs is not in `.venv`; docs build unchecked since `product-v2.md` and `exclude_docs: log/` were added [docs, config]
- [ ] Drive subset sync from the SSD (command in the memory note `session_state_2026-05-17.md`) — needs the SSD mounted — **user**
- [ ] Ollama on the XPS is CPU-only: ~6 min per lesson with `qwen2.5:7b`; disk at 95% [infra, not lingua] — **user**

## Done

- [x] 2026-11-14 Product v2 first pass: Today / Path / Library / Talk + Settings redesign; Farsi A1 course (8 units, 31 lessons, 8 stories, 8 role-plays); exercise engine (choose, listen, match, order, type); practice and checkpoint quizzes with test-out; stories with play-all and shadowing; recordings and speaking diary; imported audio with synced `.srt`/`.vtt`; Talk with corrections and summary cards; Piper TTS with the `fa_IR-amir-medium` voice
- [x] 2026-11-14 Ollama work committed (`json_schema` output, `OPENAI_TIMEOUT`); pixi setup committed; branch merged into `main`

- [x] 2026-11-14 Ollama wired up: Ollama upgraded to 0.40.16, `qwen2.5:7b` pulled, `.claude/launch.json` serves with Ollama
- [x] 2026-11-14 lingua-manager set up (d22fc85)
